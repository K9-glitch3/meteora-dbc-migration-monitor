import base64
import copy
from pathlib import Path
import unittest
from dbc_monitor.quotes import parameters, quote
from dbc_monitor.replay import read_jsonl

ROOT = Path(__file__).resolve().parents[1]


class QuotesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.snapshots = [c for c in read_jsonl(ROOT/"evidence/mainnet-2026-10-16/capture.jsonl") if c["kind"] == "pool_snapshot"]
        cls.supported = []
        for c in cls.snapshots:
            try:
                cls.supported.append((c, parameters(c)))
            except ValueError:
                pass

    def test_exact_supported_population(self):
        self.assertEqual(len(self.supported), 5)

    def test_outputs_are_nonnegative_integers(self):
        for _, p in self.supported:
            for direction in ("AtoB", "BtoA"):
                for amount in (1, 1000, 1000000, 1000000000):
                    answer = quote(p, amount, direction)
                    self.assertGreaterEqual(int(answer["output_amount"]), 0)
                    self.assertGreaterEqual(int(answer["total_fee"]), 0)

    def test_invalid_amounts(self):
        for amount in (0, -1, True, 1.5, 2**64):
            with self.assertRaises(ValueError):
                quote(self.supported[0][1], amount, "AtoB")

    def test_fee_rounds_up(self):
        p = {"sqrt":1<<64, "minimum":1, "maximum":1<<100, "liquidity":10**30, "fee":1, "mode":1}
        self.assertEqual(quote(p, 1, "BtoA")["total_fee"], "1")

    def test_price_range_rejected(self):
        p = {**self.supported[0][1]}
        p["minimum"] = p["sqrt"]
        with self.assertRaises(ValueError):
            quote(p, 10**9, "AtoB")

    def test_negative_controls_change_output(self):
        p = self.supported[0][1]
        original = quote(p, 1000000, "BtoA")
        self.assertNotEqual(original, quote(p, 1000001, "BtoA"))
        self.assertNotEqual(original, quote({**p, "fee":p["fee"]+10000}, 1000000, "BtoA"))

    def test_account_scope_fail_closed(self):
        original = self.supported[0][0]
        for offset, value in [(56,1), (16,2), (22,1), (484,2), (481,1), (482,1), (486,99)]:
            c = copy.deepcopy(original)
            raw = bytearray(base64.b64decode(c["result"]["value"][0]["data"][0]))
            raw[offset] = value
            c["result"]["value"][0]["data"][0] = base64.b64encode(raw).decode()
            with self.assertRaises(ValueError, msg=str(offset)):
                parameters(c)

    def test_mint_and_commitment_binding(self):
        for mutation in ("address", "owner", "commitment"):
            c = copy.deepcopy(self.supported[0][0])
            if mutation == "address": c["addresses"][1] = c["addresses"][2]
            if mutation == "owner": c["result"]["value"][1]["owner"] = "unknown"
            if mutation == "commitment": c["commitment"] = "confirmed"
            with self.assertRaises(ValueError): parameters(c)
