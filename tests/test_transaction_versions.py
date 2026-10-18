import copy
import unittest
from unittest.mock import Mock, patch

from dbc_monitor.collector import RpcError
from dbc_monitor.protocol import account_keys, migrations, DBC, MAX_SUPPORTED_TRANSACTION_VERSION
from dbc_monitor.recovery import recover
from scripts.capture_readiness import capture
from fixtures import transaction, SIGNATURE, KEYS


def versioned(version):
    tx = transaction()
    tx["version"] = version
    if version == 1:
        tx["transaction"]["message"]["transactionConfig"] = {}
        del tx["meta"]["loadedAddresses"]
    return tx


class TransactionVersionTests(unittest.TestCase):
    def test_legacy_v0_v1_decode_same_migration_identity(self):
        expected = migrations(transaction())
        for version in ("legacy", 0, 1):
            tx = versioned(version)
            original = copy.deepcopy(tx)
            self.assertEqual(migrations(tx), expected)
            self.assertEqual(account_keys(tx), KEYS + [DBC])
            self.assertEqual(tx, original)

    def test_v0_lookup_order_is_preserved(self):
        tx = versioned(0)
        tx["transaction"]["message"]["accountKeys"] = KEYS[:20]
        tx["meta"]["loadedAddresses"] = {"writable": KEYS[20:], "readonly": [DBC]}
        self.assertEqual(migrations(tx), migrations(transaction()))

    def test_v1_inner_migration_and_null_loaded_addresses(self):
        tx = versioned(1)
        ix = tx["transaction"]["message"]["instructions"].pop()
        tx["meta"]["loadedAddresses"] = None
        tx["meta"]["innerInstructions"] = [{"index": 0, "instructions": [ix]}]
        self.assertEqual(migrations(tx)[0]["instruction"], "inner:0:0")

    def test_future_or_invalid_versions_fail_closed(self):
        for version in (2, -1, True, False, "1", None, 1.0):
            with self.subTest(version=version), self.assertRaises(ValueError):
                account_keys(versioned(version))

    def test_v1_lookup_tables_are_rejected(self):
        tx = versioned(1)
        tx["meta"]["loadedAddresses"] = {"readonly": [DBC]}
        with self.assertRaises(ValueError):
            account_keys(tx)
        tx["meta"]["loadedAddresses"] = {}
        tx["transaction"]["message"]["addressTableLookups"] = [{"accountKey": DBC}]
        with self.assertRaises(ValueError):
            account_keys(tx)

    def test_malformed_keys_and_instruction_indices_are_rejected(self):
        for bad in ("not-a-list", ["invalid"], [{"pubkey": DBC}]):
            tx = versioned(1)
            tx["transaction"]["message"]["accountKeys"] = bad
            with self.assertRaises(ValueError):
                migrations(tx)
        tx = versioned(1)
        tx["transaction"]["message"]["instructions"][0]["programIdIndex"] = 99
        with self.assertRaises(ValueError):
            migrations(tx)

    def test_recovery_requests_v1_and_rejects_future_versions(self):
        for version in ("legacy", 0, 1, 2):
            rpc = Mock()
            rpc.call.side_effect = [[{"signature": SIGNATURE, "slot": 100},
                                     {"signature": "boundary", "slot": 90}], versioned(version)]
            result = recover(rpc, 90)
            self.assertEqual(result["complete"], version != 2)
            self.assertEqual(len(result["recovered"]), int(version != 2))
            options = rpc.call.call_args_list[1].args[1][1]
            self.assertEqual(options["maxSupportedTransactionVersion"], 1)
            self.assertIs(type(options["maxSupportedTransactionVersion"]), int)

    def readiness_capture(self, transactions):
        rpc = Mock()
        calls = []
        pending = iter(transactions)
        def call(method, params):
            calls.append((method, params))
            if method == "getSignaturesForAddress":
                return [{"signature": SIGNATURE, "err": None} for _ in transactions]
            if method == "getTransaction":
                self.assertEqual(params[1], {"commitment": "finalized", "encoding": "json",
                                            "maxSupportedTransactionVersion": 1})
                tx = next(pending)
                if isinstance(tx, Exception):
                    raise tx
                return tx
            return {"context": {"slot": 101}, "value": [None for _ in params[0]]}
        rpc.call.side_effect = call
        pool = {"address": KEYS[0], "config": KEYS[2], "base_mint": KEYS[13],
                "migrated": 0, "quote_reserve": "950"}
        config = {"address": KEYS[2], "threshold": "1000", "migration_option": 1, "quote_mint": KEYS[14]}
        with patch("scripts.capture_readiness.Rpc", return_value=rpc), \
             patch("scripts.capture_readiness.time.sleep"), \
             patch("scripts.capture_readiness.decode", side_effect=[[pool], [pool], [config]]) as decoder:
            result = capture()
        return result, calls, decoder

    def test_readiness_v1_runs_account_and_config_pipeline(self):
        self.assertEqual(MAX_SUPPORTED_TRANSACTION_VERSION, 1)
        result, calls, decoder = self.readiness_capture([versioned(1)])
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["items"][0]["stage"], "APPROACHING")
        self.assertEqual(result["items"][0]["progress_bps"], 9500)
        self.assertEqual(result["items"][0]["slot"], 101)
        self.assertEqual(calls[2][1][0], KEYS + [DBC])
        self.assertEqual(decoder.call_count, 3)

    def test_readiness_retains_good_samples_but_reports_bad_transactions(self):
        for bad, expected in ((None, "transaction_unavailable"),
                              (RpcError("RPC error -32015"), "RPC error -32015"),
                              (versioned(2), "ValueError"), ({}, "KeyError")):
            result, _, _ = self.readiness_capture([bad, versioned(1)])
            self.assertEqual(result["errors"], [expected])
            self.assertEqual(len(result["items"]), 1)

    def test_readiness_checks_signature_and_execution_success(self):
        bad = versioned(1)
        bad["transaction"]["signatures"] = ["different"]
        failed = versioned(1)
        failed["meta"]["err"] = {"InstructionError": [0, "failed"]}
        for tx in (bad, failed):
            result, _, _ = self.readiness_capture([tx, versioned(1)])
            self.assertEqual(result["errors"], ["ValueError"])
            self.assertEqual(len(result["items"]), 1)
