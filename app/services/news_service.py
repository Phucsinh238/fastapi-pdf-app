from sqlalchemy import text
from app.database import engine  # đã config PostgreSQL trong database.py

def get_news(limit: int = 10):
    """Lấy danh sách tin mới nhất"""
    with engine.begin() as conn:
        result = conn.execute(
            text("SELECT * FROM news ORDER BY created_at DESC LIMIT :limit"),
            {"limit": limit}
        )
        return [dict(row) for row in result.mappings().all()]

def get_news_detail(news_id: int):
    """Lấy chi tiết 1 bài tin"""
    with engine.begin() as conn:
        result = conn.execute(
            text("SELECT * FROM news WHERE id = :id"),
            {"id": news_id}
        ).mappings().first()
        return dict(result) if result else None
