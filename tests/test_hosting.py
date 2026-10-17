import tempfile
import unittest
from pathlib import Path
from dbc_monitor.live import LiveJournal, api_server


class HostingTests(unittest.TestCase):
    def test_public_endpoint_allowlist(self):
        from examples.read_feed import live_endpoint
        for host in ("dbc-monitor.188-166-88-35.sslip.io", "old.trycloudflare.com"):
            self.assertEqual(live_endpoint({"enabled": True, "endpoint": "https://" + host}),
                             "https://" + host + "/v1/feed.json")
        for url in ("", "http://dbc-monitor.188-166-88-35.sslip.io", "https://127.0.0.1",
                    "https://evil.sslip.io", "https://old.trycloudflare.com.evil.com",
                    "https://user:secret@old.trycloudflare.com", "https://old.trycloudflare.com:9999",
                    "https://old.trycloudflare.com/path", "https://old.trycloudflare.com/?x=y",
                    "https://old.trycloudflare.com/#fragment"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                live_endpoint({"enabled": True, "endpoint": url})

    def test_loopback_remains_default_and_container_bind_is_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            journal = LiveJournal(Path(directory) / "live.sqlite3")
            try:
                for requested, expected in ((None, "127.0.0.1"), ("0.0.0.0", "0.0.0.0")):
                    server = api_server(journal, 0) if requested is None else api_server(journal, 0, requested)
                    try:
                        self.assertEqual(server.server_address[0], expected)
                    finally:
                        server.server_close()
                with self.assertRaises(ValueError):
                    api_server(journal, 0, "example.com")
            finally:
                journal.shutdown()

    def test_restart_retains_evidence_and_watermark(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "live.sqlite3"
            first = LiveJournal(path)
            first.set_metadata("last_slot", 123456)
            identifier = first.feed()["health_events"][0]["id"]
            evidence = first.evidence(identifier)
            epoch = first.epoch
            first.shutdown()
            second = LiveJournal(path)
            try:
                self.assertEqual(second.resume_slot, 123456)
                self.assertEqual(second.evidence(identifier), evidence)
                self.assertNotEqual(second.epoch, epoch)
                self.assertEqual(second.health()["status"], "offline")
            finally:
                second.shutdown()
