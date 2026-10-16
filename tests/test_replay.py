import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from dbc_monitor.collector import Rpc, RpcError, Journal
from dbc_monitor.records import canonical
from dbc_monitor.replay import build, verify, replay, export
from fixtures import captures


class ReplayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root/"capture.jsonl").write_bytes(b"".join(canonical(r)+b"\n" for r in captures()))

    def tearDown(self): self.temp.cleanup()

    def test_replay_and_export(self):
        manifest = build(self.root, source="synthetic_test")
        self.assertEqual(manifest["observations"],4)
        self.assertTrue(verify(self.root)["verified"])
        self.assertEqual(replay(self.root,source="synthetic_test"), replay(self.root,source="synthetic_test"))
        export(self.root,self.root/"view.json")
        self.assertEqual(len(json.loads((self.root/"view.json").read_text())["observations"]),4)

    def test_frozen_run_cannot_be_overwritten(self):
        build(self.root)
        with self.assertRaises(ValueError): build(self.root)

    def test_capture_tampering(self):
        build(self.root)
        with (self.root/"capture.jsonl").open("a") as f: f.write("{}\n")
        with self.assertRaisesRegex(ValueError,"Checksum"): verify(self.root)

    def test_observation_tampering(self):
        build(self.root)
        (self.root/"observations.jsonl").write_text("{}\n")
        with self.assertRaisesRegex(ValueError,"Checksum"): verify(self.root)

    def test_manifest_totals_tampering(self):
        build(self.root)
        path = self.root/"manifest.json"; manifest = json.loads(path.read_text()); manifest["observations"] = 100
        path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError,"totals"): verify(self.root)

    def test_incomplete_capture_not_frozen(self):
        (self.root/"capture.jsonl").write_bytes(b"".join(canonical(r)+b"\n" for r in captures()[:-1]))
        with self.assertRaisesRegex(ValueError,"incomplete"): build(self.root)

    def test_manifest_timestamps_and_scope_cannot_be_changed(self):
        build(self.root)
        path = self.root/"manifest.json"
        original = json.loads(path.read_text())
        for key,value in [("started_at","2020-01-01T00:00:00Z"),("comparison_scope","all swap prices verified")]:
            manifest = {**original,key:value}
            path.write_text(json.dumps(manifest))
            with self.assertRaises(ValueError): verify(self.root)

    def test_read_only_rpc_allowlist(self):
        for method in ["sendTransaction","requestAirdrop","simulateTransaction"]:
            with self.assertRaises(ValueError): Rpc("https://example.com").call(method,[])

    def test_endpoint_errors_do_not_leak_tokens(self):
        with patch("dbc_monitor.collector.urlopen",side_effect=OSError("https://example.com/?api-key=SECRET")):
            with self.assertRaises(RpcError) as caught: Rpc("https://example.com/?api-key=SECRET").call("getSlot",[])
            self.assertNotIn("SECRET",str(caught.exception))

    def test_journal_is_append_only_and_sequence_is_stable(self):
        path = self.root/"new.jsonl"; j = Journal(path)
        j.write("one"); j.write("two"); j.close()
        self.assertEqual([json.loads(x)["sequence"] for x in path.read_text().splitlines()],[1,2])
        with self.assertRaises(FileExistsError): Journal(path)
