"""
Global Exception Handler
Centralized exception handling for FastAPI applications.
"""

import logging
import traceback
from typing import Optional, Any
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from .exceptions import BaseAPIException

logger = logging.getLogger(__name__)


def create_error_response(
    error_code: str,
    message: str,
    status_code: int = 500,
    details: Optional[Any] = None,
    request: Optional[Request] = None
) -> JSONResponse:
    """
    Create standardized error response.
    
    Args:
        error_code: Error code identifier
        message: Human-readable error message
        status_code: HTTP status code
        details: Additional error details
        request: FastAPI request object (for logging context)
        
    Returns:
        JSONResponse with standardized error format
    """
    error_data = {
        "error": {
            "code": error_code,
            "message": message,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    }
    
    # Add details if provided
    if details:
        error_data["error"]["details"] = details
    
    # Log error with context
    if request:
        logger.error(
            f"Error {error_code}: {message}",
            extra={
                "error_code": error_code,
                "status_code": status_code,
                "path": request.url.path,
                "method": request.method,
                "details": details
            }
        )
    else:
        logger.error(f"Error {error_code}: {message}")
    
    return JSONResponse(
        status_code=status_code,
        content=error_data
    )


def setup_exception_handlers(app: FastAPI):
    """
    Setup global exception handlers for FastAPI app.
    
    Args:
        app: FastAPI application instance
    """
    
    @app.exception_handler(BaseAPIException)
    async def base_api_exception_handler(request: Request, exc: BaseAPIException):
        """Handle custom API exceptions."""
        return create_error_response(
            error_code=exc.error_code,
            message=exc.message,
            status_code=exc.status_code,
            details=exc.details,
            request=request
        )
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle FastAPI HTTPExceptions and standardize format."""
        # Extract error code from detail if it's a dict, otherwise use status code
        if isinstance(exc.detail, dict):
            error_code = exc.detail.get("error_code", f"HTTP_{exc.status_code}")
            message = exc.detail.get("message", exc.detail.get("detail", str(exc.detail)))
            details = exc.detail.get("details")
        else:
            error_code = f"HTTP_{exc.status_code}"
            message = str(exc.detail) if exc.detail else "An error occurred"
            details = None
        
        return create_error_response(
            error_code=error_code,
            message=message,
            status_code=exc.status_code,
            details=details,
            request=request
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle Pydantic validation errors."""
        errors = exc.errors()
        error_messages = []
        for error in errors:
            field = ".".join(str(loc) for loc in error["loc"])
            message = error["msg"]
            error_messages.append(f"{field}: {message}")
        
        # Log detailed validation errors for debugging
        logger.error(
            f"Validation error on {request.method} {request.url.path}: {error_messages}",
            extra={
                "validation_errors": errors,
                "path": request.url.path,
                "method": request.method,
                "query_params": dict(request.query_params)
            }
        )
        
        return create_error_response(
            error_code="VALIDATION_ERROR",
            message="Request validation failed",
            status_code=422,
            details={"validation_errors": error_messages},
            request=request
        )
    
    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        """Handle unexpected exceptions."""
        # Log full traceback for debugging
        logger.error(
            f"Unexpected error: {type(exc).__name__}: {str(exc)}",
            exc_info=True,
            extra={
                "path": request.url.path,
                "method": request.method,
                "exception_type": type(exc).__name__
            }
        )
        
        # Don't expose internal error details in production
        # In development, you might want to include traceback
        return create_error_response(
            error_code="INTERNAL_SERVER_ERROR",
            message="An unexpected error occurred",
            status_code=500,
            details=None,  # Don't expose internal details
            request=request
        )

