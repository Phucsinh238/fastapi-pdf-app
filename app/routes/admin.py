from fastapi import APIRouter, Request, UploadFile, Form, HTTPException
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
import boto3, os
from sqlalchemy import text
from app.database import engine
from datetime import datetime

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# ==============================
# 🔧 Config Cloudflare R2
# ==============================
R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID", "bcdb766b6e3d7d90bf451671a1d7c3de")
R2_ACCESS_KEY = os.getenv("R2_ACCESS_KEY", "24bcd7f68391b74c3712d0919b6a0c66")
R2_SECRET_KEY = os.getenv("R2_SECRET_KEY", "8eb34c1864c1e90ec42f67d0217aa2e3e7fac5225dd8b32e52b3575536ac6f4b")
R2_BUCKET = os.getenv("R2_BUCKET", "fastapi-pdf-app")

R2_ENDPOINT = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

s3 = boto3.client(
    "s3",
    endpoint_url=R2_ENDPOINT,
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


# 📤 Upload file → Cloudflare R2 + Postgres
@router.post("/upload")
async def upload_file(request: Request, file: UploadFile, folder: str = Form("")):
    role = request.session.get("role")
    username = request.session.get("username")

    if role not in ["admin", "superadmin"]:
        raise HTTPException(status_code=403, detail="You are not allowed to upload files.")

    # Đường dẫn "ảo" trong bucket
    key = os.path.join(folder.strip("/\\"), file.filename)

    # Upload trực tiếp lên R2
    try:
        s3.upload_fileobj(file.file, R2_BUCKET, key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload to R2 failed: {str(e)}")

    # Ghi log vào database Postgres
    r2_url = f"{R2_ENDPOINT}/{R2_BUCKET}/{key}"  # URL API nội bộ
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO documents (filename, filepath, uploaded_by, upload_time)
                VALUES (:filename, :filepath, :uploaded_by, :upload_time)
            """),
            {
                "filename": file.filename,
                "filepath": r2_url,
                "uploaded_by": username,
                "upload_time": datetime.utcnow()
            }
        )

    return RedirectResponse(url="/", status_code=302)
