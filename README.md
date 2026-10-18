# DBC Migration Monitor

[Live monitor](https://k9-glitch3.github.io/meteora-dbc-migration-monitor/) |
[Historical evidence](https://k9-glitch3.github.io/meteora-dbc-migration-monitor/evidence.html) |
[Build updates](https://k9-glitch3.github.io/meteora-dbc-migration-monitor/updates.html) |
[CI](https://github.com/K9-glitch3/meteora-dbc-migration-monitor/actions/workflows/ci.yml)

Read-only developer tooling for Meteora DBC migrations to DAMM v2. Version 0.4
adds a continuous mainnet collector, public live JSON API, five-second browser
refresh, separate freshness/health indicators, and bounded durable retention.
Version 0.4.2 runs continuously on an independent remote server, with persistent
storage, automatic restart and HTTPS. It does not need my PC or browser to remain
on. This reuses existing paid hosting without a new subscription; no uptime SLA
or complete chain coverage is claimed.

[Open watchlist](https://k9-glitch3.github.io/meteora-dbc-migration-monitor/monitor.html) |
[Developer pilot](https://k9-glitch3.github.io/meteora-dbc-migration-monitor/pilot.html) |
[Live endpoint discovery](https://k9-glitch3.github.io/meteora-dbc-migration-monitor/live-config.json)

[One-minute walkthrough](https://k9-glitch3.github.io/meteora-dbc-migration-monitor/updates.html#walkthrough) |
[Continuation plan](docs/CONTINUATION.md)

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
are atomic-unit ratios. A separate v0.3 report compares a deliberately narrow
static-fee, standard-SPL, concentrated-liquidity quote scope with the official SDK
on identical captured bytes. This is not an external audit or execution evidence.

## Developer workflow and reference checks

The watchlist supports browser-local saved addresses, stage filters, evidence links
and local activity. The default view uses the continuous stream; the historical
v1 API remains recorded evidence, not a live fallback. Live v2 reports upstream
message time, heartbeat, queue depth, errors, pool states and retained evidence.
Readiness is resampled separately, not represented as a complete pool stream.
No background email/push/webhook alerts or uptime SLA are offered in this pilot.

```powershell
python examples/read_feed.py
npm ci --ignore-scripts
python scripts/compare_quotes.py evidence/mainnet-2026-10-16/capture.jsonl runs/quotes.json
python scripts/capture_readiness.py runs/readiness.json
```

Read [dependency limitations](docs/DEPENDENCIES.md) before installing the offline
reference SDKs. The vulnerable bigint-buffer package has been replaced with a
bounded, independently implemented pure-JavaScript adapter. Clean install and
audit report zero known vulnerabilities as of 17 October 2026; this is not an audit
of the project. The readiness sampler invokes the pinned SDK decoder locally.
The public API exposes no input-to-SDK, signing, proxy or filesystem route.

See [live operations](docs/LIVE_OPERATIONS.md) for the PC dependency, restart,
endpoint publication, retention and recovery limits.

See the [pilot contract](docs/PILOT.md) and [independent review brief](docs/REVIEW_SCOPE.md).
Three invitations and a review enquiry have been sent; acceptance, integration,
repeat use and independent validation remain unconfirmed.

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
