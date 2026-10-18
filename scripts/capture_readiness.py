"""Bounded sample of active DBC accounts with same-context pool/config pairs."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dbc_monitor.collector import Rpc, RpcError, DBC, utc_now
from dbc_monitor.lifecycle import readiness
from dbc_monitor.records import canonical, digest
from dbc_monitor.protocol import account_keys, MAX_SUPPORTED_TRANSACTION_VERSION


def decode(items):
    run = subprocess.run(["node", str(ROOT/"scripts/decode_dbc.cjs")], input=json.dumps(items), text=True, capture_output=True, check=True, timeout=30)
    return json.loads(run.stdout)


def capture():
    rpc = Rpc(os.environ.get("DBC_RPC_URL", "https://api.mainnet-beta.solana.com"))
    receipt = {"schema_version": "1.0", "started_at": utc_now(), "sampling": "up to 4 recent finalized DBC transactions; not all pools", "responses": [], "errors": [], "items": []}
    def call(method, params):
        time.sleep(1.1)
        result = rpc.call(method, params)
        receipt["responses"].append({"method": method, "params": params, "observed_at": utc_now(), "result": result})
        return result
    try:
        signatures = call("getSignaturesForAddress", [DBC, {"commitment": "finalized", "limit": 12}])
        keys = []
        for row in [s for s in signatures if s.get("err") is None][:4]:
            try:
                tx = call("getTransaction", [row["signature"], {"commitment": "finalized", "encoding": "json", "maxSupportedTransactionVersion": MAX_SUPPORTED_TRANSACTION_VERSION}])
                if tx is None:
                    receipt["errors"].append("transaction_unavailable")
                    continue
                if tx["transaction"]["signatures"][0] != row["signature"] or tx["meta"]["err"] is not None:
                    raise ValueError("Transaction identity or success mismatch")
                keys += account_keys(tx)
            except (RpcError, ValueError, KeyError, TypeError, IndexError) as error:
                receipt["errors"].append(str(error) if isinstance(error, RpcError) else type(error).__name__)
        keys = list(dict.fromkeys(keys))[:80]
        if keys:
            accounts = call("getMultipleAccounts", [keys, {"commitment": "finalized", "encoding": "base64"}])
            pools = [p for p in decode([{"address": k, "account": a} for k,a in zip(keys, accounts["value"])]) if p][:8]
            pair_keys = list(dict.fromkeys([key for p in pools for key in (p["address"], p["config"])]))
            if pair_keys:
                pairs = call("getMultipleAccounts", [pair_keys, {"commitment": "finalized", "encoding": "base64", "minContextSlot": accounts["context"]["slot"]}])
                account_map = dict(zip(pair_keys, pairs["value"]))
                decoded_pools = decode([{"address": p["address"], "account": account_map[p["address"]]} for p in pools])
                decoded_configs = decode([{"kind": "config", "address": p["config"], "account": account_map[p["config"]]} for p in pools])
                for pool, config in zip(decoded_pools, decoded_configs):
                    row = readiness(pool, config)
                    row.update(slot=pairs["context"]["slot"], observed_at=receipt["responses"][-1]["observed_at"], commitment="finalized")
                    row["id"] = digest(row)
                    receipt["items"].append(row)
    except (RpcError, ValueError, KeyError, TypeError) as error:
        receipt["errors"].append(str(error) if isinstance(error, RpcError) else type(error).__name__)
    receipt.update(ended_at=utc_now(), raw_responses_sha256=digest(receipt["responses"]))
    return receipt


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("output", type=Path)
    args = p.parse_args()
    result = capture()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("xb") as handle:
        handle.write(canonical(result)+b"\n")
    print(json.dumps({"pools":len(result["items"]), "errors":result["errors"]}))
