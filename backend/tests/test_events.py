import pytest
from datetime import datetime, timedelta
from app.models import User, UserRole
from app.models.venue import Venue, SeatCategory
from app.models.event import Event
from app.core.security import get_password_hash, create_access_token

def get_token_for_role(db, role: UserRole, email: str = "test@example.com"):
    user = User(
        email=email,
        hashed_password=get_password_hash("password123"),
        full_name="Test User",
        role=role
    )
    db.add(user)
    db.commit()
    token = create_access_token(subject=user.id)
    user_id = user.id
    return token, user_id

def create_venue_and_category(db):
    v = Venue(name="V1", address="A1")
    c = SeatCategory(name="Premium")
    db.add_all([v, c])
    db.commit()
    v_id, c_id = v.id, c.id
    
    # Add a seat to make category valid for venue
    from app.models.venue import Seat
    s = Seat(venue_id=v_id, category_id=c_id, row_identifier="A", seat_number=1)
    db.add(s)
    db.commit()
    
    return v_id, c_id

def test_organiser_create_event(client, db_session):
    token, _ = get_token_for_role(db_session, UserRole.ORGANISER)
    v_id, c_id = create_venue_and_category(db_session)
    
    headers = {"Authorization": f"Bearer {token}"}
    start_time = (datetime.now() + timedelta(days=1)).isoformat()
    payload = {
        "title": "Movie Night",
        "description": "A fun movie night",
        "venue_id": v_id,
        "start_time": start_time,
        "category_pricings": [
            {"category_id": c_id, "price": 500.0}
        ]
    }
    
    response = client.post("/api/v1/events", json=payload, headers=headers)
    assert response.status_code == 201
    assert response.json()["data"]["title"] == "Movie Night"
    assert len(response.json()["data"]["category_pricings"]) == 1

def test_customer_cannot_create_event(client, db_session):
    token, _ = get_token_for_role(db_session, UserRole.CUSTOMER)
    v_id, c_id = create_venue_and_category(db_session)
    
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "title": "Movie Night",
        "venue_id": v_id,
        "start_time": (datetime.now() + timedelta(days=1)).isoformat(),
        "category_pricings": []
    }
    
    response = client.post("/api/v1/events", json=payload, headers=headers)
    assert response.status_code == 403

def test_create_event_invalid_venue(client, db_session):
    token, _ = get_token_for_role(db_session, UserRole.ORGANISER)
    headers = {"Authorization": f"Bearer {token}"}
    
    payload = {
        "title": "Movie Night",
        "venue_id": 999,
        "start_time": (datetime.now() + timedelta(days=1)).isoformat(),
        "category_pricings": []
    }
    
    response = client.post("/api/v1/events", json=payload, headers=headers)
    assert response.status_code == 404
    assert "not found" in response.json()["message"]

def test_create_event_past_time(client, db_session):
    token, _ = get_token_for_role(db_session, UserRole.ORGANISER)
    v_id, c_id = create_venue_and_category(db_session)
    headers = {"Authorization": f"Bearer {token}"}
    
    payload = {
        "title": "Movie Night",
        "venue_id": v_id,
        "start_time": (datetime.now() - timedelta(days=1)).isoformat(),
        "category_pricings": []
    }
    
    response = client.post("/api/v1/events", json=payload, headers=headers)
    assert response.status_code == 400
    assert "future" in response.json()["message"]

def test_list_events(client, db_session):
    db = db_session
    v_id, c_id = create_venue_and_category(db)
    e1 = Event(title="Event 1", venue_id=v_id, organiser_id=1, start_time=datetime.now() + timedelta(days=1))
    e2 = Event(title="Movie 2", venue_id=v_id, organiser_id=1, start_time=datetime.now() + timedelta(days=2))
    db.add_all([e1, e2])
    db.commit()
    
    # List all
    response = client.get("/api/v1/events")
    assert response.status_code == 200
    assert len(response.json()["data"]) == 2
    
    # Filter by title
    response = client.get("/api/v1/events?title=Movie")
    assert response.status_code == 200
    assert len(response.json()["data"]) == 1
    assert response.json()["data"][0]["title"] == "Movie 2"

def test_update_event_ownership(client, db_session):
    db = db_session
    token1, user1_id = get_token_for_role(db, UserRole.ORGANISER, "o1@example.com")
    token2, user2_id = get_token_for_role(db, UserRole.ORGANISER, "o2@example.com")
    v_id, c_id = create_venue_and_category(db)
    
    e = Event(title="Original Title", venue_id=v_id, organiser_id=user1_id, start_time=datetime.now() + timedelta(days=1))
    db.add(e)
    db.commit()
    e_id = e.id
    
    # Owner updates
    headers1 = {"Authorization": f"Bearer {token1}"}
    response = client.patch(f"/api/v1/events/{e_id}", json={"title": "Updated Title"}, headers=headers1)
    assert response.status_code == 200
    assert response.json()["data"]["title"] == "Updated Title"
    
    # Non-owner updates
    headers2 = {"Authorization": f"Bearer {token2}"}
    response = client.patch(f"/api/v1/events/{e_id}", json={"title": "Evil Update"}, headers=headers2)
    assert response.status_code == 403

def test_delete_event_ownership(client, db_session):
    db = db_session
    token1, user1_id = get_token_for_role(db, UserRole.ORGANISER, "o1@example.com")
    token2, user2_id = get_token_for_role(db, UserRole.ORGANISER, "o2@example.com")
    v_id, c_id = create_venue_and_category(db)
    
    e = Event(title="To be deleted", venue_id=v_id, organiser_id=user1_id, start_time=datetime.now() + timedelta(days=1))
    db.add(e)
    db.commit()
    e_id = e.id
    
    # Non-owner deletes
    headers2 = {"Authorization": f"Bearer {token2}"}
    response = client.delete(f"/api/v1/events/{e_id}", headers=headers2)
    assert response.status_code == 403
    
    # Owner deletes
    headers1 = {"Authorization": f"Bearer {token1}"}
    response = client.delete(f"/api/v1/events/{e_id}", headers=headers1)
    assert response.status_code == 200

def test_delete_event_with_bookings_blocked(client, db_session):
    db = db_session
    from app.models.venue import Seat
    from app.models.event import EventCategoryPricing
    from app.models.inventory import ShowSeat, SeatStatus
    from app.models.booking import Booking, BookingSeat, BookingStatus

    token1, user1_id = get_token_for_role(db, UserRole.ORGANISER, "o1@example.com")
    v_id, c_id = create_venue_and_category(db)

    e = Event(title="Has bookings", venue_id=v_id, organiser_id=user1_id, start_time=datetime.now() + timedelta(days=1))
    db.add(e)
    db.commit()

    s = Seat(venue_id=v_id, category_id=c_id, row_identifier="B", seat_number=1)
    db.add(s)
    db.commit()

    ss = ShowSeat(event_id=e.id, physical_seat_id=s.id, status=SeatStatus.BOOKED)
    db.add(ss)
    db.commit()

    booking = Booking(user_id=user1_id, event_id=e.id, status=BookingStatus.CONFIRMED, total_price=500)
    db.add(booking)
    db.commit()

    bs = BookingSeat(booking_id=booking.id, show_seat_id=ss.id, price_at_booking=500)
    db.add(bs)
    db.commit()

    headers1 = {"Authorization": f"Bearer {token1}"}
    response = client.delete(f"/api/v1/events/{e.id}", headers=headers1)
    assert response.status_code == 400
    assert "bookings" in response.json()["message"].lower()

def test_delete_event_with_waitlist_entry_blocked(client, db_session):
    db = db_session
    from app.models.waitlist import WaitlistEntry, WaitlistStatus

    token1, user1_id = get_token_for_role(db, UserRole.ORGANISER, "o1@example.com")
    token2, user2_id = get_token_for_role(db, UserRole.CUSTOMER, "c1@example.com")
    v_id, c_id = create_venue_and_category(db)

    e = Event(title="Has waitlist", venue_id=v_id, organiser_id=user1_id, start_time=datetime.now() + timedelta(days=1))
    db.add(e)
    db.commit()

    entry = WaitlistEntry(user_id=user2_id, event_id=e.id, category_id=c_id, status=WaitlistStatus.PENDING)
    db.add(entry)
    db.commit()

    headers1 = {"Authorization": f"Bearer {token1}"}
    response = client.delete(f"/api/v1/events/{e.id}", headers=headers1)
    assert response.status_code == 400
    assert "waitlist" in response.json()["message"].lower()

    # Event must still exist
    assert db.query(Event).filter(Event.id == e.id).first() is not None

def test_delete_event_with_waitlist_offer_blocked(client, db_session):
    db = db_session
    from app.models.venue import Seat
    from app.models.inventory import ShowSeat, SeatStatus
    from app.models.waitlist import WaitlistEntry, WaitlistOffer, WaitlistStatus, OfferStatus

    token1, user1_id = get_token_for_role(db, UserRole.ORGANISER, "o1@example.com")
    _, user2_id = get_token_for_role(db, UserRole.CUSTOMER, "c1@example.com")
    v_id, c_id = create_venue_and_category(db)

    e = Event(title="Has waitlist offer", venue_id=v_id, organiser_id=user1_id, start_time=datetime.now() + timedelta(days=1))
    db.add(e)
    db.commit()

    s = Seat(venue_id=v_id, category_id=c_id, row_identifier="C", seat_number=1)
    db.add(s)
    db.commit()

    ss = ShowSeat(event_id=e.id, physical_seat_id=s.id, status=SeatStatus.AVAILABLE)
    db.add(ss)
    db.commit()

    # Entry already resolved (accepted) but the offer record still references the event's seat
    entry = WaitlistEntry(user_id=user2_id, event_id=e.id, category_id=c_id, status=WaitlistStatus.ACCEPTED)
    db.add(entry)
    db.commit()

    offer = WaitlistOffer(
        waitlist_entry_id=entry.id,
        show_seat_id=ss.id,
        status=OfferStatus.EXPIRED,
        expires_at=datetime.now() - timedelta(minutes=5),
    )
    db.add(offer)
    db.commit()

    headers1 = {"Authorization": f"Bearer {token1}"}
    response = client.delete(f"/api/v1/events/{e.id}", headers=headers1)
    assert response.status_code == 400
    assert "waitlist" in response.json()["message"].lower()

def test_delete_event_without_bookings_or_waitlist_succeeds(client, db_session):
    db = db_session
    token1, user1_id = get_token_for_role(db, UserRole.ORGANISER, "o1@example.com")
    v_id, c_id = create_venue_and_category(db)

    e = Event(title="Clean event", venue_id=v_id, organiser_id=user1_id, start_time=datetime.now() + timedelta(days=1))
    db.add(e)
    db.commit()
    e_id = e.id

    headers1 = {"Authorization": f"Bearer {token1}"}
    response = client.delete(f"/api/v1/events/{e_id}", headers=headers1)
    assert response.status_code == 200
    assert db.query(Event).filter(Event.id == e_id).first() is None
