"""Evidence-only lifecycle views. Threshold progress is not a migration forecast."""
from collections import defaultdict


def readiness(pool, config):
    if not pool or not config or pool["config"] != config["address"]:
        return {"stage": "UNKNOWN", "reason": "missing_or_mismatched_config"}
    if config["migration_option"] != 1 or pool["migrated"] not in (0, 1):
        return {"stage": "UNSUPPORTED", "reason": "unsupported_migration_configuration"}
    reserve, threshold = int(pool["quote_reserve"]), int(config["threshold"])
    if reserve < 0 or threshold <= 0:
        return {"stage": "UNKNOWN", "reason": "invalid_threshold_or_reserve"}
    stage = "MIGRATED_FLAG" if pool["migrated"] else "THRESHOLD_REACHED" if reserve >= threshold else "APPROACHING" if reserve*100 >= threshold*90 else "BELOW_THRESHOLD"
    return {"stage": stage, "reason": "captured_account_state_not_forecast", "progress_bps": min(10000, reserve*10000//threshold),
            "quote_reserve": str(reserve), "threshold": str(threshold), "base_mint": pool["base_mint"],
            "quote_mint": config["quote_mint"], "config": config["address"], "virtual_pool": pool["address"]}


def migration_rows(observations):
    groups = defaultdict(list)
    for row in observations:
        if row["kind"] == "migration" and row["signature"]:
            groups[row["signature"]].append(row)
    result = []
    for signature, rows in groups.items():
        latest = rows[-1]
        # A FINALIZED stage in the legacy contract can still be a missing response.
        verified = [r for r in rows if r["reason"] in ("finalized_migration_identity_matches", "migration_outside_freshness_window")]
        chosen = verified[-1] if verified else latest
        stage = "FINALIZED_VERIFIED" if verified else "REJECTED" if latest["verdict"] == "REJECTED_OBSERVATION" else "UNRESOLVED" if latest["stage"] == "FINALIZED" else "DETECTED"
        result.append({"signature": signature, "pool": chosen["pool"], "virtual_pool": chosen["details"].get("virtual_pool"),
                       "base_mint": chosen["details"].get("base_mint"), "stage": stage, "reason": chosen["reason"],
                       "slot": chosen["slot"], "observed_at": chosen["observed_at"], "freshness_at_capture": chosen["freshness"],
                       "evidence_ids": [r["id"] for r in rows]})
    return sorted(result, key=lambda r: (r["observed_at"], r["signature"]), reverse=True)
