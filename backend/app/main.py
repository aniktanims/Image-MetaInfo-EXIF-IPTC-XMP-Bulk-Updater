from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
