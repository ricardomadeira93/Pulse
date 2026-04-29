# Phase 0 — Setup + Production Foundations

## How You Learn This Phase

You read a snippet. You close it. You type it yourself from memory.
If you can't type it from memory, you haven't read it carefully enough.
Every time you get an error, read the error before asking anyone.
The error message tells you exactly what's wrong 90% of the time.

Do not move to Phase 1 until every checkbox is ticked AND you can
answer every question at the bottom out loud without notes.

---

## Folder Structure

Create this by hand. No generators for the root structure.

```
pulse/
  backend/
    main.py
    requirements.txt
    Dockerfile
    .env
    .env.example
  frontend/
    (Next.js goes here)
  workers/
  agent/
  docker-compose.yml
  .gitignore
  README.md
```

Commands:
```bash
mkdir pulse
cd pulse
mkdir backend frontend workers agent
touch docker-compose.yml .gitignore README.md
cd backend
touch main.py requirements.txt Dockerfile .env .env.example
```

---

## Step 0.1 — Backend: FastAPI health endpoint

### Install
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn
pip freeze > requirements.txt
```

### main.py
```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}
```

### Run
```bash
uvicorn main:app --reload
```

Visit http://localhost:8000/health — you should see `{"status":"ok"}`
Visit http://localhost:8000/docs — you should see the Swagger UI

**What you learn:**
`FastAPI()` creates the app. `@app.get` registers a route.
`uvicorn` is the server that runs the app. `--reload` restarts on file changes.

---

## Step 0.2 — Frontend: Next.js

```bash
cd ../frontend
npx create-next-app@latest . --typescript --tailwind --app --no-src-dir
```

Delete everything inside `app/page.tsx` and replace with:

```tsx
export default function Home() {
  return (
    <main className="p-8">
      <h1 className="text-2xl font-bold">Pulse Dashboard</h1>
    </main>
  )
}
```

Run it:
```bash
npm run dev
```

Visit http://localhost:3000

---

## Step 0.3 — Dockerfiles

### backend/Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Why requirements.txt is copied first:**
Docker caches layers. If you copy requirements.txt first and it hasn't changed,
Docker skips reinstalling packages. This makes rebuilds much faster.

### frontend/Dockerfile
```dockerfile
FROM node:20-alpine

WORKDIR /app

COPY package*.json .
RUN npm install

COPY . .

RUN npm run build

CMD ["npm", "start"]
```

---

## Step 0.4 — Docker Compose (base)

### docker-compose.yml
```yaml
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    env_file:
      - ./backend/.env
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000

  db:
    image: postgres:15
    environment:
      POSTGRES_USER: pulse
      POSTGRES_PASSWORD: pulse
      POSTGRES_DB: pulse
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U pulse"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```

**Why healthchecks matter:**
`depends_on` without a healthcheck only waits for the container to start,
not for the service inside it to be ready. PostgreSQL takes a few seconds
to be ready after the container starts. Without a healthcheck your backend
crashes on startup trying to connect to a database that isn't ready yet.

Run it:
```bash
docker compose up --build
```

---

## Step 0.5 — pydantic-settings: Environment Configuration

### Install
```bash
pip install pydantic-settings python-dotenv
pip freeze > requirements.txt
```

### backend/config.py
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    redis_url: str
    secret_key: str
    groq_api_key: str
    sentry_dsn: str = ""
    env: str = "development"

    class Config:
        env_file = ".env"

settings = Settings()
```

### backend/.env
```
DATABASE_URL=postgresql://pulse:pulse@localhost:5432/pulse
REDIS_URL=redis://localhost:6379
SECRET_KEY=change-this-in-production-use-a-long-random-string
GROQ_API_KEY=your-groq-api-key-here
SENTRY_DSN=
ENV=development
```

### backend/.env.example
```
DATABASE_URL=postgresql://pulse:pulse@localhost:5432/pulse
REDIS_URL=redis://localhost:6379
SECRET_KEY=
GROQ_API_KEY=
SENTRY_DSN=
ENV=development
```

**Why this matters:**
If `database_url` is missing, the app crashes immediately on startup with a
clear error: "field required". Without this, it crashes later with a confusing
database connection error. Fail fast with a clear message.

**Never commit .env to git. Add it to .gitignore:**
```
.env
.venv
__pycache__
```

Import settings in main.py:
```python
from config import settings
print(settings.env)  # verify it loads
```

---

## Step 0.6 — structlog: Structured Logging

### Install
```bash
pip install structlog
pip freeze > requirements.txt
```

### backend/logger.py
```python
import structlog
import logging

def setup_logging():
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.stdlib.add_log_level,
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    )

log = structlog.get_logger()
```

### Update main.py
```python
from fastapi import FastAPI
from config import settings
from logger import setup_logging, log

setup_logging()

app = FastAPI()

@app.get("/health")
def health():
    log.info("health.check", env=settings.env)
    return {"status": "ok"}
```

Now when you hit /health you get a JSON log line:
```json
{"event": "health.check", "env": "development", "level": "info", "timestamp": "2026-04-28T..."}
```

**Why JSON logs:**
Plain text logs are for humans reading a terminal.
JSON logs are for machines — you can search, filter and alert on them.
In production you pipe these to a log aggregator and search them when
something breaks at 3am.

---

## Step 0.7 — Sentry: Error Tracking

### Install
```bash
pip install sentry-sdk[fastapi]
pip freeze > requirements.txt
```

Sign up at sentry.io. Create a new Python project. Copy the DSN.
Add it to your .env: `SENTRY_DSN=https://...`

### Update main.py
```python
import sentry_sdk
from config import settings
from logger import setup_logging, log

if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.env,
        traces_sample_rate=1.0,
    )

setup_logging()
app = FastAPI()
```

**Test it works:**
Add a temporary route that raises an exception:
```python
@app.get("/test-sentry")
def test_sentry():
    raise Exception("Sentry is working")
```

Hit it. Check your Sentry dashboard — the error should appear within seconds.
Delete the route after testing.

**What Sentry gives you that logs don't:**
Logs tell you something happened.
Sentry tells you: what happened, where in the code, what the full stack trace
was, how many times it happened, which users were affected, and sends you
an email alert. That is what you need when something breaks in production.

---

## Step 0.8 — Health Check with Dependencies

Update the health endpoint to actually check if dependencies are alive:

```python
from fastapi import FastAPI, HTTPException
from sqlalchemy import text
import redis as redis_lib
from config import settings

redis_client = redis_lib.Redis.from_url(settings.redis_url)

@app.get("/health")
def health(db=Depends(get_db)):
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
```

**Why this matters:**
A health endpoint that only checks if the server is running is useless.
If the database is down, the server is technically up but nothing works.
Load balancers and deployment platforms use /health to decide if your
app is ready to receive traffic. Make it tell the truth.

---

## Update docker-compose.yml for production DATABASE_URL

The backend needs to use the Docker service name not localhost:

```yaml
backend:
  environment:
    - DATABASE_URL=postgresql://pulse:pulse@db:5432/pulse
    - REDIS_URL=redis://redis:6379
```

Inside Docker, services communicate by service name.
`db` resolves to the PostgreSQL container.
`localhost` inside the backend container refers to the backend container itself.

---

## Final Check — Phase 0 Complete When:

```bash
docker compose up --build
```

- http://localhost:8000/health returns status, database and redis all "ok"
- http://localhost:3000 shows Pulse Dashboard
- Logs are JSON format in the terminal
- Sentry dashboard shows your test error (then delete the test route)
- .env is in .gitignore and NOT committed

---

## Answer These Out Loud Before Moving to Phase 1

1. What does uvicorn do and why is it separate from FastAPI?
2. What does --reload do and why turn it off in production?
3. Why does the Dockerfile copy requirements.txt before the rest of the code?
4. What happens if DATABASE_URL is missing from .env?
5. Why are JSON logs better than plain text logs in production?
6. What does Sentry give you that a log file does not?
7. Why is the healthcheck in docker-compose.yml important?
8. Why does DATABASE_URL use "db" as the host inside Docker but "localhost" outside?

If you can't answer all eight, go back. Don't move forward.
