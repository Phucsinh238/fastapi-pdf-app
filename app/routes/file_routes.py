# app/routes/file_routes.py

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from app.dependencies import get_current_user
from app.models import User

file_router = APIRouter()

@file_router.get("/view-file/{file_id}")
async def view_file(file_id: int, current_user: User = Depends(get_current_user)):
    # Giả sử file ở static/files
    file_path = f"static/files/file_{file_id}.pdf"
    return FileResponse(file_path, media_type="application/pdf")
