from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import generate, upload

app = FastAPI(title="Comicly")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router, prefix="/api/upload", tags=["upload"])
app.include_router(generate.router, prefix="/api/generate", tags=["generate"])


@app.get("/")
def root():
    return {"status": "ok", "message": "Comicly backend running"}


@app.get("/health")
def health():
    return {"status": "healthy"}

