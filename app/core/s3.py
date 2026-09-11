import aioboto3
from botocore.exceptions import ClientError

from app.core.config import get_settings


def _client_kwargs() -> dict:
    s = get_settings()
    return {
        "endpoint_url": s.s3_endpoint_url,
        "aws_access_key_id": s.s3_access_key,
        "aws_secret_access_key": s.s3_secret_key,
        "region_name": s.s3_region,
    }


async def ensure_bucket() -> None:
    s = get_settings()
    session = aioboto3.Session()
    async with session.client("s3", **_client_kwargs()) as s3:
        try:
            await s3.head_bucket(Bucket=s.s3_bucket)
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code in ("404", "NoSuchBucket", "NotFound"):
                await s3.create_bucket(Bucket=s.s3_bucket)
            else:
                raise


async def upload_png(key: str, data: bytes) -> str:
    return await upload_bytes(key, data, "image/png")


async def upload_bytes(key: str, data: bytes, content_type: str) -> str:
    s = get_settings()
    session = aioboto3.Session()
    async with session.client("s3", **_client_kwargs()) as s3:
        await s3.put_object(
            Bucket=s.s3_bucket, Key=key, Body=data, ContentType=content_type
        )
    return f"{s.s3_public_url.rstrip('/')}/{key}"


async def download_key(key: str) -> bytes:
    s = get_settings()
    session = aioboto3.Session()
    async with session.client("s3", **_client_kwargs()) as s3:
        resp = await s3.get_object(Bucket=s.s3_bucket, Key=key)
        body = resp["Body"]
        try:
            return await body.read()
        finally:
            body.close()


async def presigned_get(key: str, expires: int = 3600) -> str:
    s = get_settings()
    session = aioboto3.Session()
    async with session.client("s3", **_client_kwargs()) as s3:
        return await s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": s.s3_bucket, "Key": key},
            ExpiresIn=expires,
        )


async def download_bytes(url: str) -> bytes:
    import httpx

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.content
