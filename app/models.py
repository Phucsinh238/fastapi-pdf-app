from pydantic import BaseModel, EmailStr

class User(BaseModel):
    username: str
    email: EmailStr
    password: str
    is_active: bool = False
    is_admin: bool = False

# Optional: thêm Document model nếu lưu metadata sau này
class Document(BaseModel):
    filename: str
    uploaded_by: str
    upload_date: str
