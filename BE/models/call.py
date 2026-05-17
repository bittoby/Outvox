"""
Call Data Models
Pydantic models for call-related operations.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Any
from datetime import datetime
from utils.pydantic_validators import validate_and_normalize_phone


class CallResultBase(BaseModel):
    """Base call result model."""
    lead_id: int
    agent_id: str
    twilio_number: str
    call_sid: str
    call_duration: int = 0
    result_type: str = Field(..., description="interested, not_interested, callback, dnc, no_answer, voicemail")
    customer_transcript: str = ""
    agent_transcript: str = ""
    combined_transcript: str = ""


class CallResultCreate(CallResultBase):
    """Model for creating a call result."""
    pass


class CallResultResponse(CallResultBase):
    """Model for call result response."""
    result_id: int
    lead_name: Optional[str] = None
    lead_phone: Optional[str] = None
    store_id: Optional[int] = None
    store_name: Optional[str] = None
    created_at: datetime
    recording_url: Optional[str] = None
    
    class Config:
        from_attributes = True


class CallHistoryResponse(BaseModel):
    """Model for call history list response."""
    total: int
    calls: list[CallResultResponse]


class StartCallRequest(BaseModel):
    """Model for starting a call."""
    lead_id: Optional[int] = None
    phone_number: Optional[str] = Field(None, description="Phone number (will be normalized to E.164 format)")
    override_agent: Optional[str] = None
    
    @field_validator('phone_number', mode='before')
    @classmethod
    def validate_phone_number(cls, value: Any) -> Optional[str]:
        """Validate and normalize phone number to E.164 format."""
        if value is None:
            return None
        return validate_and_normalize_phone(value)


class StartCampaignRequest(BaseModel):
    """Model for starting a campaign."""
    count: int = Field(..., ge=1, le=100, description="Number of parallel calls")
    store_id: Optional[int] = None
    priority_filter: Optional[int] = None

