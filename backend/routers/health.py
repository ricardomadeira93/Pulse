from fastapi import APIRouter, Depends
from sqlalchemy import text

from database import get_db
from logger import log
from services.realtime import redis_client


router = APIRouter(tags=["health"])


@router.get("/health")
def health(db=Depends(get_db)):
    result = {"status": "Ok", "database": "unknown", "redis": "unknown"}
    try:
        db.execute(text("Select 1"))
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
