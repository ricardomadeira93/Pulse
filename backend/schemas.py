from pydantic import BaseModel, EmailStr, Field
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
        
        
class StageResponse(BaseModel):
    id: UUID
    job_id: UUID
    name: str
    status: str
    result: str | None
    started_at: datetime | None
    completed_at: datetime | None
    
    class Config:
        from_attributes = True
        
class JobDetailResponse(JobResponse):
    stages: list[StageResponse] = Field(default_factory=list)
    

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)

    
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    
class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    created_at: datetime
    
    class Config:
        from_attributes = True