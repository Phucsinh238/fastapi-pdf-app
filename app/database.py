# app/database.py
import sqlite3

def get_db():
    conn = sqlite3.connect("app/document.db")
    conn.row_factory = sqlite3.Row  # để truy cập kết quả như dict
    return conn

#from app.database import get_db

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