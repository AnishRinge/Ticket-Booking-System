from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import status
from app.models.venue import Venue, SeatCategory
from app.repositories.venue import venue_repository, seat_category_repository
from app.schemas.venue import VenueCreate, VenueUpdate, SeatCategoryCreate, SeatCategoryUpdate
from app.core.exceptions import AppException

class VenueService:
    def create_venue(self, db: Session, venue_in: VenueCreate) -> Venue:
        return venue_repository.create(db, obj_in=venue_in.model_dump())

    def get_venue(self, db: Session, venue_id: int) -> Venue:
        venue = venue_repository.get(db, id=venue_id)
        if not venue:
            raise AppException(
                status_code=status.HTTP_404_NOT_FOUND,
                message=f"Venue with id {venue_id} not found."
            )
        return venue

    def list_venues(self, db: Session, skip: int = 0, limit: int = 100) -> List[Venue]:
        return venue_repository.get_multi(db, skip=skip, limit=limit)

    def update_venue(self, db: Session, venue_id: int, venue_in: VenueUpdate) -> Venue:
        venue = self.get_venue(db, venue_id)
        return venue_repository.update(db, db_obj=venue, obj_in=venue_in)

    def delete_venue(self, db: Session, venue_id: int) -> Venue:
        venue = self.get_venue(db, venue_id)
        # Check if venue has events before deletion
        if venue.events:
            raise AppException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Cannot delete venue with active events."
            )
        return venue_repository.remove(db, id=venue_id)

    # Seat Category methods
    def create_category(self, db: Session, category_in: SeatCategoryCreate) -> SeatCategory:
        if seat_category_repository.get_by_name(db, name=category_in.name):
             raise AppException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=f"Category '{category_in.name}' already exists."
            )
        return seat_category_repository.create(db, obj_in=category_in.model_dump())

    def list_categories(self, db: Session) -> List[SeatCategory]:
        return seat_category_repository.get_multi(db)
    
    def get_category(self, db: Session, category_id: int) -> SeatCategory:
        category = seat_category_repository.get(db, id=category_id)
        if not category:
            raise AppException(
                status_code=status.HTTP_404_NOT_FOUND,
                message=f"Seat category with id {category_id} not found."
            )
        return category

venue_service = VenueService()
