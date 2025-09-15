import boto3
from fastapi import APIRouter

router = APIRouter()

R2_ACCESS_KEY = "da77dbc893cb7a2b6658b8e84518b3"
R2_SECRET_KEY = "d73e0c0337a3b2aefce9b2a5bca2750530475ea135089e2386e397abe743"
R2_BUCKET = "fastapi-pdf-app"

# ✅ Dùng r2.dev thay cho cloudflarestorage.com
R2_ENDPOINT = f"https://{R2_BUCKET}.r2.dev"

s3 = boto3.client(
    "s3",
    endpoint_url=R2_ENDPOINT,
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY,
)

@router.get("/r2/test")
def test_r2():
    try:
        # Upload thử
        s3.put_object(Bucket=R2_BUCKET, Key="test.txt", Body=b"Hello from Render + R2!")

        # Lấy file về
        obj = s3.get_object(Bucket=R2_BUCKET, Key="test.txt")
        content = obj["Body"].read().decode("utf-8")

        return {
            "status": "success",
            "bucket": R2_BUCKET,
            "content": content,
            "public_url": f"https://{R2_BUCKET}.r2.dev/test.txt"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
