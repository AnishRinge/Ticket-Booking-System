import pytest
from datetime import datetime, timedelta
from app.models import User, UserRole
from app.models.venue import Venue, SeatCategory, Seat
from app.models.event import Event
from app.models.inventory import ShowSeat, SeatStatus
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

def setup_venue_with_seats(db):
    v = Venue(name="Cinema 1", address="Mall")
    c = SeatCategory(name="Standard")
    db.add_all([v, c])
    db.commit()
    
    s1 = Seat(venue_id=v.id, category_id=c.id, row_identifier="A", seat_number=1)
    s2 = Seat(venue_id=v.id, category_id=c.id, row_identifier="A", seat_number=2)
    db.add_all([s1, s2])
    db.commit()
    v_id, c_id = v.id, c.id
    return v_id, c_id

def test_initialize_inventory_success(client, db_session):
    db = db_session
    token, user_id = get_token_for_role(db, UserRole.ORGANISER)
    v_id, c_id = setup_venue_with_seats(db)
    
    e = Event(title="Movie", venue_id=v_id, organiser_id=user_id, start_time=datetime.now() + timedelta(days=1))
    db.add(e)
    db.commit()
    e_id = e.id
    
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(f"/api/v1/events/{e_id}/inventory/initialize", headers=headers)
    assert response.status_code == 201
    assert len(response.json()["data"]) == 2
    assert all(s["status"] == "AVAILABLE" for s in response.json()["data"])

def test_initialize_inventory_ownership(client, db_session):
    db = db_session
    token1, user1_id = get_token_for_role(db, UserRole.ORGANISER, "o1@example.com")
    token2, user2_id = get_token_for_role(db, UserRole.ORGANISER, "o2@example.com")
    v_id, c_id = setup_venue_with_seats(db)
    
    e = Event(title="Event", venue_id=v_id, organiser_id=user1_id, start_time=datetime.now() + timedelta(days=1))
    db.add(e)
    db.commit()
    e_id = e.id
    
    # Non-owner fails
    headers2 = {"Authorization": f"Bearer {token2}"}
    response = client.post(f"/api/v1/events/{e_id}/inventory/initialize", headers=headers2)
    assert response.status_code == 403

def test_initialize_inventory_admin(client, db_session):
    db = db_session
    token, _ = get_token_for_role(db, UserRole.ADMIN, "admin@example.com")
    v_id, c_id = setup_venue_with_seats(db)
    
    # Create event owned by someone else
    e = Event(title="Admin Init", venue_id=v_id, organiser_id=999, start_time=datetime.now() + timedelta(days=1))
    db.add(e)
    db.commit()
    e_id = e.id
    
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(f"/api/v1/events/{e_id}/inventory/initialize", headers=headers)
    assert response.status_code == 201
    assert len(response.json()["data"]) == 2

def test_initialize_inventory_idempotency(client, db_session):
    db = db_session
    token, user_id = get_token_for_role(db, UserRole.ORGANISER)
    v_id, c_id = setup_venue_with_seats(db)
    
    e = Event(title="Movie", venue_id=v_id, organiser_id=user_id, start_time=datetime.now() + timedelta(days=1))
    db.add(e)
    db.commit()
    e_id = e.id
    
    headers = {"Authorization": f"Bearer {token}"}
    # First call
    client.post(f"/api/v1/events/{e_id}/inventory/initialize", headers=headers)
    # Second call
    response = client.post(f"/api/v1/events/{e_id}/inventory/initialize", headers=headers)
    assert response.status_code == 201
    assert len(response.json()["data"]) == 2

def test_get_seat_map(client, db_session):
    db = db_session
    token, user_id = get_token_for_role(db, UserRole.ORGANISER)
    v_id, c_id = setup_venue_with_seats(db)
    
    e = Event(title="Movie", venue_id=v_id, organiser_id=user_id, start_time=datetime.now() + timedelta(days=1))
    db.add(e)
    db.commit()
    e_id = e.id
    
    headers = {"Authorization": f"Bearer {token}"}
    # Initialize
    client.post(f"/api/v1/events/{e_id}/inventory/initialize", headers=headers)
    
    # Get seat map (Public)
    response = client.get(f"/api/v1/events/{e_id}/seat-map")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["event_id"] == e_id
    assert len(data["seats"]) == 2
    assert data["seats"][0]["physical_seat"]["row_identifier"] == "A"

def test_inventory_isolation(client, db_session):
    db = db_session
    token, user_id = get_token_for_role(db, UserRole.ORGANISER)
    v_id, c_id = setup_venue_with_seats(db)
    
    e1 = Event(title="E1", venue_id=v_id, organiser_id=user_id, start_time=datetime.now() + timedelta(days=1))
    e2 = Event(title="E2", venue_id=v_id, organiser_id=user_id, start_time=datetime.now() + timedelta(days=1))
    db.add_all([e1, e2])
    db.commit()
    e1_id, e2_id = e1.id, e2.id
    
    headers = {"Authorization": f"Bearer {token}"}
    client.post(f"/api/v1/events/{e1_id}/inventory/initialize", headers=headers)
    client.post(f"/api/v1/events/{e2_id}/inventory/initialize", headers=headers)
    
    # Change status of a seat in E1
    s1 = db.query(ShowSeat).filter(ShowSeat.event_id == e1_id).first()
    s1.status = SeatStatus.BOOKED
    db.commit()
    
    # Check E1
    resp1 = client.get(f"/api/v1/events/{e1_id}/seat-map")
    assert any(s["status"] == "BOOKED" for s in resp1.json()["data"]["seats"])
    
    # Check E2
    resp2 = client.get(f"/api/v1/events/{e2_id}/seat-map")
    assert all(s["status"] == "AVAILABLE" for s in resp2.json()["data"]["seats"])
