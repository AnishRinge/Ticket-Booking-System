from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.deps import get_db

router = APIRouter()

@router.get("/health", response_model=dict[str, str])
def health_check() -> Any:
    """
    Check if the application is running.
    """
    return {"status": "ok"}

@router.get("/ready", response_model=dict[str, str])
def readiness_check(db: Session = Depends(get_db)) -> Any:
    """
    Check if the database is reachable.
    """
    try:
        # Try to execute a simple query to verify database connectivity
        db.execute(text("SELECT 1"))
        return {"status": "ready", "database": "connected"}
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Database not reachable: {str(e)}"
        )
