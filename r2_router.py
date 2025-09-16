import boto3
from fastapi import APIRouter

router = APIRouter(prefix="/r2", tags=["Cloudflare R2"])

R2_ACCOUNT_ID = "bcd766b6e3d7d90bf451671a1d7c3de"
R2_ACCESS_KEY = "al6cc8fb6c39f659e9dfe3219a4bd"
R2_SECRET_KEY = "49bcc87eaa6ff1edb88312346373914a2d83d4ca209ae700a4a379f77c34b"
R2_BUCKET = "fastapi-pdf-app"

# ✅ Bucket phải đưa vào host
R2_ENDPOINT = f"https://{R2_BUCKET}.{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
# Nếu vẫn lỗi, thử: R2_ENDPOINT = f"https://{R2_BUCKET}.{R2_ACCOUNT_ID}.r2.dev"

s3 = boto3.client(
    "s3",
    endpoint_url=R2_ENDPOINT,
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY,
)

@router.get("/upload-test")
def upload_test():
    try:
        with open("test.txt", "w") as f:
            f.write("Hello from Cloudflare R2 via Render!")
        s3.upload_file("test.txt", R2_BUCKET, "test.txt")
        return {"status": "success", "message": "Uploaded test.txt to R2"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/download-test")
def download_test():
    try:
        s3.download_file(R2_BUCKET, "test.txt", "downloaded_test.txt")
        with open("downloaded_test.txt", "r") as f:
            content = f.read()
        return {"status": "success", "content": content}
    except Exception as e:
        return {"status": "error", "message": str(e)}
