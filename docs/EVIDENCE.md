# Evidence notes

## Retained aggregate

The included JSON is a byte-for-byte transcription of the retained aggregate
used in the 2 October 2026 reviewer package. The source snapshot recorded:

- 120 seconds
- 3,156 updates
- 284 pools
- 200 sampled updates
- 166 comparable stream-to-chain observations
- 132 matching supported math comparisons
- no problems listed in the retained aggregate

## What the evidence does not prove

The package does not independently re-query Solana, authenticate the source
account images, establish finality, rerun the original comparator, or expose
the raw transaction-level corpus. It does not establish an unconditional
accuracy rate because unavailable, unsupported, and skipped observations are
not successful comparisons.

No profitability, token-safety, liquidity-safety, or customer-adoption claim is
derived from this evidence.
