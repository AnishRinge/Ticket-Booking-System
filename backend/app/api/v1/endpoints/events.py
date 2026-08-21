from typing import List, Optional
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session

from app.api import deps
from app.db.deps import get_db
from app.schemas.event import EventCreate, EventUpdate, EventResponse
from app.schemas.inventory import ShowSeatResponse, SeatMapResponse
from app.schemas.base import ResponseSchema
from app.services.event import event_service
from app.services.inventory import inventory_service
from app.models.user import User, UserRole

router = APIRouter()

@router.post("", response_model=ResponseSchema[EventResponse], status_code=status.HTTP_201_CREATED)
def create_event(
    *,
    db: Session = Depends(get_db),
    event_in: EventCreate,
    current_user: User = Depends(deps.get_current_organiser)
):
    """
    Create a new event. Only for ORGANISER.
    """
    event = event_service.create_event(db, event_in=event_in, organiser_id=current_user.id)
    return ResponseSchema(
        message="Event created successfully",
        data=event,
        status_code=status.HTTP_201_CREATED
    )

@router.get("", response_model=ResponseSchema[List[EventResponse]])
def list_events(
    db: Session = Depends(get_db),
    title: Optional[str] = Query(None),
    venue_id: Optional[int] = Query(None),
    skip: int = 0,
    limit: int = 100
):
    """
    List events with optional filtering. Public access.
    """
    events = event_service.list_events(
        db, title=title, venue_id=venue_id, skip=skip, limit=limit
    )
    return ResponseSchema(
        message="Events retrieved successfully",
        data=events
    )

@router.get("/{event_id}", response_model=ResponseSchema[EventResponse])
def get_event(
    event_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a single event by ID. Public access.
    """
    event = event_service.get_event(db, event_id=event_id)
    return ResponseSchema(
        message="Event retrieved successfully",
        data=event
    )

@router.patch("/{event_id}", response_model=ResponseSchema[EventResponse])
def update_event(
    event_id: int,
    event_in: EventUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_organiser)
):
    """
    Update an event. Only for ORGANISER who owns the event.
    """
    event = event_service.update_event(
        db, event_id=event_id, event_in=event_in, organiser_id=current_user.id
    )
    return ResponseSchema(
        message="Event updated successfully",
        data=event
    )

@router.delete("/{event_id}", response_model=ResponseSchema[dict])
def delete_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_organiser)
):
    """
    Delete an event. Only for ORGANISER who owns the event.
    """
    event_service.delete_event(
        db, event_id=event_id, organiser_id=current_user.id
    )
    return ResponseSchema(
        message="Event deleted successfully",
        data={"id": event_id}
    )

# Inventory / Seat Map Endpoints
@router.post("/{event_id}/inventory/initialize", response_model=ResponseSchema[List[ShowSeatResponse]], status_code=status.HTTP_201_CREATED)
def initialize_inventory(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.RoleChecker([UserRole.ORGANISER, UserRole.ADMIN]))
):
    """
    Initialize ShowSeat inventory for an event. Only for ORGANISER who owns the event, or ADMIN.
    """
    inventory = inventory_service.initialize_inventory(db, event_id=event_id, current_user=current_user)
    return ResponseSchema(
        message="Inventory initialized successfully",
        data=inventory,
        status_code=status.HTTP_201_CREATED
    )

@router.get("/{event_id}/seat-map", response_model=ResponseSchema[SeatMapResponse])
def get_seat_map(
    event_id: int,
    db: Session = Depends(get_db)
):
    """
    Retrieve the seat map for an event. Public access.
    """
    inventory = inventory_service.get_seat_map(db, event_id=event_id)
    return ResponseSchema(
        message="Seat map retrieved successfully",
        data=SeatMapResponse(event_id=event_id, seats=inventory)
    )
