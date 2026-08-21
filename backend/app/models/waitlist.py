import enum
from sqlalchemy import Column, Integer, String, ForeignKey, Enum, DateTime
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin

class WaitlistStatus(str, enum.Enum):
    PENDING = "PENDING"
    OFFERED = "OFFERED"
    ACCEPTED = "ACCEPTED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"

class OfferStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    ACCEPTED = "ACCEPTED"
    EXPIRED = "EXPIRED"
    DECLINED = "DECLINED"

class WaitlistEntry(Base, TimestampMixin):
    __tablename__ = "waitlist_entries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("seat_categories.id"), nullable=False, index=True)
    status = Column(Enum(WaitlistStatus), default=WaitlistStatus.PENDING, nullable=False, index=True)

    user = relationship("User")
    event = relationship("Event")
    category = relationship("SeatCategory")
    offers = relationship("WaitlistOffer", back_populates="waitlist_entry")

class WaitlistOffer(Base, TimestampMixin):
    __tablename__ = "waitlist_offers"

    id = Column(Integer, primary_key=True, index=True)
    waitlist_entry_id = Column(Integer, ForeignKey("waitlist_entries.id"), nullable=False, index=True)
    show_seat_id = Column(Integer, ForeignKey("show_seats.id"), nullable=False, index=True)
    status = Column(Enum(OfferStatus), default=OfferStatus.ACTIVE, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)

    waitlist_entry = relationship("WaitlistEntry", back_populates="offers")
    show_seat = relationship("ShowSeat")
