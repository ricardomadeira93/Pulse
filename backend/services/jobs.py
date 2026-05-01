from fastapi import HTTPException
from sqlalchemy.orm import Session

from arq import create_pool

from models import Job
from services.realtime import REDIS_SETTINGS


async def create_job_record(db: Session, filename: str) -> Job:
    job = Job(filename=filename)
    db.add(job)
    db.commit()
    db.refresh(job)

    redis = await create_pool(REDIS_SETTINGS)
    await redis.enqueue_job("process_document", str(job.id), filename)
    await redis.close()

    return job


def get_job_or_404(db: Session, job_id: str) -> Job:
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
