import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import app
from app.db.deps import get_db
from app.models import Base, User, UserRole
from app.core.security import get_password_hash, create_access_token

# Setup In-memory SQLite for tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def get_admin_token():
    db = TestingSessionLocal()
    admin = User(
        email="admin@example.com",
        hashed_password=get_password_hash("password123"),
        full_name="Admin",
        role=UserRole.ADMIN
    )
    db.add(admin)
    db.commit()
    token = create_access_token(subject=admin.id)
    db.close()
    return token

def get_customer_token():
    db = TestingSessionLocal()
    customer = User(
        email="customer@example.com",
        hashed_password=get_password_hash("password123"),
        full_name="Customer",
        role=UserRole.CUSTOMER
    )
    db.add(customer)
    db.commit()
    token = create_access_token(subject=customer.id)
    db.close()
    return token

def test_admin_create_venue():
    token = get_admin_token()
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/api/v1/venues",
        json={"name": "Grand Cinema", "address": "123 Main St"},
        headers=headers
    )
    assert response.status_code == 201
    assert response.json()["data"]["name"] == "Grand Cinema"

def test_customer_cannot_create_venue():
    token = get_customer_token()
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/api/v1/venues",
        json={"name": "Grand Cinema", "address": "123 Main St"},
        headers=headers
    )
    assert response.status_code == 403

def test_list_venues_public():
    # Create a venue first
    db = TestingSessionLocal()
    from app.models.venue import Venue
    db.add(Venue(name="V1", address="A1"))
    db.commit()
    db.close()
    
    response = client.get("/api/v1/venues")
    assert response.status_code == 200
    assert len(response.json()["data"]) == 1

def test_seat_category_management():
    token = get_admin_token()
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

def test_physical_seat_management():
    token = get_admin_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    # Setup: Venue and Category
    db = TestingSessionLocal()
    from app.models.venue import Venue, SeatCategory
    v = Venue(name="V", address="A")
    c = SeatCategory(name="Premium")
    db.add_all([v, c])
    db.commit()
    venue_id = v.id
    category_id = c.id
    db.close()
    
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

def test_duplicate_seat_rejected():
    token = get_admin_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    # Setup
    db = TestingSessionLocal()
    from app.models.venue import Venue, SeatCategory
    v = Venue(name="V", address="A")
    c = SeatCategory(name="Premium")
    db.add_all([v, c])
    db.commit()
    venue_id = v.id
    category_id = c.id
    db.close()
    
    payload = {"category_id": category_id, "row_identifier": "A", "seat_number": 1}
    client.post(f"/api/v1/venues/{venue_id}/seats", json=payload, headers=headers)
    
    # Duplicate
    response = client.post(f"/api/v1/venues/{venue_id}/seats", json=payload, headers=headers)
    assert response.status_code == 400
    assert "already exists" in response.json()["message"]
