import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, UUID, String, DateTime, Enum as SQLEnum
from database import Base


class JobStatus(str, enum.Enum):
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String, nullable=False)
    status = Column(SQLEnum(JobStatus), default=JobStatus.queued)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Job id={self.id} filename={self.filename} status={self.status}>"
