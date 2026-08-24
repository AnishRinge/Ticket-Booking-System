from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api import deps
from app.db.deps import get_db
from app.schemas.hold import HoldCreate, HoldResponse, ActiveHoldResponse
from app.schemas.base import ResponseSchema
from app.services.hold import hold_service
from app.models.user import User, UserRole

router = APIRouter()

@router.post("", response_model=ResponseSchema[HoldResponse], status_code=status.HTTP_201_CREATED)
def create_hold(
    hold_in: HoldCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.RoleChecker([UserRole.CUSTOMER]))
):
    """
    Create a seat hold. Only for CUSTOMER users.
    """
    hold = hold_service.create_hold(db, show_seat_id=hold_in.show_seat_id, user=current_user)
    return ResponseSchema(
        message="Seat held successfully",
        data=HoldResponse(show_seat=hold, message="Hold will expire soon"),
        status_code=status.HTTP_201_CREATED
    )

@router.delete("/{show_seat_id}", response_model=ResponseSchema[HoldResponse])
def release_hold(
    show_seat_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    Release a seat hold. Only for the user who owns the hold.
    """
    hold = hold_service.release_hold(db, show_seat_id=show_seat_id, user=current_user)
    return ResponseSchema(
        message="Hold released successfully",
        data=HoldResponse(show_seat=hold, message="Seat is now available")
    )

@router.get("", response_model=ResponseSchema[ActiveHoldResponse])
def get_my_holds(
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    Retrieve active holds for the current user.
    """
    holds = hold_service.get_user_holds(db, user_id=current_user.id)
    return ResponseSchema(
        message="Active holds retrieved successfully",
        data=ActiveHoldResponse(seats=holds)
    )
