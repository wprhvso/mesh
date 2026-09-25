from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import SSHKey
from app.core.auth import require_admin, Identity
from app.core.reconciler import trigger_reconcile

router = APIRouter()

class SSHKeyCreate(BaseModel):
    title: str
    public_key: str

@router.get("/ssh")
def list_ssh_keys(identity: Identity = Depends(require_admin), db: Session = Depends(get_db)):
    return db.query(SSHKey).all()

@router.post("/ssh")
def create_ssh_key(payload: SSHKeyCreate, identity: Identity = Depends(require_admin), db: Session = Depends(get_db)):
    key = SSHKey(title=payload.title, public_key=payload.public_key.strip())
    db.add(key)
    db.commit()
    db.refresh(key)
    trigger_reconcile()
    return key

@router.delete("/ssh/{key_id}")
def delete_ssh_key(key_id: int, identity: Identity = Depends(require_admin), db: Session = Depends(get_db)):
    key = db.query(SSHKey).filter(SSHKey.id == key_id).first()
    if not key:
        raise HTTPException(status_code=404, detail="Key not found")
    db.delete(key)
    db.commit()
    trigger_reconcile()
    return {"status": "deleted"}
