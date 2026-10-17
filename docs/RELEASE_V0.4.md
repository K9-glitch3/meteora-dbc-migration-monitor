# v0.4.0 / Continuous live pilot

I have moved the default monitor to continuous read-only Solana mainnet
collection, independent of browser tabs. The UI polls a public JSON API every
five seconds. Historical snapshots remain a separate selectable mode.

## Delivered

- Continuous WebSocket collection with finalized migration identity checks.
- Bounded SQLite evidence retention, raw-record hashes and live evidence links.
- Upstream heartbeat, connection state, backlog, errors and coverage history.
- A separately refreshed readiness sample, explicitly not full-market coverage.
- Collector/tunnel supervision, restart watermark recovery and login startup.
- Automatic publication of a new endpoint after a tunnel replacement.
- Replacement of the unpatched native bigint-buffer dependency with a bounded,
  independently implemented pure-JavaScript adapter.

## Verification

- 84 Python tests, including continuous mode, restart, freshness, retention,
  HTTP route restrictions and the Windows status-file-lock regression.
- 212 BigInt/layout conversion cases and 11 negative controls.
- 120 supported SDK quote cases still match exactly; exclusions are unchanged.
- Three frozen evidence runs replay without changes to historical capture bytes.
- Clean npm installation and audit: zero known advisories on 17 October 2026.
- Desktop/mobile checks: live updates, watchlist filtering, evidence links,
  historical mode, no page-width overflow at the tested mobile size.
- Initial public check: 13 reads over 120 seconds, slots advanced from
  457875206 to 457875755; log notifications increased from 5,253 to 7,302.
  Nine retained evidence hashes matched. A further seven public reads over
  60 seconds passed after restart.
- An actual collector process-tree termination was recovered automatically
  by the supervisor without changing the tunnel endpoint. Duplicate startup
  was rejected by the single-instance lock.

The Windows restart test also exposed a status-file sharing failure. That
failure is fixed and regression-tested: a failed status write no longer stops
collection. Runtime data is outside the OneDrive-synced source folder.

Public verification receipts are in evidence/live-pilot-2026-10-17.
They are bounded observations, not a continuous coverage or uptime benchmark.
The first verification URL was retired during deployment testing; live-config.json
is the current endpoint discovery mechanism.

## Boundaries

This is a live, PC-hosted pilot, not production 24/7 hosting. Availability depends
on the PC, network, RPC and temporary Cloudflare tunnel. Recovery has explicit
request budgets; the restart test retained incomplete recovery rather than
claiming every missed event was recovered. Historical pool updates are not backfilled.

There are no wallet, signing, order submission or trading features.
Zero known dependency advisories is not an independent security audit.
Existing third-party licensing review items remain documented separately.

This is post-submission development, not work claimed for the original judged
period. I am continuing the project regardless of the Colosseum outcome.

## Package

The Python wheel contains the collector and live API module. Running the
documented supervised deployment/readiness sampler requires the source checkout,
its pinned Node dependencies and separately downloaded official cloudflared.
Wheel SHA-256:
be6324a2a8578de1d138e6c25f523450db68a0d4487cb3f852b9ba1ef3b4995f
