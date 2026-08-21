from typing import Optional
from pydantic import Field
from .base import BaseSchema, TimestampSchema

class SeatBase(BaseSchema):
    category_id: int
    row_identifier: str = Field(..., min_length=1)
    seat_number: int = Field(..., gt=0)
    x_pos: Optional[int] = None
    y_pos: Optional[int] = None

class SeatCreate(SeatBase):
    pass

class SeatUpdate(BaseSchema):
    category_id: Optional[int] = None
    row_identifier: Optional[str] = None
    seat_number: Optional[int] = None
    x_pos: Optional[int] = None
    y_pos: Optional[int] = None

class SeatResponse(SeatBase, TimestampSchema):
    id: int
    venue_id: int

class SeatWithCategoryResponse(SeatResponse):
    category: Optional["SeatCategoryResponse"] = None

from .venue import SeatCategoryResponse
