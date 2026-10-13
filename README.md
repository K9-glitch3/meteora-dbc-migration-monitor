# DBC Migration Monitor

DBC Migration Monitor helps Solana developers inspect what happens when a
Meteora Dynamic Bonding Curve graduates to DAMM v2. It follows streamed
account changes, checks migration and pool-role data, calculates supported
prices, and keeps missing or unsupported observations visible.

The product is intended for launchpad builders, trading-terminal developers,
indexers and risk teams that need dependable migration data rather than a
single opaque alert.

## What it does

- Detects supported DBC graduation and migration observations.
- Checks that the expected pool and token roles are connected.
- Applies integer pricing for supported DAMM v2 configurations.
- Compares streamed account state with available chain events.
- Reports unavailable, unsupported and partial observations separately.
- Produces structured evidence that can be reviewed and reproduced.

## Public reviewer package

This repository contains:

- A Python validator for the retained aggregate evidence.
- A static dashboard in `web/`.
- Eleven automated tests covering valid, malformed and unsupported inputs.
- Architecture notes and a prior-work disclosure in `docs/`.

## Development-run evidence

One retained 120-second development run processed 200 account updates:

- 166 had streamed state and a comparable chain swap event.
- 33 transactions were unavailable.
- 1 update did not contain a comparable swap event.
- 132 of the 166 comparable observations produced supported mathematical
  comparisons and matched.
- The remaining 34 were classified as not applicable, unsupported, or skipped
  partial fills and were not counted as matches.

These results describe the retained development run. They are not presented as
customer validation or as an independent audit of the Solana chain.

## Run the checks

Python 3.10 or later is sufficient. No third-party package is required.

```powershell
python -m dbc_monitor evidence/stream_vs_chain_20261001.json
python -m unittest discover -s tests -v
```

Open `web/index.html` directly to view the dashboard.

## Project status

The product is pre-pilot. The next milestone is to test the workflow with a
small group of launchpad, terminal, indexer and risk-tool developers.

The public package does not contain credentials, wallets or private execution
components. The DBC and DAMM v2 technical foundation predates Crypto World's
Fair; the competition-period work is recorded in
`docs/PRIOR_WORK_DISCLOSURE.md`.

## License

Code created for this reviewer package is available under the MIT License.
Third-party software and protocol names remain subject to their own rights and
licences.


