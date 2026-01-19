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
#from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
#from .database import Base
#from sqlalchemy import Text
#from datetime import datetime
#from app.database import Base

from sqlalchemy import Column, Integer, String, Boolean, DateTime, func, ForeignKey, Text
from sqlalchemy.orm import relationship
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

    # Quan hệ với purchases
    purchases = relationship("Purchase", back_populates="user", cascade="all, delete-orphan")


# Bảng documents
class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    filepath = Column(String, nullable=False)
    uploaded_by = Column(String)
    upload_time = Column(DateTime(timezone=True), server_default=func.now())

    # Quan hệ với purchases
    purchases = relationship("Purchase", back_populates="document", cascade="all, delete-orphan")


# Bảng purchases
class Purchase(Base):
    __tablename__ = "purchases"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    purchased_at = Column(DateTime(timezone=True), server_default=func.now())

    # Quan hệ ORM
    user = relationship("User", back_populates="purchases")
    document = relationship("Document", back_populates="purchases")


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


# Bảng news
class News(Base):
    __tablename__ = "news"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(Text, nullable=False)
    summary = Column(Text)
    content = Column(Text)
    image_url = Column(String)
    link = Column(String)  # 🔗 Thêm cột link
    created_at = Column(DateTime, default=datetime.now)
    priority = Column(Integer, default=0)
