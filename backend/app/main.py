from os import getenv
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .database import init_db
from .logger import get_logger
from .routes.jobs import router as jobs_router
from .routes.scan import router as scan_router
from .routes.system import router as system_router
from .routes.ws import router as ws_router

app = FastAPI(title="MetaINFO Updater API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_origin_regex=r"https?://(localhost|127\\.0\\.0\\.1):\\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _resolve_frontend_dist() -> Path | None:
    env_dist = getenv("FRONTEND_DIST_DIR")
    candidates: list[Path] = []
    if env_dist:
        candidates.append(Path(env_dist))

    # Source layout: <repo>/frontend/dist
    # Frozen layout (PyInstaller): <_MEIPASS>/frontend/dist
    candidates.append(Path(__file__).resolve().parents[2] / "frontend" / "dist")

    for candidate in candidates:
        if candidate.exists() and (candidate / "index.html").exists():
            return candidate
    return None


@app.on_event("startup")
def startup() -> None:
    logger = get_logger()
    init_db()
    logger.info("Application startup complete")


@app.get("/health")
def health() -> dict:
    return {"ok": True}


app.include_router(scan_router)
app.include_router(jobs_router)
app.include_router(system_router)
app.include_router(ws_router)

frontend_dist = _resolve_frontend_dist()
if frontend_dist:
    # Mounted last so API routes keep priority.
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
