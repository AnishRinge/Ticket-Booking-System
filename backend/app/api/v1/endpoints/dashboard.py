from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api import deps
from app.db.deps import get_db
from app.models.user import User, UserRole
from app.schemas.dashboard import OrganiserDashboard, AdminDashboard
from app.schemas.base import ResponseSchema
from app.services.dashboard import dashboard_service

router = APIRouter()

@router.get("/organiser", response_model=ResponseSchema[OrganiserDashboard])
def get_organiser_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_organiser)
):
    """
    Get organiser dashboard summary.
    """
    data = dashboard_service.get_organiser_dashboard(db, organiser_id=current_user.id)
    return ResponseSchema(
        message="Organiser dashboard retrieved successfully",
        data=data
    )

@router.get("/admin", response_model=ResponseSchema[AdminDashboard])
def get_admin_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.RoleChecker([UserRole.ADMIN]))
):
    """
    Get admin dashboard summary.
    """
    data = dashboard_service.get_admin_dashboard(db)
    return ResponseSchema(
        message="Admin dashboard retrieved successfully",
        data=data
    )
