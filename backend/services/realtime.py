import json
from urllib.parse import urlparse

import redis
import redis.asyncio as aioredis
from arq.connections import RedisSettings

from config import settings
from logger import log


redis_client = redis.Redis.from_url(settings.redis_url)
redis_url = urlparse(settings.redis_url)
REDIS_SETTINGS = RedisSettings(
    host=redis_url.hostname or "localhost",
    port=redis_url.port or 6379,
)


async def redis_listener(manager) -> None:
    redis_connection = aioredis.Redis.from_url(settings.redis_url)
    pubsub = redis_connection.pubsub()

    try:
        await pubsub.psubscribe("job:*")
        log.info("redis.listener.started", pattern="job:*")

        async for message in pubsub.listen():
            if message["type"] != "pmessage":
                continue

            try:
                payload = message["data"]
                if isinstance(payload, bytes):
                    payload = payload.decode("utf-8")

                data = json.loads(payload)
                job_id = data.get("job_id")
                if job_id:
                    await manager.send_update(job_id, data)
            except Exception as e:
                log.error("redis.listener.message_error", error=str(e))
    except Exception as e:
        log.error("redis.listener.failed", error=str(e))
        raise
    finally:
        await pubsub.close()
        await redis_connection.close()
