from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.booking import Booking, BookingSeat
from app.repositories.base import BaseRepository

class BookingRepository(BaseRepository[Booking]):
    def get_by_user(
        self, db: Session, *, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[Booking]:
        return (
            db.query(self.model)
            .filter(self.model.user_id == user_id)
            .order_by(self.model.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_count_by_user(self, db: Session, *, user_id: int) -> int:
        return db.query(self.model).filter(self.model.user_id == user_id).count()

    def get_with_details(self, db: Session, *, booking_id: int) -> Optional[Booking]:
        return (
            db.query(self.model)
            .filter(self.model.id == booking_id)
            .first()
        )

booking_repository = BookingRepository(Booking)
