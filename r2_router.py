from fastapi import APIRouter
import boto3
from botocore.client import Config
import os

router = APIRouter(prefix="/r2", tags=["Cloudflare R2"])

# =============================
# Cloudflare R2 Config
# =============================
R2_ACCESS_KEY_ID = "24bcd7f68391b74c3712d0919b6a0c66"
R2_SECRET_ACCESS_KEY = "8eb34c1864c1e90ec42f67d0217aa2e3e7fac5225dd8b32e52b3575536ac6f4b"
R2_BUCKET = "fastapi-pdf-app"
R2_ENDPOINT = "https://bcdb766b6e3d7d90bf451671a1d7c3de.r2.cloudflarestorage.com"

# =============================
# Boto3 Client
# =============================
s3 = boto3.client(
    "s3",
    endpoint_url=R2_ENDPOINT,
    aws_access_key_id=R2_ACCESS_KEY_ID,
    aws_secret_access_key=R2_SECRET_ACCESS_KEY,
    config=Config(signature_version="s3v4"),
    region_name="auto",
)

# =============================
# Routes
# =============================

@router.get("/upload-test")
def upload_test():
    try:
        test_content = b"Hello from Render + Cloudflare R2!"
        s3.put_object(Bucket=R2_BUCKET, Key="test.txt", Body=test_content)
        return {"status": "success", "message": "File uploaded to R2 successfully"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/download-test")
def download_test():
    try:
        obj = s3.get_object(Bucket=R2_BUCKET, Key="test.txt")
        content = obj["Body"].read().decode("utf-8")
        return {"status": "success", "content": content}
    except Exception as e:
        return {"status": "error", "message": str(e)}
