from typing import Optional, List
from .base import BaseSchema, TimestampSchema
from .seat import SeatWithCategoryResponse
from app.models.inventory import SeatStatus

from datetime import datetime

class ShowSeatBase(BaseSchema):
    event_id: int
    physical_seat_id: int
    status: SeatStatus
    held_by_id: Optional[int] = None
    hold_expires_at: Optional[datetime] = None

class ShowSeatResponse(ShowSeatBase, TimestampSchema):
    id: int
    physical_seat: Optional[SeatWithCategoryResponse] = None

class SeatMapResponse(BaseSchema):
    event_id: int
    seats: List[ShowSeatResponse]
