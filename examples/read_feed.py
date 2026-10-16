"""Minimal read-only integration. No credentials, wallet or trading dependencies."""
import argparse
from datetime import datetime, timezone
import json
from urllib.request import urlopen

DEFAULT = "https://k9-glitch3.github.io/meteora-dbc-migration-monitor/api/v1/feed.json"


def summarize(feed, address=None):
    if feed.get("api_version") != "1.0" or feed.get("mode") != "recorded_snapshot":
        raise ValueError("Unsupported API contract")
    rows=feed["migrations"]
    if address:
        rows=[r for r in rows if address in (r.get("pool"),r.get("virtual_pool"),r.get("base_mint"))]
    recorded=datetime.fromisoformat(feed["migration_recorded_until"].replace("Z","+00:00"))
    age=(datetime.now(timezone.utc)-recorded).total_seconds()
    return {"recorded_until":feed["migration_recorded_until"], "stale":age>feed["limits"]["stale_after_seconds"] or age < -5,
            "mode":feed["mode"], "continuous_coverage":False, "matches":rows}


if __name__ == "__main__":
    p=argparse.ArgumentParser();p.add_argument("--url",default=DEFAULT);p.add_argument("--address");a=p.parse_args()
    with urlopen(a.url,timeout=20) as response:
        raw=response.read(5_000_001)
    if len(raw)>5_000_000:raise ValueError("Feed exceeds limit")
    print(json.dumps(summarize(json.loads(raw),a.address),indent=2))
