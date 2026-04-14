import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..config import WEBSOCKET_PING_SECONDS
from ..services.progress_hub import progress_hub

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/jobs/{job_id}")
async def job_progress(websocket: WebSocket, job_id: str) -> None:
    await progress_hub.connect(job_id, websocket)
    try:
        while True:
            await asyncio.sleep(WEBSOCKET_PING_SECONDS)
            await websocket.send_json({"event": "ping", "job_id": job_id})
    except WebSocketDisconnect:
        await progress_hub.disconnect(job_id, websocket)
    except Exception:
        await progress_hub.disconnect(job_id, websocket)
