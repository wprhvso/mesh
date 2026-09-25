import io
import base64
import subprocess
import qrcode
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import Client
from app.core.auth import Identity, get_current_identity, require_admin
from app.core.reconciler import trigger_reconcile

router = APIRouter()

class ClientCreate(BaseModel):
    name: str
    is_admin: bool = False

class ClientUpdate(BaseModel):
    is_active: bool = None
    is_admin: bool = None
    domain: str = None

def generate_awg_keys():
    priv = subprocess.run(["awg", "genkey"], capture_output=True, text=True, check=True).stdout.strip()
    pub = subprocess.run(["awg", "pubkey"], input=priv, capture_output=True, text=True, check=True).stdout.strip()
    return priv, pub

def get_server_pubkey():
    try:
        with open("/etc/amnezia/amneziawg/server_private.key") as f:
            priv = f.read().strip()
            return subprocess.run(["awg", "pubkey"], input=priv, capture_output=True, text=True).stdout.strip()
    except Exception:
        return ""

def build_client_config(client: Client):
    server_pub = get_server_pubkey()
    return f"""[Interface]
Address = {client.ip}/32
PrivateKey = {client.private_key}
DNS = 10.10.1.1
Jc = 4
Jmin = 40
Jmax = 70
S1 = 15
S2 = 30
H1 = 123456789
H2 = 987654321
H3 = 135792468
H4 = 246813579

[Peer]
PublicKey = {server_pub}
Endpoint = 91.230.210.17:51820
AllowedIPs = 0.0.0.0/0, ::/0
PersistentKeepalive = 25
"""

@router.get("/clients")
def list_clients(admin: Identity = Depends(require_admin), db: Session = Depends(get_db)):
    return db.query(Client).all()

@router.post("/clients")
def create_client(payload: ClientCreate, admin: Identity = Depends(require_admin), db: Session = Depends(get_db)):
    existing = db.query(Client).filter(Client.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Client name already exists")

    existing_ips = {c.ip for c in db.query(Client).all()}
    allocated_ip = None
    for octet in range(2, 250):
        test_ip = f"10.10.1.{octet}"
        if test_ip not in existing_ips:
            allocated_ip = test_ip
            break

    if not allocated_ip:
        raise HTTPException(status_code=500, detail="No available IP addresses in 10.10.1.0/24")

    priv, pub = generate_awg_keys()
    domain = f"{payload.name}.mesh"

    new_client = Client(
        name=payload.name,
        domain=domain,
        ip=allocated_ip,
        private_key=priv,
        public_key=pub,
        is_admin=payload.is_admin,
        is_active=True
    )
    db.add(new_client)
    db.commit()
    db.refresh(new_client)

    trigger_reconcile()
    return new_client

@router.patch("/clients/{client_id}")
def update_client(client_id: int, payload: ClientUpdate, admin: Identity = Depends(require_admin), db: Session = Depends(get_db)):
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    if payload.is_active is not None:
        client.is_active = payload.is_active
    if payload.is_admin is not None:
        client.is_admin = payload.is_admin
    if payload.domain is not None:
        client.domain = payload.domain

    db.commit()
    db.refresh(client)
    trigger_reconcile()
    return client

@router.delete("/clients/{client_id}")
def delete_client(client_id: int, admin: Identity = Depends(require_admin), db: Session = Depends(get_db)):
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    db.delete(client)
    db.commit()
    trigger_reconcile()
    return {"status": "deleted"}

@router.get("/clients/{client_id}/config")
def get_config(client_id: int, identity: Identity = Depends(get_current_identity), db: Session = Depends(get_db)):
    if not identity.is_admin and identity.client.id != client_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    conf_text = build_client_config(client)
    return Response(
        content=conf_text,
        media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="{client.name}.conf"'}
    )

@router.get("/clients/{client_id}/qr")
def get_qr(client_id: int, identity: Identity = Depends(get_current_identity), db: Session = Depends(get_db)):
    if not identity.is_admin and identity.client.id != client_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    conf_text = build_client_config(client)
    img = qrcode.make(conf_text)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64_qr = base64.b64encode(buf.getvalue()).decode("utf-8")

    return {
        "id": client.id,
        "name": client.name,
        "config_text": conf_text,
        "qr_url": f"data:image/png;base64,{b64_qr}"
    }
