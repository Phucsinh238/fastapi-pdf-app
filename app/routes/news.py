from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi import Depends, Form, UploadFile, File
from sqlalchemy.orm import Session
from datetime import datetime
from math import ceil
import uuid
import boto3
from fastapi.templating import Jinja2Templates
from app.database import get_db
from app.models import News
from app.services.news_service import get_news, get_news_detail

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

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

# ---------------- Proxy ảnh từ R2 ----------------
@router.get("/news/image/{key:path}")
def get_news_image(key: str):
    try:
        obj = s3.get_object(Bucket=R2_BUCKET, Key=key)
        return StreamingResponse(obj["Body"], media_type=obj["ContentType"])
    except Exception:
        raise HTTPException(status_code=404, detail="Image not found")


# ---------------- Admin: Form tạo tin ----------------
@router.get("/admin/news/new")
def new_news_form(request: Request):
    if request.session.get("role") not in ["admin", "superadmin"]:
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse("news_form.html", {"request": request})


@router.post("/admin/news/new")
async def create_news(
    request: Request,
    db: Session = Depends(get_db),
    title: str = Form(...),
    summary: str = Form(...),
    content: str = Form(...),
    link: str = Form(None),             # 🔗 nhận thêm link
    image: UploadFile = File(None)
):
    if request.session.get("role") not in ["admin", "superadmin"]:
        return RedirectResponse("/", status_code=303)

    image_key = None
    if image:
        ext = image.filename.split(".")[-1]
        key = f"news/{uuid.uuid4()}.{ext}"

        # Upload file lên Cloudflare R2
        s3.upload_fileobj(
            image.file,
            R2_BUCKET,
            key,
            ExtraArgs={"ContentType": image.content_type}
        )
        # ❗ chỉ lưu key (không lưu URL)
        image_key = key

    new_item = News(
        title=title,
        summary=summary,
        content=content,
        image_url=image_key,
        link=link,                    # 🔗 lưu link vào DB
        created_at=datetime.now()
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)

    return RedirectResponse("/", status_code=303)


# ---------------- Xem chi tiết tin ----------------
@router.get("/news/{news_id}", response_class=HTMLResponse)
def news_detail(request: Request, news_id: int):
    news_item = get_news_detail(news_id)
    if not news_item:
        raise HTTPException(status_code=404, detail="News not found")

    return templates.TemplateResponse("news_detail.html", {
        "request": request,
        "news": news_item
    })


# ---------------- Danh sách tin trong admin ----------------
@router.get("/admin/news")
def admin_news_list(
    request: Request,
    page: int = 1,
    per_page: int = 10,
    search: str = "",
    db: Session = Depends(get_db)
):
    if request.session.get("role") not in ["admin", "superadmin"]:
        return RedirectResponse("/", status_code=303)

    query = db.query(News)

    if search:
        query = query.filter(News.title.ilike(f"%{search}%"))

    total = query.count()
    pages = ceil(total / per_page)

    news_list = (
        query.order_by(News.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    return templates.TemplateResponse("news_admin_list.html", {
        "request": request,
        "news_list": news_list,
        "page": page,
        "pages": pages,
        "total": total,
        "search": search
    })


# ---------------- Sửa tin ----------------
@router.get("/admin/news/edit/{news_id}")
def edit_news_form(news_id: int, request: Request, db: Session = Depends(get_db)):
    if request.session.get("role") not in ["admin", "superadmin"]:
        return RedirectResponse("/", status_code=303)

    news = db.query(News).filter(News.id == news_id).first()
    if not news:
        return RedirectResponse("/admin/news", status_code=303)

    return templates.TemplateResponse("news_edit.html", {"request": request, "news": news})


@router.post("/admin/news/edit/{news_id}")
async def update_news(
    news_id: int,
    request: Request,
    db: Session = Depends(get_db),
    title: str = Form(...),
    summary: str = Form(...),
    content: str = Form(...),
    image: UploadFile = File(None)
):
    if request.session.get("role") not in ["admin", "superadmin"]:
        return RedirectResponse("/", status_code=303)

    news = db.query(News).filter(News.id == news_id).first()
    if not news:
        return RedirectResponse("/admin/news", status_code=303)

    news.title = title
    news.summary = summary
    news.content = content

    if image and image.filename:
        ext = image.filename.split(".")[-1]
        key = f"news/{uuid.uuid4()}.{ext}"

        s3.upload_fileobj(
            image.file,
            R2_BUCKET,
            key,
            ExtraArgs={"ContentType": image.content_type}
        )
        news.image_url = key   # ❗ chỉ lưu key

    db.commit()
    db.refresh(news)
    return RedirectResponse("/admin/news", status_code=303)

# ---------------- Xoá tin ----------------
@router.get("/admin/news/delete/{news_id}")
def delete_news(news_id: int, request: Request, db: Session = Depends(get_db)):
    if request.session.get("role") not in ["admin", "superadmin"]:
        return RedirectResponse("/", status_code=303)

    news = db.query(News).filter(News.id == news_id).first()
    if news:
        # Nếu có ảnh thì xoá khỏi R2 luôn (không bắt buộc, tuỳ nhu cầu)
        if news.image_url:
            try:
                s3.delete_object(Bucket=R2_BUCKET, Key=news.image_url)
            except Exception:
                pass

        db.delete(news)
        db.commit()

    return RedirectResponse("/admin/news", status_code=303)
