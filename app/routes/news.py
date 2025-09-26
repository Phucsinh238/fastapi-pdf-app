from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from app.services.news_service import get_news, get_news_detail
from fastapi.templating import Jinja2Templates

from fastapi import Depends, Form, UploadFile, File
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime
import shutil, os
from math import ceil
from app.database import get_db
from app.models import News

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
UPLOAD_DIR = "static/agri/news/"

@router.get("/admin/news/new")
def new_news_form(request: Request):
    # Kiểm tra quyền admin
    if request.session.get("role") not in ["admin", "superadmin"]:
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse("news_form.html", {"request": request})

@router.post("/admin/news/new")
def create_news(
    request: Request,
    db: Session = Depends(get_db),
    title: str = Form(...),
    summary: str = Form(...),
    content: str = Form(...),
    image: UploadFile = File(None)
):
    if request.session.get("role") not in ["admin", "superadmin"]:
        return RedirectResponse("/", status_code=303)

    # Xử lý upload ảnh
    image_url = None
    if image:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        file_path = os.path.join(UPLOAD_DIR, image.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        image_url = "/" + file_path  # để load qua static

    # Lưu vào DB
    new_item = News(
        title=title,
        summary=summary,
        content=content,
        image_url=image_url,
        created_at=datetime.now()
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)

    return RedirectResponse("/", status_code=303)



@router.get("/news/{news_id}", response_class=HTMLResponse)
def news_detail(request: Request, news_id: int):
    news_item = get_news_detail(news_id)
    if not news_item:
        raise HTTPException(status_code=404, detail="News not found")

    return templates.TemplateResponse("news_detail.html", {
        "request": request,
        "news": news_item
    })



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



@router.get("/admin/news/edit/{news_id}")
def edit_news_form(news_id: int, request: Request, db: Session = Depends(get_db)):
    if request.session.get("role") not in ["admin", "superadmin"]:
        return RedirectResponse("/", status_code=303)

    news = db.query(News).filter(News.id == news_id).first()
    if not news:
        return RedirectResponse("/admin/news", status_code=303)

    return templates.TemplateResponse("news_edit.html", {"request": request, "news": news})


@router.post("/admin/news/edit/{news_id}")
def update_news(
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

    # Nếu có upload ảnh mới thì thay
    if image and image.filename:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        file_path = os.path.join(UPLOAD_DIR, image.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        news.image_url = "/" + file_path

    db.commit()
    return RedirectResponse("/admin/news", status_code=303)


@router.get("/admin/news/delete/{news_id}")
def delete_news(news_id: int, request: Request, db: Session = Depends(get_db)):
    if request.session.get("role") not in ["admin", "superadmin"]:
        return RedirectResponse("/", status_code=303)

    news = db.query(News).filter(News.id == news_id).first()
    if news:
        db.delete(news)
        db.commit()

    return RedirectResponse("/admin/news", status_code=303)
