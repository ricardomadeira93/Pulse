from fastapi import WebSocket
from logger import log

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, job_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[job_id] = websocket
        log.info("websocket.connected", job_id=job_id, total=len(self.active_connections))

    def disconnect(self, job_id: str):
        self.active_connections.pop(job_id, None)
        log.info("websocket.disconnected", job_id=job_id)

    async def send_update(self, job_id: str, message:dict):
        websocket = self.active_connections.get(job_id)
        if websocket:
            try:
                await websocket.send_json(message)
                log.info("websocket.sent", job_id=job_id, status=message.get("status"))
            except Exception as e:
                log.error("websocket.send.failed", job_id=job_id, error=str(e))
                self.disconnect(job_id)

manager = ConnectionManager()