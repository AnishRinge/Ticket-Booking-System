from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.inventory import ShowSeat, SeatStatus
from app.repositories.base import BaseRepository

class ShowSeatRepository(BaseRepository[ShowSeat]):
    def get_by_event(self, db: Session, *, event_id: int) -> List[ShowSeat]:
        return db.query(self.model).filter(self.model.event_id == event_id).all()

    def get_by_event_and_seat(
        self, db: Session, *, event_id: int, physical_seat_id: int
    ) -> Optional[ShowSeat]:
        return (
            db.query(self.model)
            .filter(
                self.model.event_id == event_id,
                self.model.physical_seat_id == physical_seat_id
            )
            .first()
        )

    def bulk_create(self, db: Session, *, obj_list: List[dict]) -> None:
        db.bulk_insert_mappings(self.model, obj_list)
        db.commit()

    def get_active_holds_by_user(self, db: Session, *, user_id: int) -> List[ShowSeat]:
        from datetime import datetime
        return (
            db.query(self.model)
            .filter(
                self.model.held_by_id == user_id,
                self.model.status == SeatStatus.HELD,
                self.model.hold_expires_at > datetime.now()
            )
            .all()
        )

    def get_expired_holds(self, db: Session) -> List[ShowSeat]:
        from datetime import datetime
        return (
            db.query(self.model)
            .filter(
                self.model.status == SeatStatus.HELD,
                self.model.hold_expires_at <= datetime.now()
            )
            .all()
        )

show_seat_repository = ShowSeatRepository(ShowSeat)
