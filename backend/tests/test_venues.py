import pytest
from app.models import User, UserRole
from app.core.security import get_password_hash, create_access_token

def get_admin_token(db):
    admin = User(
        email="admin@example.com",
        hashed_password=get_password_hash("password123"),
        full_name="Admin",
        role=UserRole.ADMIN
    )
    db.add(admin)
    db.commit()
    token = create_access_token(subject=admin.id)
    return token

def get_customer_token(db):
    customer = User(
        email="customer@example.com",
        hashed_password=get_password_hash("password123"),
        full_name="Customer",
        role=UserRole.CUSTOMER
    )
    db.add(customer)
    db.commit()
    token = create_access_token(subject=customer.id)
    return token

def test_admin_create_venue(client, db_session):
    token = get_admin_token(db_session)
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/api/v1/venues",
        json={"name": "Grand Cinema", "address": "123 Main St"},
        headers=headers
    )
    assert response.status_code == 201
    assert response.json()["data"]["name"] == "Grand Cinema"

def test_customer_cannot_create_venue(client, db_session):
    token = get_customer_token(db_session)
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/api/v1/venues",
        json={"name": "Grand Cinema", "address": "123 Main St"},
        headers=headers
    )
    assert response.status_code == 403

def test_list_venues_public(client, db_session):
    # Create a venue first
    db = db_session
    from app.models.venue import Venue
    db.add(Venue(name="V1", address="A1"))
    db.commit()
    
    response = client.get("/api/v1/venues")
    assert response.status_code == 200
    assert len(response.json()["data"]) == 1

def test_seat_category_management(client, db_session):
    token = get_admin_token(db_session)
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create category
    response = client.post(
        "/api/v1/venues/categories",
        json={"name": "VIP", "description": "Luxe seats"},
        headers=headers
    )
    assert response.status_code == 201
    cat_id = response.json()["data"]["id"]
    
    # List categories
    response = client.get("/api/v1/venues/categories")
    assert response.status_code == 200
    assert any(c["name"] == "VIP" for c in response.json()["data"])

def test_physical_seat_management(client, db_session):
    token = get_admin_token(db_session)
    headers = {"Authorization": f"Bearer {token}"}
    
    # Setup: Venue and Category
    db = db_session
    from app.models.venue import Venue, SeatCategory
    v = Venue(name="V", address="A")
    c = SeatCategory(name="Premium")
    db.add_all([v, c])
    db.commit()
    venue_id = v.id
    category_id = c.id
    
    # Create seat
    response = client.post(
        f"/api/v1/venues/{venue_id}/seats",
        json={"category_id": category_id, "row_identifier": "A", "seat_number": 1},
        headers=headers
    )
    assert response.status_code == 201
    seat_id = response.json()["data"]["id"]
    
    # List seats
    response = client.get(f"/api/v1/venues/{venue_id}/seats")
    assert response.status_code == 200
    assert len(response.json()["data"]) == 1
    
    # Update seat
    response = client.patch(
        f"/api/v1/venues/seats/{seat_id}",
        json={"seat_number": 2},
        headers=headers
    )
    assert response.status_code == 200
    assert response.json()["data"]["seat_number"] == 2
    
    # Delete seat
    response = client.delete(f"/api/v1/venues/seats/{seat_id}", headers=headers)
    assert response.status_code == 200
    
    # Verify deletion
    response = client.get(f"/api/v1/venues/seats/{seat_id}")
    assert response.status_code == 404

def test_duplicate_seat_rejected(client, db_session):
    token = get_admin_token(db_session)
    headers = {"Authorization": f"Bearer {token}"}
    
    # Setup
    db = db_session
    from app.models.venue import Venue, SeatCategory
    v = Venue(name="V", address="A")
    c = SeatCategory(name="Premium")
    db.add_all([v, c])
    db.commit()
    venue_id = v.id
    category_id = c.id
    
    payload = {"category_id": category_id, "row_identifier": "A", "seat_number": 1}
    client.post(f"/api/v1/venues/{venue_id}/seats", json=payload, headers=headers)
    
    # Duplicate
    response = client.post(f"/api/v1/venues/{venue_id}/seats", json=payload, headers=headers)
    assert response.status_code == 400
    assert "already exists" in response.json()["message"]
