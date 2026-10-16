import json
from pathlib import Path
import unittest
from examples.read_feed import summarize
from scripts.build_feed import build

ROOT=Path(__file__).resolve().parents[1]


class PilotTests(unittest.TestCase):
    def test_feed_rebuild_matches_saved(self):
        saved=json.loads((ROOT/"docs/api/v1/feed.json").read_text())
        self.assertEqual(saved,build(ROOT/"evidence"/saved["source_run"],ROOT/"evidence/readiness-2026-10-16.json"))

    def test_client_rejects_unknown_schema(self):
        with self.assertRaises(ValueError):summarize({"api_version":"2.0"})

    def test_client_filter_and_stale_snapshot(self):
        feed=json.loads((ROOT/"docs/api/v1/feed.json").read_text())
        feed["migration_recorded_until"]="2000-01-01T00:00:00Z"
        result=summarize(feed,"unmatched")
        self.assertTrue(result["stale"])
        self.assertEqual(result["matches"],[])

    def test_unavailable_transaction_stays_unresolved(self):
        feed=build(ROOT/"evidence/mainnet-2026-10-16",ROOT/"evidence/readiness-2026-10-16.json")
        unresolved=[r for r in feed["migrations"] if r["reason"]=="finalized_transaction_unavailable"]
        self.assertEqual(len(unresolved),1)
        self.assertEqual(unresolved[0]["stage"],"UNRESOLVED")
