from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from logger import log
from models import Job, Stage
from schemas import CreateJobRequest, JobDetailResponse, JobResponse
from services.jobs import create_job_record, get_job_or_404


router = APIRouter(tags=["jobs"])


@router.post("/jobs", response_model=JobResponse)
async def create_job(request: CreateJobRequest, db: Session = Depends(get_db)):
    job = await create_job_record(db, request.filename)
    log.info("job.created", job_id=str(job.id), filename=job.filename)
    return job


@router.get("/jobs", response_model=list[JobResponse])
def list_jobs(db: Session = Depends(get_db)):
    jobs = db.query(Job).order_by(Job.created_at.desc()).all()
    log.info("jobs.listed", count=len(jobs))
    return jobs


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str, db: Session = Depends(get_db)):
    return get_job_or_404(db, job_id)


@router.get("/jobs/{job_id}/detail", response_model=JobDetailResponse)
def get_job_detail(job_id: str, db: Session = Depends(get_db)):
    job = get_job_or_404(db, job_id)
    stages = db.query(Stage).filter(Stage.job_id == job_id).order_by(Stage.started_at).all()
    return {**job.__dict__, "stages": stages}
