# Remote hosting verification

The collector and HTTPS proxy run on an existing remote server, not the user's PC.
The retained SQLite database was migrated with SQLite's online backup API.

- restart-check.json records an actual collector process crash, automatic restart,
  a new process epoch, unchanged retained evidence and unchanged other containers.
- pc-off-progress.json samples the public API for 120 seconds after stopping the
  PC collector, tunnel and publishing supervisor. It checks upstream progress and
  retained observation hashes, not full-market coverage or long-term uptime.

This is bounded deployment verification. The PC itself was not powered off, and
the shared server was not rebooted. The service has no connection to the PC;
only its former collector/tunnel were shut down for the independence test.
Docker's unless-stopped restart policy and enabled daemon provide boot startup.
No wallet or trading operation is part of this deployment.

The final runtime was built from commit b49c3fef17e1678cefdb258dfea0cd539eab0dae.
final-restart-check.json repeats the crash and persistence check against that
image; final-progress.json contains seven further samples over 60 seconds and
nine retained evidence hash checks. http-boundaries.json verifies TLS, the HTTP
redirect, CORS/no-cache headers, HEAD and rejection of unsupported paths/methods.
Both restart checks left the other existing container's start time unchanged.
The database remains local to the server; this is not an off-server backup plan.

Browser verification on 17 October 2026:
- Desktop: live status, remote JSON URL and per-observation evidence links.
- Mobile 390 x 844: no document horizontal overflow; project image loaded.
- No browser console errors during the final check.
- Temporary mobile viewport reset; public monitor left open.

Runtime CI: https://github.com/K9-glitch3/meteora-dbc-migration-monitor/actions/runs/38997854421
All five jobs passed: Linux/Windows on Python 3.10/3.12 plus offline,
read-only container regression tests. The source uses 87 Python tests,
212 BigInt conversion cases, 11 negative controls and 120 SDK quote matches.
