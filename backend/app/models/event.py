from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Float
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin

class Event(Base, TimestampMixin):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    organiser_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime)

    venue = relationship("Venue", back_populates="events")
    organiser = relationship("User")
    category_pricings = relationship("EventCategoryPricing", back_populates="event", cascade="all, delete-orphan")
    show_seats = relationship("ShowSeat", back_populates="event", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="event")

class EventCategoryPricing(Base, TimestampMixin):
    __tablename__ = "event_category_pricings"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("seat_categories.id"), nullable=False)
    price = Column(Float, nullable=False)

    event = relationship("Event", back_populates="category_pricings")
    category = relationship("SeatCategory")
