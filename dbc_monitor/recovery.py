"""Budgeted finalized-history recovery; unresolved history is never called complete."""
from .protocol import DBC, migrations
from .collector import RpcError


def recover(rpc, since_slot, *, known=(), signature_limit=100, transaction_limit=10):
    if type(since_slot) is not int or since_slot < 0 or not 1 <= signature_limit <= 1000 or not 1 <= transaction_limit <= 50:
        raise ValueError("Invalid recovery bounds")
    report = {"since_slot": since_slot, "scope": "finalized_history_at_query", "scanned": 0,
              "transactions_requested": 0, "unresolved": 0, "boundary_reached": False,
              "complete": False, "errors": [], "recovered": []}
    try:
        entries = rpc.call("getSignaturesForAddress", [DBC, {"limit": signature_limit, "commitment": "finalized"}])
        if not isinstance(entries, list):
            raise ValueError("Malformed history response")
        seen = set(known)
        previous_slot = None
        for entry in entries:
            slot, signature = entry["slot"], entry["signature"]
            if type(slot) is not int or slot < 0 or not isinstance(signature, str) or (previous_slot is not None and slot > previous_slot):
                raise ValueError("Malformed or unordered history response")
            previous_slot = slot
            report["scanned"] += 1
            if slot <= since_slot:
                report["boundary_reached"] = True
                break
            if signature in seen or entry.get("err") is not None:
                continue
            seen.add(signature)
            if report["transactions_requested"] >= transaction_limit:
                report["unresolved"] += 1
                continue
            report["transactions_requested"] += 1
            try:
                tx = rpc.call("getTransaction", [signature, {"encoding": "json", "commitment": "finalized", "maxSupportedTransactionVersion": 0}])
                if tx is None or tx["slot"] != slot or tx["transaction"]["signatures"][0] != signature:
                    report["unresolved"] += 1
                    continue
                if not isinstance(tx.get("meta"), dict) or "err" not in tx["meta"]:
                    raise ValueError("Transaction result metadata is unavailable")
                if migrations(tx):
                    report["recovered"].append({"signature": signature, "slot": slot, "transaction": tx})
            except (RpcError, ValueError, KeyError, TypeError, IndexError) as exc:
                report["unresolved"] += 1
                report["errors"].append(type(exc).__name__)
        report["complete"] = report["boundary_reached"] and report["unresolved"] == 0
    except (RpcError, ValueError, KeyError, TypeError) as exc:
        report["errors"].append(type(exc).__name__)
    return report
