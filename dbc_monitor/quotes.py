"""Narrow, offline integer quote checker. No wallet, RPC or execution API."""
import base64
from datetime import datetime
from .records import decode_pool, FIELDS

SPL = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
DENOMINATOR = 1_000_000_000


def parameters(capture):
    if capture.get("kind") != "pool_snapshot" or capture.get("commitment") != "finalized":
        raise ValueError("finalized_snapshot_required")
    accounts = capture["result"]["value"]
    if len(accounts) != 3 or any(a is None for a in accounts):
        raise ValueError("mint_accounts_required")
    info = decode_pool(accounts[0])
    raw = base64.b64decode(accounts[0]["data"][0], validate=True)
    def n(name):
        field = FIELDS[name]
        return int.from_bytes(raw[field["offset"]:field["offset"]+field["size"]], "little")
    if capture["addresses"] != [capture["pool"], info["token_a_mint"], info["token_b_mint"]]:
        raise ValueError("mint_address_mismatch")
    if any(a.get("owner") != SPL or a.get("executable") is not False for a in accounts[1:]) or n("token_a_flag") or n("token_b_flag"):
        raise ValueError("token_2022_or_unknown_mint_excluded")
    mint_data = [base64.b64decode(a["data"][0], validate=True) for a in accounts[1:]]
    if any(a["data"][1] != "base64" for a in accounts[1:]) or any(len(raw_mint) != 82 or raw_mint[45] != 1 for raw_mint in mint_data):
        raise ValueError("unsupported_mint_layout")
    # PoolFees POD: base fee bytes 0..31, dynamic initialized at byte 48.
    fee = int.from_bytes(raw[8:16], "little")
    if raw[56] != 0:
        raise ValueError("dynamic_fee_excluded")
    if raw[16] not in (0, 1) or int.from_bytes(raw[22:24], "little") != 0:
        raise ValueError("nonstatic_fee_excluded")
    if n("collect_fee_mode") not in (0, 1) or int.from_bytes(raw[54:56], "little"):
        raise ValueError("compounding_excluded")
    if n("pool_status") != 0 or n("fee_version") not in (0, 1):
        raise ValueError("disabled_or_unknown_fee_version")
    point = capture["result"]["context"]["slot"] if n("activation_type") == 0 else int(datetime.fromisoformat(capture["observed_at"].replace("Z", "+00:00")).timestamp())
    if n("activation_type") not in (0, 1) or point < n("activation_point"):
        raise ValueError("activation_not_established")
    max_fee = 500_000_000 if n("fee_version") == 0 else 990_000_000
    if not 0 <= fee <= max_fee or n("liquidity") <= 0:
        raise ValueError("invalid_fee_or_liquidity")
    return {"sqrt": n("sqrt_price"), "minimum": n("sqrt_min_price"), "maximum": n("sqrt_max_price"),
            "liquidity": n("liquidity"), "fee": fee, "mode": n("collect_fee_mode"), "point": point,
            "account_sha256": info["account_sha256"]}


def quote(p, amount, direction):
    if type(amount) is not int or not 0 < amount < 2**64 or direction not in ("AtoB", "BtoA"):
        raise ValueError("invalid_input")
    def ceildiv(a, b):
        return (a+b-1)//b
    s, liquidity = p["sqrt"], p["liquidity"]
    fee_on_input = p["mode"] == 1 and direction == "BtoA"
    fee = ceildiv(amount*p["fee"], DENOMINATOR) if fee_on_input else 0
    actual = amount-fee
    if direction == "AtoB":
        next_sqrt = ceildiv(liquidity*s, liquidity+actual*s)
        output = liquidity*(s-next_sqrt)//(1 << 128)
    else:
        next_sqrt = s+actual*(1 << 128)//liquidity
        output = liquidity*(next_sqrt-s)//(s*next_sqrt)
    if not p["minimum"] <= next_sqrt <= p["maximum"]:
        raise ValueError("price_range_exceeded")
    if not fee_on_input:
        fee = ceildiv(output*p["fee"], DENOMINATOR)
        output -= fee
    if output < 0 or output >= 2**64:
        raise ValueError("output_outside_u64")
    return {"output_amount": str(output), "next_sqrt_price": str(next_sqrt), "total_fee": str(fee)}
