"""
Phone Number Management Router (Refactored)
Handles Twilio phone number operations using service layer.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Path, Body
from pydantic import BaseModel

from models import PhoneNumberCreate
from services.phone_number_service import get_phone_number_service, PhoneNumberService
from core.exceptions import ResourceNotFoundError, ValidationError

# Router instance
router = APIRouter(prefix="/api/phone-numbers", tags=["phone_numbers"])


# Dependency injection
def get_service() -> PhoneNumberService:
    """Dependency injection for PhoneNumberService."""
    return get_phone_number_service()


# Request models
class AssignStoreRequest(BaseModel):
    store_id: Optional[int] = None


# ============================================================================
# GET ENDPOINTS
# ============================================================================

@router.get("", summary="Get all phone numbers")
async def get_all_phone_numbers(
    store_id: Optional[int] = None,
    service: PhoneNumberService = Depends(get_service)
):
    """Get all phone numbers with optional store filter."""
    # Let exceptions bubble up to global handler
    return service.get_all_phone_numbers(store_id=store_id)


@router.get("/available", summary="Get available Twilio numbers")
async def get_available_twilio_numbers(
    store_id: Optional[int] = None,
    for_manual_dial: Optional[str] = None,
    service: PhoneNumberService = Depends(get_service)
):
    """
    Get Twilio numbers available for making calls/SMS.
    
    If for_manual_dial=true, returns a single phone_number string (first available).
    Otherwise, returns a list of available_numbers.
    """
    result = service.get_available_numbers(store_id=store_id)
    
    # If for_manual_dial is requested, return single phone_number format
    if for_manual_dial and for_manual_dial.lower() == 'true':
        available_numbers = result.get('available_numbers', [])
        if available_numbers:
            # Return first available number in the format expected by twilio_service
            return {
                "phone_number": available_numbers[0].get('phone_number'),
                "number_id": available_numbers[0].get('number_id'),
                "store_id": available_numbers[0].get('store_id')
            }
        else:
            # No numbers available - return None in phone_number field
            return {
                "phone_number": None,
                "number_id": None,
                "store_id": None
            }
    
    # Default: return list format
    return result


@router.get("/stats", summary="Get phone number statistics")
async def get_phone_number_stats(
    service: PhoneNumberService = Depends(get_service)
):
    """Get overall statistics for all phone numbers."""
    # Let exceptions bubble up to global handler
    return service.get_statistics()


# ============================================================================
# POST/PUT ENDPOINTS
# ============================================================================

@router.put("/{phone_number_id}/assign-store", summary="Assign phone number to store")
async def assign_phone_to_store(
    phone_number_id: int,
    request: AssignStoreRequest,
    service: PhoneNumberService = Depends(get_service)
):
    """Assign a phone number to a specific store (or unassign if store_id is null)."""
    # Let exceptions bubble up to global handler
    return service.assign_to_store(phone_number_id, request.store_id)


@router.put("/{phone_number}/activate", summary="Activate phone number")
async def activate_phone_number(
    phone_number: str = Path(..., description="Phone number (will be normalized to E.164 format)"),
    service: PhoneNumberService = Depends(get_service)
):
    """Activate a phone number."""
    # Validate and normalize phone number from path
    from utils.phone_validator import validate_us_phone_number
    is_valid, normalized, error = validate_us_phone_number(phone_number)
    if not is_valid:
        raise ValidationError(f"Invalid phone number: {error}")
    phone_number = normalized
    
    # Get phone number by phone string
    phone = service.repository.get_by_phone(phone_number)
    if not phone:
        raise ResourceNotFoundError("Phone Number", phone_number)
    
    # Let exceptions bubble up to global handler
    return service.update_active_status(phone['number_id'], True)


@router.put("/{phone_number}/deactivate", summary="Deactivate phone number")
async def deactivate_phone_number(
    phone_number: str = Path(..., description="Phone number (will be normalized to E.164 format)"),
    service: PhoneNumberService = Depends(get_service)
):
    """Deactivate a phone number."""
    # Validate and normalize phone number from path
    from utils.phone_validator import validate_us_phone_number
    is_valid, normalized, error = validate_us_phone_number(phone_number)
    if not is_valid:
        raise ValidationError(f"Invalid phone number: {error}")
    phone_number = normalized
    
    # Get phone number by phone string
    phone = service.repository.get_by_phone(phone_number)
    if not phone:
        raise ResourceNotFoundError("Phone Number", phone_number)
    
    # Let exceptions bubble up to global handler
    return service.update_active_status(phone['number_id'], False)


@router.get("/check/{phone_number}", summary="Check if Twilio number exists and is active")
async def check_twilio_number(
    phone_number: str = Path(..., description="Phone number (will be normalized to E.164 format)"),
    service: PhoneNumberService = Depends(get_service)
):
    """
    Check if a specific Twilio number exists and is active.
    Used for verifying SMS sender numbers for manual dials.
    
    Returns:
        {
            "exists": bool,
            "is_active": bool,
            "phone_number": str,
            "store_id": int or None,
            "daily_call_count": int,
            "hourly_call_count": int
        }
    """
    # Validate and normalize phone number from path
    from utils.phone_validator import validate_us_phone_number
    is_valid, normalized, error = validate_us_phone_number(phone_number)
    if not is_valid:
        raise ValidationError(f"Invalid phone number: {error}")
    phone_number = normalized
    
    return service.check_phone_number(phone_number)


@router.post("/{phone_number}/update-usage", summary="Update usage count and timestamp for Twilio number")
async def update_number_usage(
    phone_number: str = Path(..., description="Phone number (will be normalized to E.164 format)"),
    service: PhoneNumberService = Depends(get_service)
):
    """Update the usage count and timestamp for a Twilio number."""
    # Validate and normalize phone number from path
    from utils.phone_validator import validate_us_phone_number
    is_valid, normalized, error = validate_us_phone_number(phone_number)
    if not is_valid:
        raise ValidationError(f"Invalid phone number: {error}")
    phone_number = normalized
    
    return service.update_usage(phone_number)


@router.put("/{phone_number}/weight", summary="Set rotation weight for Twilio number")
async def set_rotation_weight(
    phone_number: str = Path(..., description="Phone number (will be normalized to E.164 format)"),
    weight: int = Body(...),
    service: PhoneNumberService = Depends(get_service)
):
    """Set rotation weight for a Twilio number."""
    # Validate and normalize phone number from path
    from utils.phone_validator import validate_us_phone_number
    is_valid, normalized, error = validate_us_phone_number(phone_number)
    if not is_valid:
        raise ValidationError(f"Invalid phone number: {error}")
    phone_number = normalized
    
    return service.set_rotation_weight(phone_number, weight)


@router.post("", summary="Add new Twilio number")
async def add_twilio_number(
    phone_data: PhoneNumberCreate,
    service: PhoneNumberService = Depends(get_service)
):
    """Add a new Twilio number to the system."""
    return service.create_phone_number(
        phone_number=phone_data.phone_number,
        rotation_weight=phone_data.rotation_weight or 1,
        store_id=phone_data.store_id
    )


@router.delete("/{phone_number}", summary="Delete Twilio number")
async def delete_twilio_number(
    phone_number: str = Path(..., description="Phone number (will be normalized to E.164 format)"),
    service: PhoneNumberService = Depends(get_service)
):
    """Delete a Twilio number from the system."""
    # Validate and normalize phone number from path
    from utils.phone_validator import validate_us_phone_number
    is_valid, normalized, error = validate_us_phone_number(phone_number)
    if not is_valid:
        raise ValidationError(f"Invalid phone number: {error}")
    phone_number = normalized
    
    return service.delete_phone_number_by_phone(phone_number)
