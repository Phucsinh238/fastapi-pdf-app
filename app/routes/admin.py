from fastapi import APIRouter, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
import os, openpyxl
from sqlalchemy import text
from app.database import engine
from datetime import datetime
import boto3, os

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# 🔑 Cloudflare R2 config (hardcode)
R2_ENDPOINT_URL = "https://bcdb766b6e3d7d90bf451671a1d7c3de.r2.cloudflarestorage.com"
R2_ACCESS_KEY_ID = "24bcd7f68391b74c3712d0919b6a0c66"
R2_SECRET_ACCESS_KEY = "8eb34c1864c1e90ec42f67d0217aa2e3e7fac5225dd8b32e52b3575536ac6f4b"
R2_BUCKET_NAME = "fastapi-pdf-app"

R2_BUCKET = os.getenv("R2_BUCKET_NAME", "fastapi-pdf-app")  # đổi thành tên bucket của anh

s3_client = boto3.client(
    "s3",
    endpoint_url=R2_ENDPOINT_URL,
    aws_access_key_id=R2_ACCESS_KEY_ID,
    aws_secret_access_key=R2_SECRET_ACCESS_KEY,
)

UPLOAD_DIR = "app/uploads"
UPLOAD_FOLDER = "app/uploads"


router = APIRouter()


# 📤 Form upload
@router.get("/upload")
def upload_form(request: Request):
    role = request.session.get("role")
    if role not in ["admin", "superadmin"]:
        raise HTTPException(status_code=403, detail="Only admins can upload files.")
    return templates.TemplateResponse("upload.html", {"request": request})

# 📤 Upload file (ghi vào Postgres + R2)
@router.post("/upload")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    folder: str = Form(""),
    price: float = Form(19.99)   # mặc định 19.99 nếu không nhập
):
    role = request.session.get("role")
    username = request.session.get("username")

    if role not in ["admin", "superadmin"]:
        raise HTTPException(status_code=403, detail="You are not allowed to upload files.")

    # object_key chính là đường dẫn file trên R2
    object_key = os.path.join(folder.strip("/\\"), file.filename) if folder else file.filename

    # Upload lên R2
    try:
        s3_client.upload_fileobj(
            file.file,
            R2_BUCKET,
            object_key
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload to R2 failed: {e}")

    # Ghi log vào database Postgres (lưu cả r2_key + price)
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO documents (filename, filepath, r2_key, price, uploaded_by, upload_time)
                VALUES (:filename, :filepath, :r2_key, :price, :uploaded_by, :upload_time)
            """),
            {
                "filename": file.filename,
                "filepath": object_key,   # không lưu local nữa, lưu luôn key
                "r2_key": object_key,     # chuẩn để xoá sau này
                "price": price,
                "uploaded_by": username,
                "upload_time": datetime.utcnow()
            }
        )

    request.session["flash"] = f"✅ File '{file.filename}' uploaded with price ${price:.2f}"
    return RedirectResponse(url="/", status_code=302)



# 🗑️ Xóa file theo ID (admin/superadmin)
@router.get("/delete/{file_id}")
def delete_file(file_id: int, request: Request):
    role = request.session.get("role")
    if role not in ["admin", "superadmin"]:
        raise HTTPException(status_code=403, detail="You are not allowed to delete files.")

    with engine.begin() as conn:
        result = conn.execute(
            text("SELECT r2_key FROM documents WHERE id = :id"),
            {"id": file_id}
        )
        row = result.fetchone()

        if row and row[0]:
            try:
                s3_client.delete_object(Bucket=R2_BUCKET, Key=row[0])
                print(f"✅ Deleted {row[0]} from R2")
            except Exception as e:
                print(f"⚠️ Lỗi khi xóa file trên R2: {e}")

        conn.execute(text("DELETE FROM documents WHERE id = :id"), {"id": file_id})

    return RedirectResponse(url="/", status_code=302)


