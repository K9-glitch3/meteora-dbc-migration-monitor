"""CI gate: replay every published run and verify the browser data export."""
from pathlib import Path
import json
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from dbc_monitor.replay import verify, read_jsonl
from dbc_monitor.records import SCHEMA

root = Path(__file__).resolve().parents[1]
assert json.loads((root/"docs"/"observation.schema.json").read_text()) == SCHEMA
count = 0
for manifest_path in sorted((root/"evidence").glob("*/manifest.json")):
    directory = manifest_path.parent
    print(directory.name, verify(directory))
    count += 1
for file in sorted((root/"docs"/"data").glob("*.json")):
    if file.name == "index.json": continue
    data = json.loads(file.read_text())
    candidates = [p for p in (root/"evidence").glob("*/manifest.json")
                  if json.loads(p.read_text()) == data["manifest"]]
    assert len(candidates) == 1, f"No unique evidence manifest for {file.name}"
    expected = list(read_jsonl(candidates[0].parent/"observations.jsonl"))
    assert expected == data["observations"], f"Browser export mismatch: {file.name}"
assert count > 0, "No published evidence runs"
print(f"Verified {count} evidence runs and dashboard exports")
