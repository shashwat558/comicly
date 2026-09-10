from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.db import init_db
from app.routes.v1 import books_router, generate_router, jobs_router, pages_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if settings.env != "test":
        try:
            await init_db()
        except Exception as e:
            print(f"DB init failed (will retry on request): {e}")
        try:
            from app.services.image_store import ensure_bucket
            await ensure_bucket()
        except Exception as e:
            print(f"S3 bucket ensure failed: {e}")
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Comicly", version="2.0.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url],
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )


    app.include_router(books_router, prefix="/api/v1/books", tags=["books"])
    app.include_router(pages_router, prefix="/api/v1/books", tags=["pages"])
    app.include_router(generate_router, prefix="/api/v1/books", tags=["generate"])
    app.include_router(jobs_router, prefix="/api/v1/jobs", tags=["jobs"])


    try:
        from app.routes import generate as legacy_generate
        from app.routes import upload as legacy_upload
        app.include_router(legacy_upload.router, prefix="/api/upload", tags=["legacy-upload"])
        app.include_router(legacy_generate.router, prefix="/api/generate", tags=["legacy-generate"])
    except Exception as e:
        print(f"Legacy routers not mounted: {e}")

    @app.get("/")
    def root():
        return {"status": "ok", "message": "Comicly backend running", "version": "2.0.0"}

    @app.get("/health")
    def health():
        return {"status": "healthy"}

    @app.get("/ready")
    async def ready():
        checks: dict = {}
        try:
            from sqlalchemy import text

            from app.core.db import SessionLocal
            async with SessionLocal() as s:
                await s.execute(text("SELECT 1"))
            checks["db"] = "ok"
        except Exception as e:
            checks["db"] = f"error: {e}"[:200]
        try:
            from app.core.redis import get_redis
            await get_redis().ping()
            checks["redis"] = "ok"
        except Exception as e:
            checks["redis"] = f"error: {e}"[:200]
        ok = all(v == "ok" for v in checks.values())
        return {"ready": ok, "checks": checks}

    return app


app = create_app()
