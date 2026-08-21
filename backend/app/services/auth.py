from typing import Optional
from sqlalchemy.orm import Session
from fastapi import status
from app.models.user import User, UserRole
from app.repositories.user import user_repository
from app.schemas.auth import UserCreate, LoginRequest
from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.exceptions import AppException

class AuthService:
    def register_user(self, db: Session, user_in: UserCreate) -> User:
        # Check if user exists
        user = user_repository.get_by_email(db, email=user_in.email)
        if user:
            raise AppException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="A user with this email already exists."
            )
        
        # Prevent manual creation of ADMIN accounts
        if user_in.role == UserRole.ADMIN:
             raise AppException(
                status_code=status.HTTP_403_FORBIDDEN,
                message="Cannot register as an administrator."
            )

        # Create user
        obj_in = {
            "email": user_in.email.lower(),
            "hashed_password": get_password_hash(user_in.password),
            "full_name": user_in.full_name,
            "role": user_in.role
        }
        return user_repository.create(db, obj_in=obj_in)

    def authenticate(self, db: Session, login_data: LoginRequest) -> User:
        user = user_repository.get_by_email(db, email=login_data.email.lower())
        if not user:
             raise AppException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                message="Incorrect email or password."
            )
        if not verify_password(login_data.password, user.hashed_password):
            raise AppException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                message="Incorrect email or password."
            )
        return user

auth_service = AuthService()
