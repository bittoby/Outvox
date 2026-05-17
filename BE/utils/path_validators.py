"""
Path Parameter Validators
Validates phone numbers and other parameters passed in URL paths.
"""

from fastapi import HTTPException, Path
from utils.phone_validator import validate_us_phone_number
from core.exceptions import PhoneNumberValidationError


def validate_phone_path_param(phone_number: str = Path(..., description="Phone number in E.164 format")) -> str:
    """
    Validate and normalize phone number from path parameter.
    
    Args:
        phone_number: Phone number from URL path
        
    Returns:
        Normalized phone number in E.164 format
        
    Raises:
        HTTPException: If phone number is invalid
    """
    is_valid, normalized, error = validate_us_phone_number(phone_number)
    
    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "PHONE_VALIDATION_ERROR",
                "message": f"Invalid phone number in path: {error}",
                "phone_number": phone_number
            }
        )
    
    return normalized

