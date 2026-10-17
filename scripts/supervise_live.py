"""Own only this pilot's two child processes; publish only its endpoint configuration."""
import argparse
import base64
from collections import deque
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import threading
import time
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
REPO = "K9-glitch3/meteora-dbc-migration-monitor"
ENDPOINT = re.compile(r"https://[a-z0-9]+(?:-[a-z0-9]+)*\.trycloudflare\.com\b")
FLAGS = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


def publish(endpoint):
    if not ENDPOINT.fullmatch(endpoint):
        raise ValueError("Unapproved tunnel endpoint")
    with urlopen(endpoint+"/healthz", timeout=15) as response:
        health = json.load(response)
    if health.get("status") not in ("live", "degraded"):
        return False
    gh = shutil.which("gh")
    if not gh:
        raise RuntimeError("GitHub CLI unavailable")
    path = "repos/"+REPO+"/contents/docs/live-config.json"
    current = subprocess.run([gh, "api", path], capture_output=True, check=True, timeout=30, creationflags=FLAGS)
    current = json.loads(current.stdout)
    config = {"enabled": True, "endpoint": endpoint, "version": "0.4.0"}
    if json.loads(base64.b64decode(current["content"])) == config:
        return True
    payload = {"message": "ops: refresh live pilot endpoint", "sha": current["sha"],
               "content": base64.b64encode((json.dumps(config, separators=(",", ":"))+"\n").encode()).decode(),
               "branch": "master"}
    subprocess.run([gh, "api", "--method", "PUT", path, "--input", "-"],
                   input=json.dumps(payload).encode(), capture_output=True, check=True, timeout=30, creationflags=FLAGS)
    return True


def run(data, tunnel, publish_enabled):
    data.mkdir(parents=True, exist_ok=True)
    lock = (data/"supervisor.lock").open("a+b")
    if os.name == "nt":
        import msvcrt
        lock.seek(0)
        if not lock.read(1):
            lock.write(b"0");lock.flush()
        lock.seek(0)
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        import fcntl
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    children, tails = {}, {"collector": deque(maxlen=60), "tunnel": deque(maxlen=60)}
    endpoint = [None]
    published, last_publish, restarts = None, 0, {"collector": 0, "tunnel": 0}
    last_start = {"collector": 0, "tunnel": 0}
    status_error = None

    def start(name, command):
        process = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                   encoding="utf-8", errors="replace", creationflags=FLAGS)
        def read():
            for line in process.stdout:
                tails[name].append(line[-2000:].rstrip())
                if name == "tunnel":
                    match = ENDPOINT.search(line)
                    if match:
                        endpoint[0] = match[0]
            process.stdout.close()
        threading.Thread(target=read, daemon=True).start()
        children[name] = process
        last_start[name] = time.monotonic()
        restarts[name] += 1

    try:
        while not (data/"STOP").exists():
            for name, command in (
                ("collector", [sys.executable, str(ROOT/"scripts/serve_live.py"), "--data", str(data), "--port", "8898"]),
                ("tunnel", [str(tunnel), "tunnel", "--url", "http://127.0.0.1:8898", "--no-autoupdate",
                            "--protocol", "http2", "--metrics", "127.0.0.1:0"])):
                if name not in children or (children[name].poll() is not None and time.monotonic()-last_start[name] >= 30):
                    if name == "tunnel":
                        endpoint[0] = None
                    start(name, command)
            if publish_enabled and endpoint[0] and endpoint[0] != published and time.monotonic()-last_publish > 300:
                last_publish = time.monotonic()
                try:
                    if publish(endpoint[0]):
                        published, status_error = endpoint[0], None
                except Exception as exc:
                    status_error = type(exc).__name__
            status = {"supervisor_pid": os.getpid(), "updated_at_unix": time.time(), "endpoint": endpoint[0],
                      "published_endpoint": published, "publish_error": status_error,
                      "pids": {k: v.pid for k,v in children.items()}, "starts": restarts,
                      "exit_codes": {k: v.poll() for k,v in children.items()},
                      "logs": {k: list(v) for k,v in tails.items()}}
            pending = data/"supervisor-status.tmp"
            pending.write_text(json.dumps(status, indent=2), encoding="utf-8")
            pending.replace(data/"supervisor-status.json")
            time.sleep(2)
    finally:
        for process in children.values():
            if process.poll() is None:
                process.terminate()
        for process in children.values():
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill();process.wait(timeout=10)
        lock.close()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--data", type=Path, default=ROOT/"runs/live")
    p.add_argument("--tunnel", type=Path, default=ROOT/"runs/live-tools/cloudflared.exe")
    p.add_argument("--publish", action="store_true")
    a = p.parse_args()
    run(a.data.resolve(), a.tunnel.resolve(), a.publish)
