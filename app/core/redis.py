import redis.asyncio as redis

from app.core.config import get_settings

_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.from_url(get_settings().redis_url, decode_responses=True)
    return _client


async def publish_progress(job_id: str, payload: dict) -> None:
    import json

    r = get_redis()
    await r.publish(f"comicly:job:{job_id}", json.dumps(payload))

    await r.set(f"comicly:job:{job_id}:last", json.dumps(payload), ex=3600)


async def last_progress(job_id: str) -> dict | None:
    import json

    r = get_redis()
    raw = await r.get(f"comicly:job:{job_id}:last")
    return json.loads(raw) if raw else None
