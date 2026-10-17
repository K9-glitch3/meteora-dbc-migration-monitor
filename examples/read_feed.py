"""Minimal read-only integration. No credentials, wallet or trading dependencies."""
import argparse
from datetime import datetime, timezone
import json
from urllib.request import urlopen

DEFAULT = "https://k9-glitch3.github.io/meteora-dbc-migration-monitor/live-config.json"


def live_endpoint(config):
    from urllib.parse import urlsplit
    endpoint = urlsplit(config.get("endpoint", ""))
    host = endpoint.hostname or ""
    allowed = host == "dbc-monitor.188-166-88-35.sslip.io" or host.endswith(".trycloudflare.com")
    if (not config.get("enabled") or endpoint.scheme != "https" or not allowed
            or endpoint.username or endpoint.password or endpoint.port
            or endpoint.path not in ("", "/") or endpoint.query or endpoint.fragment):
        raise ValueError("Live endpoint unavailable")
    return config["endpoint"].rstrip("/") + "/v1/feed.json"


def summarize(feed, address=None):
    contract = (feed.get("api_version"), feed.get("mode"))
    if contract not in (("1.0", "recorded_snapshot"), ("2.0", "continuous_live")):
        raise ValueError("Unsupported API contract")
    rows=feed["migrations"]
    if address:
        rows=[r for r in rows if address in (r.get("pool"),r.get("virtual_pool"),r.get("base_mint"))]
    try:
        recorded=datetime.fromisoformat(feed["migration_recorded_until"].replace("Z","+00:00"))
        age=(datetime.now(timezone.utc)-recorded).total_seconds()
    except (TypeError, ValueError, AttributeError):
        age=float("inf")
    stale=age>feed["limits"]["stale_after_seconds"] or age < -5
    if contract[0]=="2.0":
        stale=stale or feed["health"]["status"]!="live"
        for key in ("generated_at", "heartbeat_at"):
            value=feed.get(key) if key=="generated_at" else feed["health"].get(key)
            try:
                elapsed=(datetime.now(timezone.utc)-datetime.fromisoformat(value.replace("Z","+00:00"))).total_seconds()
                stale=stale or elapsed>30 or elapsed < -5
            except (TypeError,ValueError,AttributeError):
                stale=True
    return {"recorded_until":feed["migration_recorded_until"], "stale":stale,
            "mode":feed["mode"], "continuous_coverage":False, "matches":rows}


if __name__ == "__main__":
    p=argparse.ArgumentParser();p.add_argument("--url",default=DEFAULT);p.add_argument("--address");a=p.parse_args()
    if a.url==DEFAULT:
        with urlopen(DEFAULT,timeout=20) as response:
            config=json.loads(response.read(10000))
        a.url=live_endpoint(config)
    with urlopen(a.url,timeout=20) as response:
        raw=response.read(5_000_001)
    if len(raw)>5_000_000:raise ValueError("Feed exceeds limit")
    print(json.dumps(summarize(json.loads(raw),a.address),indent=2))
