import datetime
import json
import urllib.request
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import GitHubAccount
from app.core.auth import require_admin, Identity

router = APIRouter()

class DonorCreate(BaseModel):
    username: str
    pat_token: str
    repo_name: str
    target_runners: int = 20

@router.get("/donors")
def list_donors(identity: Identity = Depends(require_admin), db: Session = Depends(get_db)):
    return db.query(GitHubAccount).all()

@router.post("/donors")
def create_donor(payload: DonorCreate, identity: Identity = Depends(require_admin), db: Session = Depends(get_db)):
    acc = GitHubAccount(
        username=payload.username,
        pat_token=payload.pat_token,
        repo_name=payload.repo_name,
        target_runners=payload.target_runners,
        is_active=True
    )
    db.add(acc)
    db.commit()
    db.refresh(acc)
    return acc

@router.delete("/donors/{donor_id}")
def delete_donor(donor_id: int, identity: Identity = Depends(require_admin), db: Session = Depends(get_db)):
    acc = db.query(GitHubAccount).filter(GitHubAccount.id == donor_id).first()
    if not acc:
        raise HTTPException(status_code=404, detail="Donor not found")
    db.delete(acc)
    db.commit()
    return {"status": "deleted"}

@router.post("/donors/{donor_id}/dispatch")
def dispatch_donor(donor_id: int, identity: Identity = Depends(require_admin), db: Session = Depends(get_db)):
    acc = db.query(GitHubAccount).filter(GitHubAccount.id == donor_id).first()
    if not acc:
        raise HTTPException(status_code=404, detail="Donor not found")

    url = f"https://api.github.com/repos/{acc.repo_name}/actions/workflows/mesh.yml/dispatches"
    req = urllib.request.Request(url, data=json.dumps({"ref": "main"}).encode(), headers={
        "Authorization": f"token {acc.pat_token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json"
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            acc.last_dispatched_at = datetime.datetime.utcnow()
            db.commit()
            return {"status": "dispatched"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
