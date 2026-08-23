from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import update
from fastapi import status

from app.models.inventory import ShowSeat, SeatStatus
from app.models.user import User
from app.repositories.inventory import show_seat_repository
from app.repositories.waitlist import waitlist_offer_repository
from app.core.exceptions import AppException
from app.core.config import settings

class HoldService:
    def create_hold(self, db: Session, show_seat_id: int, user: User) -> ShowSeat:
        # Use SELECT ... FOR UPDATE to acquire a row-level lock.
        # This ensures that only one transaction can examine and update this seat at a time.
        show_seat = (
            db.query(ShowSeat)
            .filter(ShowSeat.id == show_seat_id)
            .with_for_update()
            .first()
        )
        
        if not show_seat:
            raise AppException(
                status_code=status.HTTP_404_NOT_FOUND,
                message=f"ShowSeat with id {show_seat_id} not found."
            )

        now = datetime.now()
        
        # Logic to check if the seat is available or if the existing hold has expired.
        # A seat is claimable if it's AVAILABLE or if it's HELD but the hold has expired.
        is_available = (show_seat.status == SeatStatus.AVAILABLE)
        is_expired = (show_seat.status == SeatStatus.HELD and show_seat.hold_expires_at <= now)
        
        if not (is_available or is_expired):
             # If we can't acquire it, we must roll back to release the lock immediately.
             db.rollback()
             raise AppException(
                status_code=status.HTTP_409_CONFLICT,
                message="Seat is not available for holding."
            )
        
        # Check if there's an active waitlist offer for this seat.
        # If so, it's reserved and cannot be held by anyone else.
        active_offer = waitlist_offer_repository.get_active_offer_for_seat(db, show_seat_id=show_seat_id)
        if active_offer:
            db.rollback()
            raise AppException(
                status_code=status.HTTP_409_CONFLICT,
                message="Seat is reserved for waitlist."
            )

        # Apply the hold state.
        show_seat.status = SeatStatus.HELD
        show_seat.held_by_id = user.id
        show_seat.hold_expires_at = now + timedelta(seconds=settings.SEAT_HOLD_TTL_SECONDS)
        show_seat.updated_at = now
        
        db.add(show_seat)
        db.commit()
        db.refresh(show_seat)
        return show_seat

    def release_hold(self, db: Session, show_seat_id: int, user: User) -> ShowSeat:
        show_seat = show_seat_repository.get(db, id=show_seat_id)
        if not show_seat:
            raise AppException(
                status_code=status.HTTP_404_NOT_FOUND,
                message=f"ShowSeat with id {show_seat_id} not found."
            )
        
        if show_seat.held_by_id != user.id:
            raise AppException(
                status_code=status.HTTP_403_FORBIDDEN,
                message="You do not own this hold."
            )
        
        # If it was already expired/released, we just return it or handle gracefully
        if show_seat.status != SeatStatus.HELD:
             # Already released or booked
             return show_seat

        show_seat.status = SeatStatus.AVAILABLE
        show_seat.held_by_id = None
        show_seat.hold_expires_at = None
        
        db.add(show_seat)
        
        # Integration: Trigger waitlist allocation for released seat
        from app.services.waitlist import waitlist_service
        waitlist_service.process_waitlist_for_seat(db, show_seat_id=show_seat.id, commit=False)
        
        db.commit()
        db.refresh(show_seat)
        return show_seat

    def get_user_holds(self, db: Session, user_id: int) -> List[ShowSeat]:
        return show_seat_repository.get_active_holds_by_user(db, user_id=user_id)

    def cleanup_expired_holds(self, db: Session) -> int:
        expired_seats = show_seat_repository.get_expired_holds(db)
        count = 0
        from app.services.waitlist import waitlist_service
        for seat in expired_seats:
            seat.status = SeatStatus.AVAILABLE
            seat.held_by_id = None
            seat.hold_expires_at = None
            db.add(seat)
            
            # Integration: Trigger waitlist allocation for released seat
            waitlist_service.process_waitlist_for_seat(db, show_seat_id=seat.id, commit=False)
            count += 1
        
        if count > 0:
            db.commit()
        return count

hold_service = HoldService()
