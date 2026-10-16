"""Copy a completed local run into public evidence without altering its bytes."""
import argparse
from pathlib import Path
import shutil
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dbc_monitor.replay import build, export, file_hash, verify

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("name")
    args = parser.parse_args()
    if not args.name or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in args.name):
        parser.error("Use a lowercase alphanumeric run name with hyphens")
    target = ROOT / "evidence" / args.name
    target.mkdir(exist_ok=False)
    shutil.copyfile(args.run / "capture.jsonl", target / "capture.jsonl")
    assert file_hash(args.run / "capture.jsonl") == file_hash(target / "capture.jsonl")
    build(target)
    export(target, ROOT / "docs" / "data" / (args.name + ".json"))
    print(verify(target))


if __name__ == "__main__":
    main()
