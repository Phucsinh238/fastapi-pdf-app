from fastapi import APIRouter, Request, Query, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import os
import math
from sqlalchemy import text
from app.database import engine  # đã config PostgreSQL trong database.py
from app.routes.auth import get_current_user
from ..utils import convert_pdf_first_page

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

ITEMS_PER_PAGE = 10  # số tài liệu mỗi trang


# 🏠 Trang chủ
@router.get("/", response_class=HTMLResponse)
def home(request: Request, page: int = Query(1, ge=1)):
    with engine.connect() as conn:
        # Đếm tổng số tài liệu
        result = conn.execute(text("SELECT COUNT(*) FROM documents"))
        total_docs = result.scalar() or 0

        # Tính offset và total_pages
        total_pages = math.ceil(total_docs / ITEMS_PER_PAGE) if total_docs else 1
        offset = (page - 1) * ITEMS_PER_PAGE

        # Lấy dữ liệu phân trang
        result = conn.execute(
            text("""
                SELECT id, filename, filepath, upload_time
                FROM documents
                ORDER BY upload_time DESC
                LIMIT :limit OFFSET :offset
            """),
            {"limit": ITEMS_PER_PAGE, "offset": offset}
        )
        documents = result.mappings().all()  # trả về list[dict]

    flash = request.session.pop("flash", None)

    return templates.TemplateResponse("index.html", {
        "request": request,
        "documents": documents,
        "page": page,
        "total_pages": total_pages
    })


# 📄 Xem file
@router.get("/view/{file_id}", response_class=HTMLResponse)
def view_file(
    request: Request,
    file_id: int,
    current_user: dict = Depends(get_current_user)
):
    print("👤 Current User:", current_user)

    is_admin = current_user.get("role") in ["admin", "superadmin"]
    print("🔐 Is Admin?", is_admin)

    document = get_document_by_id(file_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if document["filename"].lower().endswith(".pdf"):
        if is_admin:
            full_pdf_url = "/uploads/" + os.path.basename(document["filepath"])
            return templates.TemplateResponse("file_viewer.html", {
                "request": request,
                "file": document,
                "full_pdf": full_pdf_url,
                "is_admin": True
            })
        else:
            preview_dir = os.path.join("static", "previews")
            os.makedirs(preview_dir, exist_ok=True)

            output_image_path = os.path.join(preview_dir, f"{file_id}.png")
            convert_pdf_first_page(document["filepath"], output_image_path)

            image_url = f"/static/previews/{file_id}.png"

            return templates.TemplateResponse("file_viewer.html", {
                "request": request,
                "file": document,
                "preview_image": image_url,
                "is_admin": False
            })


# 🔎 Hàm lấy document theo ID (Postgres)
def get_document_by_id(doc_id: int):
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT id, filename, filepath, upload_time FROM documents WHERE id = :id"),
            {"id": doc_id}
        )
        row = result.mappings().first()

    if row:
        return dict(row)
    return None
