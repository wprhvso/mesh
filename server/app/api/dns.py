from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import Client, Runner, DNSRecord
from app.core.auth import require_admin, Identity

router = APIRouter()

@router.get("/dns")
def list_dns_records(identity: Identity = Depends(require_admin), db: Session = Depends(get_db)):
    records = [
        {"domain": "server.mesh", "ip": "10.10.1.1", "description": "Primary Mesh Gateway & Control Plane"},
        {"domain": "server1.mesh", "ip": "10.10.1.1", "description": "Primary Mesh Gateway Alias"},
    ]
    for c in db.query(Client).filter(Client.is_active == True).all():
        records.append({"domain": c.domain, "ip": c.ip, "description": f"Client device: {c.name}"})
    for r in db.query(Runner).all():
        records.append({"domain": f"runner{r.node_id}.mesh", "ip": r.mesh_ip, "description": f"Azure Runner node #{r.node_id}"})
    for cr in db.query(DNSRecord).all():
        records.append({"domain": cr.domain, "ip": cr.ip, "description": "Custom alias record"})
    return records
