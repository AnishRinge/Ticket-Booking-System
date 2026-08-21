import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from datetime import datetime, timedelta

from app.main import app
from app.db.deps import get_db
from app.models import Base, User, UserRole
from app.models.venue import Venue, SeatCategory, Seat
from app.models.event import Event
from app.models.inventory import ShowSeat, SeatStatus
from app.core.security import get_password_hash, create_access_token
from app.core.config import settings

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

def setup_event_with_inventory(organiser_id):
    db = TestingSessionLocal()
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
    db.close()
    return ss_id

def test_customer_create_hold():
    token, _ = get_token_for_role(UserRole.CUSTOMER)
    ss_id = setup_event_with_inventory(999) 
    
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post("/api/v1/holds", json={"show_seat_id": ss_id}, headers=headers)
    assert response.status_code == 201
    assert response.json()["data"]["show_seat"]["status"] == "HELD"
    assert response.json()["data"]["show_seat"]["hold_expires_at"] is not None

def test_hold_conflict():
    token1, _ = get_token_for_role(UserRole.CUSTOMER, "c1@example.com")
    token2, _ = get_token_for_role(UserRole.CUSTOMER, "c2@example.com")
    ss_id = setup_event_with_inventory(999)
    
    headers1 = {"Authorization": f"Bearer {token1}"}
    client.post("/api/v1/holds", json={"show_seat_id": ss_id}, headers=headers1)
    
    # Second customer tries to hold same seat
    headers2 = {"Authorization": f"Bearer {token2}"}
    response = client.post("/api/v1/holds", json={"show_seat_id": ss_id}, headers=headers2)
    assert response.status_code == 409

def test_release_own_hold():
    token, _ = get_token_for_role(UserRole.CUSTOMER)
    ss_id = setup_event_with_inventory(999)
    
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/api/v1/holds", json={"show_seat_id": ss_id}, headers=headers)
    
    response = client.delete(f"/api/v1/holds/{ss_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["data"]["show_seat"]["status"] == "AVAILABLE"

def test_release_others_hold_fails():
    token1, _ = get_token_for_role(UserRole.CUSTOMER, "c1@example.com")
    token2, _ = get_token_for_role(UserRole.CUSTOMER, "c2@example.com")
    ss_id = setup_event_with_inventory(999)
    
    headers1 = {"Authorization": f"Bearer {token1}"}
    client.post("/api/v1/holds", json={"show_seat_id": ss_id}, headers=headers1)
    
    headers2 = {"Authorization": f"Bearer {token2}"}
    response = client.delete(f"/api/v1/holds/{ss_id}", headers=headers2)
    assert response.status_code == 403

def test_expired_hold_reconciliation():
    token, _ = get_token_for_role(UserRole.CUSTOMER)
    ss_id = setup_event_with_inventory(999)
    
    # Create expired hold manually
    db = TestingSessionLocal()
    ss = db.query(ShowSeat).filter(ShowSeat.id == ss_id).first()
    ss.status = SeatStatus.HELD
    ss.held_by_id = 998 # Someone else
    ss.hold_expires_at = datetime.now() - timedelta(minutes=1)
    db.commit()
    db.close()
    
    # Now our customer tries to hold it. It should reconcile and succeed.
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post("/api/v1/holds", json={"show_seat_id": ss_id}, headers=headers)
    assert response.status_code == 201
    assert response.json()["data"]["show_seat"]["status"] == "HELD"

def test_cleanup_worker():
    ss_id = setup_event_with_inventory(999)
    db = TestingSessionLocal()
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
    db.close()
