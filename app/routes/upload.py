from typing import Optional
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi import Form
router = APIRouter()

@router.post("/", status_code=201)
async def upload_file(file: UploadFile = File(...), title: str = Form(...), author: str = Form(...), publication_date: Optional[str] = Form(None), isbn: Optional[str] = Form(None)):
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "size_bytes": len(content),
    }
