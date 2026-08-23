from pydantic import BaseModel, ConfigDict
from datetime import datetime
from app.models.waitlist import WaitlistStatus

class WaitlistEntryBase(BaseModel):
    event_id: int
    category_id: int

class WaitlistEntryCreate(BaseModel):
    category_id: int

class WaitlistEntryResponse(WaitlistEntryBase):
    id: int
    user_id: int
    status: WaitlistStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
