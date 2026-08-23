import pytest
from fastapi import status
from datetime import datetime, timedelta
from app.models.waitlist import WaitlistStatus, OfferStatus
from app.models.inventory import SeatStatus, ShowSeat
from app.models import User, UserRole
from app.models.venue import Venue, SeatCategory, Seat
from app.models.event import Event, EventCategoryPricing
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
    return token, user

def setup_event_context(db):
    v = Venue(name="Venue 1", address="Address 1")
    db.add(v)
    db.commit()
    c = SeatCategory(name="Premium")
    db.add(c)
    db.commit()
    e = Event(
        title="Event 1", 
        venue_id=v.id, 
        organiser_id=999, 
        start_time=datetime.now() + timedelta(days=1)
    )
    db.add(e)
    db.commit()
    p = EventCategoryPricing(event_id=e.id, category_id=c.id, price=1000.0)
    db.add(p)
    db.commit()
    return e, c

def setup_seat_for_event(db, event, category):
    s = Seat(venue_id=event.venue_id, category_id=category.id, row_identifier="A", seat_number=1)
    db.add(s)
    db.commit()
    ss = ShowSeat(event_id=event.id, physical_seat_id=s.id, status=SeatStatus.AVAILABLE)
    db.add(ss)
    db.commit()
    return ss

def test_owner_can_decline_active_offer(client, db_session):
    db = db_session
    token, user = get_token_for_role(db, UserRole.CUSTOMER)
    event, category = setup_event_context(db)
    show_seat = setup_seat_for_event(db, event, category)

    # Join waitlist
    client.post(
        f"/api/v1/events/{event.id}/waitlist",
        json={"category_id": category.id},
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Trigger offer
    from app.services.waitlist import waitlist_service
    offer = waitlist_service.process_waitlist_for_seat(db, show_seat_id=show_seat.id)
    assert offer is not None
    assert offer.status == OfferStatus.ACTIVE

    # Decline offer
    response = client.post(
        f"/api/v1/waitlist/offers/{offer.id}/decline",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == status.HTTP_200_OK
    
    # Verify status
    db.refresh(offer)
    assert offer.status == OfferStatus.DECLINED
    assert offer.waitlist_entry.status == WaitlistStatus.CANCELLED

def test_non_owner_cannot_decline_offer(client, db_session):
    db = db_session
    token1, user1 = get_token_for_role(db, UserRole.CUSTOMER, "c1@test.com")
    token2, user2 = get_token_for_role(db, UserRole.CUSTOMER, "c2@test.com")
    event, category = setup_event_context(db)
    show_seat = setup_seat_for_event(db, event, category)

    client.post(
        f"/api/v1/events/{event.id}/waitlist",
        json={"category_id": category.id},
        headers={"Authorization": f"Bearer {token1}"}
    )
    
    from app.services.waitlist import waitlist_service
    offer = waitlist_service.process_waitlist_for_seat(db, show_seat_id=show_seat.id)

    # Second user tries to decline it
    response = client.post(
        f"/api/v1/waitlist/offers/{offer.id}/decline",
        headers={"Authorization": f"Bearer {token2}"}
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN

def test_cannot_decline_already_declined_offer(client, db_session):
    db = db_session
    token, user = get_token_for_role(db, UserRole.CUSTOMER)
    event, category = setup_event_context(db)
    show_seat = setup_seat_for_event(db, event, category)

    client.post(
        f"/api/v1/events/{event.id}/waitlist",
        json={"category_id": category.id},
        headers={"Authorization": f"Bearer {token}"}
    )
    
    from app.services.waitlist import waitlist_service
    offer = waitlist_service.process_waitlist_for_seat(db, show_seat_id=show_seat.id)
    
    client.post(
        f"/api/v1/waitlist/offers/{offer.id}/decline",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Try declining again
    response = client.post(
        f"/api/v1/waitlist/offers/{offer.id}/decline",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST

def test_decline_promotes_next_customer(client, db_session):
    db = db_session
    token1, user1 = get_token_for_role(db, UserRole.CUSTOMER, "c1@test.com")
    token2, user2 = get_token_for_role(db, UserRole.CUSTOMER, "c2@test.com")
    event, category = setup_event_context(db)
    show_seat = setup_seat_for_event(db, event, category)

    client.post(f"/api/v1/events/{event.id}/waitlist", json={"category_id": category.id}, headers={"Authorization": f"Bearer {token1}"})
    client.post(f"/api/v1/events/{event.id}/waitlist", json={"category_id": category.id}, headers={"Authorization": f"Bearer {token2}"})
    
    from app.services.waitlist import waitlist_service
    offer1 = waitlist_service.process_waitlist_for_seat(db, show_seat_id=show_seat.id)
    assert offer1.waitlist_entry.user_id == user1.id

    # Decline offer 1
    client.post(f"/api/v1/waitlist/offers/{offer1.id}/decline", headers={"Authorization": f"Bearer {token1}"})
    
    # Verify offer 2 created for same seat
    from app.models.waitlist import WaitlistOffer
    offer2 = db.query(WaitlistOffer).filter(
        WaitlistOffer.show_seat_id == show_seat.id,
        WaitlistOffer.status == OfferStatus.ACTIVE
    ).first()
    
    assert offer2 is not None
    assert offer2.waitlist_entry.user_id == user2.id
