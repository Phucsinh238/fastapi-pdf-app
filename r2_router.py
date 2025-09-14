import boto3
from fastapi import APIRouter

router = APIRouter()

# ==============================
# 🔧 Config Cloudflare R2
# ==============================
R2_ACCOUNT_ID = "bcd766b6e3d7d90bf451671a1d7c3de"
R2_ACCESS_KEY = "da77dbc893cb7a2b6658b8e84518b3"
R2_SECRET_KEY = "d73e0c0337a3b2aefce9b2a5bca2750530475ea135089e2386e397abe743"
R2_BUCKET = "fastapi-pdf-app"

# Dùng endpoint chuẩn (không dùng .r2.dev cho boto3)
R2_ENDPOINT = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

# Kết nối client
s3 = boto3.client(
    "s3",
    endpoint_url=R2_ENDPOINT,
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY,
    verify=False,  # ⚠️ Bỏ SSL verify để tránh lỗi handshake trên Render
)

# ==============================
# 🧪 Test API
# ==============================

@router.get("/r2/upload-test")
def upload_test():
    try:
        # Upload nội dung "Hello" trực tiếp lên R2
        s3.put_object(
            Bucket=R2_BUCKET,
            Key="test.txt",
            Body=b"Hello from Cloudflare R2 via Render!",
        )
        return {"status": "success", "message": "Uploaded test.txt to R2 ✅"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/r2/download-test")
def download_test():
    try:
        obj = s3.get_object(Bucket=R2_BUCKET, Key="test.txt")
        content = obj["Body"].read().decode("utf-8")
        return {"status": "success", "content": content}
    except Exception as e:
        return {"status": "error", "message": str(e)}
