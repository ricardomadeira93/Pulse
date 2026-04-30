import asyncio
import json
from contextlib import asynccontextmanager
from urllib.parse import urlparse

import redis
import redis.asyncio as aioredis
import sentry_sdk
from arq import create_pool
from arq.connections import RedisSettings
from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from config import settings
from connection_manager import manager
from database import get_db
from logger import setup_logging, log
from models import Job
from schemas import CreateJobRequest, JobResponse

sentry_sdk.init(
    dsn=settings.sentry_dsn,
    # Add data like request headers and IP for users,
    # see https://docs.sentry.io/platforms/python/data-management/data-collected/ for more info
    send_default_pii=True,
)

redis_client = redis.Redis.from_url(settings.redis_url)
redis_url = urlparse(settings.redis_url)
REDIS_SETTINGS = RedisSettings(
    host=redis_url.hostname or "localhost",
    port=redis_url.port or 6379,
)
setup_logging()

async def redis_listener():
    r = aioredis.Redis.from_url(settings.redis_url)
    pubsub = r.pubsub()
    await pubsub.psubscribe("job:*")
    log.info("redis.listener.started")
    async for message in pubsub.listen():
        if message["type"] != "pmessage":
            continue

        try:
            data = json.loads(message["data"])
            job_id = data.get("job_id")
            if job_id:
                await manager.send_update(job_id, data)
        except Exception as e:
            log.error("redis.listener.error", error=str(e))

@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(redis_listener())
    log.info("app.started")
    yield
    log.info("app.stopped")

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health(db=Depends(get_db)):
    result = {"status": "Ok", "database":"unknown", "redis": "unknown"}
    try:
        db.execute(text("Select 1"))
        result["database"] = "ok"
    except Exception as e:
        result["database"] = "error"
        result["status"] = "degraded"
        log.error("health.database.error",
    error=str(e))
        
    try:
        redis_client.ping()
        result["redis"] = "ok"
    except Exception as e:
        result["redis"] = "error"
        result["status"] = "degraded"
        log.error("health.redis.error",
        error=str(e))    

    return result

@app.post("/jobs", response_model=JobResponse)
async def create_job(request: CreateJobRequest, db: Session = Depends(get_db)):
    job = Job(filename=request.filename)
    db.add(job)
    db.commit()
    db.refresh(job)

    redis = await create_pool(REDIS_SETTINGS)
    await redis.enqueue_job("process_document", str(job.id), request.filename)
    await redis.close()
    
    log.info("job.created", job_id=str(job.id),
    filename=job.filename)
    return job

@app.get("/jobs", response_model=list[JobResponse])
def list_jobs(db: Session = Depends(get_db)):    
    jobs = db.query(Job).order_by(Job.created_at.desc()).all()
    log.info("jobs.listed", count=len(jobs))
    return jobs

@app.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@app.websocket("/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id:str):
    await manager.connect(job_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(job_id)
        log.info("websocket.client.disconnected", job_id=job_id)
