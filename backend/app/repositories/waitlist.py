from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.waitlist import WaitlistEntry, WaitlistStatus, WaitlistOffer, OfferStatus
from app.repositories.base import BaseRepository

class WaitlistRepository(BaseRepository[WaitlistEntry]):
    def get_active_entry(
        self, db: Session, *, user_id: int, event_id: int, category_id: int
    ) -> Optional[WaitlistEntry]:
        """Get an active (PENDING or OFFERED) waitlist entry for a user, event, and category."""
        return db.query(self.model).filter(
            and_(
                self.model.user_id == user_id,
                self.model.event_id == event_id,
                self.model.category_id == category_id,
                self.model.status.in_([WaitlistStatus.PENDING, WaitlistStatus.OFFERED])
            )
        ).first()

    def get_fifo_waitlist(
        self, db: Session, *, event_id: int, category_id: int, limit: int = 10
    ) -> List[WaitlistEntry]:
        """Get PENDING waitlist entries in FIFO order."""
        return db.query(self.model).filter(
            and_(
                self.model.event_id == event_id,
                self.model.category_id == category_id,
                self.model.status == WaitlistStatus.PENDING
            )
        ).order_by(
            self.model.created_at.asc(),
            self.model.id.asc()
        ).limit(limit).all()

    def get_user_entries(self, db: Session, *, user_id: int) -> List[WaitlistEntry]:
        """Get all waitlist entries for a user."""
        return db.query(self.model).filter(
            self.model.user_id == user_id
        ).all()

waitlist_repository = WaitlistRepository(WaitlistEntry)

class WaitlistOfferRepository(BaseRepository[WaitlistOffer]):
    def get_active_offer_for_seat(self, db: Session, *, show_seat_id: int) -> Optional[WaitlistOffer]:
        """Get an active offer for a specific show seat."""
        return db.query(self.model).filter(
            and_(
                self.model.show_seat_id == show_seat_id,
                self.model.status == OfferStatus.ACTIVE
            )
        ).first()

    def get_expired_offers(self, db: Session) -> List[WaitlistOffer]:
        """Get all active offers that have expired."""
        return db.query(self.model).filter(
            and_(
                self.model.status == OfferStatus.ACTIVE,
                self.model.expires_at <= datetime.now()
            )
        ).all()

waitlist_offer_repository = WaitlistOfferRepository(WaitlistOffer)
