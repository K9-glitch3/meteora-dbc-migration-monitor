"""Explicitly synthetic fixtures; none are chain observations."""
import base64
from datetime import datetime
from dbc_monitor.protocol import DBC, DAMM, MIGRATE, b58encode
from dbc_monitor.records import FIELDS, LAYOUT

SIGNATURE = b58encode(bytes(range(64)))
WHEN = "2026-10-16T03:00:00Z"
BLOCK_TIME = int(datetime.fromisoformat(WHEN.replace("Z", "+00:00")).timestamp()) - 20
KEYS = [b58encode(bytes([i+1])*32) for i in range(25)]
KEYS[3] = "FhVo3mqL8PW5pH5U2CN4XE33DokiyZnUwuGpH2hmHLuM"
KEYS[12] = DAMM
POOL = KEYS[4]


def transaction():
    return {"slot": 100, "blockTime": BLOCK_TIME,
        "transaction": {"signatures": [SIGNATURE], "message": {"accountKeys": KEYS + [DBC],
            "instructions": [{"programIdIndex": 25, "accounts": list(range(25)), "data": b58encode(MIGRATE)}]}},
        "meta": {"err": None, "loadedAddresses": {"writable": [], "readonly": []}, "innerInstructions": []}}


def account(**overrides):
    raw = bytearray(LAYOUT["account_size"])
    raw[:8] = bytes(LAYOUT["discriminator"])
    for name, value in {"sqrt_price": 2 << 64, "sqrt_min_price": 1, "sqrt_max_price": (1 << 128)-1,
                        "liquidity": 1000, "layout_version": 1, "collect_fee_mode": 0}.items():
        f = FIELDS[name]
        raw[f["offset"]:f["offset"]+f["size"]] = value.to_bytes(f["size"], "little")
    for name, index in [("token_a_mint",13), ("token_b_mint",14), ("token_a_vault",15), ("token_b_vault",16)]:
        f = FIELDS[name]
        raw[f["offset"]:f["offset"]+32] = bytes([index+1])*32
    return {"owner": DAMM, "executable": False, "data": [base64.b64encode(raw).decode(), "base64"], **overrides}


def captures():
    rows = [
        {"kind": "run_start", "duration_seconds": 30},
        {"kind": "migration_notification", "commitment": "confirmed", "result": {
            "context": {"slot": 100}, "value": {"signature": SIGNATURE, "err": None,
            "logs": ["Program log: Instruction: MigrationDammV2"]}}},
        {"kind": "transaction", "commitment": "finalized", "signature": SIGNATURE,
         "notification_slot": 100, "result": transaction()},
        {"kind": "pool_snapshot", "commitment": "finalized", "signature": SIGNATURE, "pool": POOL,
         "result": {"context": {"slot": 101}, "value": [account(), None, None]}},
        {"kind": "account_update", "commitment": "confirmed", "pool": POOL,
         "result": {"context": {"slot": 102}, "value": account()}},
        {"kind": "run_end", "reason": "duration_complete", "elapsed_seconds": 30},
    ]
    return [{"capture_version": "1.0", "sequence": i+1, "observed_at": WHEN, **row} for i,row in enumerate(rows)]
