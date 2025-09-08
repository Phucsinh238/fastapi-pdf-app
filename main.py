from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.routes import auth, admin, viewer
from starlette.middleware.sessions import SessionMiddleware
from app.routes import router_pay
from fastapi import Request

app = FastAPI()

@app.middleware("http")
async def add_current_user(request: Request, call_next):
    user = None
    if "user" in request.session:
        user = {
            "username": request.session.get("user"),
            "role": request.session.get("role")
        }
    request.state.current_user = user
    response = await call_next(request)
    return response


# Thêm middleware cho session
"""
 app.add_middleware(SessionMiddleware, secret_key="your-secret-key") 
"""

# Kích hoạt session
app.add_middleware(SessionMiddleware, secret_key="super-secret-session-key")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# app.mount("/static", StaticFiles(directory="app/static"), name="static")


app.mount("/uploads", StaticFiles(directory="app/uploads"), name="uploads")

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(viewer.router)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(router_pay.router)





