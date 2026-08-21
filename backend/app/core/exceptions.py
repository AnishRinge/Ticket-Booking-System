from typing import Any, Dict, List, Optional, Union
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

class AppException(Exception):
    def __init__(
        self,
        status_code: int,
        message: str,
        errors: Optional[Union[List[Any], Dict[str, Any]]] = None,
    ):
        self.status_code = status_code
        self.message = message
        self.errors = errors

async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "message": exc.message,
            "errors": exc.errors,
            "status_code": exc.status_code,
        },
    )

async def validation_exception_handler(
    request: Request, exc: Union[RequestValidationError, ValidationError]
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "message": "Validation Error",
            "errors": exc.errors(),
            "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
        },
    )

async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # Log the full exception here in a real app
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "message": "Internal Server Error",
            "errors": str(exc) if hasattr(exc, "detail") else None,
            "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
        },
    )
