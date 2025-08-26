from fastapi import APIRouter, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
import shutil, os
import openpyxl
from fastapi.responses import FileResponse
import sqlite3
from datetime import datetime

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

UPLOAD_DIR = "app/uploads"


UPLOAD_FOLDER = "app/uploads"



"""
@router.get("/upload")
def upload_form(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})

@router.post("/upload")
def upload_file(file: UploadFile = File(...)):
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    with open(f"{UPLOAD_DIR}/{file.filename}", "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return RedirectResponse(url="/", status_code=303)
"""


@router.get("/admin/delete/{filename}")
def delete_file(filename: str):
    file_path = f"{UPLOAD_DIR}/{filename}"
    if os.path.exists(file_path):
        os.remove(file_path)
    return RedirectResponse(url="/", status_code=303)



@router.get("/admin/export-log")
def export_log():
    conn = sqlite3.connect("app/document.db")
    cur = conn.cursor()
    cur.execute("SELECT user, file, timestamp FROM access_log")
    rows = cur.fetchall()
    conn.close()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Access Log"
    ws.append(["Username", "File", "Timestamp"])

    for row in rows:
        ws.append(row)

    export_path = "app/static/access_log.xlsx"
    wb.save(export_path)
    return FileResponse(export_path, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', filename="access_log.xlsx")


@router.get("/delete/{file_id}")
def delete_file(file_id: int, request: Request):
    role = request.session.get("role")

    if role != "admin" and role != "superadmin":
        raise HTTPException(status_code=403, detail="You are not allowed to delete files.")

    # Nếu quyền hợp lệ, thực hiện xóa
    conn = sqlite3.connect("app/document.db")
    cur = conn.cursor()
    cur.execute("SELECT filepath FROM documents WHERE id=?", (file_id,))
    file = cur.fetchone()
    if file:
        try:
            os.remove(file[0])
        except FileNotFoundError:
            pass
    cur.execute("DELETE FROM documents WHERE id=?", (file_id,))
    conn.commit()
    conn.close()

    return RedirectResponse(url="/", status_code=302)




@router.get("/upload")
def upload_form(request: Request):
    role = request.session.get("role")
    if role not in ["admin", "superadmin"]:
        raise HTTPException(status_code=403, detail="Only admins can upload files.")
    
    return templates.TemplateResponse("upload.html", {"request": request})

@router.post("/upload")
async def upload_file(request: Request, file: UploadFile, folder: str = Form("")):
    role = request.session.get("role")
    username = request.session.get("username")

    if role not in ["admin", "superadmin"]:
        raise HTTPException(status_code=403, detail="You are not allowed to upload files.")

    # Tạo thư mục upload theo cây thư mục
    save_dir = os.path.join(UPLOAD_FOLDER, folder.replace("..", "").strip("/\\"))
    os.makedirs(save_dir, exist_ok=True)

    # Lưu file
    file_path = os.path.join(save_dir, file.filename)
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Ghi vào database
    conn = sqlite3.connect("app/document.db")
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO documents (filename, filepath, uploaded_by)
        VALUES (?, ?, ?)
    """, (file.filename, file_path, username))
    conn.commit()
    conn.close()

    return RedirectResponse(url="/", status_code=302)
