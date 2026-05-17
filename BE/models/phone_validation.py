"""
Phone Validation Models
Pydantic models for Trestle Real Contact API phone validation.

Key Fields from Real Contact API:
- phone.is_valid: True if phone number is valid
- phone.activity_score: 0-100 (100=active, 0=disconnected)
- phone.line_type: Mobile, Landline, FixedVOIP, NonFixedVOIP, etc.
- phone.contact_grade: A-F grade (A=best, F=bad)
- phone.name_match: True if name matches phone owner

SMS Filtering Rules:
- activity_score > 30: Number is likely active
- line_type = Mobile: Required for SMS consent messages
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class LineType(str, Enum):
    """Phone line types from Trestle API."""
    LANDLINE = "Landline"
    MOBILE = "Mobile"
    FIXED_VOIP = "FixedVOIP"
    NON_FIXED_VOIP = "NonFixedVOIP"
    PREMIUM = "Premium"
    TOLL_FREE = "TollFree"
    VOICEMAIL = "Voicemail"
    OTHER = "Other"
    UNKNOWN = "Unknown"


class ContactGrade(str, Enum):
    """Contact quality grade from Trestle Real Contact API."""
    A = "A"  # Best - real and contactable
    B = "B"  # Good
    C = "C"  # Average
    D = "D"  # Below average
    E = "E"  # Poor
    F = "F"  # Bad - should be deprioritized


class PhoneValidationStatus(str, Enum):
    """Phone validation status."""
    VALID = "valid"
    INVALID = "invalid"
    UNKNOWN = "unknown"


class PhoneValidationResult(BaseModel):
    """Result from Trestle Real Contact API phone validation."""
    phone_number: str = Field(..., description="Phone number in E.164 format")
    is_valid: bool = Field(default=False, description="Whether the phone number is valid")
    line_type: Optional[str] = Field(default=None, description="Line type (Mobile, Landline, etc.)")
    activity_score: Optional[int] = Field(default=None, description="Activity score 0-100 (100=active, 0=disconnected)")
    contact_grade: Optional[str] = Field(default=None, description="Contact quality grade A-F")
    name_match: Optional[bool] = Field(default=None, description="Whether name matches phone owner")
    carrier: Optional[str] = Field(default=None, description="Carrier name")
    is_prepaid: Optional[bool] = Field(default=None, description="Whether the phone is prepaid")
    is_commercial: Optional[bool] = Field(default=None, description="Whether the phone is commercial/business")
    owner_name: Optional[str] = Field(default=None, description="Owner name from Trestle")
    owner_type: Optional[str] = Field(default=None, description="Owner type (Person or Business)")
    error_message: Optional[str] = Field(default=None, description="Error message if validation failed")
    validated_at: datetime = Field(default_factory=datetime.utcnow, description="When validation was performed")
    
    # Computed fields for business logic
    is_sms_capable: bool = Field(default=False, description="Whether the number can receive SMS (Mobile + activity_score > 30)")
    is_callable: bool = Field(default=False, description="Whether the number can receive calls")
    validation_warnings: List[str] = Field(default_factory=list, description="Warnings from validation")
    
    class Config:
        from_attributes = True


class PhoneValidationRequest(BaseModel):
    """Request to validate a phone number."""
    phone_number: str = Field(..., description="Phone number to validate")
    skip_cache: bool = Field(default=False, description="Skip cached result and force new lookup")


class PhoneValidationResponse(BaseModel):
    """API response for phone validation."""
    success: bool
    phone_number: str
    is_valid: bool
    is_sms_capable: bool
    is_callable: bool
    line_type: Optional[str] = None
    activity_score: Optional[int] = Field(default=None, description="Activity score 0-100")
    contact_grade: Optional[str] = Field(default=None, description="Contact quality grade A-F")
    carrier: Optional[str] = None
    owner_name: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)
    message: Optional[str] = None
    cached: bool = Field(default=False, description="Whether result was from cache")


class BulkPhoneValidationRequest(BaseModel):
    """Request to validate multiple phone numbers."""
    phone_numbers: List[str] = Field(..., description="List of phone numbers to validate")
    skip_cache: bool = Field(default=False, description="Skip cached results")


class BulkPhoneValidationResponse(BaseModel):
    """Response for bulk phone validation."""
    success: bool
    total: int
    valid_count: int
    invalid_count: int
    sms_capable_count: int
    results: List[PhoneValidationResponse]
