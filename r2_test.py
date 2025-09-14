from fastapi import APIRouter
import boto3
import os
from io import BytesIO

router = APIRouter()

# ==============================
# 🔧 Config Cloudflare R2
# ==============================
R2_ACCESS_KEY = os.getenv("R2_ACCESS_KEY")
R2_SECRET_KEY = os.getenv("R2_SECRET_KEY")
R2_BUCKET = os.getenv("R2_BUCKET", "fastapi-pdf-app")

# ✅ Dùng endpoint r2.dev thay vì account_id
R2_ENDPOINT = f"https://{R2_BUCKET}.r2.dev"

s3 = boto3.client(
    "s3",
    endpoint_url=R2_ENDPOINT,
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY,
)

# ==============================
# 🧪 Test APIs
# ==============================
@router.get("/r2/upload-test")
def upload_test():
    data = b"Hello from Render + Cloudflare R2!"
    s3.upload_fileobj(BytesIO(data), R2_BUCKET, "test.txt")
    return {"message": "✅ Uploaded test.txt to R2"}

@router.get("/r2/download-test")
def download_test():
    buffer = BytesIO()
    s3.download_fileobj(R2_BUCKET, "test.txt", buffer)
    buffer.seek(0)
    content = buffer.read().decode("utf-8")
    return {"message": "✅ Downloaded test.txt from R2", "content": content}
