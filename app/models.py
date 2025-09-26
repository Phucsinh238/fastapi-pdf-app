#from pydantic import BaseModel, EmailStr

#class User(BaseModel):
#    username: str
#    email: EmailStr
#    password: str
#    is_active: bool = False
#    is_admin: bool = False

# Optional: thêm Document model nếu lưu metadata sau này
#class Document(BaseModel):
#    filename: str
#    uploaded_by: str
#    upload_date: str
# app/models.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
from .database import Base
from sqlalchemy import Text
from datetime import datetime
from app.database import Base


# Bảng users
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    active = Column(Boolean, default=True)
    role = Column(String, default="user")


# Bảng documents
class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    filepath = Column(String, nullable=False)
    uploaded_by = Column(String)
    upload_time = Column(DateTime(timezone=True), server_default=func.now())


# Bảng login_log
class LoginLog(Base):
    __tablename__ = "login_log"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String)
    ip = Column(String)
    user_agent = Column(String)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())


# Bảng access_log
class AccessLog(Base):
    __tablename__ = "access_log"

    id = Column(Integer, primary_key=True, index=True)
    user = Column(String)
    file = Column(String)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())




class News(Base):
    __tablename__ = "news"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(Text, nullable=False)
    summary = Column(Text)
    content = Column(Text)
    image_url = Column(String)
    created_at = Column(DateTime, default=datetime.now)

