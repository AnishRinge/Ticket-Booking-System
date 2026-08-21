from pydantic import EmailStr, Field
from app.models.user import UserRole
from .base import BaseSchema

class UserCreate(BaseSchema):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str
    role: UserRole = UserRole.CUSTOMER

class UserResponse(BaseSchema):
    id: int
    email: EmailStr
    full_name: str
    role: UserRole

class UserShortResponse(BaseSchema):
    id: int
    full_name: str

class Token(BaseSchema):
    access_token: str
    token_type: str = "bearer"

class TokenPayload(BaseSchema):
    sub: str | None = None

class LoginRequest(BaseSchema):
    email: EmailStr
    password: str
