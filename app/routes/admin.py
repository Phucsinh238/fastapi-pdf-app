from fastapi import APIRouter, Request, UploadFile, Form, HTTPException
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


# 📤 Upload file (Cloudflare R2 + Postgres log)
@router.post("/upload")
async def upload_file(request: Request, file: UploadFile, folder: str = Form("")):
    role = request.session.get("role")
    username = request.session.get("username")

    if role not in ["admin", "superadmin"]:
        raise HTTPException(status_code=403, detail="You are not allowed to upload files.")

    try:
        # Đường dẫn object trong bucket
        object_key = os.path.join(folder.strip("/\\"), file.filename).replace("\\", "/")
        
        # Upload trực tiếp lên R2
        s3_client.upload_fileobj(file.file, R2_BUCKET_NAME, object_key)

        # Ghi log vào Postgres
        with engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO documents (filename, filepath, uploaded_by, upload_time)
                    VALUES (:filename, :filepath, :uploaded_by, :upload_time)
                """),
                {
                    "filename": file.filename,
                    "filepath": f"s3://{R2_BUCKET_NAME}/{object_key}",
                    "uploaded_by": username,
                    "upload_time": datetime.utcnow()
                }
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload to R2 failed: {e}")

    return RedirectResponse(url="/", status_code=302)




# 🗑️ Xóa file theo ID (admin/superadmin)
@router.get("/delete/{file_id}")
def delete_file(file_id: int, request: Request):
    role = request.session.get("role")
    if role not in ["admin", "superadmin"]:
        raise HTTPException(status_code=403, detail="You are not allowed to delete files.")

    with engine.begin() as conn:
        result = conn.execute(
            text("SELECT filename, filepath FROM documents WHERE id = :id"),
            {"id": file_id}
        )
        row = result.fetchone()

        if row:
            filename = row[0]
            file_path = row[1]

            # Xóa file local (nếu có)
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                print(f"⚠️ Lỗi khi xóa local file: {e}")

            # Xóa file trên R2
            try:
                s3_client.delete_object(Bucket=R2_BUCKET, Key=filename)
                print(f"✅ Deleted {filename} from R2")
            except Exception as e:
                print(f"⚠️ Lỗi khi xóa file trên R2: {e}")

            # Xóa record DB
            conn.execute(text("DELETE FROM documents WHERE id = :id"), {"id": file_id})

    return RedirectResponse(url="/", status_code=302)

