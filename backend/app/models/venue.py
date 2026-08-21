from sqlalchemy import Column, Integer, String, ForeignKey, Float
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin

class Venue(Base, TimestampMixin):
    __tablename__ = "venues"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    address = Column(String, nullable=False)

    seats = relationship("Seat", back_populates="venue", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="venue")

class SeatCategory(Base, TimestampMixin):
    __tablename__ = "seat_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)  # e.g., VIP, Premium, Standard
    description = Column(String)

    seats = relationship("Seat", back_populates="category")

class Seat(Base, TimestampMixin):
    __tablename__ = "seats"

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("seat_categories.id"), nullable=False)
    row_identifier = Column(String, nullable=False)  # e.g., 'A'
    seat_number = Column(Integer, nullable=False)   # e.g., 12
    
    # Optional layout positioning
    x_pos = Column(Integer)
    y_pos = Column(Integer)

    venue = relationship("Venue", back_populates="seats")
    category = relationship("SeatCategory", back_populates="seats")
    show_seats = relationship("ShowSeat", back_populates="physical_seat")
