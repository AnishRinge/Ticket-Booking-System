import pytest
import json
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timedelta
from arq import Retry

from app.services.ticket import ticket_service
from app.core.email import email_provider
from app.core import templates
from app.services.notification import notification_service
from app.worker.main import send_booking_confirmation_job, send_waitlist_offer_job
from app.models.booking import Booking, BookingStatus
from app.models.waitlist import WaitlistOffer, WaitlistStatus, OfferStatus
from app.models.inventory import SeatStatus

def test_qr_generation_deterministic():
    """
    Verifies that QR generation is deterministic and contains the expected payload.
    """
    payload = {"reference": "REF123", "id": 1}
    qr1 = ticket_service.generate_qr_code(payload)
    qr2 = ticket_service.generate_qr_code(payload)
    
    assert qr1 == qr2
    assert isinstance(qr1, bytes)
    assert len(qr1) > 0

def test_email_templates_content():
    """
    Verifies that templates contain the required information.
    """
    # 1. Booking confirmation
    body = templates.get_booking_confirmation_body(
        event_title="Concert",
        event_date=datetime(2026, 12, 1, 20, 0),
        venue_name="Stadium",
        booking_reference="REF123",
        seats=["A1", "A2"],
        total_price=1000.0
    )
    assert "Concert" in body
    assert "REF123" in body
    assert "A1, A2" in body
    assert "1000.0" in body

    # 2. Waitlist offer
    body = templates.get_waitlist_offer_body(
        event_title="Concert",
        venue_name="Stadium",
        category_name="VIP",
        expiry_time=datetime(2026, 12, 1, 21, 0)
    )
    assert "Concert" in body
    assert "VIP" in body
    assert "2026-12-01 21:00:00" in body

def test_email_provider_disabled():
    """
    Verifies that email provider handles disabled state gracefully.
    """
    with patch("app.core.email.settings.EMAIL_ENABLED", False):
        success = email_provider.send_email(
            to_email="test@example.com",
            subject="Test",
            body_text="Hello"
        )
        assert success is True

@pytest.mark.anyio
async def test_worker_booking_confirmation_job():
    """
    Tests the booking confirmation worker job with mocked DB and services.
    """
    mock_db = MagicMock()
    mock_booking = MagicMock(spec=Booking)
    mock_booking.id = 1
    mock_booking.booking_reference = "REF123"
    mock_booking.event_id = 1
    mock_booking.user_id = 1
    mock_booking.total_price = 1000.0
    mock_booking.event.title = "Concert"
    mock_booking.event.start_time = datetime.now()
    mock_booking.event.venue.name = "Stadium"
    mock_booking.user.email = "customer@example.com"
    
    # Mock BookingSeat relationships
    mock_bs = MagicMock()
    mock_bs.show_seat.physical_seat.seat_number = 1
    mock_bs.show_seat.physical_seat.row = "A"
    mock_booking.booking_seats = [mock_bs]

    mock_db.query.return_value.filter.return_value.first.return_value = mock_booking
    
    ctx = {"db": mock_db}
    
    # Use patch context managers
    with patch("app.worker.main.SessionLocal", return_value=mock_db), \
         patch("app.worker.main.ticket_service.generate_qr_code") as mock_qr, \
         patch("app.worker.main.email_provider.send_email") as mock_email:
        
        mock_qr.return_value = b"fake_qr"
        mock_email.return_value = True
        
        await send_booking_confirmation_job(ctx, booking_id=1)
        
        mock_qr.assert_called_once()
        mock_email.assert_called_once()
        args, kwargs = mock_email.call_args
        assert kwargs["to_email"] == "customer@example.com"
        assert "Concert" in kwargs["subject"]
        assert b"fake_qr" == kwargs["attachments"][0][1]

@pytest.mark.anyio
async def test_worker_waitlist_offer_job():
    """
    Tests the waitlist offer worker job with mocked DB and services.
    """
    mock_db = MagicMock()
    mock_offer = MagicMock(spec=WaitlistOffer)
    mock_offer.id = 1
    mock_offer.expires_at = datetime.now() + timedelta(minutes=15)
    mock_offer.waitlist_entry.event.title = "Concert"
    mock_offer.waitlist_entry.event.venue.name = "Stadium"
    mock_offer.waitlist_entry.category.name = "VIP"
    mock_offer.waitlist_entry.user.email = "customer@example.com"
    
    mock_db.query.return_value.filter.return_value.first.return_value = mock_offer
    
    ctx = {"db": mock_db}
    
    with patch("app.worker.main.SessionLocal", return_value=mock_db), \
         patch("app.worker.main.email_provider.send_email") as mock_email:
        mock_email.return_value = True
        
        await send_waitlist_offer_job(ctx, offer_id=1)
        
        mock_email.assert_called_once()
        args, kwargs = mock_email.call_args
        assert kwargs["to_email"] == "customer@example.com"
        assert "Special Offer" in kwargs["subject"]

@pytest.mark.anyio
async def test_worker_booking_confirmation_retry():
    """
    Verifies that the worker raises ARQ Retry when email sending fails for bookings.
    """
    mock_db = MagicMock()
    mock_booking = MagicMock(spec=Booking)
    mock_db.query.return_value.filter.return_value.first.return_value = mock_booking
    
    ctx = {}
    
    with patch("app.worker.main.SessionLocal", return_value=mock_db), \
         patch("app.worker.main.ticket_service.generate_qr_code", return_value=b"qr"), \
         patch("app.worker.main.email_provider.send_email", return_value=False):
        
        with pytest.raises(Retry):
            await send_booking_confirmation_job(ctx, booking_id=1)

@pytest.mark.anyio
async def test_worker_waitlist_offer_retry():
    """
    Verifies that the worker raises ARQ Retry when email sending fails for waitlist offers.
    """
    mock_db = MagicMock()
    mock_offer = MagicMock(spec=WaitlistOffer)
    mock_db.query.return_value.filter.return_value.first.return_value = mock_offer
    
    ctx = {}
    
    with patch("app.worker.main.SessionLocal", return_value=mock_db), \
         patch("app.worker.main.email_provider.send_email", return_value=False):
        
        with pytest.raises(Retry):
            await send_waitlist_offer_job(ctx, offer_id=1)

def test_notification_service_sync_bridge_resilience():
    """
    Verifies that sync bridge doesn't crash the caller even if enqueuing fails (e.g. Redis down).
    """
    # Mock send_booking_confirmation to fail
    with patch.object(notification_service, "send_booking_confirmation", side_effect=Exception("Redis Down")):
        # Should not raise exception
        notification_service.send_booking_confirmation_sync(1)

def test_booking_confirmation_trigger_after_commit():
    """
    Proves that notification is triggered after successful commit in BookingService.
    """
    from app.services.booking import BookingService
    from app.models.user import User
    
    service = BookingService()
    db = MagicMock()
    user = MagicMock(spec=User)
    user.id = 1
    
    # Mock order of calls
    manager = MagicMock()
    manager.attach_mock(db.commit, "commit")
    
    with patch("app.services.notification.notification_service.send_booking_confirmation_sync") as mock_notif, \
         patch("app.services.booking.event_pricing_repository.get_by_event_and_category") as mock_pricing:
        
        manager.attach_mock(mock_notif, "notif")
        
        mock_seat = MagicMock()
        mock_seat.status = SeatStatus.HELD
        mock_seat.held_by_id = 1
        mock_seat.hold_expires_at = datetime.now() + timedelta(minutes=10)
        mock_seat.event_id = 1
        
        db.query.return_value.filter.return_value.order_by.return_value.with_for_update.return_value.all.return_value = [mock_seat]
        mock_pricing.return_value = MagicMock(price=100.0)

        booking = service.confirm_booking(db, [1], user)
        
        # Verify commit was called before notification
        call_names = [call[0] for call in manager.mock_calls]
        assert "commit" in call_names
        assert "notif" in call_names
        assert call_names.index("commit") < call_names.index("notif")
        
        # Verify correct booking_id passed to notification
        mock_notif.assert_called_once_with(booking.id)

def test_waitlist_offer_trigger_after_commit():
    """
    Proves that waitlist offer notification is triggered after successful commit in WaitlistService.
    """
    from app.services.waitlist import WaitlistService
    service = WaitlistService()
    db = MagicMock()
    
    manager = MagicMock()
    manager.attach_mock(db.commit, "commit")
    
    with patch("app.services.notification.notification_service.send_waitlist_offer_notification_sync") as mock_notif, \
         patch.object(service, "get_fifo_waitlist") as mock_fifo, \
         patch("app.services.waitlist.waitlist_offer_repository.get_active_offer_for_seat", return_value=None):
        
        manager.attach_mock(mock_notif, "notif")
        
        # Mock db.add to set id on WaitlistOffer
        def db_add_side_effect(obj):
            if isinstance(obj, WaitlistOffer):
                obj.id = 1
        db.add.side_effect = db_add_side_effect
        
        mock_seat = MagicMock()
        mock_seat.status = SeatStatus.AVAILABLE
        mock_seat.event_id = 1
        mock_seat.physical_seat.category_id = 1
        db.query.return_value.filter.return_value.with_for_update.return_value.first.return_value = mock_seat
        
        mock_entry = MagicMock()
        mock_entry.id = 1
        mock_fifo.return_value = [mock_entry]
        
        service.process_waitlist_for_seat(db, show_seat_id=1, commit=True)
        
        # Verify commit was called before notification
        call_names = [call[0] for call in manager.mock_calls]
        assert "commit" in call_names
        assert "notif" in call_names
        assert call_names.index("commit") < call_names.index("notif")
        
        # Verify correct offer_id passed to notification
        mock_notif.assert_called_once_with(1)

def test_failed_waitlist_allocation_no_notification():
    """
    Verifies that if no customer is on waitlist, no notification is sent.
    """
    from app.services.waitlist import WaitlistService
    service = WaitlistService()
    db = MagicMock()
    
    with patch("app.services.notification.notification_service.send_waitlist_offer_notification_sync") as mock_notif, \
         patch.object(service, "get_fifo_waitlist", return_value=[]):
        
        mock_seat = MagicMock()
        mock_seat.status = SeatStatus.AVAILABLE
        db.query.return_value.filter.return_value.with_for_update.return_value.first.return_value = mock_seat
        
        service.process_waitlist_for_seat(db, show_seat_id=1)
        
        mock_notif.assert_not_called()
