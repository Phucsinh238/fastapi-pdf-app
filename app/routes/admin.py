

from fastapi import APIRouter, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
import shutil, os
import openpyxl
from sqlalchemy import text
from app.database import engine
from datetime import datetime
import boto3


from app.database import engine

router = APIRouter()

# ==============================
# 🔧 Config Cloudflare R2
# ==============================
R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID", "bcdb766b6e3d7d90bf451671a1d7c3de")
R2_ACCESS_KEY = os.getenv("R2_ACCESS_KEY", "24bcd7f68391b74c3712d0919b6a0c66")
R2_SECRET_KEY = os.getenv("R2_SECRET_KEY", "8eb34c1864c1e90ec42f67d0217aa2e3e7fac5225dd8b32e52b3575536ac6f4b")
R2_BUCKET = os.getenv("R2_BUCKET", "fastapi-pdf-app")

# Dùng endpoint r2.dev thay vì cloudflarestorage.com
R2_ENDPOINT = f"https://{R2_BUCKET}.{R2_ACCOUNT_ID}.r2.dev"

s3 = boto3.client(
    "s3",
    endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",  # API gốc cho boto3
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY,
)

# 📤 Form upload
@router.get("/upload")
def upload_form(request: Request):
    role = request.session.get("role")
    if role not in ["admin", "superadmin"]:
        raise HTTPException(status_code=403, detail="Only admins can upload files.")
    
    return templates.TemplateResponse("upload.html", {"request": request})


# 📤 Upload file lên R2
@router.post("/upload")
async def upload_file(request: Request, file: UploadFile, folder: str = Form("")):
    role = request.session.get("role")
    username = request.session.get("username")

    if role not in ["admin", "superadmin"]:
        raise HTTPException(status_code=403, detail="You are not allowed to upload files.")

    object_key = f"{folder.strip('/')}/{file.filename}" if folder else file.filename

    try:
        s3.upload_fileobj(file.file, R2_BUCKET, object_key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload to R2 failed: {e}")

    # Ghi log vào Postgres
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO documents (filename, filepath, uploaded_by, upload_time)
                VALUES (:filename, :filepath, :uploaded_by, :upload_time)
            """),
            {
                "filename": file.filename,
                "filepath": object_key,  # Lưu object_key thay vì path local
                "uploaded_by": username,
                "upload_time": datetime.utcnow()
            }
        )

    return RedirectResponse(url="/", status_code=302)


# 📥 Download file từ R2 (redirect thẳng link public .r2.dev)
@router.get("/download/{filename}")
def download_file(filename: str):
    # Trả về link public R2
    file_url = f"{R2_ENDPOINT}/{filename}"
    return {"status": "success", "url": file_url}
