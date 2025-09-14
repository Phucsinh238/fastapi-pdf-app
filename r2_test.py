import os
import boto3
from botocore.exceptions import ClientError

# ==============================
# 🔧 Config Cloudflare R2
# ==============================
R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID", "bcd766b6e3d7d90bf451671a1d7c3de")
R2_ACCESS_KEY = os.getenv("R2_ACCESS_KEY", "YOUR_ACCESS_KEY")
R2_SECRET_KEY = os.getenv("R2_SECRET_KEY", "YOUR_SECRET_KEY")
R2_BUCKET = os.getenv("R2_BUCKET", "fastapi-pdf-app")

# Endpoint chuẩn cho boto3
R2_ENDPOINT = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

# Tạo client
s3 = boto3.client(
    "s3",
    endpoint_url=R2_ENDPOINT,
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY,
)

# ==============================
# 🧪 Test Upload & Download
# ==============================

def test_r2():
    try:
        # 1. Tạo file test.txt local
        with open("test.txt", "w") as f:
            f.write("Hello from Cloudflare R2!")
        print("📄 Created local file test.txt")

        # 2. Upload lên bucket
        s3.upload_file("test.txt", R2_BUCKET, "test.txt")
        print("✅ Uploaded test.txt to R2")

        # 3. Download từ R2 về (đặt tên mới)
        s3.download_file(R2_BUCKET, "test.txt", "downloaded_test.txt")
        print("✅ Downloaded test.txt from R2")

        # 4. Kiểm tra nội dung file tải về
        with open("downloaded_test.txt", "r") as f:
            content = f.read()
        print("📥 Downloaded file content:", content)

        return {"status": "success", "content": content}

    except ClientError as e:
        print("❌ Boto3 ClientError:", e)
        return {"status": "error", "details": str(e)}
    except Exception as e:
        print("❌ Unexpected Error:", e)
        ret
