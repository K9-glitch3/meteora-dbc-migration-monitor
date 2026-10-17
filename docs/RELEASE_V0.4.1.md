# v0.4.1 - Independent continuous hosting

The continuous DBC Migration Monitor now runs on an existing remote DigitalOcean
server. The user's PC and browser can be switched off without stopping collection.

## Shipped

- Non-root, read-only collector/proxy containers with CPU, memory, process,
  temporary-storage and log limits; digest-pinned base images.
- Persistent SQLite evidence, migrated with a consistent online backup.
- Automatic container restart and boot startup through the enabled Docker daemon.
- HTTPS with automatic certificate renewal and stable IP-derived DNS.
- Public endpoint discovery and client allowlists updated; no arbitrary proxy,
  file browsing, wallet, signing or trading route.
- Previous PC collector/tunnel/publisher stopped and Startup shortcut disabled.
- Documented deployment, recovery and stop commands scoped to this service.

## Verification

- 87 Python tests; Windows/Linux matrix plus an offline read-only container job.
- 212 BigInt cases, 11 negative controls, all 120 prior SDK quote matches.
- Three frozen evidence archives replay successfully; npm audit: no known advisories.
- Actual forced collector crashes recovered automatically with stored evidence intact.
- Public feed advanced after the PC services stopped: 13 samples / 120 seconds,
  11 evidence hash checks; final build rechecked for 60 seconds / nine hashes.
- TLS/redirect, API route boundaries, CORS/cache headers, desktop/mobile UI and
  example-client discovery checked.

Runtime source: b49c3fef17e1678cefdb258dfea0cd539eab0dae. Subsequent release
metadata adds final receipts and HTTP verification tooling, not runtime changes.
Receipts: evidence/hosting-2026-10-17.

## Cost and limitations

This reuses an already-paid server without adding a hosting subscription. It is
not a free cloud tier, and existing hosting/provider usage terms still apply.
The single shared server has approximately 4.1 GiB free; disk capacity requires
attention. No unrelated files were deleted and no other workload was restarted.
There is no uptime SLA, redundant host, off-server live database backup, complete
chain coverage, independent security audit or evidence of trading profitability.
Public RPC errors and bounded recovery gaps remain visible rather than hidden.
The host was not rebooted and the PC itself was not powered off during testing;
the old PC services were stopped to establish independence.
