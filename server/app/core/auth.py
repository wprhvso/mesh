from fastapi import Request, HTTPException, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import Client

class Identity:
    def __init__(self, client: Client, is_admin: bool):
        self.client = client
        self.is_admin = is_admin

def get_current_identity(request: Request, db: Session = Depends(get_db)) -> Identity:
    client_ip = request.client.host
    if client_ip in ["127.0.0.1", "::1"]:
        admin_client = db.query(Client).filter(Client.is_admin == True).first()
        if admin_client:
            return Identity(client=admin_client, is_admin=True)
        return Identity(
            client=Client(name="localhost", domain="server.mesh", ip="127.0.0.1", is_admin=True),
            is_admin=True
        )

    client = db.query(Client).filter(Client.ip == client_ip, Client.is_active == True).first()
    if not client:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Client IP not recognized in Mesh VPN network"
        )
    return Identity(client=client, is_admin=client.is_admin)

def require_admin(identity: Identity = Depends(get_current_identity)):
    if not identity.is_admin:
        raise HTTPException(status_code=403, detail="Forbidden: Administrator access required")
    return identity
