from typing import List
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Ticket Booking System"
    API_V1_STR: str = "/api/v1"
    
    # Environment
    ENVIRONMENT: str = "development"
    
    # Database Configuration
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "password"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "ticket_booking"
    DATABASE_URL: str | None = None
    
    def get_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | List[str]) -> List[str] | str:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # Security
    SECRET_KEY: str = "your-super-secret-key-that-is-at-least-32-characters-long"  # Should be overridden in .env
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    SEAT_HOLD_TTL_SECONDS: int = 600  # 10 minutes
    WAITLIST_OFFER_TTL_SECONDS: int = 900  # 15 minutes
    CLEANUP_INTERVAL_SECONDS: int = 60  # 1 minute

    # Redis / ARQ
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_URL: str | None = None

    def get_redis_url(self) -> str:
        if self.REDIS_URL:
            return self.REDIS_URL
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # Email Configuration
    EMAIL_ENABLED: bool = False
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_TLS: bool = False
    SMTP_SSL: bool = False
    EMAILS_FROM_EMAIL: str = "noreply@ticketbooking.com"
    EMAILS_FROM_NAME: str = "Ticket Booking System"

    # Worker Configuration
    WORKER_RETRY_DELAY_SECONDS: int = 5
    WORKER_MAX_RETRIES: int = 3

    # Logging
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True
    )

settings = Settings()
