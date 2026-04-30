import asyncio
import json
import os
from urllib.parse import urlparse

import redis as redis_sync

from arq.connections import RedisSettings
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from logger import log
from models import Job, JobStatus

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://pulse:pulse@localhost:5432/pulse")
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
parsed_redis_url = urlparse(redis_url)
REDIS_SETTINGS = RedisSettings(
    host=parsed_redis_url.hostname or "localhost",
    port=parsed_redis_url.port or 6379,
)
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


redis_client = redis_sync.Redis.from_url(redis_url)

def publish_update(job_id: str, status: str, stage: str | None = None, data: dict | None = None):
    message = {"job_id": job_id, "status": status}
    if stage:
        message["stage"] = stage
    if data:
        message["data"] = data
    redis_client.publish(f"job:{job_id}", json.dumps(message))
    log.info("worker.published", job_id=job_id, status=status)

async def process_document(ctx: dict, job_id: str, filename: str) -> dict[str, str] | None:
    log.info("worker.job.started", job_id=job_id, filename=filename)
    db: Session = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            log.error("worker.job.not_found", job_id=job_id)
            return

        job.status = JobStatus.processing
        db.commit()
        publish_update(job_id, "processing")

        await asyncio.sleep(3)  # Placeholder until document processing is implemented.

        job.status = JobStatus.completed
        db.commit()
        publish_update(job_id, "completed")
        log.info("worker.job_completed", job_id=job_id)

    except Exception as e:
        log.error("worker.job.failed", job_id=job_id, error=str(e))
        if job:
            job.status = JobStatus.failed
            db.commit()
            publish_update(job_id, "failed", data={"error": str(e)})
        raise
    finally:
        db.close()

class WorkerSettings:
    functions = [process_document]
    redis_settings = REDIS_SETTINGS
