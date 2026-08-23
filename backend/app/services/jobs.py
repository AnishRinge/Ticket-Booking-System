import logging
from app.core.worker import get_redis_pool

logger = logging.getLogger(__name__)

class JobService:
    """
    Abstractions for enqueueing background jobs.
    Later phases will add specific methods like enqueue_email.
    """
    
    async def enqueue_test_job(self, message: str):
        """
        Enqueues a test task.
        """
        redis = await get_redis_pool()
        job = await redis.enqueue_job("worker_test_task", message)
        logger.info(f"Enqueued test_job with id: {job.job_id}")
        return job

    async def enqueue_booking_confirmation(self, booking_id: int):
        """
        Enqueues a booking confirmation job.
        """
        redis = await get_redis_pool()
        job = await redis.enqueue_job("send_booking_confirmation_job", booking_id)
        logger.info(f"Enqueued booking_confirmation job for booking {booking_id}, job_id: {job.job_id}")
        return job

    async def enqueue_waitlist_offer(self, offer_id: int):
        """
        Enqueues a waitlist offer notification job.
        """
        redis = await get_redis_pool()
        job = await redis.enqueue_job("send_waitlist_offer_job", offer_id)
        logger.info(f"Enqueued waitlist_offer job for offer {offer_id}, job_id: {job.job_id}")
        return job

job_service = JobService()
