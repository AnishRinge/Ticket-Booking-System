from typing import Any, List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api import deps
from app.models.user import User, UserRole
from app.schemas.booking import BookingCreate, BookingRead, BookingDetail, BookingList
from app.services.booking import booking_service

router = APIRouter()

@router.post("/", response_model=BookingRead, status_code=status.HTTP_201_CREATED)
def confirm_booking(
    *,
    db: Session = Depends(deps.get_db),
    booking_in: BookingCreate,
    current_user: User = Depends(deps.RoleChecker([UserRole.CUSTOMER])),
) -> Any:
    """
    Confirm a booking from active holds. Only for CUSTOMER users.
    """
    return booking_service.confirm_booking(
        db=db, show_seat_ids=booking_in.show_seat_ids, user=current_user
    )

@router.get("/", response_model=BookingList)
def get_user_bookings(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Retrieve current user's bookings.
    """
    items, total = booking_service.get_user_bookings(
        db=db, user_id=current_user.id, skip=skip, limit=limit
    )
    return {"total": total, "items": items}

@router.get("/{booking_id}", response_model=BookingDetail)
def get_booking(
    *,
    db: Session = Depends(deps.get_db),
    booking_id: int,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Get booking details.
    """
    return booking_service.get_booking(db=db, booking_id=booking_id, user=current_user)

@router.post("/{booking_id}/cancel", response_model=BookingRead)
def cancel_booking(
    *,
    db: Session = Depends(deps.get_db),
    booking_id: int,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Cancel a booking.
    """
    return booking_service.cancel_booking(db=db, booking_id=booking_id, user=current_user)
