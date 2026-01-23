from fastapi import APIRouter, File, HTTPException, UploadFile

router = APIRouter()

@router.post("/", status_code=201)
async def upload_file(file: UploadFile = File(...)):
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "size_bytes": len(content),
    }
