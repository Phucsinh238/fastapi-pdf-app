
from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
import sqlite3
import hashlib

from app.utils import generate_confirmation_token, confirm_token

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

from datetime import datetime

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# Cấu hình SMTP (Gmail SMTP example)
conf = ConnectionConfig(
    MAIL_USERNAME="muabanchotang@gmail.com",
    MAIL_PASSWORD="ggmx httr gcvq eiac",
    MAIL_FROM="muabanchotang@gmail.com",
    MAIL_PORT=587,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_STARTTLS = True,         # ✅ thay MAIL_TLS
    MAIL_SSL_TLS  = False,        # ✅ thay MAIL_SSL
    USE_CREDENTIALS=True
)



@router.get("/register", response_class=HTMLResponse)
async def register_form(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@router.post("/register")
async def register(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...)
):
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    conn = sqlite3.connect("app/document.db")
    cur = conn.cursor()

    try:
        cur.execute("INSERT INTO users (username, email, password, active, role) VALUES (?, ?, ?, ?, ?)",(username, email, hashed_password, 0, "user"))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": "Username or Email already exists."
        })

    conn.close()

    # Gửi email xác thực
    token = generate_confirmation_token(email)
    verify_url = f"http://localhost:8000/verify?token={token}"
    html = f"""
    <p>Hello {username},</p>
    <p>Click to activate your account:</p>
    <a href="{verify_url}">{verify_url}</a>
    """

    message = MessageSchema(
        subject="Email Verification",
        recipients=[email],
        body=html,
        subtype="html"
    )

    fm = FastMail(conf)
    await fm.send_message(message)

    return templates.TemplateResponse("message.html", {
        "request": request,
        "message": "✅ Registration successful! Please check your email to verify your account."
    })


@router.get("/verify", response_class=HTMLResponse)
async def verify_email(request: Request, token: str):
    email = confirm_token(token)
    if not email:
        return HTMLResponse("<h3>❌ Invalid or expired token.</h3>", status_code=400)

    conn = sqlite3.connect("app/document.db")
    cur = conn.cursor()
    cur.execute("UPDATE users SET active = 1 WHERE email = ?", (email,))
    conn.commit()
    conn.close()

    return HTMLResponse("<h3>✅ Email verified! You can now <a href='/login'>login</a>.</h3>")

@router.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    hashed = hashlib.sha256(password.encode()).hexdigest()
    conn = sqlite3.connect("app/document.db")
    cur = conn.cursor()
    cur.execute("SELECT username, password, active, role FROM users WHERE username = ?", (username,))
    user = cur.fetchone()
    conn.close()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if user[1] != hashed:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if user[2] != 1:
        raise HTTPException(status_code=403, detail="Account not activated")

    request.session["user"] = user[0]
    request.session["role"] = user[3]
    return RedirectResponse(url="/", status_code=302)







@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=302)



# app/routes/auth.py

"""

def get_current_user(token: str = Depends(oauth2_scheme)):
    # Tạm thời chấp nhận mọi token, hoặc kiểm tra token ở đây
    if token != "secret-token":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    return {"username": "nickynguyen", "role": "admin"}  # Hoặc user bình thường
"""

def get_current_user(request: Request):
    username = request.session.get("user")
    role = request.session.get("role")

    if not username or not role:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return {"username": username, "role": role}
