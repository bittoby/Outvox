"""
Lead Data Models
Pydantic models for lead-related operations.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Any
from datetime import datetime
from utils.pydantic_validators import validate_and_normalize_phone


class LeadBase(BaseModel):
    """Base lead model with common fields."""
    name: Optional[str] = None
    phone_number: str = Field(..., description="Phone number (will be normalized to E.164 format)")
    Address: Optional[str] = None
    City: Optional[str] = None
    County: Optional[str] = None
    State: Optional[str] = None
    Zip: Optional[str] = None
    priority: Optional[int] = Field(default=1, ge=1, le=5, description="Priority level (1-5)")
    
    @field_validator('phone_number', mode='before')
    @classmethod
    def validate_phone_number(cls, value: Any) -> str:
        """Validate and normalize phone number to E.164 format."""
        return validate_and_normalize_phone(value)


class LeadCreate(LeadBase):
    """Model for creating a new lead."""
    store_id: Optional[int] = None


class LeadUpdate(BaseModel):
    """Model for updating an existing lead."""
    name: Optional[str] = None
    phone_number: Optional[str] = Field(None, description="Phone number (will be normalized to E.164 format)")
    Address: Optional[str] = None
    City: Optional[str] = None
    County: Optional[str] = None
    State: Optional[str] = None
    Zip: Optional[str] = None
    priority: Optional[int] = Field(default=None, ge=1, le=5)
    store_id: Optional[int] = None
    dnc_flag: Optional[bool] = None
    sms_verified: Optional[bool] = None
    
    @field_validator('phone_number', mode='before')
    @classmethod
    def validate_phone_number(cls, value: Any) -> Optional[str]:
        """Validate and normalize phone number to E.164 format."""
        if value is None:
            return None
        return validate_and_normalize_phone(value)


class LeadResponse(LeadBase):
    """Model for lead response."""
    lead_id: int
    store_id: Optional[int] = None
    store_name: Optional[str] = None
    dnc_flag: bool = False
    sms_verified: bool = False
    sms_verified_at: Optional[datetime] = None
    # call_eligible and call_eligible_reason removed - now determined dynamically
    last_called_at: Optional[datetime] = None
    call_count: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class BulkAssignRequest(BaseModel):
    """Model for bulk assigning leads to a store."""
    lead_ids: list[int] = Field(..., description="List of lead IDs to assign")
    store_id: int = Field(..., description="Store ID to assign leads to")


class CSVImportRequest(BaseModel):
    """Model for CSV import request."""
    csv_content: str = Field(..., description="CSV file content as string")
    auto_assign_store: Optional[int] = Field(None, description="Automatically assign to store ID")


class CSVExportRequest(BaseModel):
    """Model for CSV export request."""
    dnc_only: Optional[bool] = None
    limit: Optional[int] = None


class BulkLeadRequest(BaseModel):
    """Model for bulk lead import request."""
    leads: list[dict] = Field(..., description="List of lead dictionaries")


class DNCARequest(BaseModel):
    """Model for marking a lead as DNC."""
    phone_number: str = Field(..., description="Phone number (will be normalized to E.164 format)")
    agent_id: str = "SYSTEM"
    reason: Optional[str] = None
    
    @field_validator('phone_number', mode='before')
    @classmethod
    def validate_phone_number(cls, value: Any) -> str:
        """Validate and normalize phone number to E.164 format."""
        return validate_and_normalize_phone(value)

