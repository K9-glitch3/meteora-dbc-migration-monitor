"""Bounded, read-only Solana log and pool-account collection."""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from time import monotonic
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

DBC = "dbcij3LWUppWqq96dh6gJWwBifmcGfLSB5D4DuSMaqN"
DAMM = "cpamdpZCGKUy5JxQXB4dcpGPiikHawvSWAd6mEn1sGG"
READ_METHODS = {"getTransaction", "getMultipleAccounts", "getSlot", "getSignatureStatuses", "getSignaturesForAddress"}


def utc_now():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class RpcError(RuntimeError):
    pass


class Rpc:
    def __init__(self, endpoint, timeout=12):
        if urlsplit(endpoint).scheme != "https":
            raise ValueError("RPC endpoint must use HTTPS")
        self.endpoint, self.timeout = endpoint, timeout

    def call(self, method, params):
        if method not in READ_METHODS:
            raise ValueError("Only explicitly permitted read methods are available")
        payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
        request = Request(self.endpoint, payload, {"Content-Type": "application/json", "User-Agent": "DBC-Monitor/0.2"})
        try:
            with urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read(8_000_000))
            if "error" in data:
                raise RpcError("RPC error " + str(data["error"].get("code", "unknown")))
            return data["result"]
        except RpcError:
            raise
        except Exception as exc:
            # Endpoint URLs may contain credentials. Never persist exception text.
            raise RpcError(type(exc).__name__) from None


class Journal:
    def __init__(self, path):
        self.path = Path(path)
        self.handle = self.path.open("x", encoding="utf-8", newline="\n")
        self.sequence = 0

    def write(self, kind, **payload):
        self.sequence += 1
        record = {"capture_version": "1.0", "sequence": self.sequence,
                  "observed_at": utc_now(), "kind": kind, **payload}
        self.handle.write(json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")
        self.handle.flush()
        return record

    def close(self):
        self.handle.close()


async def collect(directory, *, seconds=1800, endpoint=None, ws_endpoint=None,
                  max_pools=4, max_events=20000):
    import websockets
    from .protocol import migrations
    from .recovery import recover
    if not 1 <= seconds <= 3600 or not 1 <= max_pools <= 16 or not 1 <= max_events <= 100000:
        raise ValueError("Run duration/capacity outside bounded limits")
    endpoint = endpoint or os.environ.get("DBC_RPC_URL", "https://api.mainnet-beta.solana.com")
    ws_endpoint = ws_endpoint or os.environ.get("DBC_WS_URL", "wss://api.mainnet-beta.solana.com")
    if urlsplit(ws_endpoint).scheme != "wss":
        raise ValueError("WebSocket endpoint must use WSS")
    rpc = Rpc(endpoint)
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=False)
    journal = Journal(root / "capture.jsonl")
    started = monotonic()
    deadline = started + seconds
    stats = {"log_notifications": 0, "migration_candidates": 0, "pool_notifications": 0,
             "duplicates": 0, "reconnects": 0, "rpc_errors": 0, "queue_overflows": 0}
    seen, pools, finalized = {}, set(), set()
    last_slot = None
    queue = asyncio.Queue(maxsize=64)
    from .replay import code_hash
    journal.write("run_start", collector_code_sha256=code_hash(), duration_seconds=seconds, max_pools=max_pools,
                  max_events=max_events, program=DBC, commitment="confirmed",
                  rpc_host=urlsplit(endpoint).hostname, websocket_host=urlsplit(ws_endpoint).hostname)

    async def snapshot_pools(tx, signature):
        for migration in migrations(tx):
            pool = migration["pool"]
            if len(pools) < max_pools or pool in pools:
                pools.add(pool)
            try:
                snapshot = await asyncio.to_thread(rpc.call, "getMultipleAccounts",
                    [[pool, migration["base_mint"], migration["quote_mint"]],
                     {"encoding": "base64", "commitment": "finalized", "minContextSlot": tx["slot"]}])
                journal.write("pool_snapshot", signature=signature, pool=pool,
                              addresses=[pool, migration["base_mint"], migration["quote_mint"]],
                              commitment="finalized", result=snapshot)
            except RpcError as exc:
                stats["rpc_errors"] += 1
                journal.write("rpc_error", operation="getMultipleAccounts", error=str(exc))

    async def worker():
        while True:
            item = await queue.get()
            try:
                signature, slot = item
                final = None
                for attempt in range(12):
                    try:
                        final = await asyncio.to_thread(rpc.call, "getTransaction", [signature,
                            {"encoding": "json", "commitment": "finalized", "maxSupportedTransactionVersion": 0}])
                        if final is not None:
                            break
                    except RpcError as exc:
                        stats["rpc_errors"] += 1
                        journal.write("rpc_error", operation="getTransaction", error=str(exc))
                    await asyncio.sleep(5)
                journal.write("transaction", signature=signature, notification_slot=slot,
                              commitment="finalized", result=final)
                if final is not None and final["slot"] == slot and final["transaction"]["signatures"][0] == signature:
                    finalized.add(signature)
                    await snapshot_pools(final, signature)
            except (ValueError, KeyError, TypeError, IndexError) as exc:
                journal.write("decode_error", error=type(exc).__name__)
            finally:
                queue.task_done()

    task = asyncio.create_task(worker())
    stop_reason = "interrupted"
    try:
        while monotonic() < deadline and journal.sequence < max_events:
            try:
                async with websockets.connect(ws_endpoint, open_timeout=12, ping_interval=20,
                                               ping_timeout=20, max_size=2**22, max_queue=64) as ws:
                    journal.write("connection_open", epoch=stats["reconnects"])
                    if stats["reconnects"] and last_slot is not None:
                        recovered = await asyncio.to_thread(recover, rpc, max(0, last_slot-64), known=list(finalized), transaction_limit=5)
                        recovered_items = recovered.pop("recovered")
                        recovered["recovered_count"] = len(recovered_items)
                        for item in recovered_items:
                            signature, slot, tx = item["signature"], item["slot"], item["transaction"]
                            if signature in finalized:
                                continue
                            if signature not in seen:
                                seen[signature] = slot
                                journal.write("migration_notification", commitment="finalized", discovery="history_backfill",
                                              result={"context": {"slot": slot}, "value": {"signature": signature, "err": None, "logs": tx["meta"].get("logMessages", [])}})
                            journal.write("transaction", signature=signature, notification_slot=seen[signature], commitment="finalized", result=tx)
                            finalized.add(signature)
                            if seen[signature] == slot:
                                await snapshot_pools(tx, signature)
                        journal.write("recovery_report", **recovered)
                    request_id = 1
                    requests, subscriptions = {1: ("logs", DBC)}, {}
                    subscribed = set()
                    await ws.send(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "logsSubscribe",
                        "params": [{"mentions": [DBC]}, {"commitment": "confirmed"}]}))
                    while monotonic() < deadline and journal.sequence < max_events:
                        for pool in sorted(pools - subscribed):
                            request_id += 1
                            requests[request_id] = ("account", pool)
                            await ws.send(json.dumps({"jsonrpc": "2.0", "id": request_id,
                                "method": "accountSubscribe", "params": [pool, {"encoding": "base64", "commitment": "confirmed"}]}))
                            subscribed.add(pool)
                        try:
                            message = json.loads(await asyncio.wait_for(ws.recv(), timeout=min(3, max(.01, deadline-monotonic()))))
                        except asyncio.TimeoutError:
                            continue
                        if "id" in message:
                            if "error" in message:
                                raise RpcError("Subscription rejected")
                            request = requests.get(message["id"])
                            if request:
                                subscriptions[message["result"]] = request
                                journal.write("subscription", subscription_type=request[0], address=request[1])
                            continue
                        params = message.get("params", {})
                        subscription = subscriptions.get(params.get("subscription"))
                        if not subscription:
                            continue
                        result = params["result"]
                        if subscription[0] == "account":
                            stats["pool_notifications"] += 1
                            journal.write("account_update", pool=subscription[1], commitment="confirmed", result=result)
                            continue
                        stats["log_notifications"] += 1
                        value, slot = result["value"], result["context"]["slot"]
                        last_slot = max(last_slot or 0, slot)
                        if not any(line == "Program log: Instruction: MigrationDammV2" for line in value.get("logs", [])):
                            continue
                        sig = value["signature"]
                        if sig in seen:
                            stats["duplicates"] += 1
                            if seen[sig] != slot:
                                journal.write("slot_conflict", signature=sig, previous_slot=seen[sig], slot=slot)
                            continue
                        seen[sig] = slot
                        stats["migration_candidates"] += 1
                        journal.write("migration_notification", commitment="confirmed", result=result)
                        try:
                            queue.put_nowait((sig, slot))
                        except asyncio.QueueFull:
                            stats["queue_overflows"] += 1
                            journal.write("gap", reason="transaction_queue_full", signature=sig)
            except (OSError, RpcError, ValueError, KeyError, TypeError, websockets.exceptions.WebSocketException) as exc:
                stats["reconnects"] += 1
                journal.write("gap", reason="connection_lost", error=type(exc).__name__, epoch=stats["reconnects"])
                await asyncio.sleep(min(5, max(0, deadline-monotonic())))
        stop_reason = "event_capacity" if journal.sequence >= max_events else "duration_complete"
        try:
            await asyncio.wait_for(queue.join(), timeout=90)
        except asyncio.TimeoutError:
            journal.write("gap", reason="finalization_drain_timeout", pending=queue.qsize())
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        journal.write("run_end", reason=stop_reason, elapsed_seconds=round(monotonic()-started, 3), **stats)
        journal.close()
    return {"directory": str(root), **stats, "reason": stop_reason}
