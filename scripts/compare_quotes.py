"""Replay captured static-fee pools against the pinned official SDK."""
import argparse
from collections import Counter
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dbc_monitor.quotes import parameters, quote
from dbc_monitor.records import canonical
from dbc_monitor.replay import read_jsonl, file_hash


def compare(path):
    cases, requests, excluded = [], [], []
    for c in read_jsonl(path):
        if c["kind"] != "pool_snapshot":
            continue
        try:
            p = parameters(c)
        except (ValueError, KeyError, TypeError, IndexError) as error:
            excluded.append({"sequence": c["sequence"], "pool": c["pool"], "reason": str(error)})
            continue
        for direction in ("AtoB", "BtoA"):
            for amount in (1, 1000, 1_000_000, 1_000_000_000):
                try:
                    calculated = quote(p, amount, direction)
                except ValueError as error:
                    excluded.append({"sequence": c["sequence"], "direction": direction, "amount": str(amount), "reason": str(error)})
                    continue
                requests.append({"account": c["result"]["value"][0]["data"][0], "amount": str(amount), "direction": direction, "point": str(p["point"])})
                cases.append({"sequence": c["sequence"], "pool": c["pool"], "slot": c["result"]["context"]["slot"],
                              "account_sha256": p["account_sha256"], "direction": direction, "amount": str(amount),
                              "fee_numerator": str(p["fee"]), "collect_fee_mode": p["mode"], "current_point": str(p["point"]),
                              "current_point_basis": "snapshot_slot_or_capture_wallclock; not execution proof", "calculated": calculated})
    run = subprocess.run(["node", str(ROOT/"scripts/sdk_reference.cjs")], input=json.dumps(requests), text=True, capture_output=True, check=True, timeout=120, cwd=ROOT)
    reference = json.loads(run.stdout)
    if len(reference) != len(cases):
        raise ValueError("Reference length mismatch")
    for case, answer in zip(cases, reference):
        case.update(reference=answer, result="MATCH" if case["calculated"] == answer else "MISMATCH")
    return {"schema_version": "1.0", "source_capture_sha256": file_hash(path), "sdk": "@meteora-ag/cp-amm-sdk@1.5.1",
            "lock_sha256": file_hash(ROOT/"package-lock.json"),
            "bigint_adapter_sha256": file_hash(ROOT/"vendor/bigint-buffer-safe/index.cjs"),
            "scope": "offline exact-input static-fee concentrated-liquidity SPL-token quotes; no fills or profitability",
            "counts": dict(Counter(c["result"] for c in cases)), "cases": cases, "excluded": excluded}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("capture", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = compare(args.capture)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical(result)+b"\n")
    print(json.dumps({"counts": result["counts"], "excluded": len(result["excluded"])}))
    sys.exit(1 if result["counts"].get("MISMATCH") or not result["cases"] else 0)
