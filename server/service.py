import asyncio
import os
import uvicorn
from app.main import app_panel, app_register
from app.core.reconciler import reconcile_loop

async def main():
    config_panel = uvicorn.Config(
        app_panel,
        host=os.environ.get("PANEL_HOST", "10.10.1.1"),
        port=int(os.environ.get("PANEL_PORT", "80")),
        log_level="warning"
    )
    config_reg = uvicorn.Config(
        app_register,
        host=os.environ.get("REG_HOST", "0.0.0.0"),
        port=int(os.environ.get("REG_PORT", "51822")),
        log_level="warning"
    )

    server_panel = uvicorn.Server(config_panel)
    server_reg = uvicorn.Server(config_reg)

    await asyncio.gather(
        server_panel.serve(),
        server_reg.serve(),
        reconcile_loop()
    )

if __name__ == "__main__":
    asyncio.run(main())
