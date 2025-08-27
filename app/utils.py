import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import sqlite3
from itsdangerous import URLSafeTimedSerializer
from pdf2image import convert_from_path
import os

def send_email(to_email: str, subject: str, body: str):
    sender = "noreply@example.com"
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to_email

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login("muabanchotang@gmail.com", "your_test_password")
        server.send_message(msg)

def log_access(username: str, filename: str):
    conn = sqlite3.connect("app/document.db")
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS access_log (user TEXT, file TEXT, timestamp TEXT)")
    cur.execute("INSERT INTO access_log (user, file, timestamp) VALUES (?, ?, ?)", 
                (username, filename, datetime.now().isoformat()))
    conn.commit()
    conn.close()



# Khóa bí mật dùng để mã hóa token xác thực email
SECRET_KEY = "matkhaunayratladai@"
SALT = "email-confirm-salt"

def generate_confirmation_token(email: str) -> str:
    """
    Tạo token từ địa chỉ email để gửi trong link xác thực
    """
    serializer = URLSafeTimedSerializer(SECRET_KEY)
    return serializer.dumps(email, salt=SALT)

def confirm_token(token: str, expiration: int = 3600) -> str | None:
    """
    Xác minh token và trả lại email nếu token hợp lệ và chưa hết hạn
    """
    serializer = URLSafeTimedSerializer(SECRET_KEY)
    try:
        email = serializer.loads(token, salt=SALT, max_age=expiration)
    except Exception:
        return None
    return email


def convert_pdf_first_page(file_path: str, output_path: str):
    print(f"file_path and output_path: {file_path} {output_path}")
    try:
        poppler_path = "/usr/bin"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        images = convert_from_path(
            file_path,
            dpi=200,
            first_page=1,
            last_page=1,
            poppler_path=poppler_path
        )
        if images:
            images[0].save(output_path, "PNG")
            return output_path  # -> static/previews/<file_id>.png
        else:
            return None
    except Exception as e:
        print(f"[X] Error converting PDF: {e}")
        return None

