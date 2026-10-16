# DBC Migration Monitor

[Evidence explorer](https://k9-glitch3.github.io/meteora-dbc-migration-monitor/) |
[Build updates](https://k9-glitch3.github.io/meteora-dbc-migration-monitor/updates.html) |
[CI](https://github.com/K9-glitch3/meteora-dbc-migration-monitor/actions/workflows/ci.yml)

Read-only developer tooling for Meteora DBC migrations to DAMM v2. Version 0.2
adds bounded Solana collection, transaction-level evidence, deterministic replay
and an interactive evidence explorer.

## Implemented
- Versioned JSON observations: source, slot, commitment, freshness, verdict,
  scope, reason and capture hash.
- Confirmed migration discovery followed by finalized transaction lookups.
- Top-level/CPI decoding, loaded addresses and pool/mint/vault-role checks.
- Pool-state decoding with exact integer-derived price ratios.
- Reconnection, signature deduplication, duplicate-account detection, slot
  conflicts, out-of-order handling and explicit gaps.
- Frozen captures, SHA-256 manifests and deterministic offline replay.
- Search, filters, pagination, details, explorer links and JSON download.
- Windows/Linux CI on Python 3.10 and 3.12.

**Scope:** in the new schema, `SUPPORTED_COMPARISON` means a fresh finalized
**migration identity** matched its notification and supported instruction.
It does not mean a swap quote, profitable trade or secure token. Pool prices
are atomic-unit ratios, not independently verified swap quotes.

## Install and verify
Python 3.10 or later:
```powershell
python -m pip install .
python -m unittest discover -s tests -v
python scripts/check_evidence.py
python -m dbc_monitor verify evidence/synthetic-v1
```

Verification recomputes observations from captured responses and checks hashes
and totals without network access. `same_code: false` means the replay source
changed since freezing, not that the evidence failed verification.

## Collect a bounded sample
```powershell
python -m dbc_monitor collect runs/my-run --seconds 1800 --max-pools 4
python -m dbc_monitor replay runs/my-run
python -m dbc_monitor verify runs/my-run
python -m dbc_monitor export runs/my-run my-run.json
```

Defaults use Solana public mainnet HTTPS/WSS endpoints. Optional environment
variables `DBC_RPC_URL` and `DBC_WS_URL` select a provider. Never commit
credentials. Captures retain hosts, not credential-bearing URLs. RPC methods are
read-only allowlisted. There is no wallet, signing or transaction submission.

Collection is followed by up to 90 seconds of queued finalization drain.
Rate limits, missing transactions and gaps remain visible. Coverage is not
exhaustive.

## Evidence
- New frozen runs: `evidence/<run>/capture.jsonl`, observations and manifest.
- Explicit synthetic tests: `evidence/synthetic-v1/`.
- Original private-prototype aggregate: `evidence/stream_vs_chain_20261001.json`.
  Its 200 updates / 132 matches are historical aggregate claims, not
  transaction-level proof or results produced by this public collector.

See [architecture](docs/ARCHITECTURE.md), [supported scope](docs/SUPPORTED_SCOPE.md)
and [prior-work disclosure](docs/PRIOR_WORK_DISCLOSURE.md).
Pre-pilot, not independently audited or production-certified.

## Local explorer
The page fetches JSON and must be served over HTTP:
```powershell
python -m http.server 8897 --bind 127.0.0.1 --directory docs
```
Open http://127.0.0.1:8897/. The page shows recorded evidence, not a live stream.

## License
Original code is MIT licensed. Pinned Meteora SDK IDL definitions are MIT
licensed with attribution in `docs/METEORA_SDK_LICENSE.txt`.
