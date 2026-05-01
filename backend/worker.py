import asyncio
import json
import os
from datetime import datetime, timezone
from urllib.parse import urlparse

import redis as redis_sync
from arq.connections import RedisSettings
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from logger import log, setup_logging
from models import Job, JobStatus, Stage
from stages import (
    classify_document,
    extract_entities,
    extract_text,
    generate_insights,
    summarise_document,
)

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://pulse:pulse@localhost:5432/pulse"
)
setup_logging(service="worker", env=os.getenv("ENV", "development"))

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
parsed_redis_url = urlparse(redis_url)
REDIS_SETTINGS = RedisSettings(
    host=parsed_redis_url.hostname or "localhost",
    port=parsed_redis_url.port or 6379,
)
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

redis_client = redis_sync.Redis.from_url(redis_url)

PIPELINE = [
    ("extract_text", extract_text),
    ("classify_document", classify_document),
    ("summarise_document", summarise_document),
    ("extract_entities", extract_entities),
    ("generate_insights", generate_insights),
]


def publish(job_id: str, event: dict):
    redis_client.publish(f"job:{job_id}", json.dumps(event))
    log.info(
        "worker.published",
        job_id=job_id,
        status=event.get("status"),
        stage=event.get("stage"),
        stage_status=event.get("stage_status"),
    )


async def process_document(
    ctx: dict, job_id: str, filename: str, content: str = ""
) -> None:
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
        publish(job_id, {"job_id": job_id, "status": "processing"})

        current_input = content or filename

        for stage_name, stage_fn in PIPELINE:
            stage = Stage(
                job_id=job.id,
                name=stage_name,
                status="running",
                started_at=datetime.now(timezone.utc),
            )
            db.add(stage)
            db.commit()

            publish(
                job_id,
                {
                    "job_id": job_id,
                    "stage": stage_name,
                    "stage_status": "running",
                },
            )
            log.info("worker.stage.started", job_id=job_id, stage=stage_name)

            try:
                result = await asyncio.get_running_loop().run_in_executor(
                    None, stage_fn, current_input
                )
                stage.status = "completed"
                stage.result = str(result)[:2000]
                stage.completed_at = datetime.now(timezone.utc)
                current_input = str(result)
                db.commit()

                publish(
                    job_id,
                    {
                        "job_id": job_id,
                        "stage": stage_name,
                        "stage_status": "completed",
                        "preview": str(result)[:100],
                    },
                )
                log.info("worker.stage.completed", job_id=job_id, stage=stage_name)

            except Exception as e:
                stage.status = "failed"
                stage.completed_at = datetime.now(timezone.utc)
                db.commit()

                publish(
                    job_id,
                    {
                        "job_id": job_id,
                        "stage": stage_name,
                        "stage_status": "failed",
                        "error": str(e),
                    },
                )
                log.error(
                    "worker.stage.failed",
                    job_id=job_id,
                    stage=stage_name,
                    error=str(e),
                )
                raise

        job.status = JobStatus.completed
        db.commit()
        publish(job_id, {"job_id": job_id, "status": "completed"})
        log.info("worker.job.completed", job_id=job_id)

    except Exception as e:
        log.error("worker.job.failed", job_id=job_id, error=str(e))
        if job is not None:
            job.status = JobStatus.failed
            db.commit()
        publish(job_id, {"job_id": job_id, "status": "failed", "error": str(e)})
        raise
    finally:
        db.close()


class WorkerSettings:
    functions = [process_document]
    redis_settings = REDIS_SETTINGS
    max_jobs = 5
    job_timeout = 300
    retry_jobs = True
    max_tries = 3
