"""CI gate for the independently derived pilot API and SDK reference report."""
import json
import base64
import copy
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from dbc_monitor.lifecycle import readiness
from dbc_monitor.records import digest
from scripts.capture_readiness import decode
from scripts.build_feed import build
from scripts.compare_quotes import compare


def verify_readiness(receipt):
    assert digest(receipt["responses"]) == receipt["raw_responses_sha256"], "Readiness raw hash mismatch"
    responses=[r for r in receipt["responses"] if r["method"] == "getMultipleAccounts"]
    assert len(responses)>=2, "No paired pool/config snapshot"
    last=responses[-1]
    assert last["params"][1]["commitment"] == "finalized"
    keys, accounts=last["params"][0],last["result"]["value"]
    assert len(keys)==len(accounts)
    pools=[p for p in decode([{"address":k,"account":a} for k,a in zip(keys,accounts)]) if p]
    configs={c["address"]:c for c in decode([{"address":k,"account":a,"kind":"config"} for k,a in zip(keys,accounts)]) if c}
    expected=[]
    for pool in pools:
        row=readiness(pool,configs.get(pool["config"]))
        row.update(slot=last["result"]["context"]["slot"],observed_at=last["observed_at"],commitment="finalized")
        row["id"]=digest(row);expected.append(row)
    assert expected==receipt["items"], "Readiness differs from captured account bytes"
    first=next((k,a) for k,a in zip(keys,accounts) if k==pools[0]["address"])
    negative=[]
    for mutation in ("owner","length","discriminator"):
        account=copy.deepcopy(first[1])
        if mutation=="owner":account["owner"]="invalid"
        else:
            raw=bytearray(base64.b64decode(account["data"][0]))
            if mutation=="length":raw.append(0)
            else:raw[0]^=1
            account["data"][0]=base64.b64encode(raw).decode()
        negative.append({"address":first[0],"account":account})
    assert decode(negative)==[None,None,None], "Readiness decoder failed negative controls"
    return len(expected)


def check():
    assert not list((ROOT/"node_modules/bigint-buffer").rglob("*.node")), "Native bigint-buffer must not be built"
    feed_path=ROOT/"docs/api/v1/feed.json"
    feed=json.loads(feed_path.read_text())
    readiness_path=ROOT/"evidence/readiness-2026-10-16.json"
    pools=verify_readiness(json.loads(readiness_path.read_text()))
    assert feed==build(ROOT/"evidence"/feed["source_run"],readiness_path), "Feed differs from source evidence"
    saved=json.loads((ROOT/"docs/api/v1/quotes.json").read_text())
    # The comparison report explicitly identifies its source independently of the feed.
    captures=list((ROOT/"evidence").glob("*/capture.jsonl"))
    from dbc_monitor.replay import file_hash
    source=next(p for p in captures if file_hash(p)==saved["source_capture_sha256"])
    actual=compare(source)
    assert saved==actual, "SDK comparison changed"
    assert actual["cases"] and not actual["counts"].get("MISMATCH"), "No passing SDK reference cases"
    print(json.dumps({"sdk_matches":actual["counts"],"replayed_readiness_pools":pools,"feed_migrations":len(feed["migrations"])}))


if __name__=="__main__":check()
