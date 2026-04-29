from fastapi import FastAPI, Depends, HTTPException
from config import settings
from logger import setup_logging, log
import redis
from sqlalchemy import text
from sqlalchemy.orm import Session
import sentry_sdk
from schemas import CreateJobRequest, JobResponse
from models import Job
from database import get_db

sentry_sdk.init(
    dsn=settings.sentry_dsn,
    # Add data like request headers and IP for users,
    # see https://docs.sentry.io/platforms/python/data-management/data-collected/ for more info
    send_default_pii=True,
)

redis_client = redis.Redis.from_url(settings.redis_url)


setup_logging()
app = FastAPI()


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
def create_job(request: CreateJobRequest, db: Session = Depends(get_db)):
    job = Job(filename=request.filename)
    db.add(job)
    db.commit()
    db.refresh(job)
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
    
