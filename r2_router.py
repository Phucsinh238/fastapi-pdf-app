# r2_router.py
from fastapi import APIRouter
import boto3, os

router = APIRouter()

# ==============================
# 🔧 Config Cloudflare R2
# ==============================
R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID", "bcd766b6e3d7d90bf451671a1d7c3de")
R2_ACCESS_KEY = os.getenv("R2_ACCESS_KEY", "da77dbc893cb7a2b6658b8e84518b3")
R2_SECRET_KEY = os.getenv("R2_SECRET_KEY", "d73e0c0337a3b2aefce9b2a5bca2750530475ea135089e2386e397abe743")
R2_BUCKET = os.getenv("R2_BUCKET", "fastapi-pdf-app")

R2_ENDPOINT = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

s3 = boto3.client(
    "s3",
    endpoint_url=R2_ENDPOINT,
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY,
)

# ==============================
# 🧪 Endpoint test R2
# ==============================
@router.get("/r2/test")
def test_r2():
    try:
        # Upload file test lên R2
        s3.put_object(Bucket=R2_BUCKET, Key="test.txt", Body="Hello from Render + Cloudflare R2!")

        # Download lại file
        obj = s3.get_object(Bucket=R2_BUCKET, Key="test.txt")
        content = obj["Body"].read().decode()

        return {
            "status": "ok",
            "bucket": R2_BUCKET,
            "content": content
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
