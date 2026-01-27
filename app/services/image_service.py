import boto3

s3 = boto3.client(
    "s3",
    endpoint_url="http://localhost:9000",
    aws_access_key_id="minioadmin",
    aws_secret_access_key="minioadmin",
    region_name="us-east-1",
    
);

def upload_image_to_s3(image_bytes: bytes, bucket_name:str, object_name:str) -> str:
    """Uploads image bytes to S3 and returns the URL.

    Args:
        image_bytes (bytes): The image data in bytes.
        bucket_name (str): The name of the S3 bucket.
        object_name (str): The object name (key) in the S3 bucket.

    Returns:
        str: The URL of the uploaded image.
    """
    s3.put_object(Bucket=bucket_name, Key=object_name, Body=image_bytes, ContentType='image/png')
    url = f"{s3.meta.endpoint_url}/{bucket_name}/{object_name}"
    return url

