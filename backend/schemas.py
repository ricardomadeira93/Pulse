from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from models import JobStatus

class CreateJobRequest(BaseModel):
    filename: str

class JobResponse(BaseModel):
    id: UUID
    filename: str
    status: JobStatus
    created_at: datetime

    class Config:
        from_attributes = True