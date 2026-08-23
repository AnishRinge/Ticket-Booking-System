import pytest
from datetime import datetime, timedelta
from fastapi import status
from app.models import User, UserRole
from app.models.venue import Venue, SeatCategory, Seat
from app.models.event import Event, EventCategoryPricing
from app.models.waitlist import WaitlistStatus, WaitlistEntry
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
    return token, user.id

def setup_event_context(db):
    # Setup Venue
    v = Venue(name="Venue 1", address="Address 1")
    db.add(v)
    db.commit()
    
    # Setup Category
    c = SeatCategory(name="Premium")
    db.add(c)
    db.commit()
    
    # Setup Event
    e = Event(
        title="Event 1", 
        venue_id=v.id, 
        organiser_id=999, 
        start_time=datetime.now() + timedelta(days=1)
    )
    db.add(e)
    db.commit()
    
    # Setup Pricing
    p = EventCategoryPricing(event_id=e.id, category_id=c.id, price=1000.0)
    db.add(p)
    db.commit()
    
    return e, c

def test_join_waitlist_customer(client, db_session):
    db = db_session
    token, user_id = get_token_for_role(db, UserRole.CUSTOMER)
    event, category = setup_event_context(db)
    
    response = client.post(
        f"/api/v1/events/{event.id}/waitlist",
        json={"category_id": category.id},
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()["data"]
    assert data["event_id"] == event.id
    assert data["category_id"] == category.id
    assert data["status"] == WaitlistStatus.PENDING
    assert data["user_id"] == user_id

def test_join_waitlist_unauthenticated(client, db_session):
    db = db_session
    event, category = setup_event_context(db)
    
    response = client.post(
        f"/api/v1/events/{event.id}/waitlist",
        json={"category_id": category.id}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_join_waitlist_organiser_forbidden(client, db_session):
    db = db_session
    token, _ = get_token_for_role(db, UserRole.ORGANISER)
    event, category = setup_event_context(db)
    
    response = client.post(
        f"/api/v1/events/{event.id}/waitlist",
        json={"category_id": category.id},
        headers={"Authorization": f"Bearer {token}"}
    )
    # Based on RBAC, organisers might be forbidden from CUSTOMER-only actions
    assert response.status_code == status.HTTP_403_FORBIDDEN

def test_join_waitlist_invalid_event(client, db_session):
    db = db_session
    token, _ = get_token_for_role(db, UserRole.CUSTOMER)
    _, category = setup_event_context(db)
    
    response = client.post(
        "/api/v1/events/9999/waitlist",
        json={"category_id": category.id},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND

def test_join_waitlist_invalid_category(client, db_session):
    db = db_session
    token, _ = get_token_for_role(db, UserRole.CUSTOMER)
    event, _ = setup_event_context(db)
    
    response = client.post(
        f"/api/v1/events/{event.id}/waitlist",
        json={"category_id": 9999},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND

def test_join_waitlist_category_not_in_event(client, db_session):
    db = db_session
    token, _ = get_token_for_role(db, UserRole.CUSTOMER)
    event, _ = setup_event_context(db)
    
    # Create another category
    other_c = SeatCategory(name="Other")
    db.add(other_c)
    db.commit()
    
    response = client.post(
        f"/api/v1/events/{event.id}/waitlist",
        json={"category_id": other_c.id},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND

def test_join_waitlist_duplicate_prevention(client, db_session):
    db = db_session
    token, _ = get_token_for_role(db, UserRole.CUSTOMER)
    event, category = setup_event_context(db)
    
    # First join
    client.post(
        f"/api/v1/events/{event.id}/waitlist",
        json={"category_id": category.id},
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Second join
    response = client.post(
        f"/api/v1/events/{event.id}/waitlist",
        json={"category_id": category.id},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST

def test_leave_waitlist_success(client, db_session):
    db = db_session
    token, _ = get_token_for_role(db, UserRole.CUSTOMER)
    event, category = setup_event_context(db)
    
    # Join first
    join_resp = client.post(
        f"/api/v1/events/{event.id}/waitlist",
        json={"category_id": category.id},
        headers={"Authorization": f"Bearer {token}"}
    )
    waitlist_id = join_resp.json()["data"]["id"]
    
    # Leave
    leave_resp = client.delete(
        f"/api/v1/waitlist/{waitlist_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert leave_resp.status_code == status.HTTP_200_OK
    assert leave_resp.json()["data"]["status"] == WaitlistStatus.CANCELLED

def test_leave_waitlist_wrong_owner(client, db_session):
    db = db_session
    token1, _ = get_token_for_role(db, UserRole.CUSTOMER, "c1@example.com")
    token2, _ = get_token_for_role(db, UserRole.CUSTOMER, "c2@example.com")
    event, category = setup_event_context(db)
    
    # Customer 1 joins
    join_resp = client.post(
        f"/api/v1/events/{event.id}/waitlist",
        json={"category_id": category.id},
        headers={"Authorization": f"Bearer {token1}"}
    )
    waitlist_id = join_resp.json()["data"]["id"]
    
    # Customer 2 tries to remove Customer 1's entry
    leave_resp = client.delete(
        f"/api/v1/waitlist/{waitlist_id}",
        headers={"Authorization": f"Bearer {token2}"}
    )
    assert leave_resp.status_code == status.HTTP_403_FORBIDDEN

def test_fifo_retrieval(client, db_session):
    db = db_session
    event, category = setup_event_context(db)
    
    # Create 3 customers and join waitlist in order
    tokens_and_ids = [get_token_for_role(db, UserRole.CUSTOMER, f"c{i}@test.com") for i in range(3)]
    
    for token, _ in tokens_and_ids:
        client.post(
            f"/api/v1/events/{event.id}/waitlist",
            json={"category_id": category.id},
            headers={"Authorization": f"Bearer {token}"}
        )
    
    from app.services.waitlist import waitlist_service
    fifo_entries = waitlist_service.get_fifo_waitlist(db, event_id=event.id, category_id=category.id)
    
    assert len(fifo_entries) == 3
    assert fifo_entries[0].user_id == tokens_and_ids[0][1]
    assert fifo_entries[1].user_id == tokens_and_ids[1][1]
    assert fifo_entries[2].user_id == tokens_and_ids[2][1]
    
    # Verify deterministic ordering
    assert fifo_entries[0].id < fifo_entries[1].id < fifo_entries[2].id
