from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.venue import Seat
from app.repositories.base import BaseRepository

class SeatRepository(BaseRepository[Seat]):
    def get_by_venue(self, db: Session, *, venue_id: int, skip: int = 0, limit: int = 100) -> List[Seat]:
        return db.query(self.model).filter(self.model.venue_id == venue_id).offset(skip).limit(limit).all()

    def get_by_identity(self, db: Session, *, venue_id: int, row_identifier: str, seat_number: int) -> Optional[Seat]:
        return db.query(self.model).filter(
            self.model.venue_id == venue_id,
            self.model.row_identifier == row_identifier,
            self.model.seat_number == seat_number
        ).first()

seat_repository = SeatRepository(Seat)
