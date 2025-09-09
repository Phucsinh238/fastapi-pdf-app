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
import os

# Lấy DATABASE_URL từ biến môi trường Render
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://documentpostgres_user:xpbIpp3sUXtc28jv64nmSVPDrdZgaoXW@dpg-d303nn3e5dus73emb86g-a:5432/documentpostgres")

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



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
