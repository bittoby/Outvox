"""
Popup Queue Data Models
Pydantic models for popup queue operations.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class PopupQueueItem(BaseModel):
    """Model for popup queue item."""
    popup_id: Optional[int] = None
    lead_id: int
    status: Optional[str] = None
    created_at: Optional[str] = None
    dialed_at: Optional[str] = None
    dismissed_at: Optional[str] = None
    dialed_by: Optional[str] = None
    call_sid: Optional[str] = None


class ManualDialRequest(BaseModel):
    """Model for manual dial request (TCPA compliance)."""
    lead_id: int
    employee_name: str = Field(..., description="Required for TCPA compliance")


class UpdateCallSIDRequest(BaseModel):
    """Model for updating call SID in popup queue."""
    call_sid: str

