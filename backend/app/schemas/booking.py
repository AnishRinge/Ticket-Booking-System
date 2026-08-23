from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from app.models.booking import BookingStatus
from app.schemas.event import EventResponse
from app.schemas.inventory import ShowSeatResponse

class BookingSeatBase(BaseModel):
    show_seat_id: int
    price_at_booking: float

class BookingSeatCreate(BookingSeatBase):
    pass

class BookingSeatRead(BookingSeatBase):
    id: int
    booking_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class BookingBase(BaseModel):
    event_id: int

class BookingCreate(BaseModel):
    show_seat_ids: List[int]

class BookingRead(BookingBase):
    id: int
    booking_reference: str
    user_id: int
    status: BookingStatus
    total_price: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class BookingDetail(BookingRead):
    event: EventResponse
    booking_seats: List[BookingSeatRead]

class BookingList(BaseModel):
    total: int
    items: List[BookingRead]
