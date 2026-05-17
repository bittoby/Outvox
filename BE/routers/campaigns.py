"""
Campaign Management Router (Refactored)
Handles SMS campaign operations using service layer where possible.
"""

from typing import Optional
from datetime import datetime
from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel

from models import CampaignCreate, CampaignPreviewRequest
from services.campaign_service import get_campaign_service, CampaignService
from core.exceptions import ValidationError, CampaignError
from config import config

# Router instance
router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])


# Dependency injection
def get_service() -> CampaignService:
    """Dependency injection for CampaignService."""
    return get_campaign_service()


# ============================================================================
# GET ENDPOINTS
# ============================================================================

@router.get("", summary="Get all campaigns")
async def get_campaigns(
    store_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 100,
    service: CampaignService = Depends(get_service)
):
    """
    Get list of SMS campaigns.
    
    Args:
        store_id: Filter by store ID
        status: Filter by status (pending, running, completed, paused)
        limit: Maximum number of results
    """
    # Let exceptions bubble up to global handler
    return service.get_campaigns(store_id=store_id, status=status, limit=limit)


# IMPORTANT: This route must come BEFORE /{campaign_id} to avoid route conflicts
@router.get("/batches/{batch_id}/leads", summary="Get batch leads with status")
async def get_batch_leads(
    batch_id: int,
    service: CampaignService = Depends(get_service)
):
    """
    Get all leads for a batch with their send status and failure reasons.
    
    Returns:
        - sent_leads: Successfully sent SMS
        - failed_leads: Failed with error message/reason
        - pending_leads: Not yet processed
    """
    return service.get_batch_leads(batch_id)


@router.get("/{campaign_id}", summary="Get campaign details")
async def get_campaign_details(
    campaign_id: int,
    service: CampaignService = Depends(get_service)
):
    """Get detailed information about a specific campaign."""
    # Let exceptions bubble up to global handler
    return service.get_campaign(campaign_id)


@router.get("/{campaign_id}/batches", summary="Get campaign batches")
async def get_campaign_batches(
    campaign_id: int,
    service: CampaignService = Depends(get_service)
):
    """Get all batches for a campaign."""
    # Let exceptions bubble up to global handler
    return service.get_campaign_batches(campaign_id)


# ============================================================================
# POST ENDPOINTS
# ============================================================================

@router.post("/preview", summary="Preview campaign before starting")
async def preview_campaign(
    request: CampaignPreviewRequest,
    service: CampaignService = Depends(get_service)
):
    """
    Preview campaign details before starting (NO SMS sent).
    
    Shows:
    - Number of leads to contact
    - Estimated cost
    - Estimated time
    - Number of batches
    - Available phone numbers
    """
    # Let exceptions bubble up to global handler
    return service.preview_campaign(request.store_id, request.target_count)


class StartCampaignRequest(BaseModel):
    """Request model for starting SMS campaign."""
    store_id: int
    target_count: int
    start_time: Optional[str] = None


@router.post("/start", summary="Start campaign")
async def start_campaign(
    request: StartCampaignRequest,
    background_tasks: BackgroundTasks,
    service: CampaignService = Depends(get_service)
):
    """
    Create and schedule SMS campaign.
    
    ⚠️ CRITICAL SAFETY: This endpoint DOES NOT send any SMS messages.
    It only creates database records with status='active'.
    SMS sending will happen after explicit user confirmation.
    """
    from datetime import datetime
    from services.phone_number_service import get_phone_number_service
    from services.template_service import get_template_service
    
    store_id = request.store_id
    target_count = request.target_count
    start_time_str = request.start_time
    
    if not store_id:
        raise ValidationError("store_id is required")
    
    if not target_count or target_count <= 0:
        raise ValidationError("target_count must be positive")
    
    # Validate minimum phone numbers and templates before creating campaign
    phone_service = get_phone_number_service()
    template_service = get_template_service()
    
    # Check phone numbers
    # CRITICAL: Require minimum 3 phone numbers ASSIGNED to the store (not unassigned)
    # This ensures proper rotation and carrier compliance
    MIN_PHONE_NUMBERS = 3
    
    try:
        # Count ONLY store-assigned active phone numbers (strict requirement)
        store_assigned_numbers = phone_service.count_active_numbers(store_id)
        print(f"[Campaign API] Store {store_id} has {store_assigned_numbers} active phone number(s) assigned")
        
        # STRICT VALIDATION: Require minimum 3 numbers assigned to the store
        # Do NOT count unassigned numbers - they must be explicitly assigned
        if store_assigned_numbers < MIN_PHONE_NUMBERS:
            error_msg = (
                f"Insufficient phone numbers for campaign execution. "
                f"Store has {store_assigned_numbers} active phone number(s) assigned. "
                f"Campaign management requires minimum {MIN_PHONE_NUMBERS} numbers ASSIGNED to the store "
                f"for proper rotation and carrier compliance. "
                f"Please assign {MIN_PHONE_NUMBERS - store_assigned_numbers} more number(s) to this store before starting campaign."
            )
            print(f"[Campaign API] ERROR: {error_msg}")
            raise ValidationError(error_msg)
        
            
    except ValidationError:
        raise
    except Exception as e:
        print(f"[Campaign API] ERROR: Error checking phone numbers: {e}")
        raise ValidationError(f"Error checking phone numbers: {str(e)}")
    
    # Check SMS templates (required for sending SMS)
    # If no templates exist, create a default template automatically
    try:
        template_count = template_service.count_templates()
        print(f"[Campaign API] Found {template_count} SMS template(s)")
        
        if template_count == 0:
            print(f"[Campaign API] WARNING: No templates found. Creating default template...")
            # Create a default SMS template
            default_template = (
                "Hi {name}, " + config.brand.COMPANY_NAME + " here. "
                "We're offering cash loans on your valuables. "
                "Visit us today or reply YES for more info. Reply STOP to opt out."
            )
            try:
                template_result = template_service.create_template(default_template)
                template_count = 1
            except Exception as create_error:
                error_msg = (
                    f"No SMS templates found and failed to create default template: {str(create_error)}. "
                    f"Please create SMS templates manually by running: python BE/setup_templates.py"
                )
                print(f"[Campaign API] ERROR: {error_msg}")
                raise ValidationError(error_msg)
    except ValidationError:
        raise
    except Exception as e:
        print(f"[Campaign API] ERROR: Error checking templates: {e}")
        raise ValidationError(f"Error checking SMS templates: {str(e)}")
    
    # Parse start_time if provided
    start_time = None
    if start_time_str:
        try:
            start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
        except ValueError:
            raise ValidationError(
                "Invalid start_time format. Use ISO 8601 format (e.g., '2025-11-14T09:00:00')"
            )
    
    # Create campaign using CampaignService (automatically activates)
    print(f"\n{'='*70}")
    print(f"[Campaign API] Creating campaign for store_id={store_id}, target_count={target_count}")
    print(f"{'='*70}")
    
    result = service.create_campaign(
        store_id=store_id,
        target_count=target_count,
        start_time=start_time
    )
    
    # Execute first batch immediately in background task
    first_batch = result['batches'][0] if result['batches'] else None
    
    if first_batch:
        async def execute_batch_background(batch_id: int):
            try:
                from services.sms_campaign_manager import SMSCampaignManager
                bg_manager = SMSCampaignManager()
                await bg_manager.execute_batch(batch_id)
            except Exception as e:
                print(f"[Campaign API] ERROR: Batch execution failed: {e}")
        
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            loop.create_task(execute_batch_background(first_batch['batch_id']))
        except RuntimeError:
            background_tasks.add_task(execute_batch_background, first_batch['batch_id'])
    
    
    return result


# ============================================================================
# PUT ENDPOINTS
# ============================================================================

@router.put("/{campaign_id}/pause", summary="Pause campaign")
async def pause_campaign(
    campaign_id: int,
    service: CampaignService = Depends(get_service)
):
    """Pause an active campaign."""
    # Let exceptions bubble up to global handler
    return service.pause_campaign(campaign_id)


@router.put("/{campaign_id}/resume", summary="Resume campaign")
async def resume_campaign(
    campaign_id: int,
    service: CampaignService = Depends(get_service)
):
    """Resume a paused campaign."""
    # Let exceptions bubble up to global handler
    return service.resume_campaign(campaign_id)


# ============================================================================
# DELETE ENDPOINTS
# ============================================================================

@router.delete("/{campaign_id}", summary="Delete campaign")
async def delete_campaign(
    campaign_id: int,
    service: CampaignService = Depends(get_service)
):
    """Delete a campaign and all related batches."""
    # Let exceptions bubble up to global handler
    return service.delete_campaign(campaign_id)
