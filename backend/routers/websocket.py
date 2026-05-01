from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from connection_manager import manager
from logger import log


router = APIRouter(tags=["websocket"])


@router.websocket("/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    await manager.connect(job_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(job_id)
        log.info("websocket.client.disconnected", job_id=job_id)
