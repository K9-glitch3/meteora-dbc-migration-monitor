# Continuous live pilot / v0.4

## Architecture

The collector maintains a read-only Solana mainnet WebSocket subscription and
finalizes detected DBC-to-DAMM v2 migrations through the existing checked pipeline.
It does not finish after a timed capture. The first four discovered DAMM pools
receive account subscriptions; all supported detected migrations receive an
initial pool snapshot. This is not a subscription to every pool on Solana.

SQLite stores bounded raw evidence and observations. The API binds only to
127.0.0.1:8898. A Cloudflare quick tunnel exposes only that JSON API. The static
GitHub Pages monitor discovers its HTTPS address from live-config.json and
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

The service is on Michael's Windows PC, not an independent server. Sleep,
logout, power, internet, RPC or tunnel failures interrupt availability.
Cloudflare quick tunnels have no uptime guarantee, a changing hostname and no SSE:
[official limitations](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/).
This deployment is a live pilot, not production 24/7 hosting.

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
- Only the latest bounded supervisor output is retained.

The old frozen evidence under evidence/ is untouched. Live retention is not a
substitute for those permanent replay archives.

## Run, restart and stop

Install the Python package in a dedicated virtual environment and run npm ci
with install scripts disabled. Download cloudflared from its official releases
and verify its release digest. The deployed binary is 2026.10.1:
4d2490e74082c5d48dbfedaf92576fa5bd1702379ab88eb7faa0cfbe8dc891b6.

The deployed command is:

    runs/live-venv/Scripts/python.exe scripts/supervise_live.py --publish

The supervisor restarts only its own collector/tunnel children, with a 30-second
minimum restart interval and a single-instance lock. State and bounded logs:
runs/live/supervisor-status.json. A current-user Startup shortcut restarts it
after login. No system power policy, firewall rule, trading process or other
session is modified.

After a tunnel replacement, --publish checks the public health endpoint and
uses the existing GitHub CLI authentication to update only docs/live-config.json
in this repository. Attempts are limited to once per five minutes. GitHub Pages
deployment can cause additional recovery delay. A failed publication is visible
as publish_error, not silently counted as successful.

To stop, create runs/live/STOP. The supervisor terminates only its owned children.
Remove that file before restarting. Remove the DBC Live Monitor shortcut from
the current user's Startup folder to disable login startup. Do not terminate
unrelated Python, Node, browser or trading processes.
