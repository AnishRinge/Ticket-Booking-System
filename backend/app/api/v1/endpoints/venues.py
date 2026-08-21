from typing import List, Any
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.db.deps import get_db
from app.api.deps import RoleChecker
from app.models.user import UserRole
from app.schemas.venue import VenueCreate, VenueUpdate, VenueResponse, SeatCategoryCreate, SeatCategoryResponse
from app.schemas.seat import SeatCreate, SeatUpdate, SeatResponse
from app.services.venue import venue_service
from app.services.seat import seat_service
from app.schemas.base import ResponseSchema

router = APIRouter()

# Admin-only authorization for write operations
admin_only = RoleChecker([UserRole.ADMIN])

# Seat Category Endpoints (Admin Only) - PLACE ABOVE DYNAMIC VENUE ROUTES
@router.post("/categories", response_model=ResponseSchema[SeatCategoryResponse], status_code=status.HTTP_201_CREATED, dependencies=[Depends(admin_only)])
def create_category(*, db: Session = Depends(get_db), category_in: SeatCategoryCreate) -> Any:
    category = venue_service.create_category(db, category_in=category_in)
    return ResponseSchema(message="Category created.", data=category, status_code=status.HTTP_201_CREATED)

@router.get("/categories", response_model=ResponseSchema[List[SeatCategoryResponse]])
def list_categories(db: Session = Depends(get_db)) -> Any:
    categories = venue_service.list_categories(db)
    return ResponseSchema(message="Categories retrieved.", data=categories)

# Venue Endpoints
@router.post("", response_model=ResponseSchema[VenueResponse], status_code=status.HTTP_201_CREATED, dependencies=[Depends(admin_only)])
def create_venue(*, db: Session = Depends(get_db), venue_in: VenueCreate) -> Any:
    venue = venue_service.create_venue(db, venue_in=venue_in)
    return ResponseSchema(message="Venue created.", data=venue, status_code=status.HTTP_201_CREATED)

@router.get("", response_model=ResponseSchema[List[VenueResponse]])
def list_venues(db: Session = Depends(get_db), skip: int = 0, limit: int = 100) -> Any:
    venues = venue_service.list_venues(db, skip=skip, limit=limit)
    return ResponseSchema(message="Venues retrieved.", data=venues)

@router.get("/{venue_id}", response_model=ResponseSchema[VenueResponse])
def get_venue(venue_id: int, db: Session = Depends(get_db)) -> Any:
    venue = venue_service.get_venue(db, venue_id=venue_id)
    return ResponseSchema(message="Venue retrieved.", data=venue)

@router.patch("/{venue_id}", response_model=ResponseSchema[VenueResponse], dependencies=[Depends(admin_only)])
def update_venue(venue_id: int, venue_in: VenueUpdate, db: Session = Depends(get_db)) -> Any:
    venue = venue_service.update_venue(db, venue_id=venue_id, venue_in=venue_in)
    return ResponseSchema(message="Venue updated.", data=venue)

@router.delete("/{venue_id}", response_model=ResponseSchema[VenueResponse], dependencies=[Depends(admin_only)])
def delete_venue(venue_id: int, db: Session = Depends(get_db)) -> Any:
    venue = venue_service.delete_venue(db, venue_id=venue_id)
    return ResponseSchema(message="Venue deleted.", data=venue)

# Seat Management Endpoints
@router.post("/{venue_id}/seats", response_model=ResponseSchema[SeatResponse], status_code=status.HTTP_201_CREATED, dependencies=[Depends(admin_only)])
def create_seat(venue_id: int, seat_in: SeatCreate, db: Session = Depends(get_db)) -> Any:
    seat = seat_service.create_seat(db, venue_id=venue_id, seat_in=seat_in)
    return ResponseSchema(message="Seat created.", data=seat, status_code=status.HTTP_201_CREATED)

@router.get("/{venue_id}/seats", response_model=ResponseSchema[List[SeatResponse]])
def list_venue_seats(venue_id: int, db: Session = Depends(get_db), skip: int = 0, limit: int = 100) -> Any:
    seats = seat_service.list_venue_seats(db, venue_id=venue_id, skip=skip, limit=limit)
    return ResponseSchema(message="Seats retrieved.", data=seats)

@router.get("/seats/{seat_id}", response_model=ResponseSchema[SeatResponse])
def get_seat(seat_id: int, db: Session = Depends(get_db)) -> Any:
    seat = seat_service.get_seat(db, seat_id=seat_id)
    return ResponseSchema(message="Seat retrieved.", data=seat)

@router.patch("/seats/{seat_id}", response_model=ResponseSchema[SeatResponse], dependencies=[Depends(admin_only)])
def update_seat(seat_id: int, seat_in: SeatUpdate, db: Session = Depends(get_db)) -> Any:
    seat = seat_service.update_seat(db, seat_id=seat_id, seat_in=seat_in)
    return ResponseSchema(message="Seat updated.", data=seat)

@router.delete("/seats/{seat_id}", response_model=ResponseSchema[SeatResponse], dependencies=[Depends(admin_only)])
def delete_seat(seat_id: int, db: Session = Depends(get_db)) -> Any:
    seat = seat_service.delete_seat(db, seat_id=seat_id)
    return ResponseSchema(message="Seat deleted.", data=seat)
