import logging
from arq.connections import RedisSettings
from arq import Retry
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.booking import Booking
from app.models.waitlist import WaitlistOffer
from app.services.ticket import ticket_service
from app.core.email import email_provider
from app.core import templates

logger = logging.getLogger(__name__)

async def startup(ctx):
    """
    Called on worker startup.
    Initialize shared resources here.
    """
    logger.info("Worker starting up...")

async def shutdown(ctx):
    """
    Called on worker shutdown.
    Clean up resources here.
    """
    logger.info("Worker shutting down...")

async def worker_test_task(ctx, message: str) -> str:
    """
    A simple test task to verify the worker infrastructure.
    """
    logger.info(f"Executing worker_test_task with message: {message}")
    return f"Test task completed: {message}"

async def send_booking_confirmation_job(ctx, booking_id: int):
    """
    Background job to generate QR ticket and send booking confirmation email.
    """
    db = SessionLocal()
    try:
        # Fetch booking with details
        booking = db.query(Booking).filter(Booking.id == booking_id).first()
        if not booking:
            logger.error(f"Booking {booking_id} not found for confirmation job")
            return

        # Prepare QR payload
        qr_payload = {
            "booking_id": booking.id,
            "booking_reference": booking.booking_reference,
            "event_id": booking.event_id,
            "user_id": booking.user_id,
            "seats": [bs.show_seat.physical_seat.seat_number for bs in booking.booking_seats]
        }
        
        # Generate QR
        qr_bytes = ticket_service.generate_qr_code(qr_payload)
        
        # Prepare Email
        event = booking.event
        seats = [f"{bs.show_seat.physical_seat.row}{bs.show_seat.physical_seat.seat_number}" for bs in booking.booking_seats]
        
        subject = f"Booking Confirmation - {event.title}"
        body_text = templates.get_booking_confirmation_body(
            event_title=event.title,
            event_date=event.start_time,
            venue_name=event.venue.name,
            booking_reference=booking.booking_reference,
            seats=seats,
            total_price=booking.total_price
        )
        
        attachments = [
            (f"ticket_{booking.booking_reference}.png", qr_bytes, "image/png")
        ]
        
        # Send Email
        success = email_provider.send_email(
            to_email=booking.user.email,
            subject=subject,
            body_text=body_text,
            attachments=attachments
        )
        
        if not success:
            raise Retry(defer=settings.WORKER_RETRY_DELAY_SECONDS)

    except Exception as e:
        if isinstance(e, Retry):
            raise
        logger.exception(f"Unexpected error in send_booking_confirmation_job: {str(e)}")
        raise Retry(defer=settings.WORKER_RETRY_DELAY_SECONDS)
    finally:
        db.close()

async def send_waitlist_offer_job(ctx, offer_id: int):
    """
    Background job to send waitlist offer notification email.
    """
    db = SessionLocal()
    try:
        # Fetch offer with details
        offer = db.query(WaitlistOffer).filter(WaitlistOffer.id == offer_id).first()
        if not offer:
            logger.error(f"Waitlist offer {offer_id} not found for notification job")
            return

        # Prepare Email
        event = offer.waitlist_entry.event
        category = offer.waitlist_entry.category
        
        subject = f"Special Offer: Seats Available for {event.title}"
        body_text = templates.get_waitlist_offer_body(
            event_title=event.title,
            venue_name=event.venue.name,
            category_name=category.name,
            expiry_time=offer.expires_at
        )
        
        # Send Email
        success = email_provider.send_email(
            to_email=offer.waitlist_entry.user.email,
            subject=subject,
            body_text=body_text
        )
        
        if not success:
            raise Retry(defer=settings.WORKER_RETRY_DELAY_SECONDS)

    except Exception as e:
        if isinstance(e, Retry):
            raise
        logger.exception(f"Unexpected error in send_waitlist_offer_job: {str(e)}")
        raise Retry(defer=settings.WORKER_RETRY_DELAY_SECONDS)
    finally:
        db.close()

class WorkerSettings:
    """
    Configuration for the ARQ worker.
    """
    functions = [worker_test_task, send_booking_confirmation_job, send_waitlist_offer_job]
    redis_settings = RedisSettings(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        database=settings.REDIS_DB
    )
    on_startup = startup
    on_shutdown = shutdown
    
    # Retry configuration
    max_retries = settings.WORKER_MAX_RETRIES
