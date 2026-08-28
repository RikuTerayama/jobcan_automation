"""Start the local launcher, verify its HTTP boundary, and stop it cleanly."""

from __future__ import annotations

import argparse
import http.cookiejar
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import psutil


ROOT = Path(__file__).resolve().parents[1]


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def edge_processes():
    names = {"msedge.exe", "chrome.exe", "chromium.exe"}
    return {proc.pid for proc in psutil.process_iter(["name"]) if (proc.info.get("name") or "").lower() in names}


def wait_request(opener, request, deadline):
    last_error = None
    while time.monotonic() < deadline:
        try:
            return opener.open(request, timeout=1.5)
        except Exception as exc:
            last_error = exc
            time.sleep(0.1)
    raise RuntimeError("local app did not become ready") from last_error


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--executable", help="packaged JobcanTool.exe path")
    args = parser.parse_args()
    port = free_port()
    base = f"http://127.0.0.1:{port}"
    command = [args.executable] if args.executable else [sys.executable, str(ROOT / "local_app.py")]
    command.extend(["--no-browser", "--port", str(port)])
    before = edge_processes()
    started = time.perf_counter()
    process = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    cookie_jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))
    result = {}
    try:
        with wait_request(opener, urllib.request.Request(base + "/autofill"), time.monotonic() + 20) as response:
            html = response.read().decode("utf-8")
            result["http_status"] = response.status
        result["ready_sec"] = round(time.perf_counter() - started, 3)
        token = re.search(r'name="local-csrf-token" content="([^"]+)"', html).group(1)
        with opener.open(base + "/download-template", timeout=5) as response:
            result["template_status"] = response.status
            result["template_zip"] = response.read(4) == b"PK\x03\x04"
        shutdown = urllib.request.Request(
            base + "/local/shutdown",
            data=b"",
            method="POST",
            headers={"Origin": base, "X-CSRF-Token": token},
        )
        with opener.open(shutdown, timeout=5) as response:
            result["shutdown_status"] = response.status
        process.wait(timeout=15)
        result["exit_code"] = process.returncode
        try:
            opener.open(base + "/autofill", timeout=1)
            result["port_closed"] = False
        except Exception:
            result["port_closed"] = True
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=5)
    time.sleep(0.5)
    result["new_browser_processes"] = sorted(edge_processes() - before)
    result["affiliate_count"] = sum(html.count(marker) for marker in ("tag=", "a8.net", "googletagmanager.com", "googlesyndication.com"))
    print(json.dumps(result, ensure_ascii=False))
    expected = {
        "http_status": 200,
        "template_status": 200,
        "template_zip": True,
        "shutdown_status": 200,
        "exit_code": 0,
        "port_closed": True,
        "new_browser_processes": [],
        "affiliate_count": 0,
    }
    return 0 if all(result.get(key) == value for key, value in expected.items()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
