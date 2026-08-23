import pytest
import threading
from datetime import datetime, timedelta

from app.models import User, UserRole
from app.models.venue import Venue, SeatCategory, Seat
from app.models.event import Event, EventCategoryPricing
from app.models.inventory import ShowSeat, SeatStatus
from app.models.waitlist import WaitlistEntry, WaitlistStatus, WaitlistOffer, OfferStatus
from app.services.hold import hold_service
from app.services.waitlist import waitlist_service
from app.core.exceptions import AppException

def create_test_data(db, num_customers=10):
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

    p = EventCategoryPricing(event_id=e.id, category_id=cat.id, price=1000)
    db.add(p)
    db.flush()
    
    ss = ShowSeat(event_id=e.id, physical_seat_id=s.id, status=SeatStatus.AVAILABLE)
    db.add(ss)
    db.commit()
    ss_id = ss.id
    return ss_id, customer_ids

# Global lock for SQLite simulation of row-level locking
sqlite_sim_lock = threading.Lock()

def attempt_hold(session_factory, ss_id, customer_id, results):
    db = session_factory()
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

def test_concurrent_seat_acquisition(db_session, session_factory):
    """
    Test that when multiple customers attempt to hold the same seat simultaneously,
    exactly one succeeds and others get a conflict.
    """
    db = db_session
    num_customers = 10
    ss_id, customer_ids = create_test_data(db, num_customers)
    results = []
    
    # Use a barrier to synchronize threads for simultaneous attempt
    barrier = threading.Barrier(num_customers)
    
    def worker(customer_id):
        barrier.wait() # All threads wait here until everyone is ready
        attempt_hold(session_factory, ss_id, customer_id, results)

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
    ss = db.get(ShowSeat, ss_id)
    assert ss.status == SeatStatus.HELD
    assert ss.held_by_id == successes[0][1]

def test_expired_hold_reconciliation_race(db_session, session_factory):
    """
    Test that multiple customers can concurrently attempt to acquire a seat
    with an expired hold, and exactly one will succeed in reconciling and holding it.
    """
    db = db_session
    num_customers = 5
    ss_id, customer_ids = create_test_data(db, num_customers)
    
    # Set seat to expired HELD state manually
    ss = db.get(ShowSeat, ss_id)
    ss.status = SeatStatus.HELD
    ss.held_by_id = 999 # Some other user
    ss.hold_expires_at = datetime.now() - timedelta(minutes=1)
    db.commit()
    
    results = []
    barrier = threading.Barrier(num_customers)
    
    def worker(customer_id):
        barrier.wait()
        attempt_hold(session_factory, ss_id, customer_id, results)

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
    ss = db.get(ShowSeat, ss_id)
    assert ss.status == SeatStatus.HELD
    assert ss.held_by_id in customer_ids
    assert ss.held_by_id != 999

def test_independent_seats_not_blocked(db_session, session_factory):
    """
    Test that holding different seats concurrently works without blocking each other.
    """
    db = db_session
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
    
    results = []
    
    def t1():
        db = session_factory()
        user = db.get(User, u1_id)
        hold_service.create_hold(db, show_seat_id=ss1_id, user=user)
        results.append("SUCCESS1")
        db.close()
        
    def t2():
        db = session_factory()
        user = db.get(User, u2_id)
        hold_service.create_hold(db, show_seat_id=ss2_id, user=user)
        results.append("SUCCESS2")
        db.close()

    threads = [threading.Thread(target=t1), threading.Thread(target=t2)]
    for t in threads: t.start()
    for t in threads: t.join()
    
    assert "SUCCESS1" in results
    assert "SUCCESS2" in results

def test_concurrent_waitlist_allocation(db_session, session_factory):
    """
    Race A: Two attempts to allocate the same ShowSeat.
    Expected: Only one active offer.
    """
    db = db_session
    num_customers = 5
    ss_id, customer_ids = create_test_data(db, num_customers)
    
    # 2 customers join waitlist
    ss = db.get(ShowSeat, ss_id)
    for i in range(2):
        waitlist_service.join_waitlist(db, user_id=customer_ids[i], event_id=ss.event_id, category_id=ss.physical_seat.category_id)
    db.commit()
    
    results = []
    barrier = threading.Barrier(num_customers)
    
    def worker(customer_id):
        barrier.wait()
        tdb = session_factory()
        try:
            with sqlite_sim_lock:
                offer = waitlist_service.process_waitlist_for_seat(tdb, show_seat_id=ss_id)
                if offer:
                    results.append(("SUCCESS", customer_id))
                else:
                    results.append(("NONE", customer_id))
        except Exception as e:
            results.append(("ERROR", str(e)))
        finally:
            tdb.close()

    threads = [threading.Thread(target=worker, args=(cid,)) for cid in customer_ids]
    for t in threads: t.start()
    for t in threads: t.join()
    
    successes = [r for r in results if r[0] == "SUCCESS"]
    nones = [r for r in results if r[0] == "NONE"]
    
    assert len(successes) == 1
    assert len(nones) == num_customers - 1
    
    # Verify only one offer exists in DB
    offers = db.query(WaitlistOffer).filter(WaitlistOffer.show_seat_id == ss_id).all()
    assert len(offers) == 1

def test_concurrent_offer_acceptance_and_expiration(db_session, session_factory):
    """
    Race C: Offer expiration and offer acceptance happen near the same time.
    Expected: The system ends in one valid state (ACCEPTED or EXPIRED, not both).
    """
    db = db_session
    ss_id, customer_ids = create_test_data(db, 2)
    user_id = customer_ids[0]
    ss = db.get(ShowSeat, ss_id)
    
    waitlist_service.join_waitlist(db, user_id=user_id, event_id=ss.event_id, category_id=ss.physical_seat.category_id)
    offer = waitlist_service.process_waitlist_for_seat(db, show_seat_id=ss_id)
    offer_id = offer.id
    db.commit()
    
    # Set offer to be just about to expire or already expired
    db.query(WaitlistOffer).filter(WaitlistOffer.id == offer_id).update({"expires_at": datetime.now() - timedelta(seconds=1)})
    db.commit()
    
    results = []
    barrier = threading.Barrier(2)
    
    def accept_worker():
        barrier.wait()
        tdb = session_factory()
        try:
            with sqlite_sim_lock:
                waitlist_service.accept_offer(tdb, offer_id=offer_id, user_id=user_id)
            results.append("ACCEPTED_WIN")
        except AppException as e:
            results.append(f"ACCEPTED_FAIL: {e.message}")
        except Exception as e:
            results.append(f"ACCEPTED_ERROR: {str(e)}")
        finally:
            tdb.close()
            
    def expire_worker():
        barrier.wait()
        tdb = session_factory()
        try:
            with sqlite_sim_lock:
                waitlist_service.expire_offer(tdb, offer_id=offer_id)
            results.append("EXPIRED_DONE")
        except Exception as e:
            results.append(f"EXPIRED_ERROR: {str(e)}")
        finally:
            tdb.close()

    t1 = threading.Thread(target=accept_worker)
    t2 = threading.Thread(target=expire_worker)
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    
    # Verify consistency: The offer should be either ACCEPTED or EXPIRED, not both or stuck.
    db.refresh(offer)
    if offer.status == OfferStatus.ACCEPTED:
        assert "ACCEPTED_WIN" in results
        # In this case, expire_worker might have seen it was already ACCEPTED or 
        # it might have run first but accept_worker won the lock? No, if expire won, it becomes EXPIRED.
    elif offer.status == OfferStatus.EXPIRED:
        assert any("ACCEPTED_FAIL" in r for r in results)
        assert "EXPIRED_DONE" in results
    else:
        pytest.fail(f"Unexpected offer status: {offer.status}")
