import asyncio
import os
import subprocess
import time
import urllib.request
import json
from app.db.session import SessionLocal
from app.db.models import Client, Runner, GitHubAccount, SSHKey, DNSRecord

reconcile_event = asyncio.Event()

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

    if new_content != current_content:
        with open(zone_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        subprocess.run(["systemctl", "reload", "smartdns"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

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
    runners = db.query(Runner).all()
    healthy_tuns = []
    for r in runners:
        res = subprocess.run(["ping", "-c", "1", "-W", "1", r.tun_client_ip], stdout=subprocess.DEVNULL)
        is_healthy = (res.returncode == 0)
        r.healthy = is_healthy
        if is_healthy:
            healthy_tuns.append((r.tun_name, r.tun_client_ip))
    db.commit()

    if healthy_tuns:
        nexthops = []
        for tun, client_ip in healthy_tuns:
            nexthops.extend(["nexthop", "via", client_ip, "dev", tun, "weight", "1"])
        cmd = ["ip", "route", "replace", "default", "scope", "global", "table", "200"] + nexthops
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        default_gw = os.environ.get("DEFAULT_GW", "91.230.210.1")
        default_iface = os.environ.get("DEFAULT_IFACE", "ens3")
        subprocess.run([
            "ip", "route", "replace", "default", "via", default_gw,
            "dev", default_iface, "table", "200"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def reconcile_fleet(db):
    accounts = db.query(GitHubAccount).filter(GitHubAccount.is_active == True).all()
    for acc in accounts:
        runners_count = db.query(Runner).filter(Runner.account_id == acc.id, Runner.healthy == True).count()
        now = time.time()
        last_disp = acc.last_dispatched_at.timestamp() if acc.last_dispatched_at else 0
        if runners_count < 15 and (now - last_disp > 300):
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
