import enum
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum, UniqueConstraint
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin

class SeatStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    HELD = "HELD"
    BOOKED = "BOOKED"

class ShowSeat(Base, TimestampMixin):
    __tablename__ = "show_seats"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    physical_seat_id = Column(Integer, ForeignKey("seats.id"), nullable=False, index=True)
    status = Column(Enum(SeatStatus), default=SeatStatus.AVAILABLE, nullable=False, index=True)
    
    # Hold info
    held_by_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    hold_expires_at = Column(DateTime, nullable=True, index=True)

    event = relationship("Event", back_populates="show_seats")
    physical_seat = relationship("Seat", back_populates="show_seats")
    held_by = relationship("User")

    __table_args__ = (
        UniqueConstraint("event_id", "physical_seat_id", name="uq_show_seat_event_physical"),
    )
