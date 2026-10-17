"""Run only the read-only continuous collector and public JSON API."""
import argparse
import asyncio
from pathlib import Path
import sys
import signal

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dbc_monitor.live import serve
from scripts.capture_readiness import capture


async def main(args):
    task = asyncio.create_task(serve(args.data, args.port, readiness_capture=capture, host=args.host))
    if sys.platform != "win32":
        asyncio.get_running_loop().add_signal_handler(signal.SIGTERM, task.cancel)
    try:
        await task
    except asyncio.CancelledError:
        pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8898)
    parser.add_argument("--host", choices=("127.0.0.1", "0.0.0.0"), default="127.0.0.1")
    args = parser.parse_args()
    asyncio.run(main(args))
