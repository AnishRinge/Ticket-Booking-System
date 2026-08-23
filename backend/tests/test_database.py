import pytest
from app.models import Base  # imports all models

def test_user_creation(db_session):
    db = db_session
    from app.models import User, UserRole
    user = User(
        email="test@example.com",
        hashed_password="hashed_password",
        full_name="Test User",
        role=UserRole.CUSTOMER
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    assert user.id is not None
    assert user.email == "test@example.com"

def test_venue_and_seats(db_session):
    db = db_session
    from app.models import Venue, SeatCategory, Seat
    venue = Venue(name="Test Venue", address="123 Test St")
    db.add(venue)
    db.flush()
    
    category = SeatCategory(name="VIP", description="Very Important People")
    db.add(category)
    db.flush()
    
    seat = Seat(
        venue_id=venue.id,
        category_id=category.id,
        row_identifier="A",
        seat_number=1
    )
    db.add(seat)
    db.commit()
    
    assert len(venue.seats) == 1
    assert venue.seats[0].row_identifier == "A"

def test_show_seat_unique_constraint(db_session):
    db = db_session
    from sqlalchemy.exc import IntegrityError
    from app.models import User, UserRole, Venue, SeatCategory, Seat, Event, ShowSeat
    
    user = User(email="org@example.com", hashed_password="pw", full_name="Org", role=UserRole.ORGANISER)
    venue = Venue(name="V", address="A")
    category = SeatCategory(name="C")
    db.add_all([user, venue, category])
    db.flush()
    
    seat = Seat(venue_id=venue.id, category_id=category.id, row_identifier="A", seat_number=1)
    db.add(seat)
    db.flush()
    
    import datetime
    event = Event(
        title="Event",
        venue_id=venue.id,
        organiser_id=user.id,
        start_time=datetime.datetime.utcnow()
    )
    db.add(event)
    db.flush()
    
    ss1 = ShowSeat(event_id=event.id, physical_seat_id=seat.id)
    db.add(ss1)
    db.flush()
    
    ss2 = ShowSeat(event_id=event.id, physical_seat_id=seat.id)
    db.add(ss2)
    with pytest.raises(IntegrityError):
        db.commit()
