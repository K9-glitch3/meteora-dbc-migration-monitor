# DBC Migration Monitor v0.3.0

I am continuing development independently of the Colosseum outcome. This release
is dated post-submission work and does not rewrite the original submission period.

## Shipped

- Browser-local watchlists, stage filtering, deduplicated recorded activity and
  transaction/raw-evidence inspection, verified on desktop and mobile.
- Versioned read API with separate migration/readiness timestamps and explicit
  stale-data handling. It is a manually refreshed recorded feed, not 24/7 hosting.
- Same-context readiness samples, distinct from finalized migration identity.
- Narrow static-fee, standard-SPL exact-input quote checks against the pinned
  official SDK: 40 matches in the earlier sample and 80 in the one-hour sample,
  zero mismatches in those supported cases. Exclusions remain visible.
- Budgeted reconnect history recovery and fail-closed missing-metadata handling.
- Frozen one-hour evidence: 58 candidates, 55 finalized identity matches, three
  failed transactions, 2,566 pool-state observations across 55 pools, no recorded
  RPC errors/reconnects/queue overflows. Exact launch source is preserved.
- A one-minute captioned public-UI walkthrough, developer integration guide,
  independent-review scope and a funding-independent continuation plan.

## Verification

72 unit tests, Windows/Linux Python 3.10/3.12 CI, offline replay of every frozen
run, both SDK comparison reports reproduced, readiness redecoded from raw bytes,
public feed and reliability report rebuilt, and installed-wheel replay checked
outside the source import path. The wheel retains the MIT and Meteora notices.

## External work pending

Three developer-pilot invitations and one independent-review enquiry were sent.
Acceptance, real external integration, repeat use and completed review require
outside responses and are not claimed as achieved.

## Limits

No wallet, signing, trading, fill evidence or profitability claim. The hour did
not exercise reconnect recovery; fault-injection tests cover that path. It is not
an uptime or complete-chain-coverage benchmark. See the one-hour report for the
distinction between collector launch source and later release hardening.

Five high-severity offline-SDK dependency nodes remain flagged through the
unpatched bigint-buffer native-addon chain. Native builds are disabled and
checked absent. This is risk reduction, not a patch or audit. Transitive license
questions are documented for specialist review; no blanket legal clearance is
claimed. These Node development dependencies are not bundled in the wheel/site.

## Public links

- [Watchlist](https://k9-glitch3.github.io/meteora-dbc-migration-monitor/monitor.html)
- [Build update and walkthrough](https://k9-glitch3.github.io/meteora-dbc-migration-monitor/updates.html#v03)
- [Developer pilot](https://k9-glitch3.github.io/meteora-dbc-migration-monitor/pilot.html)
- [One-hour report](https://github.com/K9-glitch3/meteora-dbc-migration-monitor/blob/master/docs/RUN_HOUR_2026-10-16.md)
- [CI](https://github.com/K9-glitch3/meteora-dbc-migration-monitor/actions/workflows/ci.yml)
