"""
Campaign Data Models
Pydantic models for campaign-related operations.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class CampaignBase(BaseModel):
    """Base campaign model."""
    store_id: int = Field(..., description="Store ID for this campaign")
    target_count: int = Field(..., ge=1, description="Target number of SMS to send")


class CampaignCreate(CampaignBase):
    """Model for creating a new campaign."""
    start_time: Optional[datetime] = None
    template_ids: Optional[list[int]] = None


class CampaignPreviewRequest(BaseModel):
    """Model for campaign preview request."""
    store_id: int
    target_count: int


class CampaignPreviewResponse(BaseModel):
    """Model for campaign preview response."""
    store_id: int
    store_name: str
    leads_to_contact: int
    estimated_cost: float
    estimated_time_hours: float
    estimated_batches: int
    available_phone_numbers: int
    batch_size: int
    batch_spacing_minutes: int
    preview_leads: list[dict]
    warnings: list[str] = []


class CampaignResponse(BaseModel):
    """Model for campaign response."""
    campaign_id: int
    store_id: int
    store_name: Optional[str] = None
    target_count: int
    actual_sent: int = 0
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class BatchResponse(BaseModel):
    """Model for batch response."""
    batch_id: int
    campaign_id: int
    phone_number: Optional[str] = None
    batch_number: int
    target_count: int
    actual_sent: int = 0
    scheduled_at: datetime
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    class Config:
        from_attributes = True


class DailyStatsResponse(BaseModel):
    """Model for daily statistics response."""
    store_id: int
    date: str
    sms_sent: int
    sms_quota: int
    sms_remaining: int
    calls_made: int
    calls_quota: int
    calls_remaining: int
    yes_replies: int
    stop_replies: int
    interested_calls: int
    not_interested_calls: int
    callback_requests: int


class CampaignRequest(BaseModel):
    """Model for campaign request (legacy, used by agents)."""
    call_count: int
    shop_id: Optional[str] = None
