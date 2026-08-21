from datetime import datetime
from sqlalchemy import Column, DateTime
from sqlalchemy.orm import DeclarativeBase, declared_attr

class Base(DeclarativeBase):
    pass

class TimestampMixin:
    @declared_attr
    def created_at(cls):
        return Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    @declared_attr
    def updated_at(cls):
        return Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
