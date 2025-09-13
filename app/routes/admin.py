from fastapi import APIRouter, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
import shutil, os
import openpyxl
from sqlalchemy import text
from app.database import engine
from datetime import datetime

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

UPLOAD_DIR = "app/uploads"
UPLOAD_FOLDER = "app/uploads"


# 🗑️ Xóa file theo tên (admin)
@router.get("/admin/delete/{filename}")
def delete_file(filename: str):
    file_path = f"{UPLOAD_DIR}/{filename}"
    if os.path.exists(file_path):
        os.remove(file_path)
    return RedirectResponse(url="/", status_code=303)


# 📤 Xuất log ra Excel
@router.get("/admin/export-log")
def export_log():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT username, file, timestamp FROM access_log"))
        rows = result.fetchall()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Access Log"
    ws.append(["Username", "File", "Timestamp"])

    for row in rows:
        ws.append(list(row))

    export_path = "app/static/access_log.xlsx"
    wb.save(export_path)

    return FileResponse(
        export_path,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        filename="access_log.xlsx"
    )


# 🗑️ Xóa file theo ID (admin/superadmin)
@router.get("/delete/{file_id}")
def delete_file(file_id: int, request: Request):
    role = request.session.get("role")

    if role not in ["admin", "superadmin"]:
        raise HTTPException(status_code=403, detail="You are not allowed to delete files.")

    with engine.begin() as conn:
        result = conn.execute(
            text("SELECT filepath FROM documents WHERE id = :id"),
            {"id": file_id}
        )
        row = result.fetchone()
        if row:
            file_path = row[0]
            try:
                os.remove(file_path)
            except FileNotFoundError:
                pass
        conn.execute(text("DELETE FROM documents WHERE id = :id"), {"id": file_id})

    return RedirectResponse(url="/", status_code=302)


# 📤 Form upload
@router.get("/upload")
def upload_form(request: Request):
    role = request.session.get("role")
    if role not in ["admin", "superadmin"]:
        raise HTTPException(status_code=403, detail="Only admins can upload files.")
    
    return templates.TemplateResponse("upload.html", {"request": request})


# 📤 Upload file (ghi vào Postgres)
@router.post("/upload")
async def upload_file(request: Request, file: UploadFile, folder: str = Form("")):
    role = request.session.get("role")
    username = request.session.get("username")

    if role not in ["admin", "superadmin"]:
        raise HTTPException(status_code=403, detail="You are not allowed to upload files.")

    # Tạo thư mục upload
    save_dir = os.path.join(UPLOAD_FOLDER, folder.replace("..", "").strip("/\\"))
    os.makedirs(save_dir, exist_ok=True)

    # Lưu file vật lý
    file_path = os.path.join(save_dir, file.filename)
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Ghi log vào database Postgres
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO documents (filename, filepath, uploaded_by, upload_time)
                VALUES (:filename, :filepath, :uploaded_by, :upload_time)
            """),
            {
                "filename": file.filename,
                "filepath": file_path,
                "uploaded_by": username,
                "upload_time": datetime.utcnow()
            }
        )

    return RedirectResponse(url="/", status_code=302)
