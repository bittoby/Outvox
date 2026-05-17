"""
Custom Exceptions
Standardized exception classes for better error handling.
"""

from typing import Optional, Any, Dict


class BaseAPIException(Exception):
    """Base exception for all API errors."""
    
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: Optional[str] = None,
        details: Optional[Any] = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or self.__class__.__name__
        self.details = details
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for JSON serialization."""
        result = {
            "error_code": self.error_code,
            "message": self.message,
            "status_code": self.status_code
        }
        if self.details:
            result["details"] = self.details
        return result


class DatabaseError(BaseAPIException):
    """Database operation failed."""
    def __init__(self, message: str = "Database operation failed", details: Optional[Any] = None):
        super().__init__(message, status_code=500, error_code="DATABASE_ERROR", details=details)


class ResourceNotFoundError(BaseAPIException):
    """Requested resource not found."""
    def __init__(self, resource: str = "Resource", resource_id: Any = None):
        message = f"{resource} not found"
        if resource_id:
            message += f": {resource_id}"
        super().__init__(message, status_code=404, error_code="RESOURCE_NOT_FOUND")


class ValidationError(BaseAPIException):
    """Input validation failed."""
    def __init__(self, message: str = "Validation failed", details: Optional[Any] = None):
        super().__init__(message, status_code=400, error_code="VALIDATION_ERROR", details=details)


class InsufficientCapacityError(BaseAPIException):
    """Insufficient capacity to process request."""
    def __init__(self, message: str = "Insufficient capacity"):
        super().__init__(message, status_code=503, error_code="INSUFFICIENT_CAPACITY")


class TwilioError(BaseAPIException):
    """Twilio API error."""
    def __init__(self, message: str = "Twilio operation failed", details: Optional[Any] = None):
        super().__init__(message, status_code=500, error_code="TWILIO_ERROR", details=details)


class DNCViolationError(BaseAPIException):
    """Attempt to contact a number on Do Not Call list."""
    def __init__(self, phone_number: str):
        super().__init__(
            f"Cannot contact {phone_number}: On Do Not Call list",
            status_code=403,
            error_code="DNC_VIOLATION"
        )


class RateLimitError(BaseAPIException):
    """Rate limit exceeded."""
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, status_code=429, error_code="RATE_LIMIT_EXCEEDED")


class CampaignError(BaseAPIException):
    """Campaign operation failed."""
    def __init__(self, message: str = "Campaign operation failed", details: Optional[Any] = None):
        super().__init__(message, status_code=400, error_code="CAMPAIGN_ERROR", details=details)


class PhoneNumberValidationError(ValidationError):
    """Phone number validation failed."""
    def __init__(self, message: str = "Invalid phone number format", phone_number: Optional[str] = None):
        details = {"phone_number": phone_number} if phone_number else None
        super().__init__(message, details=details)
        self.error_code = "PHONE_VALIDATION_ERROR"


class StoreNotFoundError(ResourceNotFoundError):
    """Store not found."""
    def __init__(self, store_id: Any = None):
        super().__init__("Store", store_id)
        self.error_code = "STORE_NOT_FOUND"


class LeadNotFoundError(ResourceNotFoundError):
    """Lead not found."""
    def __init__(self, lead_id: Any = None):
        super().__init__("Lead", lead_id)
        self.error_code = "LEAD_NOT_FOUND"


class PhoneNumberNotFoundError(ResourceNotFoundError):
    """Phone number not found."""
    def __init__(self, phone_number: Optional[str] = None):
        message = "Phone number not found"
        if phone_number:
            message += f": {phone_number}"
        super().__init__(message, status_code=404, error_code="PHONE_NUMBER_NOT_FOUND")

