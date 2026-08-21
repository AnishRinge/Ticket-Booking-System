from datetime import datetime
from typing import Generic, TypeVar, Optional, List
from pydantic import BaseModel, ConfigDict

T = TypeVar("T")

class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

class TimestampSchema(BaseSchema):
    created_at: datetime
    updated_at: datetime

class ResponseSchema(BaseSchema, Generic[T]):
    message: str
    data: Optional[T] = None
    status_code: int = 200

class ErrorResponse(BaseSchema):
    message: str
    errors: Optional[List[dict] | dict] = None
    status_code: int
