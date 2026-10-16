"""Deterministic replay, checksummed manifests and browser dataset export."""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess

from .records import SCHEMA, canonical, derive, digest, VALIDATOR


def read_jsonl(path):
    with Path(path).open(encoding="utf-8") as handle:
        for line, text in enumerate(handle, 1):
            if len(text) > 8_000_000:
                raise ValueError(f"Record exceeds limit on line {line}")
            yield json.loads(text, parse_constant=lambda s: (_ for _ in ()).throw(ValueError(s)))


def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def code_hash():
    root = Path(__file__).parent
    return digest({p.name: file_hash(p) for p in sorted(root.iterdir()) if p.suffix in (".py", ".json")})


def replay(directory, *, source="mainnet_capture", max_age=120):
    root = Path(directory)
    captures = list(read_jsonl(root / "capture.jsonl"))
    observations = derive(captures, source=source, max_age=max_age)
    return captures, observations


def build(directory, *, source="mainnet_capture", max_age=120):
    root = Path(directory)
    if (root / "manifest.json").exists():
        raise ValueError("Run is frozen; verify it or use another output directory")
    captures, observations = replay(root, source=source, max_age=max_age)
    if not captures or captures[0]["kind"] != "run_start" or captures[-1]["kind"] != "run_end":
        raise ValueError("Cannot freeze an incomplete run")
    payload = b"".join(canonical(row)+b"\n" for row in observations)
    (root / "observations.jsonl").write_bytes(payload)
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, stderr=subprocess.DEVNULL, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        commit = "unavailable"
    manifest = {"manifest_version": "1.0", "source": source, "software_version": "0.2.0", "git_commit": commit,
                "code_sha256": code_hash(), "schema_sha256": digest(SCHEMA), "max_age_seconds": max_age,
                "started_at": captures[0]["observed_at"], "ended_at": captures[-1]["observed_at"],
                "configuration": captures[0], "run_result": captures[-1],
                "capture_records": len(captures), "observations": len(observations),
                "verdicts": dict(sorted(Counter(o["verdict"] for o in observations).items())),
                "kinds": dict(sorted(Counter(o["kind"] for o in observations).items())),
                "comparison_scope": "migration identity only; no swap quote comparison",
                "files": {name: file_hash(root/name) for name in ("capture.jsonl", "observations.jsonl")}}
    (root/"manifest.json").write_bytes(canonical(manifest)+b"\n")
    return manifest


def verify(directory):
    root = Path(directory)
    manifest = json.loads((root/"manifest.json").read_text())
    if manifest["manifest_version"] != "1.0" or set(manifest["files"]) != {"capture.jsonl", "observations.jsonl"}:
        raise ValueError("Unsupported manifest contract")
    for name, expected in manifest["files"].items():
        if file_hash(root/name) != expected:
            raise ValueError("Checksum mismatch: " + name)
    captures, records = replay(root, source=manifest["source"], max_age=manifest["max_age_seconds"])
    saved = list(read_jsonl(root/"observations.jsonl"))
    if records != saved:
        raise ValueError("Replay differs from stored observations")
    for record in saved:
        VALIDATOR.validate(record)
    if manifest["schema_sha256"] != digest(SCHEMA):
        raise ValueError("Schema checksum mismatch")
    if manifest["capture_records"] != len(captures) or manifest["observations"] != len(records):
        raise ValueError("Manifest totals mismatch")
    if manifest["verdicts"] != dict(Counter(o["verdict"] for o in records)) or manifest["kinds"] != dict(Counter(o["kind"] for o in records)):
        raise ValueError("Manifest verdict totals mismatch")
    if manifest["configuration"] != captures[0] or manifest["run_result"] != captures[-1]:
        raise ValueError("Manifest run metadata mismatch")
    if captures[0]["kind"] != "run_start" or captures[-1]["kind"] != "run_end":
        raise ValueError("Incomplete run boundaries")
    if manifest["started_at"] != captures[0]["observed_at"] or manifest["ended_at"] != captures[-1]["observed_at"]:
        raise ValueError("Manifest timestamps mismatch")
    if manifest["comparison_scope"] != "migration identity only; no swap quote comparison":
        raise ValueError("Manifest comparison scope mismatch")
    return {"verified": True, "observations": len(records), "capture_records": len(captures),
            "same_code": manifest["code_sha256"] == code_hash(), "source": manifest["source"]}


def export(directory, destination):
    verify(directory)
    root = Path(directory)
    manifest = json.loads((root/"manifest.json").read_text())
    records = list(read_jsonl(root/"observations.jsonl"))
    Path(destination).write_bytes(canonical({"manifest": manifest, "observations": records})+b"\n")
