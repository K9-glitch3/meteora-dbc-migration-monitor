"""Generate clearly labelled synthetic edge-case captures, then freeze them."""
import copy
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"tests"))
from fixtures import captures, account
from dbc_monitor.records import canonical, SCHEMA
from dbc_monitor.replay import build, export

ROOT = Path(__file__).resolve().parents[1]


def main():
    root = ROOT/"evidence"/"synthetic-v1"
    root.mkdir(exist_ok=True)
    if (root/"manifest.json").exists():
        raise SystemExit("Synthetic fixture is already frozen")
    rows = captures()
    rows[-1:-1] = [
        {**copy.deepcopy(rows[4]), "result": {"context": {"slot": 103}, "value": account(data=["AA==","base64"])}},
        {**copy.deepcopy(rows[4]), "result": {"context": {"slot": 104}, "value": account(owner="11111111111111111111111111111111")}},
        {**copy.deepcopy(rows[4]), "result": {"context": {"slot": 105}, "value": None}},
        {**copy.deepcopy(rows[4]), "result": {"context": {"slot": 99}, "value": account()}},
        {"capture_version": "1.0", "sequence": 0, "observed_at": rows[0]["observed_at"],
         "kind": "gap", "reason": "connection_lost", "epoch": 1},
    ]
    for i,row in enumerate(rows): row["sequence"] = i+1
    (root/"capture.jsonl").write_bytes(b"".join(canonical(r)+b"\n" for r in rows))
    build(root,source="synthetic_test")
    (ROOT/"docs"/"data").mkdir(exist_ok=True)
    export(root,ROOT/"docs"/"data"/"synthetic.json")
    (ROOT/"docs"/"observation.schema.json").write_bytes(canonical(SCHEMA)+b"\n")


if __name__ == "__main__": main()
