# Phase 2 — Redis + Queue

## How You Learn This Phase

The problem you are solving: document processing takes 30 seconds.
Right now the API blocks for 30 seconds before responding.
Users create duplicate jobs. Requests time out. The server can't
handle other requests while processing.

You are going to fix this with Redis and background workers.
Every concept here is a direct solution to a real problem.

---

## Install

```bash
pip install arq redis
pip freeze > requirements.txt
```

---

## Step 2.1 — Add Redis to Docker Compose

Already done in Phase 0. Verify it's there:

```yaml
redis:
  image: redis:7-alpine
  ports:
    - "6379:6379"
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 5s
    timeout: 5s
    retries: 5
```

Test Redis is working:
```bash
docker compose exec redis redis-cli ping
# Should return: PONG
```

---

## Step 2.2 — worker.py

Create `backend/worker.py`:

```python
import asyncio
from arq.connections import RedisSettings
from logger import log

REDIS_SETTINGS = RedisSettings(host="localhost", port=6379)

async def process_document(ctx, job_id: str, filename: str):
    log.info("worker.job.started", job_id=job_id, filename=filename)
    await asyncio.sleep(3)  # simulate work — replace with real AI later
    log.info("worker.job.completed", job_id=job_id)
    return {"status": "completed"}

class WorkerSettings:
    functions = [process_document]
    redis_settings = REDIS_SETTINGS
```

Run the worker in a separate terminal:
```bash
cd backend
source .venv/bin/activate
arq worker.WorkerSettings
```

You should see the worker start and wait for jobs.

**What you learn:**
`async def` — workers are async because they do IO (database, API calls).
`ctx` — the worker context. Holds the Redis connection and shared state.
`WorkerSettings.functions` — tells ARQ which functions this worker handles.

---

## Step 2.3 — Enqueue from the API

Update the `create_job` endpoint in `main.py`:

```python
from arq import create_pool
from arq.connections import RedisSettings

REDIS_SETTINGS = RedisSettings(host="localhost", port=6379)

@app.post("/jobs", response_model=JobResponse)
async def create_job(request: CreateJobRequest, db: Session = Depends(get_db)):
    job = Job(filename=request.filename)
    db.add(job)
    db.commit()
    db.refresh(job)

    redis = await create_pool(REDIS_SETTINGS)
    await redis.enqueue_job("process_document", str(job.id), request.filename)
    await redis.close()

    log.info("job.created.enqueued", job_id=str(job.id), filename=job.filename)
    return job
```

**Note:** the endpoint is now `async def` because we use `await`.

Test it:
```bash
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{"filename": "contract.pdf"}'
```

The API responds instantly. Watch the worker terminal — processing happens there.

**What just happened:**
1. API created a job record in PostgreSQL (permanent)
2. API pushed a message to Redis (temporary work instruction)
3. API returned immediately without waiting
4. Worker picked up the message and processed it separately

These are two separate concerns. The database record is the source of truth.
The Redis message is just a trigger.

---

## Step 2.4 — Worker updates PostgreSQL

The worker needs to update the job status as it processes.
Update `worker.py`:

```python
import asyncio
import os
from arq.connections import RedisSettings
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Job, JobStatus
from logger import log

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://pulse:pulse@localhost:5432/pulse")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

REDIS_SETTINGS = RedisSettings(host="localhost", port=6379)

async def process_document(ctx, job_id: str, filename: str):
    log.info("worker.job.started", job_id=job_id)
    db = SessionLocal()

    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            log.error("worker.job.not_found", job_id=job_id)
            return

        job.status = JobStatus.processing
        db.commit()
        log.info("worker.job.processing", job_id=job_id)

        await asyncio.sleep(3)  # simulate AI work

        job.status = JobStatus.completed
        db.commit()
        log.info("worker.job.completed", job_id=job_id)

    except Exception as e:
        log.error("worker.job.failed", job_id=job_id, error=str(e))
        job.status = JobStatus.failed
        db.commit()
        raise  # re-raise so ARQ knows to retry

    finally:
        db.close()

class WorkerSettings:
    functions = [process_document]
    redis_settings = REDIS_SETTINGS
```

Watch the status change:
```bash
# Terminal 1: run the worker
arq worker.WorkerSettings

# Terminal 2: create a job then poll its status
curl -X POST http://localhost:8000/jobs -H "Content-Type: application/json" -d '{"filename":"test.pdf"}'
# copy the job id
curl http://localhost:8000/jobs/<job-id>  # run this a few times
```

You should see status go: queued → processing → completed

**Why re-raise the exception:**
ARQ needs to know the job failed to decide whether to retry.
If you catch the exception and don't re-raise it, ARQ thinks the job
succeeded and won't retry it. The job just silently disappears.

**Why try/finally instead of try/except:**
`finally` runs whether or not an exception occurred.
This guarantees `db.close()` always runs, even if something crashes.
Without this, database connections leak.

---

## Step 2.5 — Retry Logic

Update WorkerSettings with retry configuration:

```python
class WorkerSettings:
    functions = [process_document]
    redis_settings = REDIS_SETTINGS
    max_jobs = 10
    job_timeout = 300  # 5 minutes max per job
    retry_jobs = True
    max_tries = 3
```

Add a random failure to test retries (temporary):

```python
import random

async def process_document(ctx, job_id: str, filename: str):
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        job.status = JobStatus.processing
        db.commit()

        if random.random() < 0.5:  # fail 50% of the time
            raise Exception("Simulated random failure")

        await asyncio.sleep(2)
        job.status = JobStatus.completed
        db.commit()
        log.info("worker.job.completed", job_id=job_id)

    except Exception as e:
        log.error("worker.job.failed", job_id=job_id, error=str(e),
                  attempt=ctx.get("job_try", 1))
        job.status = JobStatus.failed
        db.commit()
        raise
    finally:
        db.close()
```

Submit several jobs. Watch the worker terminal.
You will see failed jobs being retried automatically.

Remove the random failure after testing.

**What job_timeout does:**
If a job runs longer than 300 seconds, ARQ kills it and marks it failed.
Without this, a stuck job holds a worker slot forever.

---

## Step 2.6 — Worker in Docker Compose

Add the worker as a separate service:

```yaml
worker:
  build: ./backend
  command: arq worker.WorkerSettings
  env_file:
    - ./backend/.env
  environment:
    - DATABASE_URL=postgresql://pulse:pulse@db:5432/pulse
    - REDIS_URL=redis://redis:6379
  depends_on:
    db:
      condition: service_healthy
    redis:
      condition: service_healthy
```

Update REDIS_SETTINGS in worker.py to use environment variable:

```python
import os
from arq.connections import RedisSettings

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
REDIS_SETTINGS = RedisSettings.from_dsn(redis_url)
```

---

## File Structure After Phase 2

```
backend/
  main.py
  config.py
  logger.py
  database.py
  models.py
  schemas.py
  worker.py
  requirements.txt
```

---

## Answer These Out Loud Before Moving to Phase 3

1. What is the difference between the PostgreSQL job record and the Redis queue message?
2. Why does the API return immediately after enqueuing instead of waiting?
3. What happens if the worker crashes after setting status to "processing"?
4. Why do we re-raise exceptions in the worker?
5. Why is `finally: db.close()` important?
6. What does `max_tries` control and what happens after the last retry?
7. Why is the worker a separate Docker service instead of running inside the API?
8. What does `job_timeout` prevent?

Can't answer all eight? Go back. Don't move forward.
