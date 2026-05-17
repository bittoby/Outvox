"""
Popup Queue Management Router (Refactored)
Handles popup notification queue using service layer.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from services.popup_service import get_popup_service, PopupService
from core.exceptions import ResourceNotFoundError, ValidationError
from models import UpdateCallSIDRequest

# Router instance
router = APIRouter(prefix="/api/popup", tags=["popup"])


# Request models
class ManualDialRequest(BaseModel):
    lead_id: int
    employee_name: str


# Dependency injection
def get_service() -> PopupService:
    """Dependency injection for PopupService."""
    return get_popup_service()


# ============================================================================
# GET ENDPOINTS
# ============================================================================

@router.get("/pending", summary="Get pending popup queue items")
async def get_pending_popups(
    limit: int = 50,
    offset: int = 0,
    sort_field: Optional[str] = None,
    sort_direction: Optional[str] = None,
    priority: Optional[int] = None,
    service: PopupService = Depends(get_service)
):
    """Get pending popup notifications with pagination and sorting."""
    # Let exceptions bubble up to global handler
    return service.get_pending_popups(
        limit=limit,
        offset=offset,
        sort_field=sort_field,
        sort_direction=sort_direction,
        priority=priority
    )


# ============================================================================
# POST ENDPOINTS
# ============================================================================

@router.post("/dismiss/{popup_id}", summary="Dismiss popup")
async def dismiss_popup(
    popup_id: int,
    service: PopupService = Depends(get_service)
):
    """Dismiss a popup notification."""
    # Let exceptions bubble up to global handler
    return service.dismiss_popup(popup_id)


@router.post("/manual-dial", summary="Prepare manual dial")
async def prepare_manual_dial(
    request: ManualDialRequest,
    service: PopupService = Depends(get_service)
):
    """Prepare a manual dial for a lead."""
    # Let exceptions bubble up to global handler
    return service.prepare_manual_dial(
        lead_id=request.lead_id,
        employee_name=request.employee_name
    )


@router.post("/update-call-sid/{popup_id}", summary="Update popup with call SID")
async def update_popup_call_sid(
    popup_id: int,
    payload: UpdateCallSIDRequest,
    service: PopupService = Depends(get_service)
):
    """Update popup queue with call SID after call is initiated."""
    call_sid = payload.call_sid.strip()
    if not call_sid:
        raise HTTPException(status_code=400, detail="call_sid is required")
    
    # Let exceptions bubble up to global handler
    return service.update_call_sid(popup_id, call_sid)
