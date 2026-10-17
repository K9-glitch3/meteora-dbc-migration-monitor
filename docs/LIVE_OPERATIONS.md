# Independently hosted continuous pilot / v0.4.1

## Architecture

The collector maintains a read-only Solana mainnet WebSocket subscription and
finalizes detected DBC-to-DAMM v2 migrations through the existing checked pipeline.
It does not finish after a timed capture. The first four discovered DAMM pools
receive account subscriptions; all supported detected migrations receive an
initial pool snapshot. This is not a subscription to every pool on Solana.

SQLite stores bounded raw evidence and observations on the remote server.
The API binds to 0.0.0.0:8898 only inside its isolated Docker network; it has no
published host port. A separate unprivileged Caddy container exposes the JSON API
over HTTPS. The static GitHub Pages monitor discovers its address from live-config.json and
polls every five seconds while visible. It never silently substitutes historical
data when the live endpoint fails.

GET /healthz, /v1/feed.json and /v1/evidence/{64-character-observation-id}
are the only routes. HEAD is allowed; POST is not. No wallet, trading,
filesystem, arbitrary RPC, SDK input or proxy route is exposed.
Responses disable caching and permit browser CORS only from the GitHub Pages
origin. The endpoint is public read-only data, not authenticated private data.

## Health and limitations

Live status requires an active log subscription, a running finalization worker,
a heartbeat within 15 seconds and upstream messages within 30 seconds.
Recent RPC errors or a backlog of 32 entries mark the feed degraded.
The UI independently ages the returned timestamps, including when refresh is off.
Readiness is an up-to-eight-pool sample repeated 90 seconds after each completed
sample; it has its own timestamp and becomes stale after 180 seconds.
It is not full-market discovery, a migration forecast or a continuous account stream.

The service is now on an existing DigitalOcean server, independent of Michael's PC.
Both containers restart automatically after process failure and host boot.
The hostname is https://dbc-monitor.188-166-88-35.sslip.io, with automatically
renewed Let's Encrypt TLS. It stays the same while the server IP stays the same.
This reuses an already-paid server, not a new free-tier subscription.
Third-party DNS, host, disk, certificate, network and public-RPC failures can still
interrupt availability. There is no uptime SLA, redundant host or failover.
The server was already 96% full before installation; approximately 4.1 GiB remained
after deployment. No unrelated data or services were removed. Disk capacity needs
operator attention independently of this bounded service.

Recovery is bounded to the existing finalized-signature scan and transaction
budget. Partial recovery remains explicit in health events. Historical pool
account updates cannot be reconstructed. complete_coverage is always false.
Existing rows may predate the current process; per-row observation time is retained.

## Retention and resource bounds

- 20,000 raw records and 24 MB of raw payload; 5,000 observations.
- Raw responses above 256 KB become explicit gaps with their original hash.
- 4,096 entries per derivation/deduplication map; 64 pending finalizations.
- Latest 250 migration rows and 20 pool states/health events per API response.
- SQLite database hard limit: 128 MiB; WAL checkpoint every 500 writes.
- Expired raw evidence returns capture_retained=false; unknown/expired IDs: 404.
- HTTP request handling is sequential with a three-second connection timeout.
- Collector memory: 512 MiB, 0.5 CPU, 96 processes; proxy: 128 MiB, 0.25 CPU.
- Container logs: three 1 MB files each. Read-only root filesystems, no Linux
  capabilities, non-root users, no credentials or wallets, private Docker network.
- Collector /tmp: 32 MiB; only /data is persistent and writable.

The old frozen evidence under evidence/ is untouched. Live retention is not a
substitute for those permanent replay archives.

## Remote operations

Deployment source is /opt/dbc-monitor; persistent data is /var/lib/dbc-monitor.
TLS state is /var/lib/dbc-monitor-tls. Both directories belong to UID/GID 65532.
Base images are pinned by digest. The public proxy has no admin API or file route.
Deploy from a reviewed checkout, with at least 2 GiB free after image installation:

    docker compose -f deploy/compose.yaml build
    docker compose -f deploy/compose.yaml up -d --no-build
    docker compose -f deploy/compose.yaml ps

Restart only this service with:

    docker compose -f deploy/compose.yaml restart collector

Stop only this deployment with:

    docker compose -f deploy/compose.yaml stop

Do not restart the shared host, Docker daemon, or unrelated containers. Automatic
restart after a killed collector was exercised; a host reboot was not performed.
Docker health status reports upstream freshness; an unhealthy badge alone does not
restart a container. Collection reconnects internally; process exits restart.
Preserve the SQLite directory across redeployments. A consistent SQLite backup,
not a raw copy of an open database, was used for the initial migration.
Evidence receipts are in evidence/hosting-2026-10-17.

The old PC collector, tunnel and publishing supervisor are stopped. Its Startup
shortcut was moved out of Startup, with its database preserved for rollback.
Do not start the old --publish supervisor without deliberately changing the
public endpoint back: it can overwrite live-config.json.

## Retired PC pilot (v0.4 historical instructions)

The following describes the retired deployment, not the current live service.

Install the Python package in a dedicated virtual environment and run npm ci
with install scripts disabled. Download cloudflared from its official releases
and verify its release digest. The deployed binary is 2026.10.1:
4d2490e74082c5d48dbfedaf92576fa5bd1702379ab88eb7faa0cfbe8dc891b6.

The deployed command is:

    runs/live-venv/Scripts/python.exe scripts/supervise_live.py --publish --data "%LOCALAPPDATA%/DBCMonitor/live"

The supervisor restarts only its own collector/tunnel children, with a 30-second
minimum restart interval and a single-instance lock. State and bounded logs:
%LOCALAPPDATA%/DBCMonitor/live/supervisor-status.json. Runtime state is outside
the OneDrive-synced source folder. A current-user Startup shortcut restarts it
after login. No system power policy, firewall rule, trading process or other
session is modified.

After a tunnel replacement, --publish checks the public health endpoint and
uses the existing GitHub CLI authentication to update only docs/live-config.json
in this repository. Attempts are limited to once per five minutes. GitHub Pages
deployment can cause additional recovery delay. A failed publication is visible
as publish_error, not silently counted as successful.

To stop, create %LOCALAPPDATA%/DBCMonitor/live/STOP. The supervisor terminates only its owned children.
Remove that file before restarting. Remove the DBC Live Monitor shortcut from
the current user's Startup folder to disable login startup. Do not terminate
unrelated Python, Node, browser or trading processes.

On this Codex desktop installation, Windows resolves the runtime directory to
the user's AppData/Local/Packages/OpenAI.Codex_2p2nqsd0c76g0/LocalCache/Local/DBCMonitor/live folder.
The installed shortcut uses that absolute path, so startup does not depend on
the launching application's LOCALAPPDATA mapping. Status-file sharing errors
are retried without stopping the collector.
