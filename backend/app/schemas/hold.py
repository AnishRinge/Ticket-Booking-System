from datetime import datetime
from typing import Optional, List
from .base import BaseSchema
from .inventory import ShowSeatResponse

class HoldCreate(BaseSchema):
    show_seat_id: int

class HoldResponse(BaseSchema):
    show_seat: ShowSeatResponse
    message: str

class ActiveHoldResponse(BaseSchema):
    seats: List[ShowSeatResponse]
