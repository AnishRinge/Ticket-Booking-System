import pytest
from datetime import datetime, timedelta
from fastapi import status
from sqlalchemy.orm import Session
from app.models import User, UserRole
from app.models.waitlist import WaitlistStatus, WaitlistEntry, WaitlistOffer, OfferStatus
from app.models.inventory import SeatStatus, ShowSeat
from app.services.waitlist import waitlist_service
from app.services.hold import hold_service
from app.core.security import get_password_hash, create_access_token

def get_token_for_user(db: Session, user: User):
    return create_access_token(subject=user.id)

def create_test_user(db: Session, email: str, role: UserRole = UserRole.CUSTOMER):
    user = User(
        email=email,
        hashed_password=get_password_hash("password123"),
        full_name=f"Test User {email}",
        role=role
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@pytest.fixture
def waitlist_setup(db_session):
    from tests.test_waitlist import setup_event_context, setup_seat_for_event
    event, category = setup_event_context(db_session)
    show_seat = setup_seat_for_event(db_session, event, category)
    return event, category, show_seat

def test_accept_offer_success(client, db_session, waitlist_setup):
    db = db_session
    event, category, show_seat = waitlist_setup
    
    # 1. User joins waitlist
    user = create_test_user(db, "customer@example.com")
    token = get_token_for_user(db, user)
    waitlist_service.join_waitlist(db, user_id=user.id, event_id=event.id, category_id=category.id)
    
    # 2. Offer is created
    offer = waitlist_service.process_waitlist_for_seat(db, show_seat_id=show_seat.id)
    assert offer is not None
    
    # 3. User accepts offer
    response = client.post(
        f"/api/v1/waitlist/offers/{offer.id}/accept",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()["data"]
    assert data["status"] == "CONFIRMED"
    
    # 4. Verify states
    db.refresh(offer)
    db.refresh(show_seat)
    db.refresh(offer.waitlist_entry)
    assert offer.status == OfferStatus.ACCEPTED
    assert show_seat.status == SeatStatus.BOOKED
    assert offer.waitlist_entry.status == WaitlistStatus.ACCEPTED

def test_accept_offer_wrong_user(client, db_session, waitlist_setup):
    db = db_session
    event, category, show_seat = waitlist_setup
    
    user1 = create_test_user(db, "c1@example.com")
    user2 = create_test_user(db, "c2@example.com")
    token2 = get_token_for_user(db, user2)
    
    waitlist_service.join_waitlist(db, user_id=user1.id, event_id=event.id, category_id=category.id)
    offer = waitlist_service.process_waitlist_for_seat(db, show_seat_id=show_seat.id)
    
    response = client.post(
        f"/api/v1/waitlist/offers/{offer.id}/accept",
        headers={"Authorization": f"Bearer {token2}"}
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN

def test_accept_expired_offer(client, db_session, waitlist_setup):
    db = db_session
    event, category, show_seat = waitlist_setup
    
    user = create_test_user(db, "expired@example.com")
    token = get_token_for_user(db, user)
    waitlist_service.join_waitlist(db, user_id=user.id, event_id=event.id, category_id=category.id)
    
    offer = waitlist_service.process_waitlist_for_seat(db, show_seat_id=show_seat.id)
    # Force expire
    offer.expires_at = datetime.now() - timedelta(seconds=1)
    db.commit()
    
    response = client.post(
        f"/api/v1/waitlist/offers/{offer.id}/accept",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "expired" in response.json()["message"].lower()

def test_offer_expiration_and_promotion(db_session, waitlist_setup):
    db = db_session
    event, category, show_seat = waitlist_setup
    
    # 2 Users join waitlist
    user1 = create_test_user(db, "u1@example.com")
    user2 = create_test_user(db, "u2@example.com")
    
    waitlist_service.join_waitlist(db, user_id=user1.id, event_id=event.id, category_id=category.id)
    waitlist_service.join_waitlist(db, user_id=user2.id, event_id=event.id, category_id=category.id)
    
    # Process first offer
    offer1 = waitlist_service.process_waitlist_for_seat(db, show_seat_id=show_seat.id)
    assert offer1.waitlist_entry.user_id == user1.id
    
    # Force expire first offer
    offer1.expires_at = datetime.now() - timedelta(seconds=1)
    db.commit()
    
    # Run cleanup
    count = waitlist_service.cleanup_expired_offers(db)
    assert count == 1
    
    # Verify offer1 is expired and user1 entry is expired
    db.refresh(offer1)
    assert offer1.status == OfferStatus.EXPIRED
    assert offer1.waitlist_entry.status == WaitlistStatus.EXPIRED
    
    # Verify new offer created for user2
    offer2 = db.query(WaitlistOffer).filter(WaitlistOffer.status == OfferStatus.ACTIVE).first()
    assert offer2 is not None
    assert offer2.waitlist_entry.user_id == user2.id
    assert offer2.show_seat_id == show_seat.id

def test_expiration_idempotency(db_session, waitlist_setup):
    db = db_session
    event, category, show_seat = waitlist_setup
    
    user = create_test_user(db, "idem@example.com")
    waitlist_service.join_waitlist(db, user_id=user.id, event_id=event.id, category_id=category.id)
    
    offer = waitlist_service.process_waitlist_for_seat(db, show_seat_id=show_seat.id)
    offer.expires_at = datetime.now() - timedelta(seconds=1)
    db.commit()
    
    # Expire first time
    waitlist_service.expire_offer(db, offer_id=offer.id)
    db.refresh(offer)
    assert offer.status == OfferStatus.EXPIRED
    
    # Expire second time
    waitlist_service.expire_offer(db, offer_id=offer.id)
    # Should not raise error and should remain expired
    assert offer.status == OfferStatus.EXPIRED

def test_hold_respects_waitlist_offer(client, db_session, waitlist_setup):
    db = db_session
    event, category, show_seat = waitlist_setup
    
    # User 1 joins waitlist and gets an offer
    user1 = create_test_user(db, "waitlisted@example.com")
    waitlist_service.join_waitlist(db, user_id=user1.id, event_id=event.id, category_id=category.id)
    waitlist_service.process_waitlist_for_seat(db, show_seat_id=show_seat.id)
    
    # User 2 tries to hold the same seat
    user2 = create_test_user(db, "opportunist@example.com")
    token2 = get_token_for_user(db, user2)
    
    response = client.post(
        "/api/v1/holds",
        json={"show_seat_id": show_seat.id},
        headers={"Authorization": f"Bearer {token2}"}
    )
    
    assert response.status_code == status.HTTP_409_CONFLICT
    assert "reserved for waitlist" in response.json()["message"].lower()
