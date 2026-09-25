import datetime
import os
import subprocess
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db.models import Runner

router = APIRouter()
AUTH_TOKEN = os.environ.get("AUTH_TOKEN", "sec_7d4874b68cc6ff2ff55d81ce6a69f29f6912eb7d")
WG_IFACE = "wg-mesh"

class RegisterPayload(BaseModel):
    node_id: int
    pubkey: str
    egress_rtt: float = 5.0
    egress_ip: str = None

class HeartbeatPayload(BaseModel):
    node_id: int
    egress_rtt: float = 5.0
    uptime: int = 0
    status: str = "active"
    egress_ip: str = None

def get_server_pubkey():
    try:
        with open("/etc/wireguard/mesh_public.key") as f:
            return f.read().strip()
    except Exception:
        res = subprocess.run(["wg", "show", WG_IFACE, "public-key"], capture_output=True, text=True)
        return res.stdout.strip()

@router.post("/register")
def register_runner(payload: RegisterPayload, authorization: str = Header(None)):
    if authorization != f"Bearer {AUTH_TOKEN}":
        raise HTTPException(status_code=401, detail="Unauthorized")

    node_id = payload.node_id
    pubkey = payload.pubkey.strip()
    ip = f"10.200.0.{node_id + 10}"
    tun_name = f"tun{node_id}"
    tun_client_ip = f"10.254.{node_id}.2"
    tun_server_ip = f"10.254.{node_id}.1"

    subprocess.run([
        "wg", "set", WG_IFACE,
        "peer", pubkey,
        "allowed-ips", f"{ip}/32",
        "persistent-keepalive", "15"
    ], check=False)

    subprocess.run(["ip", "tunnel", "del", tun_name], stderr=subprocess.DEVNULL)
    subprocess.run([
        "ip", "tunnel", "add", tun_name, "mode", "ipip",
        "remote", ip, "local", "10.200.0.1", "dev", WG_IFACE
    ], check=False)
    subprocess.run(["ip", "addr", "add", f"{tun_server_ip}/30", "dev", tun_name], check=False)
    subprocess.run(["ip", "link", "set", tun_name, "mtu", "1380", "up"], check=False)

    now = datetime.datetime.utcnow()
    db = SessionLocal()
    try:
        runner = db.query(Runner).filter(Runner.node_id == node_id).first()
        if not runner:
            runner = Runner(
                node_id=node_id,
                mesh_ip=ip,
                tun_name=tun_name,
                tun_client_ip=tun_client_ip,
                tun_server_ip=tun_server_ip,
                pubkey=pubkey,
                egress_ip=payload.egress_ip,
                rtt_egress=payload.egress_rtt,
                status="active",
                healthy=True,
                registered_at=now,
                last_seen=now
            )
            db.add(runner)
        else:
            runner.mesh_ip = ip
            runner.tun_name = tun_name
            runner.tun_client_ip = tun_client_ip
            runner.tun_server_ip = tun_server_ip
            runner.pubkey = pubkey
            runner.status = "active"
            runner.healthy = True
            if payload.egress_ip:
                runner.egress_ip = payload.egress_ip
            if payload.egress_rtt:
                runner.rtt_egress = payload.egress_rtt
            runner.registered_at = now
            runner.last_seen = now
        db.commit()
    finally:
        db.close()

    return {
        "status": "ok",
        "ip": ip,
        "tun_server_ip": tun_server_ip,
        "tun_client_ip": tun_client_ip,
        "server_pubkey": get_server_pubkey(),
        "server_port": 51821
    }

@router.post("/heartbeat")
def heartbeat_runner(payload: HeartbeatPayload, authorization: str = Header(None)):
    if authorization != f"Bearer {AUTH_TOKEN}":
        raise HTTPException(status_code=401, detail="Unauthorized")

    db = SessionLocal()
    try:
        runner = db.query(Runner).filter(Runner.node_id == payload.node_id).first()
        if runner:
            runner.last_seen = datetime.datetime.utcnow()
            runner.rtt_egress = payload.egress_rtt
            runner.status = payload.status
            if payload.egress_ip:
                runner.egress_ip = payload.egress_ip
            db.commit()
            return {"status": "ok", "action": "continue" if payload.status != "draining" else "drain"}
    finally:
        db.close()

    return {"status": "not_found"}
