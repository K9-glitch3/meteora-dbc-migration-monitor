import unittest
from unittest.mock import Mock
from dbc_monitor.recovery import recover
from fixtures import transaction, SIGNATURE


class RecoveryTests(unittest.TestCase):
    def test_recovers_migration_and_reaches_boundary(self):
        rpc = Mock()
        rpc.call.side_effect = [[{"signature": SIGNATURE, "slot": 100, "err": None}, {"signature": "boundary", "slot": 90}], transaction()]
        result = recover(rpc, 90)
        self.assertTrue(result["complete"])
        self.assertEqual(len(result["recovered"]), 1)

    def test_budget_leaves_history_explicitly_unresolved(self):
        rpc = Mock()
        rpc.call.side_effect = [[{"signature": SIGNATURE, "slot": 100}, {"signature": "second", "slot": 99}, {"signature": "boundary", "slot": 90}], transaction()]
        result = recover(rpc, 90, transaction_limit=1)
        self.assertFalse(result["complete"])
        self.assertEqual(result["unresolved"], 1)

    def test_missing_transaction_or_signature_mismatch_not_recovered(self):
        for tx in [None, {**transaction(), "slot": 99}]:
            rpc = Mock()
            rpc.call.side_effect = [[{"signature": SIGNATURE, "slot": 100}, {"signature": "boundary", "slot": 90}], tx]
            result = recover(rpc, 90)
            self.assertFalse(result["complete"])
            self.assertEqual(result["recovered"], [])

    def test_known_signature_is_not_fetched(self):
        rpc = Mock()
        rpc.call.return_value = [{"signature": SIGNATURE, "slot": 100}, {"signature": "boundary", "slot": 90}]
        result = recover(rpc, 90, known=[SIGNATURE])
        self.assertTrue(result["complete"])
        self.assertEqual(rpc.call.call_count, 1)

    def test_no_boundary_never_complete(self):
        rpc = Mock()
        rpc.call.return_value = []
        self.assertFalse(recover(rpc,90)["complete"])

    def test_rpc_failure_never_complete(self):
        from dbc_monitor.collector import RpcError
        rpc=Mock();rpc.call.side_effect=RpcError("timeout")
        result=recover(rpc,90)
        self.assertFalse(result["complete"])
        self.assertEqual(result["errors"],["RpcError"])

    def test_unordered_history_never_complete(self):
        rpc=Mock();rpc.call.return_value=[{"signature":"first","slot":100,"err":"failed"},{"signature":"second","slot":101,"err":"failed"}]
        self.assertFalse(recover(rpc,90)["complete"])

    def test_invalid_bounds(self):
        for args in ({"since_slot":-1},{"since_slot":True},{"since_slot":90,"transaction_limit":0},{"since_slot":90,"signature_limit":1001}):
            with self.assertRaises(ValueError):recover(Mock(),**args)
