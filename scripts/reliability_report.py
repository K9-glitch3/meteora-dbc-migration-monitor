"""Measured capture diagnostics, not uptime or complete-chain coverage claims."""
import argparse
from collections import Counter
from datetime import datetime
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dbc_monitor.replay import read_jsonl, verify, file_hash
from dbc_monitor.records import canonical


def report(directory):
    verify(directory)
    raw = list(read_jsonl(directory/"capture.jsonl"))
    observations = list(read_jsonl(directory/"observations.jsonl"))
    notifications = {c["result"]["value"]["signature"]:c for c in raw if c["kind"] == "migration_notification"}
    delays=[]
    for c in raw:
        if c["kind"] == "transaction" and c["result"] is not None and c["signature"] in notifications:
            first=notifications[c["signature"]]
            delays.append((datetime.fromisoformat(c["observed_at"].replace("Z","+00:00"))-datetime.fromisoformat(first["observed_at"].replace("Z","+00:00"))).total_seconds())
    ordered=sorted(delays)
    reasons=Counter(o["reason"] for o in observations if o["kind"] == "migration" and o["stage"] == "FINALIZED")
    return {"schema_version":"1.0", "capture_sha256":file_hash(directory/"capture.jsonl"),
            "started_at":raw[0]["observed_at"], "ended_at":raw[-1]["observed_at"], "elapsed_seconds":raw[-1]["elapsed_seconds"],
            "collector_launch_code_sha256":raw[0].get("collector_code_sha256"), "counters":raw[-1],
            "finalized_response_reasons":dict(reasons), "pool_states":sum(o["kind"]=="pool_state" for o in observations),
            "distinct_pools":len({o["pool"] for o in observations if o["pool"]}),
            "notification_to_nonnull_finalized_response_seconds":{"count":len(delays), "median":statistics.median(delays) if delays else None,
              "p95_nearest_rank":ordered[max(0,(len(ordered)*95+99)//100-1)] if ordered else None, "maximum":max(delays) if delays else None},
            "gaps":[c for c in raw if c["kind"]=="gap"], "recoveries":[c for c in raw if c["kind"]=="recovery_report"],
            "storage_bytes":(directory/"capture.jsonl").stat().st_size,
            "cost":{"incremental_paid_rpc_usd":0, "provider":"public Solana endpoint", "local_compute_cost":"not metered"},
            "limitations":["A bounded sample is not a 24/7 uptime or network-coverage benchmark.", "No independent ground-truth stream; missed-event rate is unknown.",
              "Delay includes finality wait, polling and worker queue, not network latency alone.", "Recovery not exercised by this run unless recovery records exist.",
              "No transactions sent, fills measured or profits inferred."]}


if __name__ == "__main__":
    p=argparse.ArgumentParser();p.add_argument("directory",type=Path);p.add_argument("output",type=Path);a=p.parse_args()
    result=report(a.directory);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_bytes(canonical(result)+b"\n")
    print(json.dumps({k:result[k] for k in ("elapsed_seconds","finalized_response_reasons","notification_to_nonnull_finalized_response_seconds","storage_bytes")}))
