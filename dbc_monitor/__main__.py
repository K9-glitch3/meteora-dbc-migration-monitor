"""Command-line entry point for the retained evidence check."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .evidence import validate_evidence


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path, help="Path to aggregate JSON evidence")
    args = parser.parse_args()
    data = json.loads(args.evidence.read_text(encoding="utf-8"))
    print(json.dumps(validate_evidence(data).as_dict(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
