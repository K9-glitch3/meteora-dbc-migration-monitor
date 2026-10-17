"""Bounded external observation of the public API, not a coverage or uptime proof."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time
from urllib.request import urlopen

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from dbc_monitor.records import digest, VALIDATOR


def fetch(url):
    with urlopen(url,timeout=15) as response:
        assert "no-store" in response.headers.get("Cache-Control","")
        raw=response.read(5_000_001)
        assert len(raw)<=5_000_000
        return json.loads(raw)


def check(endpoint, seconds):
    samples=[]
    deadline=time.monotonic()+seconds
    while True:
        feed=fetch(endpoint+"/v1/feed.json")
        assert feed["api_version"]=="2.0" and feed["mode"]=="continuous_live"
        assert feed["continuous_coverage"] is False
        health=feed["health"]
        assert health["status"] in ("live","degraded"), health
        timestamp=datetime.fromisoformat(health["last_message_at"].replace("Z","+00:00"))
        assert -5 <= (datetime.now(timezone.utc)-timestamp).total_seconds() <= 30
        samples.append({"health":health,"migrations":len(feed["migrations"]),
                        "pool_states":len(feed["pool_states"]),"readiness":len(feed["readiness"]),
                        "readiness_status":feed["readiness_status"]})
        if time.monotonic()>=deadline:break
        time.sleep(min(10,max(0,deadline-time.monotonic())))
    first,last=samples[0]["health"],samples[-1]["health"]
    assert first["epoch"]==last["epoch"], "Unexpected process restart during interval"
    assert last["last_slot"]>first["last_slot"]
    assert last["counters"]["log_notifications"]>first["counters"]["log_notifications"]
    verified=[]
    for row in feed["migrations"][:5]:
        for identifier in row["evidence_ids"]:
            evidence=fetch(endpoint+"/v1/evidence/"+identifier)
            observation=evidence["observation"]
            VALIDATOR.validate(observation)
            if evidence["capture_retained"]:
                assert digest(evidence["capture"])==observation["capture_sha256"]
                verified.append(identifier)
    return {"checked_at":datetime.now(timezone.utc).isoformat(),"endpoint":endpoint,
            "scope":"bounded public API progress and retained hash checks; not complete coverage or uptime",
            "seconds":seconds,"samples":samples,"verified_evidence_ids":verified}


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--url",required=True)
    p.add_argument("--seconds",type=int,default=120)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    if not 10<=a.seconds<=600:raise ValueError("Use a bounded 10-600 second observation")
    result=check(a.url.rstrip("/"),a.seconds)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open("x",encoding="utf-8") as out:
        json.dump(result,out,indent=2)
    print(json.dumps({"samples":len(result["samples"]),"hash_checks":len(result["verified_evidence_ids"]),"passed":True}))
