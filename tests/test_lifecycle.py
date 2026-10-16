import unittest
from dbc_monitor.lifecycle import readiness, migration_rows


class LifecycleTests(unittest.TestCase):
    def test_threshold_boundaries_are_not_forecasts(self):
        pool = {"address":"p", "config":"c", "base_mint":"b", "migrated":0}
        config = {"address":"c", "threshold":"1000", "migration_option":1, "quote_mint":"q"}
        for reserve, stage in [(899,"BELOW_THRESHOLD"),(900,"APPROACHING"),(999,"APPROACHING"),(1000,"THRESHOLD_REACHED"),(2000,"THRESHOLD_REACHED")]:
            result = readiness({**pool,"quote_reserve":str(reserve)}, config)
            self.assertEqual(result["stage"], stage)
            self.assertLessEqual(result["progress_bps"], 10000)
        self.assertEqual(readiness({**pool,"migrated":1,"quote_reserve":"0"}, config)["stage"], "MIGRATED_FLAG")

    def test_unknown_config_and_migration_not_promoted(self):
        self.assertEqual(readiness(None, None)["stage"], "UNKNOWN")
        self.assertEqual(readiness({"config":"a"}, {"address":"b"})["stage"], "UNKNOWN")
        self.assertEqual(readiness({"config":"a"}, {"address":"a","migration_option":0})["stage"], "UNSUPPORTED")

    def test_missing_finalized_response_not_finalized_verified(self):
        row = {"kind":"migration", "signature":"s", "pool":None, "stage":"FINALIZED", "verdict":"NO_CONCLUSION",
               "reason":"finalized_transaction_unavailable", "details":{}, "slot":None, "observed_at":"2026-10-16T00:00:00Z", "freshness":"unknown", "id":"x"}
        self.assertEqual(migration_rows([row])[0]["stage"], "UNRESOLVED")

    def test_unknown_and_unsupported_states_preserve_pool_identity(self):
        pool = {"address":"p", "base_mint":"b", "config":"c", "migrated":0,
                "quote_reserve":"100"}
        for config in (None, {"address":"other"},
                       {"address":"c", "migration_option":0},
                       {"address":"c", "migration_option":1, "threshold":"0"}):
            result = readiness(pool, config)
            self.assertIn(result["stage"], ("UNKNOWN", "UNSUPPORTED"))
            self.assertEqual(result["virtual_pool"], "p")
            self.assertEqual(result["base_mint"], "b")
            self.assertNotIn("progress_bps", result)

    def test_stale_identity_is_verified_but_stale(self):
        row = {"kind":"migration", "signature":"s", "pool":"p", "stage":"FINALIZED", "verdict":"NO_CONCLUSION",
               "reason":"migration_outside_freshness_window", "details":{}, "slot":1, "observed_at":"2026-10-16T00:00:00Z", "freshness":"stale", "id":"x"}
        self.assertEqual(migration_rows([row])[0]["stage"], "FINALIZED_VERIFIED")
        self.assertEqual(migration_rows([row])[0]["freshness_at_capture"], "stale")
