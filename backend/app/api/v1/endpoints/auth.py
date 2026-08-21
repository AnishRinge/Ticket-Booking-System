from typing import Any
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.db.deps import get_db
from app.schemas.auth import UserCreate, UserResponse, Token, LoginRequest
from app.services.auth import auth_service
from app.core.security import create_access_token
from app.schemas.base import ResponseSchema

router = APIRouter()

@router.post("/register", response_model=ResponseSchema[UserResponse], status_code=status.HTTP_201_CREATED)
def register(
    *,
    db: Session = Depends(get_db),
    user_in: UserCreate
) -> Any:
    """
    Register a new user.
    """
    user = auth_service.register_user(db, user_in=user_in)
    return ResponseSchema(
        message="User registered successfully.",
        data=user,
        status_code=status.HTTP_201_CREATED
    )

@router.post("/login", response_model=ResponseSchema[Token])
def login(
    *,
    db: Session = Depends(get_db),
    login_data: LoginRequest
) -> Any:
    """
    Get access token for login.
    """
    user = auth_service.authenticate(db, login_data=login_data)
    access_token = create_access_token(subject=user.id)
    return ResponseSchema(
        message="Login successful.",
        data=Token(access_token=access_token),
        status_code=status.HTTP_200_OK
    )
