from datetime import datetime
from typing import Optional, List
from pydantic import Field, field_validator
from .base import BaseSchema, TimestampSchema
from .venue import SeatCategoryResponse, VenueResponse
from .auth import UserShortResponse

class EventCategoryPricingBase(BaseSchema):
    category_id: int
    price: float = Field(..., ge=0)

class EventCategoryPricingCreate(EventCategoryPricingBase):
    pass

class EventCategoryPricingResponse(EventCategoryPricingBase, TimestampSchema):
    id: int
    category: Optional[SeatCategoryResponse] = None

class EventBase(BaseSchema):
    title: str = Field(..., min_length=1)
    description: Optional[str] = None
    venue_id: int
    start_time: datetime
    end_time: Optional[datetime] = None

class EventCreate(EventBase):
    category_pricings: List[EventCategoryPricingCreate]

class EventUpdate(BaseSchema):
    title: Optional[str] = None
    description: Optional[str] = None
    venue_id: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    category_pricings: Optional[List[EventCategoryPricingCreate]] = None

class EventResponse(EventBase, TimestampSchema):
    id: int
    organiser_id: int
    organiser: Optional[UserShortResponse] = None
    category_pricings: List[EventCategoryPricingResponse]
    venue: Optional[VenueResponse] = None

class EventShortResponse(EventBase, TimestampSchema):
    id: int
    organiser_id: int
    organiser: Optional[UserShortResponse] = None
