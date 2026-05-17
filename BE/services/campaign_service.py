"""
Campaign Service
Business logic for SMS campaign operations.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from repositories.campaign_repository import CampaignRepository
from repositories.store_repository import StoreRepository
from repositories.lead_repository import LeadRepository
from repositories.phone_number_repository import PhoneNumberRepository
from services.sms_campaign_manager import SMSCampaignManager
from services.phone_number_service import get_phone_number_service
from services.template_service import get_template_service
from services.websocket_service import broadcast_event_sync, EventType
from core.exceptions import ResourceNotFoundError, ValidationError, CampaignError


class CampaignService:
    """Service for campaign business logic."""
    
    _instance = None
    
    @classmethod
    def get_instance(cls) -> 'CampaignService':
        """Get singleton instance of CampaignService."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """Initialize service with repository and manager."""
        self.repository = CampaignRepository()
        self.manager = SMSCampaignManager()
    
    def get_campaigns(
        self,
        store_id: Optional[int] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Get all campaigns with optional filtering.
        
        Args:
            store_id: Filter by store ID
            status: Filter by status (pending, active, completed, paused)
            limit: Maximum number of results
            
        Returns:
            Dict with campaigns list and count
        """
        campaigns = self.repository.get_all(store_id=store_id, status=status, limit=limit)
        
        return {
            "success": True,
            "campaigns": campaigns,
            "count": len(campaigns)
        }
    
    def get_campaign(self, campaign_id: int) -> Dict[str, Any]:
        """
        Get campaign by ID with batch summary.
        
        Args:
            campaign_id: Campaign ID
            
        Returns:
            Dict with campaign details
            
        Raises:
            ResourceNotFoundError: If campaign not found
        """
        campaign = self.repository.get_campaign_with_batches(campaign_id)
        
        if not campaign:
            raise ResourceNotFoundError("Campaign", campaign_id)
        
        # Also fetch batches for the campaign
        batches = self.repository.get_batches_by_campaign(campaign_id)
        
        return {
            "success": True,
            "campaign": campaign,
            "batches": batches
        }
    
    def get_campaign_batches(self, campaign_id: int) -> Dict[str, Any]:
        """
        Get all batches for a campaign.
        
        Args:
            campaign_id: Campaign ID
            
        Returns:
            Dict with batches list
        """
        # Verify campaign exists
        if not self.repository.get_by_id(campaign_id):
            raise ResourceNotFoundError("Campaign", campaign_id)
        
        batches = self.repository.get_batches_by_campaign(campaign_id)
        
        return {
            "success": True,
            "campaign_id": campaign_id,
            "batches": batches,
            "count": len(batches)
        }
    
    def get_batch_leads(self, batch_id: int) -> Dict[str, Any]:
        """
        Get all leads for a batch with their send status and failure reasons.
        
        Args:
            batch_id: Batch ID
            
        Returns:
            Dict with leads list including status and error messages
        """
        leads = self.repository.get_batch_leads(batch_id)
        
        # Separate into sent, failed, and pending
        sent_leads = [l for l in leads if l['status'] == 'sent']
        failed_leads = [l for l in leads if l['status'] == 'failed']
        pending_leads = [l for l in leads if l['status'] == 'pending']
        
        return {
            "success": True,
            "batch_id": batch_id,
            "leads": leads,
            "total_count": len(leads),
            "sent_count": len(sent_leads),
            "failed_count": len(failed_leads),
            "pending_count": len(pending_leads),
            "sent_leads": sent_leads,
            "failed_leads": failed_leads,
            "pending_leads": pending_leads
        }
    
    def preview_campaign(
        self,
        store_id: int,
        target_count: int
    ) -> Dict[str, Any]:
        """
        Preview campaign details before starting.
        
        This method calculates estimates without creating any database records.
        
        Args:
            store_id: Store ID for the campaign
            target_count: Target number of leads to contact
            
        Returns:
            Dict with preview information including warnings
        """
        store_repo = StoreRepository()
        lead_repo = LeadRepository()
        phone_service = get_phone_number_service()
        template_service = get_template_service()
        
        # Constants
        SMS_PER_NUMBER = 50
        MIN_PHONE_NUMBERS = 3
        batch_size = 25
        batch_spacing_minutes = 60  # 1 hour spacing to allow hourly limit reset (25 SMS/hour)
        cost_per_sms = 0.0083
        
        # Get store info
        store = store_repo.get_by_id(store_id)
        if not store:
            raise ResourceNotFoundError("Store", store_id)
        
        store_name = store.get('name', f'Store {store_id}')
        
        # Count active phone numbers for this store
        phone_count = phone_service.count_active_numbers(store_id)
        daily_quota = phone_count * SMS_PER_NUMBER
        
        # Count eligible leads (assigned to this store)
        eligible_leads = lead_repo.count_eligible_for_consent(store_id=store_id, force=False)
        
        # Also check for unassigned eligible leads as fallback
        unassigned_leads = lead_repo.count_eligible_for_consent(store_id=None, force=False)
        
        # Use store-assigned leads first, fallback to unassigned if needed
        if eligible_leads == 0 and unassigned_leads > 0:
            eligible_leads = unassigned_leads
        
        leads_to_contact = min(target_count, eligible_leads)
        
        # Count active phone numbers (assigned to this store)
        available_numbers = phone_service.count_active_numbers(store_id)
        
        # Also check for unassigned active phone numbers as fallback
        unassigned_numbers = phone_service.count_active_numbers(store_id=None)
        
        # Use store-assigned numbers first, fallback to unassigned if needed
        if available_numbers == 0 and unassigned_numbers > 0:
            available_numbers = unassigned_numbers
        
        # Calculate estimates
        estimated_batches = (leads_to_contact + batch_size - 1) // batch_size  # Ceiling division
        estimated_time_hours = (estimated_batches * batch_spacing_minutes) / 60.0
        estimated_cost = leads_to_contact * cost_per_sms
        
        # Get preview leads (try store-assigned first, then unassigned)
        preview_leads = []
        if eligible_leads > 0:
            # First try store-assigned leads
            leads = lead_repo.get_eligible_for_consent(limit=10, store_id=store_id, force=False)
            
            # If no store-assigned leads, try unassigned leads
            if not leads and unassigned_leads > 0:
                leads = lead_repo.get_eligible_for_consent(limit=10, store_id=None, force=False)
            
            preview_leads = [
                {
                    "lead_id": lead['lead_id'],
                    "name": lead.get('name', ''),
                    "phone_number": lead.get('phone_number', ''),
                    "Address": lead.get('Address', ''),
                    "City": lead.get('City', ''),
                    "State": lead.get('State', '')
                }
                for lead in leads
            ]
        
        # Check warnings with helpful guidance
        warnings = []
        if leads_to_contact > daily_quota:
            warnings.append(
                f"Campaign exceeds daily quota ({daily_quota}). Will run over multiple days."
            )
        
        # Phone number warnings with guidance
        store_assigned_numbers = phone_service.count_active_numbers(store_id)
        
        # Warn if less than minimum required phone numbers (but don't block preview)
        if store_assigned_numbers < MIN_PHONE_NUMBERS:
            warnings.append(
                f"⚠️ Store has only {store_assigned_numbers} phone number(s). "
                f"Campaign management requires minimum {MIN_PHONE_NUMBERS} numbers per store for proper rotation and carrier compliance. "
                f"Campaign start will be blocked until {MIN_PHONE_NUMBERS - store_assigned_numbers} more number(s) are assigned."
            )
        
        # Check if any numbers are available for sending (under daily limit)
        # This requires checking the repository directly for now
        phone_repo = PhoneNumberRepository()
        ready_numbers_query = """
            SELECT COUNT(*) as ready_numbers
            FROM TwilioNumbers
            WHERE store_id = ?
              AND ISNULL(is_active, 1) = 1
              AND ISNULL(daily_sms_count, 0) < 50
        """
        ready_numbers = phone_repo.execute_scalar(ready_numbers_query, (store_id,)) or 0
        
        if ready_numbers == 0:
            if available_numbers == 0:
                warnings.append(
                    f"No phone numbers assigned to store '{store_name}'. "
                    f"Please assign phone numbers to this store first. "
                    f"Campaign start will be blocked."
                )
            else:
                warnings.append(
                    f"All phone numbers for store '{store_name}' have reached daily limit (50 SMS/day). "
                    f"Campaign start will be blocked until numbers reset."
                )
        
        if eligible_leads == 0:
            warnings.append(
                f"No eligible leads found for store '{store_name}'. "
                f"Leads must be: assigned to store, not on DNC, never sent consent SMS (or sent more than cooldown days ago), and not already in a progressing campaign."
            )
        
        if leads_to_contact < target_count:
            warnings.append(
                f"Only {leads_to_contact} eligible leads found (requested {target_count}). "
                f"Campaign will contact {leads_to_contact} leads."
            )
        
        return {
            "success": True,
            "store_id": store_id,
            "store_name": store_name,
            "target_count": target_count,
            "eligible_leads": eligible_leads,
            "leads_to_contact": leads_to_contact,
            "available_phone_numbers": available_numbers,
            "daily_quota": daily_quota,
            "estimated_batches": estimated_batches,
            "batch_size": batch_size,
            "estimated_time_hours": round(estimated_time_hours, 2),
            "estimated_cost": round(estimated_cost, 2),
            "preview_leads": preview_leads,
            "warnings": warnings
        }
    
    def create_campaign(
        self,
        store_id: int,
        target_count: int,
        start_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Create a new SMS campaign.
        
        This delegates to SMSCampaignManager which handles the complex
        campaign creation logic including batch scheduling.
        
        Args:
            store_id: Store ID for the campaign
            target_count: Number of leads to contact
            start_time: Optional start time (defaults to now)
            
        Returns:
            Dict with campaign creation result (status='active')
        """
        try:
            print(f"[CampaignService] Creating campaign: store_id={store_id}, target_count={target_count}")
            result = self.manager.create_campaign(
                store_id=store_id,
                target_count=target_count,
                start_time=start_time
            )
            
            print(f"[CampaignService] Campaign created successfully: campaign_id={result.get('campaign_id')}")
            
            # Convert datetime objects to ISO strings for JSON response
            if isinstance(result.get('start_time'), datetime):
                result['start_time'] = result['start_time'].isoformat()
            
            for batch in result.get('batches', []):
                if isinstance(batch.get('scheduled_at'), datetime):
                    batch['scheduled_at'] = batch['scheduled_at'].isoformat()
            
            result['success'] = True
            
            # Activate campaign immediately after creation
            campaign_id = result.get('campaign_id')
            if campaign_id:
                try:
                    self.activate_campaign(campaign_id)
                    result['status'] = 'active'
                    print(f"[CampaignService] Campaign {campaign_id} activated")
                except Exception as e:
                    print(f"[CampaignService] WARNING: Could not activate campaign {campaign_id}: {e}")
                    # Don't fail the whole operation if activation fails
            
            # Broadcast campaign created event
            try:
                broadcast_event_sync(
                    EventType.CAMPAIGN_CREATED,
                    {
                        "campaign_id": campaign_id,
                        "store_id": store_id,
                        "target_count": target_count,
                        "batch_count": result.get('batch_count', 0)
                    }
                )
            except Exception as e:
                print(f"[CampaignService] WARNING: Could not broadcast campaign event: {e}")
            
            return result
            
        except ValueError as e:
            error_msg = str(e)
            print(f"[CampaignService] ERROR: Validation error: {error_msg}")
            raise ValidationError(error_msg)
        except Exception as e:
            error_msg = f"Failed to create campaign: {str(e)}"
            print(f"[CampaignService] ERROR: Campaign creation error: {error_msg}")
            import traceback
            traceback.print_exc()
            raise CampaignError(error_msg)
    
    def activate_campaign(self, campaign_id: int) -> Dict[str, Any]:
        """
        Activate a campaign (set status to 'active' and started_at timestamp).
        
        Args:
            campaign_id: Campaign ID to activate
            
        Returns:
            Dict with success status
            
        Raises:
            ResourceNotFoundError: If campaign not found
        """
        campaign = self.repository.get_by_id(campaign_id)
        if not campaign:
            raise ResourceNotFoundError("Campaign", campaign_id)
        
        success = self.repository.update_status(campaign_id, 'active')
        
        if not success:
            raise CampaignError(f"Failed to activate campaign {campaign_id}")
        
        # Update started_at timestamp
        self.repository.update_status(campaign_id, 'active', started_at=datetime.now())
        
        return {
            "success": True,
            "message": f"Campaign {campaign_id} activated",
            "campaign_id": campaign_id,
            "status": "active"
        }
    
    def pause_campaign(self, campaign_id: int) -> Dict[str, Any]:
        """
        Pause an active campaign.
        
        Args:
            campaign_id: Campaign ID to pause
            
        Returns:
            Dict with success status
        """
        campaign = self.repository.get_by_id(campaign_id)
        if not campaign:
            raise ResourceNotFoundError("Campaign", campaign_id)
        
        current_status = campaign['status']
        
        if current_status not in ('active', 'pending'):
            raise ValidationError(
                f"Campaign {campaign_id} is {current_status}. "
                "Can only pause 'active' or 'pending' campaigns."
            )
        
        success = self.repository.update_status(campaign_id, 'paused')
        
        if not success:
            raise CampaignError(f"Failed to pause campaign {campaign_id}")
        
        return {
            "success": True,
            "message": f"Campaign {campaign_id} paused",
            "campaign_id": campaign_id,
            "status": "paused"
        }
    
    def resume_campaign(self, campaign_id: int) -> Dict[str, Any]:
        """
        Resume a paused campaign.
        
        Args:
            campaign_id: Campaign ID to resume
            
        Returns:
            Dict with success status
        """
        campaign = self.repository.get_by_id(campaign_id)
        if not campaign:
            raise ResourceNotFoundError("Campaign", campaign_id)
        
        current_status = campaign['status']
        
        if current_status != 'paused':
            raise ValidationError(
                f"Campaign {campaign_id} is {current_status}. "
                "Can only resume 'paused' campaigns."
            )
        
        success = self.repository.update_status(campaign_id, 'active')
        
        if not success:
            raise CampaignError(f"Failed to resume campaign {campaign_id}")
        
        return {
            "success": True,
            "message": f"Campaign {campaign_id} resumed",
            "campaign_id": campaign_id,
            "status": "active"
        }
    
    def delete_campaign(self, campaign_id: int) -> Dict[str, Any]:
        """
        Delete a campaign and all related batches.
        
        Args:
            campaign_id: Campaign ID to delete
            
        Returns:
            Dict with success status
        """
        campaign = self.repository.get_by_id(campaign_id)
        if not campaign:
            raise ResourceNotFoundError("Campaign", campaign_id)
        
        success = self.repository.delete(campaign_id)
        
        if not success:
            raise CampaignError(f"Failed to delete campaign {campaign_id}")
        
        return {
            "success": True,
            "message": f"Campaign {campaign_id} and all related batches deleted",
            "campaign_id": campaign_id
        }


def get_campaign_service() -> CampaignService:
    """Get singleton instance of CampaignService."""
    return CampaignService.get_instance()



