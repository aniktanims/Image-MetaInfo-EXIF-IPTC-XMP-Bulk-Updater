import os
import time

import psutil
from fastapi import APIRouter

router = APIRouter(prefix="/api/system", tags=["system"])

PROCESS_START = time.time()


@router.get("/metrics", response_model=dict)
def metrics() -> dict:
    vm = psutil.virtual_memory()
    disk = psutil.disk_usage(os.getcwd())
    cpu = psutil.cpu_percent(interval=0.1)

    return {
        "cpu_percent": round(cpu, 2),
        "memory_percent": round(vm.percent, 2),
        "memory_used_gb": round(vm.used / (1024**3), 2),
        "memory_total_gb": round(vm.total / (1024**3), 2),
        "disk_percent": round(disk.percent, 2),
        "disk_free_gb": round(disk.free / (1024**3), 2),
        "uptime_seconds": int(time.time() - PROCESS_START),
    }
