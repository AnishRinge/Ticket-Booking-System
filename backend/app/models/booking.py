import enum
import uuid
from sqlalchemy import Column, Integer, String, ForeignKey, Enum, DateTime
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin

class BookingStatus(str, enum.Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"

class Booking(Base, TimestampMixin):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    booking_reference = Column(String, unique=True, index=True, default=lambda: str(uuid.uuid4()), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    status = Column(Enum(BookingStatus), default=BookingStatus.PENDING, nullable=False, index=True)
    total_price = Column(Integer, nullable=False) # In minor units if preferred, using Integer here

    user = relationship("User")
    event = relationship("Event", back_populates="bookings")
    booking_seats = relationship("BookingSeat", back_populates="booking", cascade="all, delete-orphan")

class BookingSeat(Base, TimestampMixin):
    __tablename__ = "booking_seats"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False)
    show_seat_id = Column(Integer, ForeignKey("show_seats.id"), nullable=False)
    price_at_booking = Column(Integer, nullable=False)

    booking = relationship("Booking", back_populates="booking_seats")
    show_seat = relationship("ShowSeat")
