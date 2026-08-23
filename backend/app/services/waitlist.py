from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import status
from app.models.waitlist import WaitlistEntry, WaitlistStatus
from app.repositories.waitlist import waitlist_repository
from app.repositories.event import event_repository, event_pricing_repository
from app.core.exceptions import AppException

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

waitlist_service = WaitlistService()
