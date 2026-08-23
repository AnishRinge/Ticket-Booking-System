import logging
from typing import Optional
from arq import create_pool
from arq.connections import RedisSettings, ArqRedis
from app.core.config import settings

logger = logging.getLogger(__name__)

_redis_pool: Optional[ArqRedis] = None

async def get_redis_pool() -> ArqRedis:
    """
    Returns a shared ARQ Redis pool instance.
    Initializes it if it doesn't exist.
    """
    global _redis_pool
    if _redis_pool is None:
        logger.info("Initializing ARQ Redis pool...")
        _redis_pool = await create_pool(
            RedisSettings(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                database=settings.REDIS_DB
            )
        )
    return _redis_pool

async def close_redis_pool():
    """
    Closes the ARQ Redis pool.
    """
    global _redis_pool
    if _redis_pool:
        logger.info("Closing ARQ Redis pool...")
        await _redis_pool.close()
        _redis_pool = None
