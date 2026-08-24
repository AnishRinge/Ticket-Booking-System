from typing import Any, List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import RoleChecker
from app.db.deps import get_db
from app.models.user import User, UserRole
from app.schemas.auth import UserResponse
from app.schemas.base import ResponseSchema

router = APIRouter()
admin_only = RoleChecker([UserRole.ADMIN])


@router.get("", response_model=ResponseSchema[List[UserResponse]])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(admin_only),
) -> Any:
    users = db.query(User).order_by(User.id).all()
    return ResponseSchema(message="Users retrieved.", data=users)