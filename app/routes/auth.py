
from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
import sqlite3
import hashlib
from app.database import SessionLocal, get_db
from app.models import User
from app.utils import generate_confirmation_token, confirm_token
from sqlalchemy.orm import Session

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
#from app.database import get_db
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

from datetime import datetime

from sqlalchemy import text
import hashlib

from app.database import engine  # file database.py đã cấu hình SQLAlchemy engine
from app.utils import confirm_token  # hàm confirm_token của bạn
#from app.templates import templates  # Jinja templates loader


router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# Cấu hình SMTP (Gmail SMTP example)
conf = ConnectionConfig(
    MAIL_USERNAME="agrireports999@gmail.com",
    MAIL_PASSWORD="kcsd pcmf xxcu jlsn",
    MAIL_FROM="agrireports999@gmail.com",
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
    db = SessionLocal()
    hashed_password = hashlib.sha256(password.encode()).hexdigest()

    new_user = User(
        username=username,
        email=email,
        password=hashed_password,
        active=False,
        role="user"
    )

    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
    except Exception:
        db.rollback()
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": "Username or Email already exists."
        })
    finally:
        db.close()

    # Gửi email xác thực
    base_url = str(request.base_url).rstrip("/")
    token = generate_confirmation_token(email)
    verify_url = f"{base_url}/verify?token={token}"

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
        "message": "✅ Registration successful! Please check your email to verify your account. If not found, please check mail in Spam mail or junk mail"
    })



# -----------------------------
# Xác thực email
# -----------------------------


@router.get("/verify", response_class=HTMLResponse)
async def verify_email(request: Request, token: str):
    email = confirm_token(token)
    if not email:
        return HTMLResponse("<h3>❌ Invalid or expired token.</h3>", status_code=400)

    try:
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE users SET active = true WHERE email = :email"),
                {"email": email}
            )

        return HTMLResponse("<h3>✅ Email verified! You can now <a href='/login'>login</a>.</h3>")

    except Exception as e:
        # In ra log cho dễ debug
        return HTMLResponse(f"<h3>❌ Error: {str(e)}</h3>", status_code=500)



# -----------------------------
# Form login
# -----------------------------
@router.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


# -----------------------------
# Xử lý login
# -----------------------------
@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    hashed = hashlib.sha256(password.encode()).hexdigest()

    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT id, username, password, active, role FROM users WHERE username = :username"),
            {"username": username}
        ).fetchone()


    if not result:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    db_id, db_username, db_password, db_active, db_role = result

    if db_password != hashed:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if db_active != 1:
        raise HTTPException(status_code=403, detail="Account not activated")

    # ✅ Ghi session đầy đủ
    request.session["user_id"] = db_id         # <--- thêm dòng này
    request.session["user"] = db_username
    request.session["role"] = db_role


    next_url = request.query_params.get("next")
    if next_url:
        return RedirectResponse(url=next_url, status_code=303)

# (Tuỳ chọn) ghi log đăng nhập hoặc cập nhật last_login
    # with engine.connect() as conn:
    #     conn.execute(text("INSERT INTO login_log (username, ip) VALUES (:u, :ip)"),
    #                  {"u": db_username, "ip": request.client.host})

    return RedirectResponse(url="/", status_code=302)





@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=302)



# app/routes/auth.py

# """

#def get_current_user(token: str = Depends(oauth2_scheme)):
    # Tạm thời chấp nhận mọi token, hoặc kiểm tra token ở đây
#    if token != "secret-token":
#        raise HTTPException(
#            status_code=status.HTTP_401_UNAUTHORIZED,
#            detail="Invalid token",
#        )
#    return {"username": "nickynguyen", "role": "admin"}  # Hoặc user bình thường
#"""

#def get_current_user(request: Request):
#    username = request.session.get("user")
#    role = request.session.get("role")

 #   if not username or not role:
 #       raise HTTPException(status_code=401, detail="Not authenticated")

 #   return {"username": username, "role": role}

def get_current_user(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="You must be logged in")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid session user")

    # 🔄 Trả về dict thay vì ORM object
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role
    }
