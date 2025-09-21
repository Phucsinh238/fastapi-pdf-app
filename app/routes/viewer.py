from fastapi import APIRouter, Request, Query, Depends, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import os, math, io, boto3
from sqlalchemy import text
from app.database import engine  # đã config PostgreSQL trong database.py
from app.routes.auth import get_current_user
from ..utils import convert_pdf_first_page

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

ITEMS_PER_PAGE = 10  # số tài liệu mỗi trang

# ==============================
# 🔧 Config Cloudflare R2
# ==============================
R2_ACCESS_KEY = "24bcd7f68391b74c3712d0919b6a0c66"
R2_SECRET_KEY = "8eb34c1864c1e90ec42f67d0217aa2e3e7fac5225dd8b32e52b3575536ac6f4b"
R2_BUCKET = "fastapi-pdf-app"
R2_ENDPOINT = "https://bcdb766b6e3d7d90bf451671a1d7c3de.r2.cloudflarestorage.com"

s3 = boto3.client(
    "s3",
    endpoint_url=R2_ENDPOINT,
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY,
)


# 🏠 Trang chủ
@router.get("/", response_class=HTMLResponse)
def home(request: Request, page: int = Query(1, ge=1)):
    with engine.connect() as conn:
        total_docs = conn.execute(text("SELECT COUNT(*) FROM documents")).scalar() or 0

        total_pages = math.ceil(total_docs / ITEMS_PER_PAGE) if total_docs else 1
        offset = (page - 1) * ITEMS_PER_PAGE

        result = conn.execute(
            text("""
                SELECT id, filename, filepath, upload_time
                FROM documents
                ORDER BY upload_time DESC
                LIMIT :limit OFFSET :offset
            """),
            {"limit": ITEMS_PER_PAGE, "offset": offset}
        )
        documents = result.mappings().all()

    return templates.TemplateResponse("index.html", {
        "request": request,
        "documents": documents,
        "page": page,
        "total_pages": total_pages
    })


# 📄 Xem file (PDF hoặc preview)
@router.get("/view/{file_id}", response_class=HTMLResponse)
def view_file(
    request: Request,
    file_id: int,
    current_user: dict = Depends(get_current_user)
):
    is_admin = current_user.get("role") in ["admin", "superadmin"]

    document = get_document_by_id(file_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if document["filename"].lower().endswith(".pdf"):
        if is_admin:
            # Trả link download trực tiếp từ API
            return templates.TemplateResponse("file_viewer.html", {
                "request": request,
                "file": document,
                "download_url": f"/download/{file_id}",
                "is_admin": True
            })
        else:
            # Tải file tạm từ R2 để convert preview
            tmp_path = f"/tmp/{document['filename']}"
            s3.download_file(R2_BUCKET, document["filename"], tmp_path)

            preview_dir = os.path.join("static", "previews")
            os.makedirs(preview_dir, exist_ok=True)

            output_image_path = os.path.join(preview_dir, f"{file_id}.png")
            convert_pdf_first_page(tmp_path, output_image_path)

            image_url = f"/static/previews/{file_id}.png"
            price = float(document.get("price") or 19.99)
            return templates.TemplateResponse("file_viewer.html", {
                "request": request,
                "file": document,
                "preview_image": image_url,
                "is_admin": False,
                "price": price
            })


# 📥 Download file từ R2
@router.get("/download/{file_id}")
def download_file(file_id: int):
    document = get_document_by_id(file_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    file_obj = io.BytesIO()
    s3.download_fileobj(R2_BUCKET, document["filename"], file_obj)
    file_obj.seek(0)

    return StreamingResponse(
        file_obj,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={document['filename']}"}
    )


# 📂 List tất cả file trong bucket (debug)
@router.get("/r2/list")
def list_r2_files():
    try:
        resp = s3.list_objects_v2(Bucket=R2_BUCKET)
        files = [obj["Key"] for obj in resp.get("Contents", [])]
        return {"status": "success", "files": files}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# 🔎 Hàm lấy document theo ID (Postgres)
def get_document_by_id(doc_id: int):
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT id, filename, filepath, upload_time FROM documents WHERE id = :id"),
            {"id": doc_id}
        ).mappings().first()
    return dict(row) if row else None
