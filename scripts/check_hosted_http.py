"""Bounded public HTTPS boundary check; no credentials or write endpoints."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def check(url):
    checks = []
    for method, path, expected in (
        ("GET", "/healthz", 200), ("HEAD", "/v1/feed.json", 200),
        ("GET", "/", 404), ("GET", "/.env", 404),
        ("GET", "/etc/passwd", 404), ("GET", "/config/", 404),
        ("GET", "/?url=https://example.com", 404),
        ("POST", "/v1/feed.json", 501),
    ):
        request = Request(url + path, method=method, data=b"{}" if method == "POST" else None)
        try:
            response = urlopen(request, timeout=10)
        except HTTPError as error:
            response = error
        with response:
            assert response.status == expected, (method, path, response.status)
            if method in ("GET", "HEAD"):
                assert response.headers["Access-Control-Allow-Origin"] == "https://k9-glitch3.github.io"
                assert "no-store" in response.headers["Cache-Control"]
                assert response.headers["X-Content-Type-Options"] == "nosniff"
            if method == "HEAD":
                assert response.read() == b""
        checks.append({"method": method, "path": path, "status": expected})
    with urlopen(url.replace("https://", "http://", 1) + "/healthz", timeout=10) as response:
        assert response.url == url + "/healthz"
    return {"checked_at": datetime.now(timezone.utc).isoformat(), "endpoint": url,
            "tls_verified": True, "http_redirects_to_https": True, "checks": checks}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = check(args.url.rstrip("/"))
    with Path(args.output).open("x") as handle:
        json.dump(result, handle, indent=2)
    print(json.dumps(result))
