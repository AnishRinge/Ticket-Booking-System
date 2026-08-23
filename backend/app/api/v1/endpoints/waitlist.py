from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api import deps
from app.db.deps import get_db
from app.schemas.waitlist import WaitlistEntryResponse
from app.schemas.booking import BookingRead
from app.schemas.base import ResponseSchema
from app.services.waitlist import waitlist_service
from app.models.user import User, UserRole
from app.core.exceptions import AppException

router = APIRouter()

@router.delete("/{waitlist_id}", response_model=ResponseSchema[WaitlistEntryResponse])
def leave_waitlist(
    waitlist_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    Leave a waitlist. Only for CUSTOMER who owns the entry.
    """
    if current_user.role != UserRole.CUSTOMER:
        raise AppException(
            status_code=status.HTTP_403_FORBIDDEN,
            message="Only customers can leave the waitlist"
        )
    
    entry = waitlist_service.leave_waitlist(
        db,
        user_id=current_user.id,
        waitlist_id=waitlist_id
    )
    return ResponseSchema(
        message="Left waitlist successfully",
        data=entry
    )

@router.post("/offers/{offer_id}/accept", response_model=ResponseSchema[BookingRead])
def accept_offer(
    offer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    Accept a waitlist offer. Only for CUSTOMER who owns the offer.
    """
    if current_user.role != UserRole.CUSTOMER:
        raise AppException(
            status_code=status.HTTP_403_FORBIDDEN,
            message="Only customers can accept waitlist offers"
        )
    
    booking = waitlist_service.accept_offer(
        db,
        offer_id=offer_id,
        user_id=current_user.id
    )
    return ResponseSchema(
        message="Offer accepted and booking confirmed",
        data=booking
    )
