"""Versioned observation contract and deterministic evidence derivation."""
from __future__ import annotations

import base64
from datetime import datetime
from fractions import Fraction
import hashlib
from importlib.resources import files
import json
import re

from jsonschema import Draft202012Validator, FormatChecker
from .protocol import b58encode, DAMM, migrations

VERDICTS = ["SUPPORTED_COMPARISON", "NO_CONCLUSION", "UNSUPPORTED_CONFIGURATION", "REJECTED_OBSERVATION"]
SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://k9-glitch3.github.io/meteora-dbc-migration-monitor/observation.schema.json",
    "title": "DBC Migration Monitor observation v1.0",
    "type": "object", "additionalProperties": False,
    "required": ["schema_version", "id", "kind", "source", "sequence", "observed_at", "slot", "signature", "pool",
                 "commitment", "stage", "verdict", "reason", "scope", "freshness", "details", "capture_sha256"],
    "properties": {
        "schema_version": {"const": "1.0"}, "id": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
        "kind": {"enum": ["migration", "pool_state", "health"]},
        "source": {"enum": ["mainnet_capture", "synthetic_test"]},
        "sequence": {"type": "integer", "minimum": 1},
        "observed_at": {"type": "string", "format": "date-time"},
        "slot": {"type": ["integer", "null"], "minimum": 0},
        "signature": {"type": ["string", "null"], "pattern": "^[1-9A-HJ-NP-Za-km-z]{64,88}$"},
        "pool": {"type": ["string", "null"], "pattern": "^[1-9A-HJ-NP-Za-km-z]{32,44}$"},
        "commitment": {"enum": ["confirmed", "finalized", "unknown"]},
        "stage": {"enum": ["DETECTED", "FINALIZED", "POOL_STATE", "HEALTH"]},
        "verdict": {"enum": VERDICTS}, "reason": {"type": "string", "minLength": 1},
        "scope": {"enum": ["migration_identity", "pool_account", "stream_health"]},
        "freshness": {"enum": ["fresh", "stale", "unknown"]},
        "details": {"type": "object"},
        "capture_sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"}
    }
}
FORMATS = FormatChecker()


@FORMATS.checks("date-time", raises=(ValueError, TypeError))
def timestamp_format(value):
    if not isinstance(value, str):
        return True
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})", value):
        return False
    return datetime.fromisoformat(value.replace("Z", "+00:00")).tzinfo is not None


VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FORMATS)
LAYOUT = json.loads(files("dbc_monitor").joinpath("pool_layout.json").read_text())
FIELDS = {f["name"]: f for f in LAYOUT["fields"]}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def decode_pool(account):
    if account is None:
        raise ValueError("pool_account_unavailable")
    if account.get("owner") != DAMM or account.get("executable") is not False:
        raise ValueError("wrong_pool_owner")
    data = account.get("data")
    if not isinstance(data, list) or len(data) != 2 or data[1] != "base64":
        raise ValueError("unsupported_account_encoding")
    try:
        raw = base64.b64decode(data[0], validate=True)
    except Exception:
        raise ValueError("invalid_account_base64") from None
    if len(raw) != LAYOUT["account_size"] or raw[:8] != bytes(LAYOUT["discriminator"]):
        raise ValueError("unsupported_pool_layout")
    def number(name):
        f = FIELDS[name]
        return int.from_bytes(raw[f["offset"]:f["offset"]+f["size"]], "little")
    def key(name):
        f = FIELDS[name]
        return b58encode(raw[f["offset"]:f["offset"]+f["size"]])
    version, fee = number("layout_version"), number("collect_fee_mode")
    if version not in (0, 1) or fee not in (0, 1, 2):
        raise ValueError("unsupported_pool_configuration")
    sqrt = number("sqrt_price")
    if not 0 < number("sqrt_min_price") <= sqrt <= number("sqrt_max_price"):
        raise ValueError("invalid_price_bounds")
    price = Fraction(sqrt * sqrt, 1 << 128)
    return {"token_a_mint": key("token_a_mint"), "token_b_mint": key("token_b_mint"),
            "token_a_vault": key("token_a_vault"), "token_b_vault": key("token_b_vault"),
            "sqrt_price_q64": str(sqrt), "raw_price_numerator": str(price.numerator),
            "raw_price_denominator": str(price.denominator), "liquidity": str(number("liquidity")),
            "layout_version": version, "fee_mode": fee, "pool_status": number("pool_status"),
            "price_units": "token_b_atomic/token_a_atomic", "quote_comparison": "NOT_PERFORMED",
            "account_sha256": hashlib.sha256(raw).hexdigest()}


def _freshness(when, block_time, max_age):
    if type(block_time) is not int:
        return "unknown"
    age = datetime.fromisoformat(when.replace("Z", "+00:00")).timestamp() - block_time
    return "fresh" if -5 <= age <= max_age else "stale"


def derive(captures, *, source="mainnet_capture", max_age=120):
    """Rebuild observations from captured responses; never trust stored verdicts."""
    result, notifications, pool_slots, transaction_migrations = [], {}, {}, {}
    finalized_seen, account_seen = set(), set()
    previous = 0
    def emit(capture, **values):
        record = {"schema_version": "1.0", "source": source, "sequence": capture["sequence"],
                  "observed_at": capture["observed_at"], "slot": None, "signature": None, "pool": None,
                  "commitment": capture.get("commitment", "unknown"), "kind": "health", "stage": "HEALTH",
                  "verdict": "NO_CONCLUSION", "reason": "unclassified", "scope": "stream_health",
                  "freshness": "unknown", "details": {}, "capture_sha256": digest(capture), **values}
        record["id"] = digest(record)
        VALIDATOR.validate(record)
        result.append(record)
    for c in captures:
        if c.get("capture_version") != "1.0" or type(c.get("sequence")) is not int or c["sequence"] != previous+1:
            raise ValueError("Capture sequence/version is invalid or incomplete")
        previous = c["sequence"]
        datetime.fromisoformat(c["observed_at"].replace("Z", "+00:00"))
        kind = c["kind"]
        if kind == "migration_notification":
            r = c["result"]
            signature, slot = r["value"]["signature"], r["context"]["slot"]
            if signature in notifications:
                emit(c, kind="migration", stage="DETECTED", scope="migration_identity", signature=signature, slot=slot,
                     reason="duplicate_notification" if notifications[signature] == slot else "notification_slot_conflict")
                continue
            notifications[signature] = slot
            emit(c, kind="migration", stage="DETECTED", scope="migration_identity", signature=signature, slot=slot,
                 reason="awaiting_finalized_transaction")
        elif kind == "transaction":
            signature, tx = c["signature"], c["result"]
            base = dict(kind="migration", stage="FINALIZED", scope="migration_identity", signature=signature)
            if tx is None:
                emit(c, **base, reason="finalized_transaction_unavailable")
                continue
            if c.get("commitment") != "finalized":
                emit(c, **base, reason="finality_not_established")
                continue
            if signature in finalized_seen:
                emit(c, **base, reason="duplicate_finalized_response")
                continue
            finalized_seen.add(signature)
            slot = tx["slot"]
            base["slot"] = slot
            base["freshness"] = _freshness(c["observed_at"], tx.get("blockTime"), max_age)
            if tx["transaction"]["signatures"][0] != signature:
                emit(c, **base, verdict="REJECTED_OBSERVATION", reason="transaction_signature_mismatch")
                continue
            if c.get("notification_slot") != slot or notifications.get(signature) != slot:
                emit(c, **base, verdict="REJECTED_OBSERVATION", reason="notification_finalized_slot_mismatch")
                continue
            if tx.get("meta", {}).get("err") is not None:
                emit(c, **base, verdict="REJECTED_OBSERVATION", reason="transaction_failed")
                continue
            try:
                found = migrations(tx)
            except (ValueError, KeyError, TypeError, IndexError):
                emit(c, **base, verdict="REJECTED_OBSERVATION", reason="invalid_migration_instruction")
                continue
            if not found:
                emit(c, **base, verdict="UNSUPPORTED_CONFIGURATION", reason="no_supported_migration_instruction")
            for migration in found:
                transaction_migrations[(signature, migration["pool"])] = {**migration, "transaction_slot": slot}
                verdict = "SUPPORTED_COMPARISON" if base["freshness"] == "fresh" else "NO_CONCLUSION"
                emit(c, **base, pool=migration["pool"], verdict=verdict,
                     reason="finalized_migration_identity_matches" if verdict == "SUPPORTED_COMPARISON" else "migration_outside_freshness_window",
                     details={**migration, "block_time": tx.get("blockTime"), "quote_comparison": "NOT_PERFORMED"})
        elif kind in ("account_update", "pool_snapshot"):
            r, pool = c["result"], c["pool"]
            slot = r["context"]["slot"]
            base = dict(kind="pool_state", stage="POOL_STATE", scope="pool_account", pool=pool, slot=slot,
                        signature=c.get("signature"))
            previous_slot = pool_slots.get(pool, -1)
            if kind == "account_update":
                pool_slots[pool] = max(previous_slot, slot)
            if slot < previous_slot and kind == "account_update":
                emit(c, **base, reason="out_of_order_slot", freshness="stale")
                continue
            account = r["value"][0] if kind == "pool_snapshot" else r["value"]
            identity = (pool, slot, digest(account), c.get("commitment"))
            if identity in account_seen:
                emit(c, **base, reason="duplicate_pool_state")
                continue
            account_seen.add(identity)
            try:
                details = decode_pool(account)
                if kind == "pool_snapshot":
                    migration = transaction_migrations.get((c["signature"], pool))
                    if migration is None:
                        raise ValueError("unbound_pool_snapshot")
                    if slot < migration["transaction_slot"]:
                        raise ValueError("snapshot_precedes_migration")
                    if any(details[name] != migration[target] for name, target in
                           [("token_a_mint", "base_mint"), ("token_b_mint", "quote_mint"),
                            ("token_a_vault", "token_a_vault"), ("token_b_vault", "token_b_vault")]):
                        raise ValueError("pool_role_mismatch")
                emit(c, **base, reason="decoded_pool_state_no_historical_quote_comparison", details=details)
            except ValueError as exc:
                reason = str(exc)
                verdict = "UNSUPPORTED_CONFIGURATION" if reason.startswith("unsupported") else "REJECTED_OBSERVATION"
                if reason in ("pool_account_unavailable", "unbound_pool_snapshot"):
                    verdict = "NO_CONCLUSION"
                emit(c, **base, verdict=verdict, reason=reason)
        elif kind in ("gap", "rpc_error", "decode_error", "slot_conflict"):
            emit(c, reason=c.get("reason", kind), details={k:v for k,v in c.items()
                 if k not in ("capture_version", "sequence", "observed_at")})
    return result
