"""
Store Data Models
Pydantic models for store-related operations.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Any
from datetime import datetime
from utils.pydantic_validators import validate_and_normalize_phone


class StoreBase(BaseModel):
    """Base store model."""
    name: str = Field(..., description="Store name")
    location: Optional[str] = None
    daily_sms_quota: int = Field(default=200, ge=0, description="Daily SMS limit")
    daily_call_quota: int = Field(default=60, ge=0, description="Daily call limit")


class StoreCreate(StoreBase):
    """Model for creating a new store."""
    pass


class StoreUpdate(BaseModel):
    """Model for updating a store."""
    name: Optional[str] = None
    location: Optional[str] = None
    daily_sms_quota: Optional[int] = Field(None, ge=0)
    daily_call_quota: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class StoreResponse(StoreBase):
    """Model for store response."""
    store_id: int
    is_active: bool = True
    created_at: datetime
    
    # Statistics (computed)
    total_leads: Optional[int] = 0
    total_phone_numbers: Optional[int] = 0
    sms_sent_today: Optional[int] = 0
    calls_made_today: Optional[int] = 0
    
    class Config:
        from_attributes = True


class PhoneNumberBase(BaseModel):
    """Base phone number model."""
    phone_number: str = Field(..., description="Twilio phone number (will be normalized to E.164 format)")
    
    @field_validator('phone_number', mode='before')
    @classmethod
    def validate_phone_number(cls, value: Any) -> str:
        """Validate and normalize phone number to E.164 format."""
        return validate_and_normalize_phone(value)


class PhoneNumberCreate(PhoneNumberBase):
    """Model for creating a phone number."""
    store_id: Optional[int] = None
    rotation_weight: Optional[int] = Field(default=1, ge=0, description="Rotation weight for phone number selection")


class PhoneNumberUpdate(BaseModel):
    """Model for updating a phone number."""
    store_id: Optional[int] = None
    is_active: Optional[bool] = None


class PhoneNumberResponse(PhoneNumberBase):
    """Model for phone number response."""
    phone_number_id: int
    store_id: Optional[int] = None
    store_name: Optional[str] = None
    is_active: bool = True
    daily_sms_count: int = 0
    hourly_sms_count: int = 0
    daily_call_count: int = 0
    hourly_call_count: int = 0
    last_batch_sent_at: Optional[datetime] = None
    last_call_at: Optional[datetime] = None
    last_hourly_reset: Optional[datetime] = None
    
    class Config:
        from_attributes = True

