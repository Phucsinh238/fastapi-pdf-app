# app/dependencies.py

from fastapi import Request, HTTPException, Depends
from app.auth import verify_token
from app.models import get_user_by_username

async def get_current_user(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    username = verify_token(token)
    user = get_user_by_username(username)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user
