import boto3
from fastapi import APIRouter

router = APIRouter()

R2_ACCOUNT_ID = "bcd766b6e3d7d90bf451671a1d7c3de"
R2_ACCESS_KEY = "da77dbc893cb7a2b6658b8e84518b3"
R2_SECRET_KEY = "d73e0c0337a3b2aefce9b2a5bca2750530475ea135089e2386e397abe743"
R2_BUCKET = "fastapi-pdf-app"

# ⚡ Dùng S3 endpoint cho boto3
R2_S3_ENDPOINT = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

# ⚡ Dùng r2.dev để truy cập file public
R2_PUBLIC_URL = f"https://{R2_BUCKET}.r2.dev"

s3 = boto3.client(
    "s3",
    endpoint_url=R2_S3_ENDPOINT,
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY,
)

@router.get("/r2/upload-test")
def upload_test():
    try:
        s3.put_object(
            Bucket=R2_BUCKET,
            Key="test.txt",
            Body=b"Hello from Cloudflare R2 via Render!",
        )
        return {
            "status": "success",
            "message": "Uploaded test.txt to R2 ✅",
            "public_url": f"{R2_PUBLIC_URL}/test.txt"
        }
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

@router.get("/r2/list-files")
def list_files():
    try:
        resp = s3.list_objects_v2(Bucket=R2_BUCKET)
        files = [item["Key"] for item in resp.get("Contents", [])]
        return {"status": "success", "files": files}
    except Exception as e:
        return {"status": "error", "message": str(e)}
