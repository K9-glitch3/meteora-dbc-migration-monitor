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
