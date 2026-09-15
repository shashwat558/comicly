from app.core import s3 as s3core


async def ensure_bucket() -> None:
    await s3core.ensure_bucket()


async def upload_frame(book_id: str, page_no: int, data: bytes) -> tuple[str, str]:
    key = f"{book_id}/{page_no:04d}.png"
    url = await s3core.upload_png(key, data)
    return key, url


async def upload_reference(book_id: str, name: str, data: bytes) -> tuple[str, str]:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)[:60]
    key = f"{book_id}/refs/{safe}.png"
    url = await s3core.upload_png(key, data)
    return key, url


async def upload_draft(book_id: str, page_no: int, attempt: int, data: bytes) -> tuple[str, str]:
    key = f"{book_id}/{page_no:04d}_draft{'_r' + str(attempt) if attempt else ''}.png"
    url = await s3core.upload_png(key, data)
    return key, url


async def upload_sheet(book_id: str, name: str, version: int, data: bytes) -> tuple[str, str]:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)[:60] or "char"
    key = f"{book_id}/sheets/{safe}_v{int(version)}.png"
    url = await s3core.upload_png(key, data)
    return key, url


async def upload_style_ref(book_id: str, name: str, data: bytes) -> tuple[str, str]:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)[:60] or "style"
    key = f"{book_id}/style/{safe}.png"
    url = await s3core.upload_png(key, data)
    return key, url


async def download_bytes(url: str) -> bytes:
    return await s3core.download_bytes(url)
