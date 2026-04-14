import asyncio
from collections import defaultdict

from fastapi import WebSocket


class ProgressHub:
    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, job_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections[job_id].add(websocket)

    async def disconnect(self, job_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            if job_id in self._connections:
                self._connections[job_id].discard(websocket)
                if not self._connections[job_id]:
                    del self._connections[job_id]

    async def broadcast(self, job_id: str, payload: dict) -> None:
        async with self._lock:
            sockets = list(self._connections.get(job_id, set()))

        stale: list[WebSocket] = []
        for socket in sockets:
            try:
                await socket.send_json(payload)
            except Exception:
                stale.append(socket)

        if stale:
            async with self._lock:
                for socket in stale:
                    self._connections[job_id].discard(socket)


progress_hub = ProgressHub()
