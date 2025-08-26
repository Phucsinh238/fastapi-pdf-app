# app/auth.py
from jose import JWTError, jwt
from datetime import datetime, timedelta
from fastapi import HTTPException, Depends, Request
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from typing import Optional
import os

SECRET_KEY = "your-secret-key"  # nên để trong biến môi trường
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

class TokenData(BaseModel):
    username: Optional[str] = None

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta if expires_delta else timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
