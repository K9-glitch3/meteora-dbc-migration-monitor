"""Bounded read-only replay of the mainnet transaction that exposed the v1 gap."""
import argparse
import json
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dbc_monitor.collector import Rpc, utc_now
from dbc_monitor.protocol import account_keys, migrations
from scripts.capture_readiness import capture

SIGNATURE = "3cChM5Ee5Xmj2bhNv6fRe3UynkA2e1dBqveuAebT7saxzY5aUgVrUFakn6J2u5haZeZfY7GtqhJ6wcdcTvN1bk6g"


def check():
    call = Rpc.call
    transactions = []
    def focused(self, method, params):
        if method == "getSignaturesForAddress":
            return [{"signature": SIGNATURE, "err": None}]
        response = call(self, method, params)
        if method == "getTransaction":
            assert params[1]["maxSupportedTransactionVersion"] == 1
            assert response and response.get("version") == 1
            assert response["transaction"]["signatures"][0] == SIGNATURE
            transactions.append({"slot": response["slot"], "version": response["version"],
                                 "accounts": len(account_keys(response)),
                                 "migrations": len(migrations(response))})
        return response
    # Only discovery is fixed; transaction and pool/config account reads use RPC.
    with patch.object(Rpc, "call", focused):
        receipt = capture()
    assert transactions, "Version-1 transaction was not read"
    assert not receipt["errors"], receipt["errors"]
    assert receipt["items"], "No readiness accounts decoded from the v1 transaction"
    return {"checked_at": utc_now(), "signature": SIGNATURE, "passed": True,
            "scope": "fixed historical v1 discovery; live finalized account-state reads",
            "transactions": transactions, "readiness": receipt["items"],
            "errors": receipt["errors"], "raw_responses_sha256": receipt["raw_responses_sha256"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = check()
    if args.output:
        with args.output.open("x", encoding="utf-8") as handle:
            json.dump(result, handle, indent=2)
    print(json.dumps(result))
