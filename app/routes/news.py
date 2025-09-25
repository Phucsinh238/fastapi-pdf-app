from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from app.services.news_service import get_news, get_news_detail
from app.templates import templates

router = APIRouter()

@router.get("/news/{news_id}", response_class=HTMLResponse)
def news_detail(request: Request, news_id: int):
    news_item = get_news_detail(news_id)
    if not news_item:
        raise HTTPException(status_code=404, detail="News not found")

    return templates.TemplateResponse("news_detail.html", {
        "request": request,
        "news": news_item
    })
