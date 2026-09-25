from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import Runner
from app.core.auth import require_admin, Identity

router = APIRouter()

@router.get("/runners")
def list_runners(identity: Identity = Depends(require_admin), db: Session = Depends(get_db)):
    runners = db.query(Runner).order_by(Runner.node_id).all()
    return [
        {
            "id": r.id,
            "node_id": r.node_id,
            "mesh_ip": r.mesh_ip,
            "tun_client_ip": r.tun_client_ip,
            "egress_ip": r.egress_ip,
            "status": r.status,
            "healthy": r.healthy,
            "rtt_mesh": r.rtt_mesh,
            "rtt_egress": r.rtt_egress,
            "rtt_total": r.rtt_total,
            "weight": r.weight,
            "last_seen": r.last_seen.isoformat() if r.last_seen else None
        }
        for r in runners
    ]
