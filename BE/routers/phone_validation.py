"""
Phone Validation Router
API endpoints for phone number validation using Trestle API.
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query

from models.phone_validation import (
    PhoneValidationRequest,
    PhoneValidationResponse,
    BulkPhoneValidationRequest,
    BulkPhoneValidationResponse
)
from services.trestle_service import get_trestle_service
from config import config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/phone-validation", tags=["phone-validation"])


@router.get("/validate/{phone_number}", response_model=PhoneValidationResponse)
async def validate_phone_number(
    phone_number: str,
    skip_cache: bool = Query(default=False, description="Skip cached result and force new lookup")
):
    """
    Validate a single phone number using Trestle API.
    
    Returns:
    - is_valid: Whether the phone number is valid
    - is_sms_capable: Whether the number can receive SMS
    - line_type: Mobile, Landline, FixedVOIP, NonFixedVOIP, etc.
    - carrier: Carrier name
    - owner_name: Owner name (if available)
    """
    if not config.trestle.API_KEY:
        raise HTTPException(
            status_code=503,
            detail="Phone validation service not configured. TRESTLE_API_KEY is missing."
        )
    
    trestle = get_trestle_service()
    result = await trestle.validate_phone(phone_number, skip_cache)
    
    return PhoneValidationResponse(
        success=True,
        phone_number=result.get('phone_number', phone_number),
        is_valid=result.get('is_valid', False),
        is_sms_capable=result.get('is_sms_capable', False),
        is_callable=result.get('is_callable', False),
        line_type=result.get('line_type'),
        activity_score=result.get('activity_score'),
        contact_grade=result.get('contact_grade'),
        carrier=result.get('carrier'),
        owner_name=result.get('owner_name'),
        warnings=result.get('warnings', []),
        message=result.get('error'),
        cached=result.get('cached', False)
    )


@router.post("/validate", response_model=PhoneValidationResponse)
async def validate_phone_number_post(request: PhoneValidationRequest):
    """
    Validate a single phone number using Trestle Real Contact API (POST method).
    
    Returns activity_score (0-100) and contact_grade (A-F) for lead quality assessment.
    SMS is only allowed for Mobile numbers with activity_score > 30.
    """
    if not config.trestle.API_KEY:
        raise HTTPException(
            status_code=503,
            detail="Phone validation service not configured. TRESTLE_API_KEY is missing."
        )
    
    trestle = get_trestle_service()
    result = await trestle.validate_phone(request.phone_number, request.skip_cache)
    
    return PhoneValidationResponse(
        success=True,
        phone_number=result.get('phone_number', request.phone_number),
        is_valid=result.get('is_valid', False),
        is_sms_capable=result.get('is_sms_capable', False),
        is_callable=result.get('is_callable', False),
        line_type=result.get('line_type'),
        activity_score=result.get('activity_score'),
        contact_grade=result.get('contact_grade'),
        carrier=result.get('carrier'),
        owner_name=result.get('owner_name'),
        warnings=result.get('warnings', []),
        message=result.get('error'),
        cached=result.get('cached', False)
    )


@router.post("/validate-bulk", response_model=BulkPhoneValidationResponse)
async def validate_phone_numbers_bulk(request: BulkPhoneValidationRequest):
    """
    Validate multiple phone numbers in bulk.
    
    Note: This will make multiple API calls, so use sparingly.
    Results are cached for 24 hours to minimize API usage.
    """
    if not config.trestle.API_KEY:
        raise HTTPException(
            status_code=503,
            detail="Phone validation service not configured. TRESTLE_API_KEY is missing."
        )
    
    if len(request.phone_numbers) > 100:
        raise HTTPException(
            status_code=400,
            detail="Maximum 100 phone numbers per request"
        )
    
    trestle = get_trestle_service()
    bulk_result = await trestle.validate_phones_bulk(request.phone_numbers, request.skip_cache)
    
    # Convert results to response format
    results = []
    for r in bulk_result.get('results', []):
        results.append(PhoneValidationResponse(
            success=True,
            phone_number=r.get('phone_number', ''),
            is_valid=r.get('is_valid', False),
            is_sms_capable=r.get('is_sms_capable', False),
            is_callable=r.get('is_callable', False),
            line_type=r.get('line_type'),
            activity_score=r.get('activity_score'),
            contact_grade=r.get('contact_grade'),
            carrier=r.get('carrier'),
            owner_name=r.get('owner_name'),
            warnings=r.get('warnings', []),
            message=r.get('error'),
            cached=r.get('cached', False)
        ))
    
    return BulkPhoneValidationResponse(
        success=True,
        total=bulk_result.get('total', 0),
        valid_count=bulk_result.get('valid_count', 0),
        invalid_count=bulk_result.get('invalid_count', 0),
        sms_capable_count=bulk_result.get('sms_capable_count', 0),
        results=results
    )


@router.get("/status")
async def get_validation_status():
    """
    Get phone validation service status.
    """
    return {
        "service": "Trestle Phone Validation",
        "configured": bool(config.trestle.API_KEY),
        "validate_on_lead_create": config.trestle.VALIDATE_ON_LEAD_CREATE,
        "validate_before_sms": config.trestle.VALIDATE_BEFORE_SMS,
        "block_invalid_numbers": config.trestle.BLOCK_INVALID_NUMBERS,
        "block_landline_for_sms": config.trestle.BLOCK_LANDLINE_FOR_SMS,
        "cache_duration_hours": config.trestle.CACHE_DURATION_HOURS
    }
