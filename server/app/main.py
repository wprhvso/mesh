import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.db.session import init_db
from app.api import me, clients, runners, donors, ssh, dns, register

init_db()

app_panel = FastAPI(title="Mesh Control Plane")
app_panel.include_router(me.router, prefix="/api")
app_panel.include_router(clients.router, prefix="/api")
app_panel.include_router(runners.router, prefix="/api")
app_panel.include_router(donors.router, prefix="/api")
app_panel.include_router(ssh.router, prefix="/api")
app_panel.include_router(dns.router, prefix="/api")

static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app_panel.mount("/assets", StaticFiles(directory=os.path.join(static_dir, "assets")), name="assets")

    @app_panel.get("/{full_path:path}")
    def serve_spa(full_path: str):
        if full_path.startswith("api/"):
            return None
        return FileResponse(os.path.join(static_dir, "index.html"))

app_register = FastAPI(title="Mesh Runner Handshake")
app_register.include_router(register.router)
