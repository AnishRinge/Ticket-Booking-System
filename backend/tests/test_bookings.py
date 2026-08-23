import pytest
from datetime import datetime, timedelta
from app.models import User, UserRole
from app.models.venue import Venue, SeatCategory, Seat
from app.models.event import Event, EventCategoryPricing
from app.models.inventory import ShowSeat, SeatStatus
from app.models.booking import Booking, BookingSeat, BookingStatus
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

def setup_booking_context(db, organiser_id):
    v = Venue(name="V1", address="A1")
    c = SeatCategory(name="Standard")
    db.add_all([v, c])
    db.commit()
    
    s1 = Seat(venue_id=v.id, category_id=c.id, row_identifier="A", seat_number=1)
    s2 = Seat(venue_id=v.id, category_id=c.id, row_identifier="A", seat_number=2)
    db.add_all([s1, s2])
    db.commit()
    
    e = Event(title="Movie", venue_id=v.id, organiser_id=organiser_id, start_time=datetime.now() + timedelta(days=1))
    db.add(e)
    db.commit()
    
    p = EventCategoryPricing(event_id=e.id, category_id=c.id, price=500.0)
    db.add(p)
    db.commit()
    
    ss1 = ShowSeat(event_id=e.id, physical_seat_id=s1.id, status=SeatStatus.AVAILABLE)
    ss2 = ShowSeat(event_id=e.id, physical_seat_id=s2.id, status=SeatStatus.AVAILABLE)
    db.add_all([ss1, ss2])
    db.commit()
    
    ss1_id = ss1.id
    ss2_id = ss2.id
    event_id = e.id
    return ss1_id, ss2_id, event_id

def test_confirm_booking_success(client, db_session):
    db = db_session
    token, user_id = get_token_for_role(db, UserRole.CUSTOMER)
    ss1_id, ss2_id, event_id = setup_booking_context(db, 999)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Hold seats
    client.post("/api/v1/holds", json={"show_seat_id": ss1_id}, headers=headers)
    client.post("/api/v1/holds", json={"show_seat_id": ss2_id}, headers=headers)
    
    # 2. Confirm booking
    response = client.post("/api/v1/bookings/", json={"show_seat_ids": [ss1_id, ss2_id]}, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "CONFIRMED"
    assert data["total_price"] == 1000.0
    assert data["user_id"] == user_id
    assert "booking_reference" in data
    
    # 3. Verify ShowSeat state
    ss1 = db.query(ShowSeat).filter(ShowSeat.id == ss1_id).first()
    assert ss1.status == SeatStatus.BOOKED
    assert ss1.held_by_id is None
    
    # 4. Verify BookingSeats
    booking_id = data["id"]
    bs = db.query(BookingSeat).filter(BookingSeat.booking_id == booking_id).all()
    assert len(bs) == 2
    assert bs[0].price_at_booking == 500.0

def test_confirm_booking_invalid_hold_ownership(client, db_session):
    db = db_session
    token1, _ = get_token_for_role(db, UserRole.CUSTOMER, "c1@example.com")
    token2, _ = get_token_for_role(db, UserRole.CUSTOMER, "c2@example.com")
    ss1_id, _, _ = setup_booking_context(db, 999)
    
    headers1 = {"Authorization": f"Bearer {token1}"}
    headers2 = {"Authorization": f"Bearer {token2}"}
    
    # Customer 1 holds seat
    client.post("/api/v1/holds", json={"show_seat_id": ss1_id}, headers=headers1)
    
    # Customer 2 tries to book it
    response = client.post("/api/v1/bookings/", json={"show_seat_ids": [ss1_id]}, headers=headers2)
    assert response.status_code == 403

def test_confirm_booking_expired_hold(client, db_session):
    db = db_session
    token, _ = get_token_for_role(db, UserRole.CUSTOMER)
    ss1_id, _, _ = setup_booking_context(db, 999)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create expired hold manually
    user = db.query(User).first()
    ss1 = db.query(ShowSeat).filter(ShowSeat.id == ss1_id).first()
    ss1.status = SeatStatus.HELD
    ss1.held_by_id = user.id
    ss1.hold_expires_at = datetime.now() - timedelta(minutes=1)
    db.commit()
    
    # Try to book
    response = client.post("/api/v1/bookings/", json={"show_seat_ids": [ss1_id]}, headers=headers)
    assert response.status_code == 409
    assert "expired" in response.json()["message"].lower()

def test_confirm_booking_multi_seat_atomic_failure(client, db_session):
    db = db_session
    token, _ = get_token_for_role(db, UserRole.CUSTOMER)
    ss1_id, ss2_id, _ = setup_booking_context(db, 999)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Hold only one seat
    client.post("/api/v1/holds", json={"show_seat_id": ss1_id}, headers=headers)
    
    # Try to book both (ss2_id is AVAILABLE, not HELD)
    response = client.post("/api/v1/bookings/", json={"show_seat_ids": [ss1_id, ss2_id]}, headers=headers)
    assert response.status_code == 409
    
    # Verify no partial booking
    assert db.query(Booking).count() == 0
    ss1 = db.query(ShowSeat).filter(ShowSeat.id == ss1_id).first()
    assert ss1.status == SeatStatus.HELD # Remains HELD

def test_cancel_booking_success(client, db_session):
    db = db_session
    token, _ = get_token_for_role(db, UserRole.CUSTOMER)
    ss1_id, _, _ = setup_booking_context(db, 999)
    headers = {"Authorization": f"Bearer {token}"}
    
    # Book seat
    client.post("/api/v1/holds", json={"show_seat_id": ss1_id}, headers=headers)
    booking_resp = client.post("/api/v1/bookings/", json={"show_seat_ids": [ss1_id]}, headers=headers)
    booking_id = booking_resp.json()["id"]
    
    # Cancel booking
    response = client.post(f"/api/v1/bookings/{booking_id}/cancel", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"
    
    # Verify ShowSeat is AVAILABLE
    ss1 = db.query(ShowSeat).filter(ShowSeat.id == ss1_id).first()
    assert ss1.status == SeatStatus.AVAILABLE
    assert ss1.held_by_id is None

def test_cancel_others_booking_fails(client, db_session):
    db = db_session
    token1, _ = get_token_for_role(db, UserRole.CUSTOMER, "c1@example.com")
    token2, _ = get_token_for_role(db, UserRole.CUSTOMER, "c2@example.com")
    ss1_id, _, _ = setup_booking_context(db, 999)
    
    headers1 = {"Authorization": f"Bearer {token1}"}
    headers2 = {"Authorization": f"Bearer {token2}"}
    
    # Customer 1 books
    client.post("/api/v1/holds", json={"show_seat_id": ss1_id}, headers=headers1)
    booking_resp = client.post("/api/v1/bookings/", json={"show_seat_ids": [ss1_id]}, headers=headers1)
    booking_id = booking_resp.json()["id"]
    
    # Customer 2 tries to cancel
    response = client.post(f"/api/v1/bookings/{booking_id}/cancel", headers=headers2)
    assert response.status_code == 403

def test_get_booking_history(client, db_session):
    db = db_session
    token, _ = get_token_for_role(db, UserRole.CUSTOMER)
    ss1_id, ss2_id, _ = setup_booking_context(db, 999)
    headers = {"Authorization": f"Bearer {token}"}
    
    # Book 1
    client.post("/api/v1/holds", json={"show_seat_id": ss1_id}, headers=headers)
    client.post("/api/v1/bookings/", json={"show_seat_ids": [ss1_id]}, headers=headers)
    
    # Book 2
    client.post("/api/v1/holds", json={"show_seat_id": ss2_id}, headers=headers)
    client.post("/api/v1/bookings/", json={"show_seat_ids": [ss2_id]}, headers=headers)
    
    # Get history
    response = client.get("/api/v1/bookings/", headers=headers)
    assert response.status_code == 200
    assert response.json()["total"] == 2
    assert len(response.json()["items"]) == 2

def test_get_booking_detail(client, db_session):
    db = db_session
    token, _ = get_token_for_role(db, UserRole.CUSTOMER)
    ss1_id, _, _ = setup_booking_context(db, 999)
    headers = {"Authorization": f"Bearer {token}"}
    
    client.post("/api/v1/holds", json={"show_seat_id": ss1_id}, headers=headers)
    booking_resp = client.post("/api/v1/bookings/", json={"show_seat_ids": [ss1_id]}, headers=headers)
    booking_id = booking_resp.json()["id"]
    
    response = client.get(f"/api/v1/bookings/{booking_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == booking_id
    assert "event" in data
    assert "booking_seats" in data
    assert len(data["booking_seats"]) == 1
    assert data["booking_seats"][0]["show_seat_id"] == ss1_id

def test_independent_events_isolation(client, db_session):
    db = db_session
    token, _ = get_token_for_role(db, UserRole.CUSTOMER)
    ss1_id_e1, _, e1_id = setup_booking_context(db, 999)
    ss1_id_e2, _, e2_id = setup_booking_context(db, 999) # This creates a NEW venue/event because of how setup_booking_context is written
    
    assert e1_id != e2_id
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Book seat in Event 1
    client.post("/api/v1/holds", json={"show_seat_id": ss1_id_e1}, headers=headers)
    client.post("/api/v1/bookings/", json={"show_seat_ids": [ss1_id_e1]}, headers=headers)
    
    ss1_e1 = db.query(ShowSeat).filter(ShowSeat.id == ss1_id_e1).first()
    ss1_e2 = db.query(ShowSeat).filter(ShowSeat.id == ss1_id_e2).first()
    
    assert ss1_e1.status == SeatStatus.BOOKED
    assert ss1_e2.status == SeatStatus.AVAILABLE
