"""Explicit support boundary for reviewer-facing migration observations."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Verdict(str, Enum):
    SUPPORTED_COMPARISON = "SUPPORTED_COMPARISON"
    NO_CONCLUSION = "NO_CONCLUSION"
    UNSUPPORTED_CONFIGURATION = "UNSUPPORTED_CONFIGURATION"
    REJECTED_OBSERVATION = "REJECTED_OBSERVATION"


@dataclass(frozen=True)
class Observation:
    transaction_available: bool
    comparable_swap_event: bool
    supported_pool_configuration: bool
    partial_fill: bool
    stream_matches_chain: bool | None = None
    math_matches_chain: bool | None = None


def assess_observation(observation: Observation) -> Verdict:
    """Classify an observation without converting absence into validation."""

    if not observation.transaction_available or not observation.comparable_swap_event:
        return Verdict.NO_CONCLUSION
    if not observation.stream_matches_chain:
        return Verdict.REJECTED_OBSERVATION
    if not observation.supported_pool_configuration:
        return Verdict.UNSUPPORTED_CONFIGURATION
    if observation.partial_fill:
        return Verdict.NO_CONCLUSION
    if observation.math_matches_chain is not True:
        return Verdict.REJECTED_OBSERVATION
    return Verdict.SUPPORTED_COMPARISON
