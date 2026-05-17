"""
SMS Data Models
Pydantic models for SMS-related operations.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Any
from datetime import datetime
from utils.pydantic_validators import validate_and_normalize_phone


class SMSMessageBase(BaseModel):
    """Base SMS message model."""
    lead_id: int
    phone_number: str = Field(..., description="Phone number (will be normalized to E.164 format)")
    message_type: str = Field(..., description="directions, photo_request, response, consent")
    message_content: str
    twilio_sid: Optional[str] = None
    
    @field_validator('phone_number', mode='before')
    @classmethod
    def validate_phone_number(cls, value: Any) -> str:
        """Validate and normalize phone number to E.164 format."""
        return validate_and_normalize_phone(value)


class SMSMessageCreate(SMSMessageBase):
    """Model for creating an SMS message."""
    pass


class SMSMessageResponse(SMSMessageBase):
    """Model for SMS message response."""
    message_id: int
    sent_at: datetime
    direction: str = "outbound"  # outbound or inbound
    status: Optional[str] = None
    
    class Config:
        from_attributes = True


class SMSConversationResponse(BaseModel):
    """Model for SMS conversation response."""
    lead_id: int
    lead_name: Optional[str] = None
    phone_number: str  # Response model - already normalized from DB
    store_id: Optional[int] = None
    store_name: Optional[str] = None
    message_count: int
    last_message: Optional[str] = None
    last_message_at: Optional[datetime] = None
    sms_verified: bool = False
    
    class Config:
        from_attributes = True


class SMSConversationDetailResponse(BaseModel):
    """Model for detailed SMS conversation."""
    lead_id: int
    lead_name: Optional[str] = None
    phone_number: str  # Response model - already normalized from DB
    messages: list[SMSMessageResponse]
    
    class Config:
        from_attributes = True


class ConsentSMSRequest(BaseModel):
    """Model for sending consent SMS."""
    lead_id: Optional[int] = None
    phone_number: Optional[str] = Field(None, description="Phone number (will be normalized to E.164 format)")
    message: Optional[str] = None
    force: bool = False
    
    @field_validator('phone_number', mode='before')
    @classmethod
    def validate_phone_number(cls, value: Any) -> Optional[str]:
        """Validate and normalize phone number to E.164 format."""
        if value is None:
            return None
        return validate_and_normalize_phone(value)


class ConsentBatchRequest(BaseModel):
    """Model for sending consent SMS batch."""
    limit: int = Field(default=100, ge=1, le=500, description="Number of leads to contact")
    store_id: Optional[int] = None
    message: Optional[str] = None
    force: bool = False


class PhotoSubmissionBase(BaseModel):
    """Base photo submission model."""
    lead_id: int
    phone_number: str = Field(..., description="Phone number (will be normalized to E.164 format)")
    photo_url: str
    status: str = "pending"  # pending, reviewed, appraised
    
    @field_validator('phone_number', mode='before')
    @classmethod
    def validate_phone_number(cls, value: Any) -> str:
        """Validate and normalize phone number to E.164 format."""
        return validate_and_normalize_phone(value)


class PhotoSubmissionCreate(PhotoSubmissionBase):
    """Model for creating a photo submission."""
    pass


class PhotoSubmissionResponse(PhotoSubmissionBase):
    """Model for photo submission response."""
    photo_id: int
    lead_name: Optional[str] = None
    submitted_at: datetime
    reviewed_at: Optional[datetime] = None
    appraised_value: Optional[float] = None
    notes: Optional[str] = None
    
    class Config:
        from_attributes = True


class PhotoStatusUpdate(BaseModel):
    """Model for updating photo status."""
    status: str = Field(..., description="reviewed or appraised")
    reviewed_by: Optional[str] = Field(None, description="Name of reviewer")
    appraised_value: Optional[float] = Field(None, ge=0, description="Appraised value in dollars")
    notes: Optional[str] = None


class ConsentSMSBatchRequest(BaseModel):
    """Model for sending consent SMS batch."""
    limit: int = Field(default=100, ge=1, le=500, description="Number of leads to contact")
    store_id: Optional[int] = Field(None, description="Filter by store ID (None = any store)")
    message: Optional[str] = None
    force: bool = Field(False, description="If True, send even if already verified")


class SMSVerificationRequest(BaseModel):
    """Model for SMS verification request."""
    lead_id: Optional[int] = None
    phone_number: Optional[str] = Field(None, description="Phone number (will be normalized to E.164 format)")
    verified: bool = True
    mark_dnc: bool = False
    source: Optional[str] = None
    
    @field_validator('phone_number', mode='before')
    @classmethod
    def validate_phone_number(cls, value: Any) -> Optional[str]:
        """Validate and normalize phone number to E.164 format."""
        if value is None:
            return None
        return validate_and_normalize_phone(value)
