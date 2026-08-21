from typing import Optional, List
from pydantic import Field
from .base import BaseSchema, TimestampSchema

class SeatCategoryBase(BaseSchema):
    name: str = Field(..., min_length=1)
    description: Optional[str] = None

class SeatCategoryCreate(SeatCategoryBase):
    pass

class SeatCategoryUpdate(BaseSchema):
    name: Optional[str] = None
    description: Optional[str] = None

class SeatCategoryResponse(SeatCategoryBase, TimestampSchema):
    id: int

class VenueBase(BaseSchema):
    name: str = Field(..., min_length=1)
    address: str = Field(..., min_length=1)

class VenueCreate(VenueBase):
    pass

class VenueUpdate(BaseSchema):
    name: Optional[str] = None
    address: Optional[str] = None

class VenueResponse(VenueBase, TimestampSchema):
    id: int
