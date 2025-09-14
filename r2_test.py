# r2_test.py
import boto3

# ==============================
# 🔧 Config Cloudflare R2
# ==============================
R2_ACCOUNT_ID = "bcd766b6e3d7d90bf451671a1d7c3de"
R2_ACCESS_KEY = "da77dbc893cb7a2b6658b8e84518b3"
R2_SECRET_KEY = "d73e0c0337a3b2aefce9b2a5bca2750530475ea135089e2386e397abe743"
R2_BUCKET = "fastapi-pdf-app"

R2_ENDPOINT = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

# Kết nối client
s3 = boto3.client(
    "s3",
    endpoint_url=R2_ENDPOINT,
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY,
)

def test_upload_download():
    # 1. Tạo file test.txt local
    with open("test.txt", "w") as f:
        f.write("Hello from Render + Cloudflare R2!")

    print("📄 Created local file test.txt")

    # 2. Upload lên bucket
    s3.upload_file("test.txt", R2_BUCKET, "test.txt")
    print("✅ Uploaded test.txt to R2")

    # 3. Download từ R2 về (đặt tên mới)
    s3.download_file(R2_BUCKET, "test.txt", "downloaded_test.txt")
    print("✅ Downloaded test.txt from R2 as downloaded_test.txt")

    # 4. Kiểm tra nội dung file tải về
    with open("downloaded_test.txt", "r") as f:
        content = f.read()
        print("📥 Downloaded file content:", content)


if __name__ == "__main__":
    test_upload_download()
