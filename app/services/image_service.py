import boto3

s3 = boto3.client(
    "s3",
    endpoint_url="http://localhost:9000",
    aws_access_key_id="minioadmin",
    aws_secret_access_key="minioadmin",
    region_name="us-east-1",

);

async def upload_image_to_s3(image_bytes: bytes, bucket_name:str, object_name:str) -> str:
    await s3.put_object(Bucket=bucket_name, Key=object_name, Body=image_bytes, ContentType='image/png')
    url = f"{s3.meta.endpoint_url}/{bucket_name}/{object_name}"
    return url

