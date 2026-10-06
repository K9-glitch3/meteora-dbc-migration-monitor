# DBC Migration Monitor

An evidence-first reviewer package for Meteora DBC to DAMM v2 migration tooling.

The private prototype detects migration candidates, checks pool-role bindings,
tracks supported DAMM v2 account state, and applies integer quote arithmetic.
This public package exposes the verification model and retained aggregate
evidence without shipping wallets, signers, trade execution, private strategy,
or credentials.

## What is included

- A standard-library Python validator for the retained aggregate evidence.
- An explicit verdict model that refuses to turn missing evidence into success.
- Unit tests for valid, malformed, and unsupported observations.
- A static reviewer dashboard in `web/`.
- Architecture, evidence, and prior-work disclosures in `docs/`.

## Recorded evidence

The retained 120-second internal run sampled 200 account updates:

- 166 had matching streamed state and a comparable chain swap event.
- 33 transactions were unavailable.
- 1 update did not contain a comparable swap event.
- Of the 166 comparable observations, 132 math comparisons matched.
- The other 34 were not applicable, unsupported, or skipped partial fills.

These are recorded internal results, not a fresh independent chain audit. The
coverage exclusions are not counted as successful comparisons. No claim of
profitability, token safety, finality, customer adoption, or complete Meteora
feature support is made.

## Run the checks

Python 3.10 or later is sufficient. No third-party package is required.

```powershell
python -m dbc_monitor evidence/stream_vs_chain_20261001.json
python -m unittest discover -s tests -v
```

Open `web/index.html` directly for the static evidence dashboard.

## Scope boundary

This repository is a reviewer-facing reference package, not a trading system,
an RPC service, a live market-data promise, or an SDK-equivalence claim. The
full private implementation and raw validation corpus remain outside this
repository pending licensing, attribution, and reviewer-access decisions.

## Development disclosure

The DBC/DAMM v2 foundation predates the Crypto World's Fair competition. Work
recorded during the competition period included keeper-ticket integration,
streamed-state pricing, comparison evidence, latency work, and this bounded
reviewer package. See `docs/PRIOR_WORK_DISCLOSURE.md`.

## License

The code created specifically for this reviewer package is provided under the
MIT License. That license does not grant rights to excluded private code,
Meteora software, Solana software, or third-party material.
