import json

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from app.core.redis import get_redis, last_progress
from app.schemas.v1.generate import JobStatus

router = APIRouter()


@router.get("/{job_id}", response_model=JobStatus)
async def job_status(job_id: str):
    data = await last_progress(job_id)
    if data is None:
        return JSONResponse({"detail": "Job not found"}, status_code=404)
    return JobStatus(
        job_id=job_id, status=data.get("status", "queued"),
        progress=int(data.get("progress", 0)), page_no=data.get("page_no"),
        image_url=data.get("image_url"), error=data.get("error"),
    )


@router.get("/{job_id}/stream")
async def job_stream(job_id: str):
    async def gen():
        r = get_redis()
        pubsub = r.pubsub()
        await pubsub.subscribe(f"comicly:job:{job_id}")

        last = await last_progress(job_id)
        if last:
            yield {"event": "progress", "data": json.dumps(last)}
            if last.get("status") in ("done", "error"):
                return
        try:
            async for msg in pubsub.listen():
                if msg.get("type") != "message":
                    continue
                data = msg["data"]
                if isinstance(data, bytes):
                    data = data.decode()
                yield {"event": "progress", "data": data}
                try:
                    payload = json.loads(data)
                except Exception:
                    continue
                if payload.get("status") in ("done", "error"):
                    break
        finally:
            try:
                await pubsub.unsubscribe(f"comicly:job:{job_id}")
                await pubsub.close()
            except Exception:
                pass

    return EventSourceResponse(gen(), ping=15)
