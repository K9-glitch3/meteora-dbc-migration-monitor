"""Run on the deployment host; optionally crash only this collector to test restart."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import time
from urllib.request import urlopen

COLLECTOR = "dbc-monitor-collector-1"
PROXY = "dbc-monitor-proxy-1"
URL = "https://dbc-monitor.188-166-88-35.sslip.io"


def command(*args):
    return subprocess.check_output(args, text=True, timeout=45).strip()


def inspect(name):
    return json.loads(command("docker", "inspect", name))[0]


def get(path):
    with urlopen(URL + path, timeout=10) as response:
        return json.load(response)


def verify(output, exercise):
    started = datetime.now(timezone.utc).isoformat()
    before = inspect(COLLECTOR)
    for name, maximum in ((COLLECTOR, 512*1024**2), (PROXY, 128*1024**2)):
        info = inspect(name)
        config = info["HostConfig"]
        assert config["ReadonlyRootfs"] and config["Memory"] == maximum
        assert config["RestartPolicy"]["Name"] == "unless-stopped"
        assert config["CapDrop"] == ["ALL"]
        assert info["Config"]["User"] == "65532:65532"
    assert not before["HostConfig"]["PortBindings"]
    others = {name: inspect(name)["State"]["StartedAt"]
              for name in command("docker", "ps", "--format", "{{.Names}}").splitlines()
              if name not in (COLLECTOR, PROXY)}
    feed = get("/v1/feed.json")
    evidence_id = feed["health_events"][0]["id"]
    evidence = get("/v1/evidence/" + evidence_id)
    result = {"started_at": started, "endpoint": URL, "security_limits_verified": True,
              "collector_image": before["Image"], "proxy_image": inspect(PROXY)["Image"],
              "restart_exercised": exercise, "epoch_before": feed["health"]["epoch"]}
    if exercise:
        kill = ("import os,signal; from pathlib import Path; "
                "pids=[int(p.name) for p in Path('/proc').iterdir() if p.name.isdigit() "
                "and (p/'cmdline').exists() and "
                "(p/'cmdline').read_bytes().split(bytes([0]))[:2]==[b'python',b'scripts/serve_live.py']]; "
                "assert len(pids)==1; os.kill(pids[0],signal.SIGKILL)")
        subprocess.run(["docker", "exec", COLLECTOR, "python", "-c", kill], timeout=15)
        deadline = time.monotonic() + 150
        while time.monotonic() < deadline:
            try:
                health = get("/healthz")
                if health["epoch"] != result["epoch_before"] and health["status"] in ("live", "degraded"):
                    break
            except Exception:
                pass
            time.sleep(3)
        else:
            raise RuntimeError("Collector did not recover")
        assert inspect(COLLECTOR)["RestartCount"] > before["RestartCount"]
        assert get("/v1/evidence/" + evidence_id) == evidence
        result.update(epoch_after=health["epoch"], retained_evidence_id=evidence_id,
                      retained_evidence_unchanged=True,
                      restart_count=inspect(COLLECTOR)["RestartCount"])
    assert all(inspect(name)["State"]["StartedAt"] == start for name, start in others.items())
    result.update(other_containers_unchanged=True, finished_at=datetime.now(timezone.utc).isoformat())
    with Path(output).open("x") as handle:
        json.dump(result, handle, indent=2)
    print(json.dumps(result))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--exercise-restart", action="store_true")
    args = parser.parse_args()
    verify(args.output, args.exercise_restart)
