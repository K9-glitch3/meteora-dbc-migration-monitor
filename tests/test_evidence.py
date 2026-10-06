import copy
import json
from pathlib import Path
import unittest

from dbc_monitor import validate_evidence


ROOT = Path(__file__).parents[1]


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(
            (ROOT / "evidence" / "stream_vs_chain_20261001.json").read_text(encoding="utf-8")
        )

    def test_retained_summary_reconciles(self):
        result = validate_evidence(self.data)
        self.assertEqual(result.sampled, 200)
        self.assertEqual(result.comparable_stream_observations, 166)
        self.assertEqual(result.matching_math_comparisons, 132)
        self.assertEqual(result.excluded_math_comparisons, 34)
        self.assertFalse(result.chain_independently_verified)

    def test_each_count_is_required(self):
        keys = (
            "sampled",
            "A_stream_equals_chain",
            "tx_unavailable",
            "no_swap_event (liquidity/fee/other write)",
            "B_math_equals_chain",
            "B_not_applicable",
            "B_unsupported_pool",
            "B_partial_fill_skipped",
        )
        for key in keys:
            with self.subTest(key=key):
                changed = copy.deepcopy(self.data)
                del changed[key]
                with self.assertRaises(ValueError):
                    validate_evidence(changed)

    def test_boolean_is_not_accepted_as_a_count(self):
        self.data["B_not_applicable"] = True
        with self.assertRaises(ValueError):
            validate_evidence(self.data)

    def test_first_stage_must_reconcile(self):
        self.data["sampled"] += 1
        with self.assertRaisesRegex(ValueError, "First-stage"):
            validate_evidence(self.data)

    def test_second_stage_must_reconcile(self):
        self.data["B_math_equals_chain"] += 1
        with self.assertRaisesRegex(ValueError, "Second-stage"):
            validate_evidence(self.data)


if __name__ == "__main__":
    unittest.main()
