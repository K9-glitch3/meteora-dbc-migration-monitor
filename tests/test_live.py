import json
import asyncio
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from dbc_monitor.collector import utc_now
from dbc_monitor.live import LiveJournal, api_server
from dbc_monitor.records import derive, digest
from fixtures import transaction, SIGNATURE
from unittest.mock import patch


class LiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name)/"live.sqlite3"
        self.j = LiveJournal(self.path)

    def tearDown(self):
        self.j.shutdown()
        self.temp.cleanup()

    def activate(self):
        self.j.write("connection_open")
        self.j.write("subscription", subscription_type="logs")
        self.j.last_error_at = None
        self.j.write("heartbeat", last_message_at=utc_now(), last_slot=123, worker_alive=True, pending=0)

    def test_health_requires_upstream_and_worker(self):
        self.assertEqual(self.j.health()["status"], "offline")
        self.activate()
        self.assertEqual(self.j.health()["status"], "live")
        self.j.heartbeat["last_message_at"] = "2020-01-01T00:00:00Z"
        self.assertEqual(self.j.health()["status"], "stale")
        self.activate()
        self.j.heartbeat["worker_alive"] = False
        self.assertEqual(self.j.health()["status"], "stale")
        self.activate()
        self.j.write("gap", reason="connection_lost")
        self.assertEqual(self.j.health()["status"], "offline")

    def test_future_or_invalid_clock_fails_closed(self):
        self.activate()
        for time in ["2999-01-01T00:00:00Z", "bad", None]:
            self.j.heartbeat["last_message_at"] = time
            self.assertEqual(self.j.health()["status"], "stale")

    def test_rpc_errors_and_backlog_degrade(self):
        self.activate()
        self.j.write("rpc_error", operation="getTransaction")
        self.assertEqual(self.j.health()["status"], "degraded")
        self.activate()
        self.j.heartbeat["pending"] = 32
        self.assertEqual(self.j.health()["status"], "degraded")

    def test_incremental_derivation_matches_batch_and_hashes(self):
        self.j.write("migration_notification", commitment="confirmed",
                     result={"context":{"slot":100},"value":{"signature":SIGNATURE,"err":None,"logs":[]}})
        self.j.write("transaction", signature=SIGNATURE, notification_slot=100, commitment="finalized", result=transaction())
        captures=[json.loads(r[0]) for r in self.j.db.execute("SELECT payload FROM captures ORDER BY rowid")]
        expected=derive(captures)
        actual=[json.loads(r[0]) for r in self.j.db.execute("SELECT payload FROM observations ORDER BY rowid")]
        self.assertEqual(actual, expected)
        row=self.j.feed()["migrations"][0]
        self.assertEqual(row["stage"], "FINALIZED_VERIFIED")
        for identifier in row["evidence_ids"]:
            evidence=self.j.evidence(identifier)
            self.assertEqual(digest(evidence["capture"]),evidence["observation"]["capture_sha256"])

    def test_row_and_byte_retention_and_state_are_bounded(self):
        self.j.max_captures=30
        self.j.max_observations=20
        self.j.max_bytes=2000
        for _ in range(100):
            self.j.write("gap", reason="injected", padding="x"*100)
        self.assertLessEqual(self.j.db.execute("SELECT COUNT(*) FROM captures").fetchone()[0],30)
        self.assertLessEqual(self.j.db.execute("SELECT SUM(LENGTH(payload)) FROM captures").fetchone()[0],2000)
        self.assertLessEqual(self.j.db.execute("SELECT COUNT(*) FROM observations").fetchone()[0],20)
        self.j.state["notifications"]={str(i):i for i in range(5000)}
        self.j.write("heartbeat")
        self.assertLessEqual(len(self.j.state["notifications"]),4096)

    def test_oversized_record_is_explicit_gap(self):
        row=self.j.write("unknown", value="x"*300000)
        self.assertEqual(row["reason"],"oversized_record_not_retained")
        self.assertIn("original_sha256",row)

    def test_restart_retains_watermark_but_not_live_health(self):
        self.activate()
        self.j.shutdown()
        self.j=LiveJournal(self.path)
        self.assertEqual(self.j.resume_slot,123)
        self.assertEqual(self.j.health()["status"],"offline")
        self.assertFalse(self.j.health()["complete_coverage"])
        self.assertEqual(self.j.feed()["mode"],"continuous_live")

    def test_readiness_stale_separately(self):
        self.activate()
        self.j.set_metadata("readiness",{"ended_at":"2020-01-01T00:00:00Z","items":[],"errors":[]})
        feed=self.j.feed()
        self.assertEqual(feed["health"]["status"],"live")
        self.assertEqual(feed["readiness_status"],"stale")

    def test_live_example_client_rejects_stale_and_degraded(self):
        from examples.read_feed import summarize
        self.activate()
        feed=self.j.feed()
        self.assertFalse(summarize(feed)["stale"])
        feed["health"]["status"]="degraded"
        self.assertTrue(summarize(feed)["stale"])
        feed["health"]["status"]="live"
        feed["health"]["heartbeat_at"]="2020-01-01T00:00:00Z"
        self.assertTrue(summarize(feed)["stale"])

    def test_api_allowlist_cors_cache_and_no_write_routes(self):
        server=api_server(self.j,0)
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        base="http://127.0.0.1:"+str(server.server_port)
        try:
            with urlopen(base+"/v1/feed.json") as r:
                self.assertEqual(r.headers["Access-Control-Allow-Origin"],"https://k9-glitch3.github.io")
                self.assertIn("no-store",r.headers["Cache-Control"])
                self.assertEqual(json.load(r)["mode"],"continuous_live")
            for path in ["/", "/../package.json", "/v1/evidence/"+"a"*64, "/?url=https://example.com"]:
                with self.assertRaises(HTTPError) as error:
                    urlopen(base+path)
                self.assertEqual(error.exception.code,404)
                error.exception.close()
            with self.assertRaises(HTTPError) as error:
                urlopen(Request(base+"/v1/feed.json",data=b"{}",method="POST"))
            self.assertEqual(error.exception.code,501)
            error.exception.close()
        finally:
            server.shutdown();server.server_close();thread.join()


class ContinuousCollectorTests(unittest.IsolatedAsyncioTestCase):
    async def test_continuous_ignores_snapshot_cap_and_recovers_restart_watermark(self):
        from dbc_monitor.collector import collect
        ticks=[0]
        def clock():
            ticks[0]+=1
            return ticks[0]
        class Socket:
            def __init__(self):
                self.messages=[{"id":1,"result":10}]+[
                    {"params":{"subscription":10,"result":{"context":{"slot":200+i},"value":{"signature":"unused","logs":[]}}}}
                    for i in range(20)]
            async def __aenter__(self):return self
            async def __aexit__(self,*args):pass
            async def send(self,value):pass
            async def recv(self):
                if self.messages:return json.dumps(self.messages.pop(0))
                raise asyncio.CancelledError()
        with tempfile.TemporaryDirectory() as tmp:
            journal=LiveJournal(Path(tmp)/"live.sqlite3")
            try:
                with patch("websockets.connect",return_value=Socket()),patch("dbc_monitor.collector.monotonic",side_effect=clock),patch("dbc_monitor.recovery.recover",return_value={"recovered":[],"complete":False,"reason":"budget"}) as recovery:
                    with self.assertRaises(asyncio.CancelledError):
                        await collect(tmp,seconds=None,max_events=1,live_journal=journal,resume_slot=150)
                self.assertGreater(journal.sequence,1)
                self.assertGreater(journal.heartbeat["log_notifications"],10)
                self.assertEqual(recovery.call_args.args[1],86)
                self.assertFalse(journal.health()["complete_coverage"])
                events=journal.feed()["health_events"]
                self.assertTrue(any(r["reason"]=="budget" and r["details"]["complete"] is False for r in events))
            finally:
                journal.shutdown()
