import asyncio
import os
import subprocess
import time
import urllib.request
import json
import datetime
from app.db.session import SessionLocal
from app.db.models import Client, Runner, GitHubAccount, SSHKey, DNSRecord

reconcile_event = asyncio.Event()
last_healthy_set = set()

def trigger_reconcile():
    reconcile_event.set()

async def reconcile_loop():
    while True:
        try:
            await asyncio.to_thread(run_reconciliation)
        except Exception:
            pass
        try:
            await asyncio.wait_for(reconcile_event.wait(), timeout=5.0)
            reconcile_event.clear()
        except asyncio.TimeoutError:
            pass

def run_reconciliation():
    db = SessionLocal()
    try:
        reconcile_clients(db)
        reconcile_dns(db)
        reconcile_ssh(db)
        reconcile_routing(db)
        reconcile_fleet(db)
    finally:
        db.close()

def reconcile_clients(db):
    clients = db.query(Client).filter(Client.is_active == True).all()
    for c in clients:
        subprocess.run([
            "awg", "set", "awg0",
            "peer", c.public_key,
            "allowed-ips", f"{c.ip}/32"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def reconcile_dns(db):
    clients = db.query(Client).filter(Client.is_active == True).all()
    runners = db.query(Runner).all()
    custom_records = db.query(DNSRecord).all()

    lines = [
        "address /server.mesh/10.10.1.1",
        "address /server1.mesh/10.10.1.1"
    ]
    for c in clients:
        lines.append(f"address /{c.domain}/{c.ip}")
    for r in runners:
        lines.append(f"address /runner{r.node_id}.mesh/{r.mesh_ip}")
    for cr in custom_records:
        lines.append(f"address /{cr.domain}/{cr.ip}")

    new_content = "\n".join(lines) + "\n"
    zone_path = "/etc/smartdns/mesh-zone.conf"
    current_content = ""
    if os.path.exists(zone_path):
        with open(zone_path, "r", encoding="utf-8") as f:
            current_content = f.read()

    smartdns_conf_path = "/etc/smartdns/smartdns.conf"
    if os.path.exists(smartdns_conf_path):
        with open(smartdns_conf_path, "r", encoding="utf-8") as sf:
            s_content = sf.read()
        if "mesh-zone.conf" not in s_content:
            with open(smartdns_conf_path, "a", encoding="utf-8") as sf:
                sf.write("\nconf-file /etc/smartdns/mesh-zone.conf\n")
            subprocess.run(["systemctl", "restart", "smartdns"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if new_content != current_content:
        with open(zone_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        subprocess.run(["systemctl", "restart", "smartdns"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def reconcile_ssh(db):
    keys = db.query(SSHKey).all()
    lines = [k.public_key.strip() for k in keys if k.public_key.strip()]
    if os.path.exists("/home/unsafie/.ssh/id_ed25519_mesh.pub"):
        with open("/home/unsafie/.ssh/id_ed25519_mesh.pub") as f:
            lines.append(f.read().strip())
    new_auth = "\n".join(set(lines)) + "\n"

    auth_path = "/root/.ssh/authorized_keys"
    current_auth = ""
    if os.path.exists(auth_path):
        with open(auth_path, "r", encoding="utf-8") as f:
            current_auth = f.read()

    if new_auth != current_auth:
        os.makedirs("/root/.ssh", exist_ok=True)
        with open(auth_path, "w", encoding="utf-8") as f:
            f.write(new_auth)
        os.chmod(auth_path, 0o600)

def reconcile_routing(db):
    global last_healthy_set
    runners = db.query(Runner).all()
    now = datetime.datetime.utcnow()

    healthy_runners = []
    current_healthy_ids = set()

    for r in runners:
        res = subprocess.run(["ping", "-c", "1", "-W", "1", r.tun_client_ip], stdout=subprocess.DEVNULL)
        is_healthy = (res.returncode == 0)
        r.healthy = is_healthy
        r.weight = 1
        if is_healthy:
            r.last_seen = now
            r.status = "active"
            healthy_runners.append(r)
            current_healthy_ids.add(r.id)
        else:
            r.status = "offline"

    db.commit()

    if current_healthy_ids != last_healthy_set:
        if healthy_runners:
            nexthops = []
            for r in healthy_runners:
                nexthops.extend(["nexthop", "via", r.tun_client_ip, "dev", r.tun_name, "weight", "1"])
            cmd = ["ip", "route", "replace", "default", "table", "200"] + nexthops
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            default_gw = os.environ.get("DEFAULT_GW", "91.230.210.1")
            default_iface = os.environ.get("DEFAULT_IFACE", "ens3")
            subprocess.run([
                "ip", "route", "replace", "default", "via", default_gw,
                "dev", default_iface, "table", "200"
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        last_healthy_set = current_healthy_ids

def reconcile_fleet(db):
    accounts = db.query(GitHubAccount).filter(GitHubAccount.is_active == True).all()
    now = time.time()
    active_runners = db.query(Runner).filter(
        Runner.healthy == True,
        Runner.status == "active"
    ).count()

    for acc in accounts:
        last_disp = acc.last_dispatched_at.timestamp() if acc.last_dispatched_at else 0
        if active_runners < 10 and (now - last_disp > 1800):
            try:
                url = f"https://api.github.com/repos/{acc.repo_name}/actions/workflows/mesh.yml/dispatches"
                req = urllib.request.Request(url, data=json.dumps({"ref": "main"}).encode(), headers={
                    "Authorization": f"token {acc.pat_token}",
                    "Accept": "application/vnd.github.v3+json",
                    "Content-Type": "application/json"
                })
                urllib.request.urlopen(req, timeout=10)
                acc.last_dispatched_at = datetime.datetime.utcnow()
                db.commit()
            except Exception:
                pass
