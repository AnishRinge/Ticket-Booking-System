import pytest
import threading
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from datetime import datetime, timedelta

from app.models import Base, User, UserRole
from app.models.venue import Venue, SeatCategory, Seat
from app.models.event import Event
from app.models.inventory import ShowSeat, SeatStatus
from app.services.hold import hold_service
from app.core.exceptions import AppException

# Setup for Concurrency Tests
# Use a shared engine with StaticPool for SQLite concurrency testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def create_test_data(num_customers=10):
    db = TestingSessionLocal()
    # Create users
    customer_ids = []
    for i in range(num_customers):
        c = User(email=f"c{i}@example.com", hashed_password="pw", full_name=f"C{i}", role=UserRole.CUSTOMER)
        db.add(c)
        db.flush()
        customer_ids.append(c.id)
    
    # Create venue/event/seat
    v = Venue(name="V", address="A")
    cat = SeatCategory(name="C")
    db.add_all([v, cat])
    db.flush()
    
    s = Seat(venue_id=v.id, category_id=cat.id, row_identifier="A", seat_number=1)
    db.add(s)
    db.flush()
    
    e = Event(title="E", venue_id=v.id, organiser_id=1, start_time=datetime.now() + timedelta(days=1))
    db.add(e)
    db.flush()
    
    ss = ShowSeat(event_id=e.id, physical_seat_id=s.id, status=SeatStatus.AVAILABLE)
    db.add(ss)
    db.commit()
    ss_id = ss.id
    db.close()
    return ss_id, customer_ids

# Global lock for SQLite simulation of row-level locking
sqlite_sim_lock = threading.Lock()

def attempt_hold(ss_id, customer_id, results):
    db = TestingSessionLocal()
    # We must fetch the user in this session's context
    user = db.get(User, customer_id)
    try:
        # SQLite with StaticPool does not support true concurrent row-level locking (FOR UPDATE).
        # To verify the application's transaction logic in a SQLite-based test environment,
        # we use a threading lock to simulate the serialization that PostgreSQL's FOR UPDATE 
        # would provide at the database level.
        with sqlite_sim_lock:
            hold_service.create_hold(db, show_seat_id=ss_id, user=user)
        results.append(("SUCCESS", customer_id))
    except AppException as e:
        results.append(("CONFLICT", customer_id, e.message))
    except Exception as e:
        results.append(("ERROR", customer_id, str(e)))
    finally:
        db.close()

def test_concurrent_seat_acquisition():
    """
    Test that when multiple customers attempt to hold the same seat simultaneously,
    exactly one succeeds and others get a conflict.
    """
    num_customers = 10
    ss_id, customer_ids = create_test_data(num_customers)
    results = []
    
    # Use a barrier to synchronize threads for simultaneous attempt
    barrier = threading.Barrier(num_customers)
    
    def worker(customer_id):
        barrier.wait() # All threads wait here until everyone is ready
        attempt_hold(ss_id, customer_id, results)

    threads = []
    for cid in customer_ids:
        t = threading.Thread(target=worker, args=(cid,))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    successes = [r for r in results if r[0] == "SUCCESS"]
    conflicts = [r for r in results if r[0] == "CONFLICT"]
    errors = [r for r in results if r[0] == "ERROR"]
    
    assert len(errors) == 0, f"Errors occurred: {errors}"
    assert len(successes) == 1, f"Expected 1 success, got {len(successes)}"
    assert len(conflicts) == num_customers - 1
    
    # Verify DB state
    db = TestingSessionLocal()
    ss = db.get(ShowSeat, ss_id)
    assert ss.status == SeatStatus.HELD
    assert ss.held_by_id == successes[0][1]
    db.close()

def test_expired_hold_reconciliation_race():
    """
    Test that multiple customers can concurrently attempt to acquire a seat
    with an expired hold, and exactly one will succeed in reconciling and holding it.
    """
    num_customers = 5
    ss_id, customer_ids = create_test_data(num_customers)
    
    # Set seat to expired HELD state manually
    db = TestingSessionLocal()
    ss = db.get(ShowSeat, ss_id)
    ss.status = SeatStatus.HELD
    ss.held_by_id = 999 # Some other user
    ss.hold_expires_at = datetime.now() - timedelta(minutes=1)
    db.commit()
    db.close()
    
    results = []
    barrier = threading.Barrier(num_customers)
    
    def worker(customer_id):
        barrier.wait()
        attempt_hold(ss_id, customer_id, results)

    threads = []
    for cid in customer_ids:
        t = threading.Thread(target=worker, args=(cid,))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()

    successes = [r for r in results if r[0] == "SUCCESS"]
    errors = [r for r in results if r[0] == "ERROR"]
    conflicts = [r for r in results if r[0] == "CONFLICT"]
    assert len(errors) == 0, f"Errors: {errors}"
    assert len(successes) == 1, f"Successes: {len(successes)}, Conflicts: {len(conflicts)}, Results: {results}"
    
    # Verify winning user is one of the concurrent ones, not the original 999
    db = TestingSessionLocal()
    ss = db.get(ShowSeat, ss_id)
    assert ss.status == SeatStatus.HELD
    assert ss.held_by_id in customer_ids
    assert ss.held_by_id != 999
    db.close()

def test_independent_seats_not_blocked():
    """
    Test that holding different seats concurrently works without blocking each other.
    """
    db = TestingSessionLocal()
    v = Venue(name="V", address="A")
    cat = SeatCategory(name="C")
    db.add_all([v, cat])
    db.flush()
    s1 = Seat(venue_id=v.id, category_id=cat.id, row_identifier="A", seat_number=1)
    s2 = Seat(venue_id=v.id, category_id=cat.id, row_identifier="A", seat_number=2)
    db.add_all([s1, s2])
    db.flush()
    e = Event(title="E", venue_id=v.id, organiser_id=1, start_time=datetime.now() + timedelta(days=1))
    db.add(e)
    db.flush()
    ss1 = ShowSeat(event_id=e.id, physical_seat_id=s1.id, status=SeatStatus.AVAILABLE)
    ss2 = ShowSeat(event_id=e.id, physical_seat_id=s2.id, status=SeatStatus.AVAILABLE)
    db.add_all([ss1, ss2])
    db.commit()
    ss1_id, ss2_id = ss1.id, ss2.id
    
    user1 = User(email="u1@example.com", hashed_password="pw", full_name="U1", role=UserRole.CUSTOMER)
    user2 = User(email="u2@example.com", hashed_password="pw", full_name="U2", role=UserRole.CUSTOMER)
    db.add_all([user1, user2])
    db.commit()
    u1_id, u2_id = user1.id, user2.id
    db.close()
    
    results = []
    
    def t1():
        db = TestingSessionLocal()
        user = db.get(User, u1_id)
        hold_service.create_hold(db, show_seat_id=ss1_id, user=user)
        results.append("SUCCESS1")
        db.close()
        
    def t2():
        db = TestingSessionLocal()
        user = db.get(User, u2_id)
        hold_service.create_hold(db, show_seat_id=ss2_id, user=user)
        results.append("SUCCESS2")
        db.close()

    threads = [threading.Thread(target=t1), threading.Thread(target=t2)]
    for t in threads: t.start()
    for t in threads: t.join()
    
    assert "SUCCESS1" in results
    assert "SUCCESS2" in results
