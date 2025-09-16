import boto3
from fastapi import APIRouter

router = APIRouter()

# ==============================
# 🔧 Config Cloudflare R2
# ==============================
R2_ACCESS_KEY = "al6cc8fb6c39f659e9d2f3e219a4bd"
R2_SECRET_KEY = "49bc8e7eaa6ff1edb88312346373914a2d83d4ca209ae700a4a379f77c34b"
R2_BUCKET = "fastapi-pdf-app"

# Endpoint Cloudflare R2 (anh copy từ dashboard)
R2_ENDPOINT = "https://bcd766b6e3d7d90bf451671a1d7c3de.r2.cloudflarestorage.com"

# Tạo client kết nối S3
s3 = boto3.client(
    "s3",
    endpoint_url=R2_ENDPOINT,
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY,
)

# ==============================
# 🧪 API Test Upload & Download
# ==============================

@router.get("/r2/upload-test")
def upload_test():
    try:
        # 1. Tạo file test.txt trong container Render
        with open("test.txt", "w") as f:
            f.write("Hello from Render -> Cloudflare R2!")

        # 2. Upload file
        s3.upload_file("test.txt", R2_BUCKET, "test.txt")

        return {"status": "success", "message": "✅ Uploaded test.txt to Cloudflare R2"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/r2/download-test")
def download_test():
    try:
        # 1. Download file từ R2 về container Render
        s3.download_file(R2_BUCKET, "test.txt", "downloaded_test.txt")

        # 2. Đọc lại nội dung
        with open("downloaded_test.txt", "r") as f:
            content = f.read()

        return {
            "status": "success",
            "message": "✅ Downloaded file from Cloudflare R2",
            "content": content,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
