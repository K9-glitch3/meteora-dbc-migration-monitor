import unittest

from dbc_monitor import Observation, Verdict, assess_observation


def observation(**updates):
    values = {
        "transaction_available": True,
        "comparable_swap_event": True,
        "supported_pool_configuration": True,
        "partial_fill": False,
        "stream_matches_chain": True,
        "math_matches_chain": True,
    }
    values.update(updates)
    return Observation(**values)


class BoundaryTests(unittest.TestCase):
    def test_supported_comparison(self):
        self.assertEqual(assess_observation(observation()), Verdict.SUPPORTED_COMPARISON)

    def test_missing_transaction_is_not_success(self):
        verdict = assess_observation(observation(transaction_available=False))
        self.assertEqual(verdict, Verdict.NO_CONCLUSION)

    def test_non_swap_is_not_success(self):
        verdict = assess_observation(observation(comparable_swap_event=False))
        self.assertEqual(verdict, Verdict.NO_CONCLUSION)

    def test_unsupported_pool_stays_explicit(self):
        verdict = assess_observation(observation(supported_pool_configuration=False))
        self.assertEqual(verdict, Verdict.UNSUPPORTED_CONFIGURATION)

    def test_partial_fill_stays_inconclusive(self):
        verdict = assess_observation(observation(partial_fill=True))
        self.assertEqual(verdict, Verdict.NO_CONCLUSION)

    def test_mismatch_is_rejected(self):
        verdict = assess_observation(observation(math_matches_chain=False))
        self.assertEqual(verdict, Verdict.REJECTED_OBSERVATION)


if __name__ == "__main__":
    unittest.main()
