"""Run only the read-only continuous collector and public JSON API."""
import argparse
import asyncio
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dbc_monitor.live import serve
from scripts.capture_readiness import capture

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8898)
    args = parser.parse_args()
    asyncio.run(serve(args.data, args.port, readiness_capture=capture))
