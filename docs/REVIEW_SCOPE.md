# Independent review brief

Status: requested, not completed. No independent audit or legal opinion is claimed.

## Technical questions

1. Can malformed/CPI/versioned transaction data produce a false migration identity?
2. Are pool, mint, vault, owner, slot and finality bindings sufficient for the claims?
3. Do replay and capture checksums preserve failed, stale and unsupported outcomes?
4. Can reconnect backfill silently imply complete history when its budget is exhausted?
5. Does the narrow integer quote implementation match the official SDK on identical
   bytes, directions, amounts and static fees, including rounding boundaries?
6. Are readiness flags and threshold ratios distinguishable from transaction proof?
7. Can malicious stored browser input or API data cause injection or misleading alerts?

## Reproduction

Run Python tests and scripts/check_evidence.py. Install reference dependencies with
`npm ci --ignore-scripts`, then run scripts/compare_quotes.py on a frozen capture.
Inspect docs/DEPENDENCIES.md before running the SDK reference tooling. No keys,
wallet, mainnet trades or paid infrastructure are necessary for offline review.

## Licensing questions (separate qualified review)

Check the project's MIT notice, Meteora IDL/math attribution, SDK package licenses,
and the transitive dependency notice inventory. Confirm redistribution obligations
for any later binary/bundled hosted release. Public availability is not proof that
all licensing/IP issues are resolved. No reviewer fee has been agreed.

## Requested output

Record the exact commit, tested scope, exclusions, severity-ranked reproducible
findings and retest result. Permission to name a reviewer is separate from receiving
a reply. Do not infer an audit from an enquiry, quotation or automated test pass.
