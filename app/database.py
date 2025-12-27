# app/database.py
import sqlite3

#def get_db():
#    conn = sqlite3.connect("app/document.db")
#    conn.row_factory = sqlite3.Row  # để truy cập kết quả như dict
#    return conn

#from app.database import get_db
# app/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
import os

# Lấy DATABASE_URL từ biến môi trường Render
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://neondb_owner:npg_YCA1sk4JfnIF@ep-calm-king-a1bgsh11-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require")

#engine = create_engine(DATABASE_URL)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,   # 🔥 CHECK connection trước khi dùng
    pool_recycle=300,     # 🔥 recycle sau 5 phút
)



SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



def get_document_by_id(file_id: int):
    with engine.begin() as conn:
        result = conn.execute(
            text("""
                SELECT id, filename, filepath, r2_key, uploaded_by, upload_time, price
                FROM documents
                WHERE id = :id
            """),
            {"id": file_id}
        )
        row = result.mappings().first()
        return dict(row) if row else None
