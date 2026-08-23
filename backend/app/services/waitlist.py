from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from fastapi import status
from app.models.waitlist import WaitlistEntry, WaitlistStatus, WaitlistOffer, OfferStatus
from app.models.inventory import ShowSeat, SeatStatus
from app.repositories.waitlist import waitlist_repository, waitlist_offer_repository
from app.repositories.event import event_repository, event_pricing_repository
from app.core.exceptions import AppException
from app.core.config import settings

class WaitlistService:
    def join_waitlist(
        self, db: Session, *, user_id: int, event_id: int, category_id: int
    ) -> WaitlistEntry:
        # 1. Event exists
        event = event_repository.get(db, id=event_id)
        if not event:
            raise AppException(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Event not found"
            )

        # 2 & 3. Seat category exists and belongs to the event's venue
        pricing = event_pricing_repository.get_by_event_and_category(
            db, event_id=event_id, category_id=category_id
        )
        if not pricing:
            raise AppException(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Seat category not found for this event"
            )

        # 4. Duplicate prevention (active entries)
        existing = waitlist_repository.get_active_entry(
            db, user_id=user_id, event_id=event_id, category_id=category_id
        )
        if existing:
            raise AppException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="You are already on the waitlist for this event and category"
            )

        # Create waitlist entry
        return waitlist_repository.create(
            db,
            obj_in={
                "user_id": user_id,
                "event_id": event_id,
                "category_id": category_id,
                "status": WaitlistStatus.PENDING
            }
        )

    def leave_waitlist(self, db: Session, *, user_id: int, waitlist_id: int) -> WaitlistEntry:
        entry = waitlist_repository.get(db, id=waitlist_id)
        if not entry:
            raise AppException(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Waitlist entry not found"
            )

        # Enforce ownership
        if entry.user_id != user_id:
            raise AppException(
                status_code=status.HTTP_403_FORBIDDEN,
                message="You can only remove your own waitlist entries"
            )

        if entry.status not in [WaitlistStatus.PENDING, WaitlistStatus.OFFERED]:
            raise AppException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=f"Cannot leave waitlist with status {entry.status}"
            )

        return waitlist_repository.update(
            db,
            db_obj=entry,
            obj_in={"status": WaitlistStatus.CANCELLED}
        )

    def get_fifo_waitlist(
        self, db: Session, *, event_id: int, category_id: int, limit: int = 10
    ) -> List[WaitlistEntry]:
        return waitlist_repository.get_fifo_waitlist(
            db, event_id=event_id, category_id=category_id, limit=limit
        )

    def process_waitlist_for_seat(self, db: Session, *, show_seat_id: int) -> Optional[WaitlistOffer]:
        """
        Allocates an available seat to the first eligible waitlisted customer.
        """
        # 1. Lock the relevant ShowSeat
        show_seat = (
            db.query(ShowSeat)
            .filter(ShowSeat.id == show_seat_id)
            .with_for_update()
            .first()
        )

        if not show_seat:
            return None

        # 2. Verify that the ShowSeat is actually available for allocation.
        # Do not allocate BOOKED or HELD inventory.
        if show_seat.status != SeatStatus.AVAILABLE:
            return None

        # 9. The same ShowSeat cannot simultaneously receive another active offer.
        existing_offer = waitlist_offer_repository.get_active_offer_for_seat(db, show_seat_id=show_seat_id)
        if existing_offer:
            return None

        # 3. Determine its event.
        event_id = show_seat.event_id
        
        # 4. Determine its physical seat category.
        category_id = show_seat.physical_seat.category_id

        # 5. Retrieve the first eligible active WaitlistEntry
        fifo_entries = self.get_fifo_waitlist(db, event_id=event_id, category_id=category_id, limit=1)
        if not fifo_entries:
            return None
        
        waitlist_entry = fifo_entries[0]

        # 6. Create a WaitlistOffer for that customer.
        # 8. Set the offer's server-controlled expiration timestamp.
        expires_at = datetime.now() + timedelta(seconds=settings.WAITLIST_OFFER_TTL_SECONDS)
        
        offer = waitlist_offer_repository.create(
            db,
            obj_in={
                "waitlist_entry_id": waitlist_entry.id,
                "show_seat_id": show_seat_id,
                "status": OfferStatus.ACTIVE,
                "expires_at": expires_at
            }
        )

        # Update WaitlistEntry status to OFFERED
        waitlist_repository.update(
            db,
            db_obj=waitlist_entry,
            obj_in={"status": WaitlistStatus.OFFERED}
        )

        db.commit()
        db.refresh(offer)
        return offer

waitlist_service = WaitlistService()
