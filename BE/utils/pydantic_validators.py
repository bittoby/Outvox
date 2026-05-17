"""
Pydantic Validators for Phone Numbers
Provides automatic validation and normalization for phone number fields.
"""

from typing import Any
from pydantic import field_validator
from utils.phone_validator import validate_us_phone_number
from core.exceptions import PhoneNumberValidationError


def validate_and_normalize_phone(value: Any) -> str:
    """
    Validate and normalize phone number to E.164 format.
    
    Args:
        value: Phone number in any format
        
    Returns:
        Normalized phone number in E.164 format (+1XXXXXXXXXX)
        
    Raises:
        PhoneNumberValidationError: If phone number is invalid
    """
    if value is None:
        raise PhoneNumberValidationError("Phone number is required")
    
    if not isinstance(value, str):
        value = str(value)
    
    # Validate and normalize
    is_valid, normalized, error = validate_us_phone_number(value)
    
    if not is_valid:
        raise PhoneNumberValidationError(error or "Invalid phone number format")
    
    return normalized


# Pydantic field validator for phone numbers
phone_validator = field_validator('phone_number', mode='before')(validate_and_normalize_phone)

