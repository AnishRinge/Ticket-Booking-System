import logging
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.scheduler import start_scheduler, stop_scheduler
from app.core.worker import close_redis_pool
from app.core.exceptions import (
    AppException,
    app_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
)

# Setup logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

# Set all CORS enabled origins
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Exception handlers
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Custom 404 handler
@app.exception_handler(404)
async def custom_404_handler(request, __):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "message": "Resource Not Found",
            "errors": None,
            "status_code": status.HTTP_404_NOT_FOUND,
        },
    )

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.on_event("startup")
async def startup_event():
    logger.info("Application starting up...")
    await start_scheduler()

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutting down...")
    await stop_scheduler()
    await close_redis_pool()
