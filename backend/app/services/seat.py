from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import status
from app.models.venue import Seat
from app.repositories.seat import seat_repository
from app.services.venue import venue_service
from app.schemas.seat import SeatCreate, SeatUpdate
from app.core.exceptions import AppException

class SeatService:
    def create_seat(self, db: Session, venue_id: int, seat_in: SeatCreate) -> Seat:
        # Validate venue exists
        venue_service.get_venue(db, venue_id)
        
        # Validate category exists
        venue_service.get_category(db, seat_in.category_id)
        
        # Check for duplicate seat in same venue
        if seat_repository.get_by_identity(
            db, 
            venue_id=venue_id, 
            row_identifier=seat_in.row_identifier, 
            seat_number=seat_in.seat_number
        ):
             raise AppException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=f"Seat {seat_in.row_identifier}{seat_in.seat_number} already exists in this venue."
            )
        
        obj_in = seat_in.model_dump()
        obj_in["venue_id"] = venue_id
        return seat_repository.create(db, obj_in=obj_in)

    def get_seat(self, db: Session, seat_id: int) -> Seat:
        seat = seat_repository.get(db, id=seat_id)
        if not seat:
            raise AppException(
                status_code=status.HTTP_404_NOT_FOUND,
                message=f"Seat with id {seat_id} not found."
            )
        return seat

    def list_venue_seats(self, db: Session, venue_id: int, skip: int = 0, limit: int = 100) -> List[Seat]:
        venue_service.get_venue(db, venue_id)
        return seat_repository.get_by_venue(db, venue_id=venue_id, skip=skip, limit=limit)

    def update_seat(self, db: Session, seat_id: int, seat_in: SeatUpdate) -> Seat:
        seat = self.get_seat(db, seat_id)
        
        if seat_in.category_id:
            venue_service.get_category(db, seat_in.category_id)
            
        # If identity is changing, check for duplicates
        if (seat_in.row_identifier and seat_in.row_identifier != seat.row_identifier) or \
           (seat_in.seat_number and seat_in.seat_number != seat.seat_number):
            
            row = seat_in.row_identifier or seat.row_identifier
            num = seat_in.seat_number or seat.seat_number
            
            if seat_repository.get_by_identity(db, venue_id=seat.venue_id, row_identifier=row, seat_number=num):
                 raise AppException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message=f"Seat {row}{num} already exists in this venue."
                )

        return seat_repository.update(db, db_obj=seat, obj_in=seat_in)

    def delete_seat(self, db: Session, seat_id: int) -> Seat:
        seat = self.get_seat(db, seat_id)
        # Check if seat is referenced in show inventory
        if seat.show_seats:
             raise AppException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Cannot delete seat referenced in show inventory."
            )
        return seat_repository.remove(db, id=seat_id)

seat_service = SeatService()
