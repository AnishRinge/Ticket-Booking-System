import logging
from app.services.jobs import job_service

logger = logging.getLogger(__name__)

import asyncio

class NotificationService:
    """
    High-level service for handling notifications.
    It prepares data and enqueues background jobs.
    """
    
    async def send_booking_confirmation(self, booking_id: int):
        """
        Triggers a booking confirmation notification.
        """
        try:
            logger.info(f"Triggering booking confirmation for booking_id: {booking_id}")
            await job_service.enqueue_booking_confirmation(booking_id)
        except Exception as e:
            logger.error(f"Error enqueuing booking confirmation for {booking_id}: {e}")

    def send_booking_confirmation_sync(self, booking_id: int):
        """
        Sync bridge for booking confirmation.
        Ensures that failures in enqueuing don't rollback the business transaction,
        but logs them for visibility.
        """
        try:
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                # We are in an async context (FastAPI)
                loop.create_task(self.send_booking_confirmation(booking_id))
            else:
                # We are in a sync context (tests/CLI)
                asyncio.run(self.send_booking_confirmation(booking_id))
        except Exception as e:
            logger.error(f"Failed to enqueue booking confirmation for {booking_id}: {e}")

    async def send_waitlist_offer_notification(self, offer_id: int):
        """
        Triggers a waitlist offer notification.
        """
        try:
            logger.info(f"Triggering waitlist offer notification for offer_id: {offer_id}")
            await job_service.enqueue_waitlist_offer(offer_id)
        except Exception as e:
            logger.error(f"Error enqueuing waitlist offer notification for {offer_id}: {e}")

    def send_waitlist_offer_notification_sync(self, offer_id: int):
        """
        Sync bridge for waitlist offer.
        Ensures that failures in enqueuing don't rollback the business transaction,
        but logs them for visibility.
        """
        try:
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                # We are in an async context (FastAPI)
                loop.create_task(self.send_waitlist_offer_notification(offer_id))
            else:
                # We are in a sync context (tests/CLI)
                asyncio.run(self.send_waitlist_offer_notification(offer_id))
        except Exception as e:
            logger.error(f"Failed to enqueue waitlist offer notification for {offer_id}: {e}")

notification_service = NotificationService()
