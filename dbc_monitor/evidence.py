"""Validate retained aggregate evidence without asserting chain truth."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping


_COUNT_FIELDS = (
    "sampled",
    "A_stream_equals_chain",
    "tx_unavailable",
    "no_swap_event (liquidity/fee/other write)",
    "B_math_equals_chain",
    "B_not_applicable",
    "B_unsupported_pool",
    "B_partial_fill_skipped",
)


@dataclass(frozen=True)
class EvidenceSummary:
    aggregate_accounting: str
    sampled: int
    comparable_stream_observations: int
    matching_math_comparisons: int
    unavailable_transactions: int
    non_swap_updates: int
    excluded_math_comparisons: int
    reported_problem_count: int
    chain_independently_verified: bool = False
    profitability_or_safety_conclusion: str = "NONE"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _count(data: Mapping[str, Any], key: str) -> int:
    value = data.get(key)
    if type(value) is not int or value < 0:
        raise ValueError(f"Missing or invalid non-negative integer: {key}")
    return value


def validate_evidence(data: Mapping[str, Any]) -> EvidenceSummary:
    """Check accounting identities and return a deliberately bounded summary."""

    if not isinstance(data, Mapping):
        raise TypeError("Evidence must be a mapping")

    counts = {key: _count(data, key) for key in _COUNT_FIELDS}
    problems = data.get("problems")
    if not isinstance(problems, list):
        raise ValueError("Missing problems list")

    stream_total = (
        counts["A_stream_equals_chain"]
        + counts["tx_unavailable"]
        + counts["no_swap_event (liquidity/fee/other write)"]
    )
    if stream_total != counts["sampled"]:
        raise ValueError("First-stage comparison accounting does not reconcile")

    excluded = (
        counts["B_not_applicable"]
        + counts["B_unsupported_pool"]
        + counts["B_partial_fill_skipped"]
    )
    if counts["B_math_equals_chain"] + excluded != counts["A_stream_equals_chain"]:
        raise ValueError("Second-stage math accounting does not reconcile")

    return EvidenceSummary(
        aggregate_accounting="CONSISTENT",
        sampled=counts["sampled"],
        comparable_stream_observations=counts["A_stream_equals_chain"],
        matching_math_comparisons=counts["B_math_equals_chain"],
        unavailable_transactions=counts["tx_unavailable"],
        non_swap_updates=counts["no_swap_event (liquidity/fee/other write)"],
        excluded_math_comparisons=excluded,
        reported_problem_count=len(problems),
    )
