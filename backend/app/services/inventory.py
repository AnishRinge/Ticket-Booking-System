from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import status

from app.models.inventory import ShowSeat, SeatStatus
from app.repositories.inventory import show_seat_repository
from app.repositories.event import event_repository
from app.core.exceptions import AppException

from app.models.user import UserRole, User

class InventoryService:
    def initialize_inventory(self, db: Session, event_id: int, current_user: User) -> List[ShowSeat]:
        # Validate event exists
        event = event_repository.get(db, id=event_id)
        if not event:
            raise AppException(
                status_code=status.HTTP_404_NOT_FOUND,
                message=f"Event with id {event_id} not found."
            )
        
        # Check ownership: Organiser must own it, or must be ADMIN
        if current_user.role != UserRole.ADMIN and event.organiser_id != current_user.id:
            raise AppException(
                status_code=status.HTTP_403_FORBIDDEN,
                message="You do not have permission to initialize inventory for this event."
            )

        # Get venue and seats
        venue = event.venue
        if not venue.seats:
             raise AppException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Cannot initialize inventory for a venue with no physical seats."
            )

        # Check if already initialized
        existing_seats = show_seat_repository.get_by_event(db, event_id=event_id)
        if existing_seats:
            # Idempotency: Return existing inventory
            return existing_seats

        # Prepare bulk insert
        show_seats_to_create = []
        for physical_seat in venue.seats:
            show_seats_to_create.append({
                "event_id": event_id,
                "physical_seat_id": physical_seat.id,
                "status": SeatStatus.AVAILABLE
            })
        
        # Bulk create commits internally in our repository implementation
        show_seat_repository.bulk_create(db, obj_list=show_seats_to_create)
        
        return show_seat_repository.get_by_event(db, event_id=event_id)

    def get_seat_map(self, db: Session, event_id: int) -> List[ShowSeat]:
        # Validate event exists
        event = event_repository.get(db, id=event_id)
        if not event:
            raise AppException(
                status_code=status.HTTP_404_NOT_FOUND,
                message=f"Event with id {event_id} not found."
            )
        
        return show_seat_repository.get_by_event(db, event_id=event_id)

inventory_service = InventoryService()
