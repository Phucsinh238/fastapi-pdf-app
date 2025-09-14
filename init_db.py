from fastapi import APIRouter
import boto3
import os
from io import BytesIO

router = APIRouter()

# ==============================
# 🔧 Config Cloudflare R2 (dùng env trên Render)
# ==============================
R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID", "bcd766b6e3d7d90bf451671a1d7c3de")
R2_ACCESS_KEY = os.getenv("R2_ACCESS_KEY", "da77dbc893cb7a2b6658b8e84518b3")
R2_SECRET_KEY = os.getenv("R2_SECRET_KEY", "d73e0c0337a3b2aefce9b2a5bca2750530475ea135089e2386e397abe743")
R2_BUCKET = os.getenv("R2_BUCKET", "fastapi-pdf-app")

# Endpoint R2 (dùng .r2.cloudflarestorage.com hoặc public .r2.dev)
R2_ENDPOINT = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

# Tạo client S3
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
    """Upload file test.txt vào R2 (trên bộ nhớ, không ghi ổ đĩa Render)"""
    data = b"Hello from Render + Cloudflare R2!"

    # Upload trực tiếp từ bộ nhớ
    s3.upload_fileobj(BytesIO(data), R2_BUCKET, "test.txt")

    return {"message": "✅ Uploaded test.txt to R2"}


@router.get("/r2/download-test")
def download_test():
    """Download test.txt từ R2 về và đọc nội dung"""
    buffer = BytesIO()
    s3.download_fileobj(R2_BUCKET, "test.txt", buffer)
    buffer.seek(0)

    content = buffer.read().decode("utf-8")

    return {"message": "✅ Downloaded test.txt from R2", "content": content}
