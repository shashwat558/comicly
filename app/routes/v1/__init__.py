from app.routes.v1.books import router as books_router
from app.routes.v1.generate import router as generate_router
from app.routes.v1.jobs import router as jobs_router
from app.routes.v1.pages import router as pages_router

__all__ = ["books_router", "generate_router", "jobs_router", "pages_router"]
