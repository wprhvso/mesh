from fastapi import APIRouter, Depends
from app.core.auth import Identity, get_current_identity

router = APIRouter()

@router.get("/me")
def get_me(identity: Identity = Depends(get_current_identity)):
    return {
        "client": {
            "id": identity.client.id,
            "name": identity.client.name,
            "domain": identity.client.domain,
            "ip": identity.client.ip,
            "is_admin": identity.client.is_admin,
            "is_active": identity.client.is_active
        },
        "is_admin": identity.is_admin,
        "system": {
            "server_ip": "10.10.1.1",
            "gateway_domain": "server.mesh"
        }
    }
