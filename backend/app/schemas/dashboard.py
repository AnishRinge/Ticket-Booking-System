from typing import List, Optional
from pydantic import BaseModel
from .base import ResponseSchema

class EventSummary(BaseModel):
    id: int
    title: str
    bookings_count: int
    revenue: float
    start_time: str
    status: str

class OrganiserDashboard(BaseModel):
    total_events: int
    total_bookings: int
    total_revenue: float
    recent_events: List[EventSummary]

class AdminDashboard(BaseModel):
    total_venues: int
    total_events: int
    total_revenue: float
    total_users: int
    recent_bookings: List[dict] # Simplified for now
