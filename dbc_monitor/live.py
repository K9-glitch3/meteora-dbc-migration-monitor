"""Continuous, read-only feed with bounded retention and fail-closed health."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import re
import sqlite3
import threading
import uuid

from .collector import collect, utc_now
from .lifecycle import migration_rows
from .records import canonical, derive, digest

ORIGIN = "https://k9-glitch3.github.io"


class RecentSet(dict):
    def add(self, value):
        self[value] = True


def age(timestamp, now=None):
    try:
        delta = (now or datetime.now(timezone.utc)).timestamp() - datetime.fromisoformat(timestamp.replace("Z", "+00:00")).timestamp()
        return delta if delta >= -5 else float("inf")
    except (TypeError, ValueError, AttributeError):
        return float("inf")


class LiveJournal:
    """One writer, locked HTTP readers. Stored records retain their original hashes."""
    def __init__(self, path, *, max_captures=20000, max_observations=5000, max_bytes=24_000_000):
        self.lock = threading.RLock()
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA max_page_count=32768")
        self.db.execute("PRAGMA journal_size_limit=1048576")
        self.db.executescript("""
          CREATE TABLE IF NOT EXISTS captures(id TEXT PRIMARY KEY, payload TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS observations(id TEXT PRIMARY KEY, kind TEXT NOT NULL, capture TEXT NOT NULL, payload TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);
        """)
        self.max_captures, self.max_observations, self.max_bytes = max_captures, max_observations, max_bytes
        self.sequence = 0
        self.epoch = uuid.uuid4().hex
        self.started_at = utc_now()
        self.state = {"finalized_seen": RecentSet(), "account_seen": RecentSet()}
        self.connected = False
        self.subscribed = False
        self.heartbeat = {}
        self.last_error_at = None
        self.resume_slot = self.metadata("last_slot")
        self.write("gap", reason="process_start_coverage_not_established", epoch=self.epoch)

    def metadata(self, key):
        with self.lock:
            row = self.db.execute("SELECT value FROM metadata WHERE key=?", (key,)).fetchone()
            return json.loads(row[0]) if row else None

    def set_metadata(self, key, value):
        with self.lock, self.db:
            self.db.execute("INSERT OR REPLACE INTO metadata VALUES (?,?)", (key, json.dumps(value)))

    def write(self, kind, **payload):
        with self.lock, self.db:
            self.sequence += 1
            record = {"capture_version": "1.0", "sequence": self.sequence, "observed_at": utc_now(), "kind": kind, **payload}
            if len(canonical(record)) > 256_000:
                record = {"capture_version": "1.0", "sequence": self.sequence, "observed_at": record["observed_at"],
                          "kind": "gap", "reason": "oversized_record_not_retained", "original_sha256": digest(record)}
                kind = "gap"
            key = digest(record)
            self.db.execute("INSERT INTO captures VALUES (?,?)", (key, canonical(record).decode()))
            for row in derive([record], _state=self.state):
                self.db.execute("INSERT OR IGNORE INTO observations VALUES (?,?,?,?)",
                                (row["id"], row["kind"], key, canonical(row).decode()))
            for name, mapping in self.state.items():
                if isinstance(mapping, dict):
                    while len(mapping) > 4096:
                        del mapping[next(iter(mapping))]
            if kind == "connection_open":
                self.connected, self.subscribed = True, False
            elif kind == "subscription" and payload.get("subscription_type") == "logs":
                self.subscribed = True
            elif kind == "gap":
                self.last_error_at = record["observed_at"]
                if payload.get("reason") == "connection_lost":
                    self.connected, self.subscribed = False, False
            elif kind in ("rpc_error", "decode_error"):
                self.last_error_at = record["observed_at"]
            elif kind == "heartbeat":
                self.heartbeat = record
                if payload.get("last_slot") is not None:
                    self.db.execute("INSERT OR REPLACE INTO metadata VALUES ('last_slot',?)", (json.dumps(payload["last_slot"]),))
            elif kind == "run_end":
                self.connected, self.subscribed = False, False
            self._prune()
        if self.sequence % 500 == 0:
            with self.lock:
                self.db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        return record

    def _prune(self):
        self.db.execute("DELETE FROM captures WHERE rowid NOT IN (SELECT rowid FROM captures ORDER BY rowid DESC LIMIT ?)", (self.max_captures,))
        self.db.execute("DELETE FROM observations WHERE rowid NOT IN (SELECT rowid FROM observations ORDER BY rowid DESC LIMIT ?)", (self.max_observations,))
        # Byte cap as well as row cap: unusual large RPC responses cannot grow storage indefinitely.
        while self.db.execute("SELECT COALESCE(SUM(LENGTH(payload)),0) FROM captures").fetchone()[0] > self.max_bytes:
            self.db.execute("DELETE FROM captures WHERE rowid IN (SELECT rowid FROM captures ORDER BY rowid LIMIT 25)")

    def health(self, now=None):
        with self.lock:
            h = self.heartbeat
            active = self.connected and self.subscribed and h.get("worker_alive") is True
            fresh = age(h.get("observed_at"), now) <= 15 and age(h.get("last_message_at"), now) <= 30
            status = "live" if active and fresh else "stale" if self.connected else "offline"
            if status == "live" and (age(self.last_error_at, now) < 60 or h.get("pending", 0) >= 32):
                status = "degraded"
            return {"status": status, "generated_at": utc_now(), "started_at": self.started_at,
                    "epoch": self.epoch, "connected": self.connected, "subscribed": self.subscribed,
                    "heartbeat_at": h.get("observed_at"), "last_message_at": h.get("last_message_at"),
                    "last_slot": h.get("last_slot"), "pending": h.get("pending"),
                    "counters": {k: h.get(k, 0) for k in ("log_notifications", "migration_candidates", "pool_notifications", "duplicates", "reconnects", "rpc_errors", "queue_overflows")},
                    "complete_coverage": False, "retention_captures": self.max_captures,
                    "recovery": "bounded migration backfill; pool-update gaps cannot be reconstructed"}

    def feed(self):
        with self.lock:
            observations = [json.loads(row[0]) for row in self.db.execute(
                "SELECT payload FROM observations WHERE kind='migration' ORDER BY rowid DESC LIMIT 2000")][::-1]
            pools = [json.loads(row[0]) for row in self.db.execute(
                "SELECT payload FROM observations WHERE kind='pool_state' ORDER BY rowid DESC LIMIT 20")]
            health_events = [json.loads(row[0]) for row in self.db.execute(
                "SELECT payload FROM observations WHERE kind='health' ORDER BY rowid DESC LIMIT 20")]
            readiness = self.metadata("readiness") or {}
            health = self.health()
            return {"api_version": "2.0", "mode": "continuous_live", "continuous_coverage": False,
                    "generated_at": health["generated_at"], "health": health,
                    "migration_recorded_until": health["last_message_at"],
                    "readiness_recorded_until": readiness.get("ended_at"),
                    "readiness_status": "stale" if age(readiness.get("ended_at")) > 180 else "degraded" if readiness.get("errors") else "sampled",
                    "readiness": readiness.get("items", []), "readiness_errors": readiness.get("errors", []),
                    "migrations": migration_rows(observations)[:250], "pool_states": pools,
                    "health_events": health_events, "limits": {"stale_after_seconds": 30, "poll_seconds": 5,
                    "max_migrations": 250, "readiness_sample_interval_seconds": 90}}

    def evidence(self, identifier):
        with self.lock:
            row = self.db.execute("SELECT payload,capture FROM observations WHERE id=?", (identifier,)).fetchone()
            if not row:
                return None
            capture = self.db.execute("SELECT payload FROM captures WHERE id=?", (row[1],)).fetchone()
            return {"observation": json.loads(row[0]), "capture": json.loads(capture[0]) if capture else None,
                    "capture_retained": capture is not None}

    def close(self):
        self.connected = self.subscribed = False

    def shutdown(self):
        with self.lock:
            self.db.close()


def api_server(journal, port=8898):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.0"

        def setup(self):
            super().setup()
            self.connection.settimeout(3)

        def log_message(self, *args):
            pass  # Do not persist client addresses or arbitrary request paths.

        def do_GET(self):
            path = self.path.split("?", 1)[0]
            if path in ("/healthz", "/v1/feed.json"):
                data = journal.health() if path == "/healthz" else journal.feed()
            elif re.fullmatch(r"/v1/evidence/[a-f0-9]{64}", path):
                data = journal.evidence(path.rsplit("/", 1)[-1])
            else:
                data = None
            code = 200 if data is not None else 404
            body = canonical(data if data is not None else {"error": "not_found_or_expired"})
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store, max-age=0")
            self.send_header("Access-Control-Allow-Origin", ORIGIN)
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'none'")
            self.end_headers()
            if self.command != "HEAD":
                try:
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError):
                    pass

        do_HEAD = do_GET

    # Sequential, short requests bound worker usage. Only this JSON API is exposed.
    return HTTPServer(("127.0.0.1", port), Handler)


async def serve(directory, port=8898, readiness_capture=None):
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    journal = LiveJournal(root / "live.sqlite3")
    server = api_server(journal, port)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    async def readiness_loop():
        while True:
            try:
                receipt = await asyncio.to_thread(readiness_capture)
                journal.set_metadata("readiness", receipt)
            except Exception as exc:
                journal.set_metadata("readiness", {"ended_at": utc_now(), "items": [], "errors": [type(exc).__name__]})
            await asyncio.sleep(90)

    sampler = asyncio.create_task(readiness_loop()) if readiness_capture else None
    try:
        await collect(root, seconds=None, live_journal=journal, resume_slot=journal.resume_slot)
    finally:
        if sampler:
            sampler.cancel()
            await asyncio.gather(sampler, return_exceptions=True)
        server.shutdown()
        server.server_close()
        journal.shutdown()
