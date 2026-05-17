"""
Standardized API Response Models
Provides consistent response structures across all endpoints.
"""

from typing import Optional, Any, Dict
from pydantic import BaseModel
from datetime import datetime


class APIResponse(BaseModel):
    """Standard API response wrapper."""
    success: bool = True
    message: Optional[str] = None
    data: Optional[Any] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    timestamp: datetime = datetime.now()


class ErrorResponse(BaseModel):
    """Standard error response."""
    success: bool = False
    error: str
    error_code: str
    details: Optional[Any] = None
    timestamp: datetime = datetime.now()


class PaginatedResponse(BaseModel):
    """Paginated response for list endpoints."""
    success: bool = True
    data: list
    total: int
    page: int = 1
    page_size: int = 50
    total_pages: int
    
    @classmethod
    def create(cls, data: list, total: int, page: int = 1, page_size: int = 50):
        """Create paginated response."""
        total_pages = (total + page_size - 1) // page_size
        return cls(
            data=data,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )


def success_response(message: str = None, data: Any = None) -> Dict:
    """Create a success response."""
    return {
        "success": True,
        "message": message,
        "data": data,
        "timestamp": datetime.now().isoformat()
    }


def error_response(error: str, error_code: str = "ERROR", details: Any = None) -> Dict:
    """Create an error response."""
    return {
        "success": False,
        "error": error,
        "error_code": error_code,
        "details": details,
        "timestamp": datetime.now().isoformat()
    }

