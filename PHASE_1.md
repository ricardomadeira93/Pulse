# Phase 1 — PostgreSQL + Database Layer

## How You Learn This Phase

This is the most important phase. Every project you build from now on
uses these patterns. Take your time. Don't rush to Phase 2.

Read the snippet. Close it. Type it. Break it deliberately.
Fix it. Explain it out loud. Then move to the next step.

---

## Install

```bash
cd backend
pip install sqlalchemy alembic psycopg2-binary
pip freeze > requirements.txt
```

---

## Step 1.1 — database.py

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from config import settings

engine = create_engine(settings.database_url)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**What each part does:**

`create_engine` — creates the connection pool to PostgreSQL.
One engine per application, created once at startup.

`SessionLocal` — a factory for database sessions.
Each request gets its own session, used for one unit of work.

`Base` — the base class all your models inherit from.
It tracks all models so Alembic can generate migrations.

`get_db` — a FastAPI dependency that creates a session,
gives it to the route, then closes it when the request ends.
The `yield` is what makes it a dependency — FastAPI runs the code
before yield, gives the value to the route, then runs the code after.

**Break it deliberately:**
Change `autocommit=False` to `autocommit=True`.
Try to understand what would break and why.
Change it back.

---

## Step 1.2 — models.py

```python
import uuid
import enum
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
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
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Job id={self.id} filename={self.filename} status={self.status}>"
```

**What each part does:**

`__tablename__` — the actual table name in PostgreSQL.

`UUID(as_uuid=True)` — stores as a proper UUID type in PostgreSQL,
not a string. Better for indexing and querying.

`nullable=False` — PostgreSQL enforces this. You cannot insert a job
without a filename. The database rejects it, not just your application code.

`onupdate=datetime.utcnow` — automatically updates `updated_at`
every time the row is modified.

`JobStatus(str, enum.Enum)` — inheriting from both str and Enum means
the values are strings. FastAPI can serialise them directly to JSON.

---

## Step 1.3 — Alembic Setup

```bash
cd backend
alembic init migrations
```

This creates:
```
backend/
  migrations/
    env.py
    versions/  (empty for now)
  alembic.ini
```

### Edit alembic.ini

Find this line:
```
sqlalchemy.url = driver://user:pass@localhost/dbname
```

Replace with:
```
sqlalchemy.url = postgresql://pulse:pulse@localhost:5432/pulse
```

### Edit migrations/env.py

Find the line:
```python
target_metadata = None
```

Replace the top of the file to import your models:
```python
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database import Base
from models import Job  # import all models here

config = context.config
fileConfig(config.config_file_name)
target_metadata = Base.metadata
```

---

## Step 1.4 — Create and Run First Migration

```bash
alembic revision --autogenerate -m "create jobs table"
```

Open the generated file in `migrations/versions/`. Read every line.
You will see `op.create_table("jobs", ...)` with every column you defined.
This is the SQL that will run on your database.

Apply it:
```bash
alembic upgrade head
```

Verify in a database client (TablePlus, DBeaver, or psql):
```sql
\dt        -- list tables
\d jobs    -- describe the jobs table
```

You should see the jobs table with all columns.

**What migrations give you:**
Every schema change is versioned — like Git commits for your database.
If you break something you can run `alembic downgrade -1` to undo it.
When you deploy to production you run `alembic upgrade head` and the
database schema updates automatically.

**What happens if you run upgrade head twice:**
Nothing. Alembic tracks which migrations have been applied in a table
called `alembic_version`. It skips already-applied migrations.

---

## Step 1.5 — schemas.py (Pydantic models for request/response)

```python
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
```

**Why separate from SQLAlchemy models:**
SQLAlchemy models represent database rows.
Pydantic models represent what comes in and goes out of your API.
They are not the same thing. A database row might have a hashed_password
column you never want to return in an API response.

---

## Step 1.6 — Update main.py with job endpoints

```python
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
import sentry_sdk
import redis as redis_lib

from config import settings
from logger import setup_logging, log
from database import get_db
from models import Job
from schemas import CreateJobRequest, JobResponse

if settings.sentry_dsn:
    sentry_sdk.init(dsn=settings.sentry_dsn, environment=settings.env)

setup_logging()
app = FastAPI()
redis_client = redis_lib.Redis.from_url(settings.redis_url)

@app.get("/health")
def health(db: Session = Depends(get_db)):
    result = {"status": "ok", "database": "unknown", "redis": "unknown"}
    try:
        db.execute(text("SELECT 1"))
        result["database"] = "ok"
    except Exception as e:
        result["database"] = "error"
        result["status"] = "degraded"
        log.error("health.database.error", error=str(e))
    try:
        redis_client.ping()
        result["redis"] = "ok"
    except Exception as e:
        result["redis"] = "error"
        result["status"] = "degraded"
        log.error("health.redis.error", error=str(e))
    return result

@app.post("/jobs", response_model=JobResponse)
def create_job(request: CreateJobRequest, db: Session = Depends(get_db)):
    job = Job(filename=request.filename)
    db.add(job)
    db.commit()
    db.refresh(job)
    log.info("job.created", job_id=str(job.id), filename=job.filename)
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
```

**Test with curl:**
```bash
# Create a job
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{"filename": "contract.pdf"}'

# List all jobs
curl http://localhost:8000/jobs

# Get specific job (use the id from create response)
curl http://localhost:8000/jobs/<job-id>
```

---

## Step 1.7 — Update Docker Compose Database URL

The backend inside Docker must use the service name `db`, not `localhost`:

```yaml
backend:
  env_file:
    - ./backend/.env
  environment:
    - DATABASE_URL=postgresql://pulse:pulse@db:5432/pulse
    - REDIS_URL=redis://redis:6379
  depends_on:
    db:
      condition: service_healthy
```

**Important:** run migrations inside Docker too:
```bash
docker compose exec backend alembic upgrade head
```

Or add it to the backend startup command in docker-compose.yml:
```yaml
backend:
  command: >
    sh -c "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8000"
```

---

## File Structure After Phase 1

```
backend/
  main.py
  config.py
  logger.py
  database.py
  models.py
  schemas.py
  requirements.txt
  Dockerfile
  .env
  .env.example
  migrations/
    env.py
    versions/
      xxxx_create_jobs_table.py
  alembic.ini
```

---

## Answer These Out Loud Before Moving to Phase 2

1. What is the difference between an SQLAlchemy model and a Pydantic schema?
2. What does `yield` do in `get_db` and what runs after it?
3. What is a database session and why does each request get its own?
4. What is a migration and what happens if you run `upgrade head` twice?
5. Why use UUID instead of an auto-incrementing integer as primary key?
6. What does `nullable=False` enforce and where does it enforce it?
7. What does `db.refresh(job)` do and why is it needed after commit?
8. Why does the backend use `db` as the PostgreSQL host inside Docker?

Can't answer all eight? Go back. Don't move forward.
