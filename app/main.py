from fastapi import FastAPI
from app.routes import generate, upload

app = FastAPI(title="Comicly")

app.include_router(upload.router, prefix="api/upload", tags=["upload"])
app.include_router(generate.router, prefix="api/generate", tags=["generate"])

@app.get("/")
def root():
    return {"status": "ok", "message": "Comicly backend running"}

