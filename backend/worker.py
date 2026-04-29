import asyncio
import os

from arq.connections import RedisSettings
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from logger import log
from models import Job, JobStatus

REDIS_SETTINGS = RedisSettings(host="localhost", port=6379)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://pulse:pulse@localhost:5432/pulse")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


async def process_document(ctx: dict, job_id: str, filename: str) -> dict[str, str] | None:
    log.info("worker.job.started", job_id=job_id, filename=filename)
    db: Session = SessionLocal()
    job: Job | None = None

    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            log.error("worker.job.not_found", job_id=job_id)
            return

        job.status = JobStatus.processing
        db.commit()
        log.info("worker.job.processing", job_id=job_id)

        await asyncio.sleep(3)  # Placeholder until document processing is implemented.

        job.status = JobStatus.completed
        db.commit()
        log.info("worker.job_completed", job_id=job_id)

    except Exception as e:
        log.error("worker.job.failed", job_id=job_id, error=str(e))
        if job is not None:
            job.status = JobStatus.failed
            db.commit()
        raise
    finally:
        db.close()

    log.info("worker.job.completed", job_id=job_id)
    return {"status": "completed"}

class WorkerSettings:
    functions = [process_document]
    redis_settings = REDIS_SETTINGS
