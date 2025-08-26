from fastapi import APIRouter, Request, Query, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.utils import log_access
from pdf2image import convert_from_path
import os
import sqlite3
import math
from bson import ObjectId
from app.database import get_document_by_id  # Tuỳ bạn tổ chức project

from app.routes.auth import get_current_user

from ..utils import convert_pdf_first_page



router = APIRouter()
templates = Jinja2Templates(directory="app/templates")







ITEMS_PER_PAGE = 5  # Số tài liệu mỗi trang

@router.get("/", response_class=HTMLResponse)
def home(request: Request, page: int = Query(1, ge=1)):
    conn = sqlite3.connect("app/document.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Đếm tổng số tài liệu
    cur.execute("SELECT COUNT(*) FROM documents")
    total_docs = cur.fetchone()[0]

    # Tính offset và total_pages
    total_pages = math.ceil(total_docs / ITEMS_PER_PAGE)
    offset = (page - 1) * ITEMS_PER_PAGE

    # Lấy dữ liệu phân trang
    cur.execute("""
        SELECT * FROM documents
        ORDER BY upload_time DESC
        LIMIT ? OFFSET ?
    """, (ITEMS_PER_PAGE, offset))
    documents = cur.fetchall()
    conn.close()

    flash = request.session.pop("flash", None)

    return templates.TemplateResponse("index.html", {
        "request": request,
        "documents": documents,
        "page": page,
        "total_pages": total_pages
    })



from fastapi import Depends
from app.routes.auth import get_current_user  # giả sử bạn có hàm này để lấy người dùng



@router.get("/view/{file_id}", response_class=HTMLResponse)
def view_file(
    request: Request,
    file_id: int,
    current_user: dict = Depends(get_current_user)
):
    # Kiểm tra thông tin user đang đăng nhập
    print("👤 Current User:", current_user)

    # Kiểm tra role có phải là admin không
    is_admin = current_user.get("role") in ["admin", "superadmin"]
    print("🔐 Is Admin?", is_admin)

    document = get_document_by_id(file_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if document["filename"].lower().endswith(".pdf"):
        if is_admin:
            print("📄 Admin is viewing full PDF.")
            full_pdf_url = "/uploads/" + os.path.basename(document["filepath"])
            return templates.TemplateResponse("file_viewer.html", {
                "request": request,
                "file": document,
                "full_pdf": full_pdf_url,
                "is_admin": True
            })
        else:
            print("👀 User is viewing preview.")
            preview_dir = os.path.join("static", "previews")
            os.makedirs(preview_dir, exist_ok=True)

            output_image_path = os.path.join(preview_dir, f"{file_id}.png")
            convert_pdf_first_page(document["filepath"], output_image_path)

            # ✅ Truyền đường dẫn cho trình duyệt
            image_url = f"/static/previews/{file_id}.png"

            return templates.TemplateResponse("file_viewer.html", {
                "request": request,
                "file": document,
                "preview_image": image_url,
                "is_admin": False
            })


"""

from app.database import get_db

def get_document_by_id(doc_id: int):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
    row = cursor.fetchone()
    if row:
        return {
            "id": row[0],
            "filename": row[1],
            "filepath": row[2],
            "upload_time": row[3],
        }
    return None

    """