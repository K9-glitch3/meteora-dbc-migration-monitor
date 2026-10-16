"""Publish deterministic, timestamped read-only pilot API artifacts."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dbc_monitor.lifecycle import migration_rows
from dbc_monitor.records import canonical, digest
from dbc_monitor.replay import verify, read_jsonl, file_hash


def build(directory, readiness_path):
    verify(directory)
    manifest = json.loads((directory/"manifest.json").read_text())
    observations = list(read_jsonl(directory/"observations.jsonl"))
    read = json.loads(readiness_path.read_text())
    if digest(read["responses"]) != read["raw_responses_sha256"]:
        raise ValueError("Readiness receipt checksum mismatch")
    return {"api_version":"1.0", "mode":"recorded_snapshot", "continuous_coverage":False,
            "migration_recorded_until":manifest["ended_at"], "readiness_recorded_until":read["ended_at"],
            "source_run":directory.name, "source_manifest_sha256":file_hash(directory/"manifest.json"),
            "migrations":migration_rows(observations), "readiness":read["items"], "readiness_errors":read["errors"],
            "health":[r for r in observations if r["kind"] == "health"],
            "limits":{"stale_after_seconds":300, "readiness_sample":read["sampling"], "watchlist_storage":"browser_local_only"}}


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("directory", type=Path)
    p.add_argument("readiness", type=Path)
    p.add_argument("output", type=Path)
    a = p.parse_args()
    feed = build(a.directory, a.readiness)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_bytes(canonical(feed)+b"\n")
    print(json.dumps({"migrations":len(feed["migrations"]), "readiness":len(feed["readiness"])}))
