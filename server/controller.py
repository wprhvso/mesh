#!/usr/bin/env python3
import json
import os
import subprocess
import time
import urllib.request

REPO = os.environ.get("GITHUB_REPOSITORY", "wprhvso/mesh")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
TARGET_RUNNERS = 20

def get_active_runs():
    url = f"https://api.github.com/repos/{REPO}/actions/runs?status=in_progress"
    req = urllib.request.Request(url, headers={
        "Authorization": f"token {TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    })
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            return data.get("total_count", 0)
    except Exception:
        return 0

def trigger_workflow():
    url = f"https://api.github.com/repos/{REPO}/actions/workflows/mesh.yml/dispatches"
    req = urllib.request.Request(url, data=json.dumps({"ref": "main"}).encode(), headers={
        "Authorization": f"token {TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json"
    })
    urllib.request.urlopen(req)

def check_nodes():
    active = []
    for i in range(1, TARGET_RUNNERS + 1):
        ip = f"10.200.0.{i + 10}"
        res = subprocess.run(["ping", "-c", "1", "-W", "1", ip], stdout=subprocess.DEVNULL)
        if res.returncode == 0:
            active.append(ip)
    return active

def main():
    while True:
        nodes = check_nodes()
        if len(nodes) < 15 and TOKEN:
            trigger_workflow()
        time.sleep(30)

if __name__ == "__main__":
    main()
