"""FastAPI local que enlaza el laboratorio con OpenDSS Cloud sin modificarlo."""

from __future__ import annotations

from contextlib import asynccontextmanager
from types import SimpleNamespace

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.app.api import experiments, graph, llm, objectives, sessions, simulations, status
from backend.app.api_ws import local_ws
from backend.app.integrations.opendss_http import RemoteOpenDSS, UpstreamError
from backend.app.logging_config import configure_logging
from backend.app.persistence.sqlite_store import Store
from backend.app.services.health_monitor import HealthMonitor
from backend.app.services.orchestrator import Orchestrator
from backend.app.services.run_manager import RunManager
from backend.app.settings import ROOT, settings

configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.host not in ("127.0.0.1", "localhost"):
        raise RuntimeError("Este prototipo solo permite servicio en 127.0.0.1")
    store = Store()
    remote = RemoteOpenDSS()
    monitor = HealthMonitor(remote)
    manager = RunManager(store)
    orchestrator = Orchestrator(remote, monitor, manager)
    app.state.services = SimpleNamespace(
        store=store,
        remote=remote,
        monitor=monitor,
        manager=manager,
        orchestrator=orchestrator,
        created_sessions=set(),
        llm_enabled=bool(settings.ollama().get("enabled", False)),
    )
    yield
    await remote.aclose()


app = FastAPI(title="DERMS TKG Power Lab", version="0.1.0", lifespan=lifespan)


@app.middleware("http")
async def prevent_exposure(request: Request, call_next):
    host = request.headers.get("host", "").split(":")[0].lower()
    if host not in ("127.0.0.1", "localhost", "testserver"):
        return JSONResponse({"detail": "Acceso solo desde loopback"}, status_code=403)
    return await call_next(request)


@app.exception_handler(UpstreamError)
async def remote_error_handler(_request: Request, exc: UpstreamError):
    code = (
        503
        if exc.code in ("OFFLINE", "NETWORK_ERROR")
        else 401
        if exc.code == "AUTH_ERROR"
        else 502
    )
    return JSONResponse({"code": exc.code, "detail": str(exc)}, status_code=code)


for module in (status, sessions, simulations, objectives, graph, experiments, llm):
    app.include_router(module.router, prefix="/api", tags=[module.__name__.rsplit(".", 1)[-1]])
app.websocket("/api/live/{run_id}")(local_ws)

STATIC = ROOT / "frontend/dist"
if STATIC.exists():
    app.mount("/assets", StaticFiles(directory=str(STATIC / "assets")), name="assets")


@app.get("/")
async def home():
    index = STATIC / "index.html"
    if index.exists():
        return FileResponse(index)
    return {
        "service": "DERMS TKG Power Lab",
        "backend": "http://127.0.0.1:8088/docs",
        "frontend": "Ejecute npm run dev desde frontend/ o npm run build",
    }
