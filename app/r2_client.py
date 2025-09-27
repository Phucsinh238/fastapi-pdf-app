import boto3
from botocore.client import Config

R2_ENDPOINT_URL = "https://bcdb766b6e3d7d90bf451671a1d7c3de.r2.cloudflarestorage.com"
R2_ACCESS_KEY_ID = "24bcd7f68391b74c3712d0919b6a0c66"
R2_SECRET_ACCESS_KEY = "8eb34c1864c1e90ec42f67d0217aa2e3e7fac5225dd8b32e52b3575536ac6f4b"
R2_BUCKET_NAME = "fastapi-pdf-app"

s3_client = boto3.client(
    "s3",
    endpoint_url=R2_ENDPOINT_URL,
    aws_access_key_id=R2_ACCESS_KEY_ID,
    aws_secret_access_key=R2_SECRET_ACCESS_KEY,
    config=Config(signature_version="s3v4"),
)
