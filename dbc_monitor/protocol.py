"""Read-only instruction decoding from Meteora's published SDK IDL."""
from __future__ import annotations

DBC = "dbcij3LWUppWqq96dh6gJWwBifmcGfLSB5D4DuSMaqN"
DAMM = "cpamdpZCGKUy5JxQXB4dcpGPiikHawvSWAd6mEn1sGG"
MIGRATE = bytes([156, 169, 230, 103, 53, 228, 80, 64])
ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def b58decode(value):
    if not isinstance(value, str) or len(value) > 2048:
        raise ValueError("Invalid base58 input")
    n = 0
    for char in value:
        if char not in ALPHABET:
            raise ValueError("Invalid base58 character")
        n = n * 58 + ALPHABET.index(char)
    return b"\0" * (len(value) - len(value.lstrip("1"))) + n.to_bytes((n.bit_length() + 7) // 8, "big")


def b58encode(value):
    n, encoded = int.from_bytes(value, "big"), ""
    while n:
        n, rem = divmod(n, 58)
        encoded = ALPHABET[rem] + encoded
    return "1" * (len(value) - len(value.lstrip(b"\0"))) + encoded


def migrations(tx):
    if not isinstance(tx, dict) or not isinstance(tx.get("meta"), dict):
        return []
    if tx["meta"].get("err") is not None:
        return []
    message = tx["transaction"]["message"]
    keys = list(message["accountKeys"])
    if any(not isinstance(k, str) or len(b58decode(k)) != 32 for k in keys):
        raise ValueError("Invalid account keys")
    loaded = tx["meta"].get("loadedAddresses", {})
    keys += loaded.get("writable", []) + loaded.get("readonly", [])
    if any(not isinstance(k, str) or len(b58decode(k)) != 32 for k in keys):
        raise ValueError("Invalid loaded account keys")
    instructions = [(f"top:{i}", ix) for i, ix in enumerate(message["instructions"])]
    for group in tx["meta"].get("innerInstructions") or []:
        instructions += [(f"inner:{group['index']}:{i}", ix) for i, ix in enumerate(group["instructions"])]
    found = []
    for location, ix in instructions:
        index = ix.get("programIdIndex")
        if type(index) is not int or not 0 <= index < len(keys):
            raise ValueError("Invalid program index")
        if keys[index] != DBC or b58decode(ix.get("data", ""))[:8] != MIGRATE:
            continue
        if b58decode(ix["data"]) != MIGRATE:
            raise ValueError("Unexpected migration instruction arguments")
        accounts = ix.get("accounts", [])
        if len(accounts) < 25 or any(type(i) is not int or not 0 <= i < len(keys) for i in accounts):
            raise ValueError("Invalid migration accounts")
        if keys[accounts[12]] != DAMM or keys[accounts[3]] != "FhVo3mqL8PW5pH5U2CN4XE33DokiyZnUwuGpH2hmHLuM":
            raise ValueError("Migration program/authority mismatch")
        found.append({"instruction": location, "virtual_pool": keys[accounts[0]],
                      "config": keys[accounts[2]], "pool": keys[accounts[4]],
                      "base_mint": keys[accounts[13]], "quote_mint": keys[accounts[14]],
                      "token_a_vault": keys[accounts[15]], "token_b_vault": keys[accounts[16]]})
    return found
