import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from datetime import datetime, timedelta

from app.main import app
from app.db.deps import get_db
from app.models import Base, User, UserRole
from app.models.venue import Venue, SeatCategory
from app.models.event import Event
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

def get_token_for_role(role: UserRole, email: str = "test@example.com"):
    db = TestingSessionLocal()
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
    db.close()
    return token, user_id

def create_venue_and_category():
    db = TestingSessionLocal()
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
    
    db.close()
    return v_id, c_id

def test_organiser_create_event():
    token, _ = get_token_for_role(UserRole.ORGANISER)
    v_id, c_id = create_venue_and_category()
    
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

def test_customer_cannot_create_event():
    token, _ = get_token_for_role(UserRole.CUSTOMER)
    v_id, c_id = create_venue_and_category()
    
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "title": "Movie Night",
        "venue_id": v_id,
        "start_time": (datetime.now() + timedelta(days=1)).isoformat(),
        "category_pricings": []
    }
    
    response = client.post("/api/v1/events", json=payload, headers=headers)
    assert response.status_code == 403

def test_create_event_invalid_venue():
    token, _ = get_token_for_role(UserRole.ORGANISER)
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

def test_create_event_past_time():
    token, _ = get_token_for_role(UserRole.ORGANISER)
    v_id, c_id = create_venue_and_category()
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

def test_list_events():
    v_id, c_id = create_venue_and_category()
    db = TestingSessionLocal()
    e1 = Event(title="Event 1", venue_id=v_id, organiser_id=1, start_time=datetime.now() + timedelta(days=1))
    e2 = Event(title="Movie 2", venue_id=v_id, organiser_id=1, start_time=datetime.now() + timedelta(days=2))
    db.add_all([e1, e2])
    db.commit()
    db.close()
    
    # List all
    response = client.get("/api/v1/events")
    assert response.status_code == 200
    assert len(response.json()["data"]) == 2
    
    # Filter by title
    response = client.get("/api/v1/events?title=Movie")
    assert response.status_code == 200
    assert len(response.json()["data"]) == 1
    assert response.json()["data"][0]["title"] == "Movie 2"

def test_update_event_ownership():
    token1, user1_id = get_token_for_role(UserRole.ORGANISER, "o1@example.com")
    token2, user2_id = get_token_for_role(UserRole.ORGANISER, "o2@example.com")
    v_id, c_id = create_venue_and_category()
    
    db = TestingSessionLocal()
    e = Event(title="Original Title", venue_id=v_id, organiser_id=user1_id, start_time=datetime.now() + timedelta(days=1))
    db.add(e)
    db.commit()
    e_id = e.id
    db.close()
    
    # Owner updates
    headers1 = {"Authorization": f"Bearer {token1}"}
    response = client.patch(f"/api/v1/events/{e_id}", json={"title": "Updated Title"}, headers=headers1)
    assert response.status_code == 200
    assert response.json()["data"]["title"] == "Updated Title"
    
    # Non-owner updates
    headers2 = {"Authorization": f"Bearer {token2}"}
    response = client.patch(f"/api/v1/events/{e_id}", json={"title": "Evil Update"}, headers=headers2)
    assert response.status_code == 403

def test_delete_event_ownership():
    token1, user1_id = get_token_for_role(UserRole.ORGANISER, "o1@example.com")
    token2, user2_id = get_token_for_role(UserRole.ORGANISER, "o2@example.com")
    v_id, c_id = create_venue_and_category()
    
    db = TestingSessionLocal()
    e = Event(title="To be deleted", venue_id=v_id, organiser_id=user1_id, start_time=datetime.now() + timedelta(days=1))
    db.add(e)
    db.commit()
    e_id = e.id
    db.close()
    
    # Non-owner deletes
    headers2 = {"Authorization": f"Bearer {token2}"}
    response = client.delete(f"/api/v1/events/{e_id}", headers=headers2)
    assert response.status_code == 403
    
    # Owner deletes
    headers1 = {"Authorization": f"Bearer {token1}"}
    response = client.delete(f"/api/v1/events/{e_id}", headers=headers1)
    assert response.status_code == 200
