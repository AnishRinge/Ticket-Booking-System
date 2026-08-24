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

def setup_event_with_inventory(db, organiser_id):
    v = Venue(name="V1", address="A1")
    c = SeatCategory(name="Standard")
    db.add_all([v, c])
    db.commit()
    s = Seat(venue_id=v.id, category_id=c.id, row_identifier="A", seat_number=1)
    db.add(s)
    db.commit()
    e = Event(title="Movie", venue_id=v.id, organiser_id=organiser_id, start_time=datetime.now() + timedelta(days=1))
    db.add(e)
    db.commit()
    ss = ShowSeat(event_id=e.id, physical_seat_id=s.id, status=SeatStatus.AVAILABLE)
    db.add(ss)
    db.commit()
    ss_id = ss.id
    return ss_id

def test_customer_create_hold(client, db_session):
    db = db_session
    token, _ = get_token_for_role(db, UserRole.CUSTOMER)
    ss_id = setup_event_with_inventory(db, 999) 
    
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post("/api/v1/holds", json={"show_seat_id": ss_id}, headers=headers)
    assert response.status_code == 201
    assert response.json()["data"]["show_seat"]["status"] == "HELD"
    assert response.json()["data"]["show_seat"]["hold_expires_at"] is not None

def test_organiser_cannot_create_hold(client, db_session):
    db = db_session
    token, _ = get_token_for_role(db, UserRole.ORGANISER)
    ss_id = setup_event_with_inventory(db, 999)

    headers = {"Authorization": f"Bearer {token}"}
    response = client.post("/api/v1/holds", json={"show_seat_id": ss_id}, headers=headers)
    assert response.status_code == 403

def test_admin_cannot_create_hold(client, db_session):
    db = db_session
    token, _ = get_token_for_role(db, UserRole.ADMIN)
    ss_id = setup_event_with_inventory(db, 999)

    headers = {"Authorization": f"Bearer {token}"}
    response = client.post("/api/v1/holds", json={"show_seat_id": ss_id}, headers=headers)
    assert response.status_code == 403

def test_hold_conflict(client, db_session):
    db = db_session
    token1, _ = get_token_for_role(db, UserRole.CUSTOMER, "c1@example.com")
    token2, _ = get_token_for_role(db, UserRole.CUSTOMER, "c2@example.com")
    ss_id = setup_event_with_inventory(db, 999)
    
    headers1 = {"Authorization": f"Bearer {token1}"}
    client.post("/api/v1/holds", json={"show_seat_id": ss_id}, headers=headers1)
    
    # Second customer tries to hold same seat
    headers2 = {"Authorization": f"Bearer {token2}"}
    response = client.post("/api/v1/holds", json={"show_seat_id": ss_id}, headers=headers2)
    assert response.status_code == 409

def test_release_own_hold(client, db_session):
    db = db_session
    token, _ = get_token_for_role(db, UserRole.CUSTOMER)
    ss_id = setup_event_with_inventory(db, 999)
    
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/api/v1/holds", json={"show_seat_id": ss_id}, headers=headers)
    
    response = client.delete(f"/api/v1/holds/{ss_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["data"]["show_seat"]["status"] == "AVAILABLE"

def test_release_others_hold_fails(client, db_session):
    db = db_session
    token1, _ = get_token_for_role(db, UserRole.CUSTOMER, "c1@example.com")
    token2, _ = get_token_for_role(db, UserRole.CUSTOMER, "c2@example.com")
    ss_id = setup_event_with_inventory(db, 999)
    
    headers1 = {"Authorization": f"Bearer {token1}"}
    client.post("/api/v1/holds", json={"show_seat_id": ss_id}, headers=headers1)
    
    headers2 = {"Authorization": f"Bearer {token2}"}
    response = client.delete(f"/api/v1/holds/{ss_id}", headers=headers2)
    assert response.status_code == 403

def test_expired_hold_reconciliation(client, db_session):
    db = db_session
    token, _ = get_token_for_role(db, UserRole.CUSTOMER)
    ss_id = setup_event_with_inventory(db, 999)
    
    # Create expired hold manually
    ss = db.query(ShowSeat).filter(ShowSeat.id == ss_id).first()
    ss.status = SeatStatus.HELD
    ss.held_by_id = 998 # Someone else
    ss.hold_expires_at = datetime.now() - timedelta(minutes=1)
    db.commit()
    
    # Now our customer tries to hold it. It should reconcile and succeed.
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post("/api/v1/holds", json={"show_seat_id": ss_id}, headers=headers)
    assert response.status_code == 201
    assert response.json()["data"]["show_seat"]["status"] == "HELD"

def test_cleanup_worker(db_session):
    db = db_session
    ss_id = setup_event_with_inventory(db, 999)
    ss = db.query(ShowSeat).filter(ShowSeat.id == ss_id).first()
    ss.status = SeatStatus.HELD
    ss.held_by_id = 1
    ss.hold_expires_at = datetime.now() - timedelta(minutes=1)
    db.commit()
    
    from app.services.hold import hold_service
    count = hold_service.cleanup_expired_holds(db)
    assert count == 1
    
    ss = db.query(ShowSeat).filter(ShowSeat.id == ss_id).first()
    assert ss.status == SeatStatus.AVAILABLE
