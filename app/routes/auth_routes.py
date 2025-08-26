# app/routes/auth_routes.py

from fastapi import APIRouter, Request, Depends, HTTPException, Response, status, Form
from fastapi.responses import RedirectResponse
from app.auth import create_access_token
from app.models import get_user_by_username

auth_router = APIRouter()

@auth_router.post("/login")
async def login(response: Response, username: str = Form(...), password: str = Form(...)):
    user = get_user_by_username(username)
    if not user or user.password != password:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(data={"sub": user.username})
    response = RedirectResponse(url="/dashboard", status_code=302)
    response.set_cookie(key="access_token", value=access_token, httponly=True)
    return response
