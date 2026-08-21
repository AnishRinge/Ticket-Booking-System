from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.venue import Venue, SeatCategory
from app.repositories.base import BaseRepository

class VenueRepository(BaseRepository[Venue]):
    pass

class SeatCategoryRepository(BaseRepository[SeatCategory]):
    def get_by_name(self, db: Session, *, name: str) -> Optional[SeatCategory]:
        return db.query(self.model).filter(self.model.name == name).first()

venue_repository = VenueRepository(Venue)
seat_category_repository = SeatCategoryRepository(SeatCategory)
