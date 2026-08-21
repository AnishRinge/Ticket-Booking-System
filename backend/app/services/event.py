from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import status
from datetime import datetime

from app.models.event import Event
from app.repositories.event import event_repository, event_pricing_repository
from app.repositories.venue import venue_repository, seat_category_repository
from app.schemas.event import EventCreate, EventUpdate
from app.core.exceptions import AppException

class EventService:
    def create_event(self, db: Session, event_in: EventCreate, organiser_id: int) -> Event:
        # Validate venue exists
        venue = venue_repository.get(db, id=event_in.venue_id)
        if not venue:
            raise AppException(
                status_code=status.HTTP_404_NOT_FOUND,
                message=f"Venue with id {event_in.venue_id} not found."
            )
        
        # Validate start time is in future
        if event_in.start_time <= datetime.now():
             raise AppException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Event start time must be in the future."
            )

        # Create event
        event_data = event_in.model_dump(exclude={"category_pricings"})
        event_data["organiser_id"] = organiser_id
        event = event_repository.create(db, obj_in=event_data)

        # Create pricings
        for pricing_in in event_in.category_pricings:
            # Validate category exists
            category = seat_category_repository.get(db, id=pricing_in.category_id)
            if not category:
                raise AppException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message=f"Seat category with id {pricing_in.category_id} not found."
                )
            
            # Validate category is relevant to the venue
            # Check if there are any seats in this venue with this category
            has_seats = any(seat.category_id == pricing_in.category_id for seat in venue.seats)
            if not has_seats:
                 raise AppException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message=f"Category {pricing_in.category_id} is not valid for venue {event_in.venue_id}."
                )

            # Check for duplicate pricing
            existing_pricing = event_pricing_repository.get_by_event_and_category(
                db, event_id=event.id, category_id=pricing_in.category_id
            )
            if existing_pricing:
                 raise AppException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message=f"Pricing for category {pricing_in.category_id} already exists for this event."
                )

            pricing_data = pricing_in.model_dump()
            pricing_data["event_id"] = event.id
            event_pricing_repository.create(db, obj_in=pricing_data)
        
        db.refresh(event)
        return event

    def get_event(self, db: Session, event_id: int) -> Event:
        event = event_repository.get(db, id=event_id)
        if not event:
            raise AppException(
                status_code=status.HTTP_404_NOT_FOUND,
                message=f"Event with id {event_id} not found."
            )
        return event

    def list_events(
        self,
        db: Session,
        title: Optional[str] = None,
        venue_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Event]:
        return event_repository.search_events(
            db, title=title, venue_id=venue_id, skip=skip, limit=limit
        )

    def update_event(
        self, db: Session, event_id: int, event_in: EventUpdate, organiser_id: int
    ) -> Event:
        event = self.get_event(db, event_id)
        
        # Check ownership
        if event.organiser_id != organiser_id:
            raise AppException(
                status_code=status.HTTP_403_FORBIDDEN,
                message="You do not have permission to update this event."
            )

        if event_in.venue_id:
            venue = venue_repository.get(db, id=event_in.venue_id)
            if not venue:
                raise AppException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message=f"Venue with id {event_in.venue_id} not found."
                )

        if event_in.start_time and event_in.start_time <= datetime.now():
             raise AppException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Event start time must be in the future."
            )

        # Update event basic info
        update_data = event_in.model_dump(exclude={"category_pricings"}, exclude_unset=True)
        event = event_repository.update(db, db_obj=event, obj_in=update_data)

        # Update pricings if provided
        if event_in.category_pricings is not None:
            for pricing_in in event_in.category_pricings:
                category = seat_category_repository.get(db, id=pricing_in.category_id)
                if not category:
                     raise AppException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        message=f"Seat category with id {pricing_in.category_id} not found."
                    )
                
                # Validate category is relevant to the venue
                venue = venue_repository.get(db, id=event.venue_id)
                has_seats = any(seat.category_id == pricing_in.category_id for seat in venue.seats)
                if not has_seats:
                    raise AppException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        message=f"Category {pricing_in.category_id} is not valid for the event's venue."
                    )

                existing_pricing = event_pricing_repository.get_by_event_and_category(
                    db, event_id=event.id, category_id=pricing_in.category_id
                )
                if existing_pricing:
                    event_pricing_repository.update(
                        db, db_obj=existing_pricing, obj_in=pricing_in.model_dump()
                    )
                else:
                    pricing_data = pricing_in.model_dump()
                    pricing_data["event_id"] = event.id
                    event_pricing_repository.create(db, obj_in=pricing_data)

        db.refresh(event)
        return event

    def delete_event(self, db: Session, event_id: int, organiser_id: int) -> Event:
        event = self.get_event(db, event_id)
        
        # Check ownership
        if event.organiser_id != organiser_id:
            raise AppException(
                status_code=status.HTTP_403_FORBIDDEN,
                message="You do not have permission to delete this event."
            )

        if event.bookings:
             raise AppException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Cannot delete event with existing bookings."
            )

        return event_repository.remove(db, id=event_id)

event_service = EventService()
