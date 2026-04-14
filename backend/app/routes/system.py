import os
import time

import psutil
from fastapi import APIRouter

from ..services.metadata_writer import get_exiftool_status

router = APIRouter(prefix="/api/system", tags=["system"])

PROCESS_START = time.time()
EXIFTOOL_CACHE_TTL_SECONDS = 10
_exiftool_cache: dict = {
    "expires_at": 0.0,
    "value": {
        "available": False,
        "path": None,
        "version": None,
        "error": "Probe pending",
    },
}


def _get_exiftool_status_cached() -> dict:
    now = time.time()
    if now < float(_exiftool_cache["expires_at"]):
        return _exiftool_cache["value"]

    status = get_exiftool_status()
    _exiftool_cache["value"] = status
    _exiftool_cache["expires_at"] = now + EXIFTOOL_CACHE_TTL_SECONDS
    return status


@router.get("/metrics", response_model=dict)
def metrics() -> dict:
    vm = psutil.virtual_memory()
    disk = psutil.disk_usage(os.getcwd())
    cpu = psutil.cpu_percent(interval=0.1)
    exiftool = _get_exiftool_status_cached()

    return {
        "cpu_percent": round(cpu, 2),
        "memory_percent": round(vm.percent, 2),
        "memory_used_gb": round(vm.used / (1024**3), 2),
        "memory_total_gb": round(vm.total / (1024**3), 2),
        "disk_percent": round(disk.percent, 2),
        "disk_free_gb": round(disk.free / (1024**3), 2),
        "uptime_seconds": int(time.time() - PROCESS_START),
        "exiftool": exiftool,
    }
