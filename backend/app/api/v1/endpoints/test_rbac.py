from typing import Any
from fastapi import APIRouter, Depends
from app.api.deps import get_current_user, RoleChecker
from app.models.user import User, UserRole

router = APIRouter()

@router.get("/me", response_model=dict)
def test_authenticated(user: User = Depends(get_current_user)) -> Any:
    return {"message": "You are authenticated", "user": user.email, "role": user.role}

@router.get("/customer-only", dependencies=[Depends(RoleChecker([UserRole.CUSTOMER]))])
def test_customer_only() -> Any:
    return {"message": "Welcome, Customer"}

@router.get("/organiser-only", dependencies=[Depends(RoleChecker([UserRole.ORGANISER]))])
def test_organiser_only() -> Any:
    return {"message": "Welcome, Organiser"}

@router.get("/admin-only", dependencies=[Depends(RoleChecker([UserRole.ADMIN]))])
def test_admin_only() -> Any:
    return {"message": "Welcome, Admin"}

@router.get("/organiser-or-admin", dependencies=[Depends(RoleChecker([UserRole.ORGANISER, UserRole.ADMIN]))])
def test_organiser_or_admin() -> Any:
    return {"message": "Welcome, Organiser or Admin"}
