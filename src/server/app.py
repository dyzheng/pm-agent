"""FastAPI application factory for the interactive dashboard."""

from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from src.server.event_bus import EventBus
from src.server.models import ApprovalManager
from src.server.state_manager import StateManager
from src.server.websocket_hub import WebSocketHub
from src.server.routes.approvals import create_router as approvals_router
from src.server.routes.dispatch import create_router as dispatch_router
from src.server.routes.optimize import create_router as optimize_router
from src.server.routes.projects import create_router as projects_router

logger = logging.getLogger(__name__)


def create_app(project_dir: Path) -> FastAPI:
    """Create and configure the FastAPI application.

    Wires together all server components: state management, event bus,
    approval manager, WebSocket hub, and REST route modules.

    Args:
        project_dir: Path to the project directory containing state/.

    Returns:
        Configured FastAPI application instance.
    """
    project_dir = Path(project_dir)

    # Core services (created before app so lifespan can reference them)
    event_bus = EventBus()
    state_mgr = StateManager(project_dir, event_bus)
    approval_mgr = ApprovalManager()
    ws_hub = WebSocketHub(event_bus)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        ws_hub.set_loop(asyncio.get_event_loop())
        yield

    app = FastAPI(
        title="PM Agent Dashboard", version="0.1.0", lifespan=lifespan
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Store on app state for access in endpoints
    app.state.event_bus = event_bus
    app.state.state_mgr = state_mgr
    app.state.approval_mgr = approval_mgr
    app.state.ws_hub = ws_hub
    app.state.project_dir = project_dir

    # Register routes
    app.include_router(projects_router(state_mgr))
    app.include_router(approvals_router(approval_mgr, event_bus))
    app.include_router(dispatch_router(state_mgr, event_bus))
    app.include_router(optimize_router(state_mgr, event_bus, project_dir))

    @app.get("/", response_class=HTMLResponse)
    def serve_dashboard():
        dashboard_file = project_dir / "dashboard.html"
        if dashboard_file.exists():
            return HTMLResponse(dashboard_file.read_text(encoding="utf-8"))
        # Generate on the fly if missing
        try:
            from tools.generate_dashboard import generate_dashboard

            generate_dashboard(project_dir)
            if dashboard_file.exists():
                return HTMLResponse(
                    dashboard_file.read_text(encoding="utf-8")
                )
        except Exception:
            pass
        return HTMLResponse(
            "<h1>Dashboard not generated yet</h1>", status_code=200
        )

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await websocket.accept()
        await ws_hub.connect(websocket)
        # Send initial state
        tasks = state_mgr.get_tasks()
        await websocket.send_text(
            json.dumps(
                {
                    "type": "state_reloaded",
                    "payload": {
                        "tasks": [t.to_dict() for t in tasks],
                        "stats": state_mgr.get_stats(),
                    },
                }
            )
        )
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            ws_hub.disconnect(websocket)

    return app
