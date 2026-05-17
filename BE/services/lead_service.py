"""
Lead Service
Business logic for lead management operations.
"""

import logging
import random
import time
from typing import Optional, List, Dict, Any
from datetime import datetime

from repositories.lead_repository import LeadRepository
from core.exceptions import ResourceNotFoundError, ValidationError
from utils.phone_validator import normalize_phone_number, validate_us_phone_number
from config import config

logger = logging.getLogger(__name__)


class LeadService:
    """Service for lead business logic."""
    
    _instance = None
    
    @classmethod
    def get_instance(cls) -> 'LeadService':
        """Get singleton instance of LeadService."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """Initialize service with repository."""
        self.repository = LeadRepository()
        self._trestle_service = None
    
    def _get_trestle_service(self):
        """Lazy load Trestle service to avoid circular imports."""
        if self._trestle_service is None:
            from services.trestle_service import get_trestle_service
            self._trestle_service = get_trestle_service()
        return self._trestle_service
    
    def get_lead(self, lead_id: int) -> Dict[str, Any]:
        """
        Get lead by ID.
        
        Args:
            lead_id: Lead ID
            
        Returns:
            Lead data
            
        Raises:
            ResourceNotFoundError: If lead not found
        """
        lead = self.repository.get_by_id(lead_id)
        if not lead:
            raise ResourceNotFoundError("Lead", lead_id)
        return lead
    
    def get_lead_by_phone(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """
        Get lead by phone number.
        
        Args:
            phone_number: Phone number
            
        Returns:
            Lead data or None
        """
        return self.repository.get_by_phone(phone_number)
    
    def get_leads(
        self,
        limit: int = 100,
        offset: int = 0,
        dnc_only: Optional[bool] = None,
        store_id: Optional[int] = None,
        unassigned_only: bool = False
    ) -> Dict[str, Any]:
        """
        Get all leads with filtering and pagination.
        
        Args:
            limit: Maximum number of results
            offset: Number of results to skip
            dnc_only: Filter by DNC status
            store_id: Filter by store ID
            unassigned_only: Get only unassigned leads
            
        Returns:
            Dict with leads and pagination info
        """
        # Validate and sanitize inputs
        limit = max(1, min(limit, 5000))
        offset = max(0, offset)
        
        leads, total = self.repository.get_all(
            limit=limit,
            offset=offset,
            dnc_only=dnc_only,
            store_id=store_id,
            unassigned_only=unassigned_only
        )
        
        return {
            "success": True,
            "leads": leads,
            "total": total,
            "limit": limit,
            "offset": offset
        }
    
    def get_next_lead(self) -> Dict[str, Any]:
        """
        Get next available lead for calling.
        
        Returns:
            Dict with lead data or None
        """
        lead = self.repository.get_next_available()
        return {
            "success": bool(lead),
            "lead": lead,
            "message": "No available leads" if not lead else None
        }
    
    def get_multiple_leads(self, count: int = 10) -> Dict[str, Any]:
        """
        Get multiple leads for parallel calling.
        
        Args:
            count: Number of leads to fetch
            
        Returns:
            Dict with leads list
        """
        leads = self.repository.get_multiple(count)
        # Format leads for campaign use (include all needed fields)
        formatted_leads = []
        for lead in leads:
            formatted_leads.append({
                "lead_id": lead.get("lead_id"),
                "phone_number": lead.get("phone_number"),
                "name": lead.get("name"),
                "Address": lead.get("Address", ""),
                "City": lead.get("City", ""),
                "County": lead.get("County", ""),
                "State": lead.get("State", ""),
                "Zip": lead.get("Zip", ""),
                "priority": lead.get("priority", 1)
            })
        return {
            "success": True,
            "leads": formatted_leads,
            "count": len(formatted_leads)
        }
    
    def create_lead(self, lead_data: Dict[str, Any], skip_validation: bool = False) -> Dict[str, Any]:
        """
        Create a new lead.
        
        Args:
            lead_data: Lead information
            skip_validation: If True, skip Trestle phone validation (for bulk imports)
            
        Returns:
            Dict with success status and lead_id
            
        Raises:
            ValidationError: If phone number already exists or is invalid
        """
        # Normalize and validate phone number - automatically add +1 if missing
        phone = lead_data.get('phone_number', '')
        if not phone:
            raise ValidationError("Phone number is required")
        
        # Validate phone number format
        is_valid, normalized, error = validate_us_phone_number(phone)
        if not is_valid:
            raise ValidationError(f"Invalid phone number: {error}")
        
        # Update lead_data with normalized phone (E.164 format: +1XXXXXXXXXX)
        lead_data['phone_number'] = normalized
        
        # Check for duplicate using normalized phone
        if self.repository.exists_by_phone(normalized):
            raise ValidationError(
                f"Lead with phone number {normalized} already exists"
            )
        
        # Trestle phone validation (if enabled)
        validation_result = None
        validation_warnings = []
        
        if not skip_validation and config.trestle.VALIDATE_ON_LEAD_CREATE and config.trestle.API_KEY:
            try:
                trestle = self._get_trestle_service()
                validation_result = trestle.validate_phone_sync(normalized)
                
                logger.info(f"Trestle validation for {normalized}: valid={validation_result.get('is_valid')}, "
                           f"line_type={validation_result.get('line_type')}, carrier={validation_result.get('carrier')}")
                
                # Check if number is valid
                if not validation_result.get('is_valid', True):
                    if config.trestle.BLOCK_INVALID_NUMBERS:
                        raise ValidationError(
                            f"Phone number {normalized} is invalid according to carrier lookup. "
                            f"Error: {validation_result.get('error', 'Number not found')}"
                        )
                    else:
                        validation_warnings.append(f"Phone validation warning: {validation_result.get('error', 'Unknown')}")
                
                # Check line type for SMS capability
                line_type = validation_result.get('line_type', 'Unknown')
                if line_type == 'Landline':
                    validation_warnings.append(f"Landline number detected - cannot receive SMS")
                elif line_type == 'NonFixedVOIP':
                    validation_warnings.append(f"NonFixedVOIP number - may have higher spam risk")
                
                # Add any warnings from API
                if validation_result.get('warnings'):
                    validation_warnings.extend(validation_result.get('warnings', []))
                    
            except ValidationError:
                raise  # Re-raise validation errors
            except Exception as e:
                logger.warning(f"Trestle validation failed for {normalized}: {e}. Proceeding with lead creation.")
                validation_warnings.append(f"Phone validation skipped due to error: {str(e)}")
        
        lead_id = self.repository.create(lead_data)
        
        result = {
            "success": True,
            "message": "Lead created successfully",
            "lead_id": lead_id,
            "phone_number": normalized  # Return normalized phone
        }
        
        # Add validation info if available
        if validation_result:
            result["phone_validation"] = {
                "is_valid": validation_result.get('is_valid'),
                "line_type": validation_result.get('line_type'),
                "carrier": validation_result.get('carrier'),
                "is_sms_capable": validation_result.get('is_sms_capable'),
                "owner_name": validation_result.get('owner_name')
            }
        
        if validation_warnings:
            result["warnings"] = validation_warnings
        
        return result
    
    def update_lead(self, lead_id: int, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing lead.
        
        Args:
            lead_id: Lead ID
            updates: Fields to update
            
        Returns:
            Dict with success status
            
        Raises:
            ResourceNotFoundError: If lead not found
            ValidationError: If phone number is invalid
        """
        # Check if lead exists
        if not self.repository.get_by_id(lead_id):
            raise ResourceNotFoundError("Lead", lead_id)
        
        # If phone_number is being updated, normalize it
        if 'phone_number' in updates:
            phone = updates['phone_number']
            if phone:
                # Validate and normalize phone number
                is_valid, normalized, error = validate_us_phone_number(phone)
                if not is_valid:
                    raise ValidationError(f"Invalid phone number: {error}")
                updates['phone_number'] = normalized
        
        # Filter valid update fields
        valid_updates = {
            k: v for k, v in updates.items()
            if k in ['name', 'Address', 'City', 'County', 'State', 'Zip', 
                    'priority', 'store_id', 'dnc_flag', 'sms_verified', 'phone_number']
        }
        
        if not valid_updates:
            return {"success": True, "message": "No changes to update"}
        
        success = self.repository.update(lead_id, valid_updates)
        
        return {
            "success": success,
            "message": f"Lead {lead_id} updated successfully" if success else "Update failed"
        }
    
    def delete_lead(self, lead_id: int) -> Dict[str, Any]:
        """
        Delete a lead.
        
        Args:
            lead_id: Lead ID
            
        Returns:
            Dict with success status
            
        Raises:
            ResourceNotFoundError: If lead not found
        """
        success = self.repository.delete(lead_id)
        
        if not success:
            raise ResourceNotFoundError("Lead", lead_id)
        
        return {
            "success": True,
            "message": f"Lead {lead_id} deleted successfully"
        }
    
    def mark_lead_called(self, lead_id: int) -> Dict[str, Any]:
        """
        Mark a lead as called.
        
        Args:
            lead_id: Lead ID
            
        Returns:
            Dict with success status
        """
        success = self.repository.mark_as_called(lead_id)
        
        return {
            "success": success,
            "message": f"Lead {lead_id} marked as called" if success else "Failed to mark lead"
        }
    
    def mark_lead_dnc(self, phone_number: str) -> Dict[str, Any]:
        """
        Mark a lead as Do Not Call.
        
        Args:
            phone_number: Phone number to mark as DNC
            
        Returns:
            Dict with success status
        """
        rows_affected = self.repository.mark_as_dnc(phone_number)
        
        if rows_affected > 0:
            return {
                "success": True,
                "message": f"Phone number {phone_number} marked as DNC"
            }
        else:
            return {
                "success": False,
                "message": f"No lead found with phone number {phone_number}"
            }
    
    def bulk_assign_leads(self, lead_ids: List[int], store_id: int) -> Dict[str, Any]:
        """
        Bulk assign leads to a store.
        
        Args:
            lead_ids: List of lead IDs
            store_id: Store ID to assign to
            
        Returns:
            Dict with success status and count
        """
        if not lead_ids:
            return {
                "success": False,
                "message": "No lead IDs provided"
            }
        
        assigned_count = self.repository.bulk_assign_to_store(lead_ids, store_id)
        
        return {
            "success": True,
            "assigned": assigned_count,
            "message": f"{assigned_count} leads assigned to store {store_id}"
        }
    
    def send_consent_sms(
        self,
        lead_id: int,
        message: Optional[str] = None,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Send consent SMS to a specific lead.
        
        Args:
            lead_id: Lead ID
            message: Optional custom message template
            force: If True, send even if already verified
            
        Returns:
            Dict with status and SMS details
            
        Raises:
            ResourceNotFoundError: If lead not found
            ValidationError: If lead is DNC or phone invalid
        """
        # Get lead
        lead = self.get_lead(lead_id)
        
        # Check DNC
        if lead.get('dnc_flag'):
            raise ValidationError("Lead is marked as DNC")
        
        # Check if already verified
        if lead.get('sms_verified') and not force:
            return {
                "lead_id": lead_id,
                "status": "skipped",
                "reason": "already_verified"
            }
        
        # Validate phone number
        phone_number = lead.get('phone_number')
        if not phone_number:
            raise ValidationError("Lead phone number is missing")
        
        is_valid, normalized_phone, error = validate_us_phone_number(phone_number)
        if not is_valid:
            raise ValidationError(f"Invalid lead phone number: {error}")
        
        # Get sender number (use PhoneNumberService)
        # CRITICAL: MUST use phone number assigned to lead's store (no fallback to unassigned)
        from services.phone_number_service import get_phone_number_service
        phone_service = get_phone_number_service()
        lead_store_id = lead.get('store_id')
        
        # MUST use numbers from the lead's assigned store only
        # Explicitly check for None, 0, or any falsy value
        if lead_store_id is None or lead_store_id == 0 or not isinstance(lead_store_id, int) or lead_store_id < 1:
            raise ValidationError(
                f"Lead {lead_id} has no valid store assigned (store_id={lead_store_id}). "
                f"Cannot send consent SMS without store assignment."
            )
        
        # CRITICAL: Ensure we're passing a valid integer store_id (never None)
        assert isinstance(lead_store_id, int) and lead_store_id > 0, \
            f"lead_store_id must be a positive integer, got: {lead_store_id} (type: {type(lead_store_id)})"
        
        # Get available numbers ONLY from the lead's assigned store
        # Explicitly pass store_id as integer to prevent any None values
        available_numbers_result = phone_service.get_available_numbers(store_id=int(lead_store_id))
        sender_number = None
        logger.info(f"[ConsentSMS] Getting phone numbers for lead_id={lead_id}, store_id={lead_store_id}")
        
        if available_numbers_result.get('available_numbers'):
            numbers = available_numbers_result['available_numbers']
            logger.info(f"[ConsentSMS] Found {len(numbers)} numbers from repository query for store_id={lead_store_id}")
            
            # CRITICAL: Log ALL numbers returned to debug any issues
            for num in numbers:
                num_store_id = num.get('store_id')
                logger.info(f"[ConsentSMS] Number {num.get('phone_number')} has store_id={num_store_id} (expected: {lead_store_id})")
            
            # CRITICAL: Filter to ensure we ONLY use numbers with the correct store_id
            # This is a safety check in case the repository query has issues
            store_assigned_numbers = [
                num for num in numbers 
                if num.get('store_id') is not None 
                and isinstance(num.get('store_id'), int)
                and num.get('store_id') == lead_store_id
            ]
            
            # Log any numbers that were filtered out (CRITICAL for debugging)
            filtered_out = [num for num in numbers if num not in store_assigned_numbers]
            if filtered_out:
                for num in filtered_out:
                    logger.error(
                        f"[ConsentSMS] ❌ FILTERED OUT: Number {num.get('phone_number')} has store_id={num.get('store_id')} "
                        f"(type: {type(num.get('store_id'))}), expected store_id={lead_store_id}"
                    )
                logger.warning(f"[ConsentSMS] Filtered out {len(filtered_out)} numbers with incorrect store_id")
            
            if store_assigned_numbers:
                selected_number = store_assigned_numbers[0]
                sender_number = selected_number.get('phone_number')
                logger.info(f"[ConsentSMS] Selected phone number {sender_number} with store_id={selected_number.get('store_id')} for lead_id={lead_id}")
                
                # Final validation: Ensure the selected number has the correct store_id
                if selected_number.get('store_id') != lead_store_id:
                    error_msg = (
                        f"CRITICAL: Selected phone number {sender_number} has store_id={selected_number.get('store_id')}, "
                        f"but lead requires store_id={lead_store_id}. This should never happen."
                    )
                    logger.error(f"[ConsentSMS] {error_msg}")
                    raise ValidationError(error_msg)
            else:
                logger.warning(f"[ConsentSMS] No numbers passed store_id validation filter for store_id={lead_store_id}")
        
        # If no numbers available for this store, raise error (do NOT fall back to unassigned)
        if not sender_number:
            raise ValidationError(
                f"No available Twilio phone numbers for store_id={lead_store_id}. "
                f"Please assign active phone numbers to this store before sending consent SMS."
            )
        
        # FINAL VALIDATION: Double-check the selected number is assigned to the correct store
        # This is the last line of defense before sending SMS
        final_check_service = get_phone_number_service()
        final_check_result = final_check_service.check_phone_number(sender_number)
        
        if not final_check_result.get('exists'):
            raise ValidationError(f"Selected phone number {sender_number} does not exist in database")
        
        final_check_store_id = final_check_result.get('store_id')
        if final_check_store_id != lead_store_id:
            error_msg = (
                f"CRITICAL ERROR: Phone number {sender_number} has store_id={final_check_store_id} "
                f"but lead requires store_id={lead_store_id}. SMS sending ABORTED."
            )
            logger.error(f"[ConsentSMS] {error_msg}")
            raise ValidationError(error_msg)
        
        if final_check_store_id is None:
            error_msg = (
                f"CRITICAL ERROR: Phone number {sender_number} is UNASSIGNED (store_id=NULL). "
                f"Lead requires store_id={lead_store_id}. SMS sending ABORTED."
            )
            logger.error(f"[ConsentSMS] {error_msg}")
            raise ValidationError(error_msg)
        
        logger.info(f"[ConsentSMS] ✅ FINAL VALIDATION PASSED: {sender_number} confirmed assigned to store_id={final_check_store_id}")
        
        # ⚠️ CRITICAL VALIDATION: Prevent sending SMS from a number to itself
        # This can happen if a lead's phone number matches a Twilio number assigned to the store
        if sender_number == normalized_phone:
            error_msg = (
                f"Cannot send consent SMS: Lead's phone number ({normalized_phone}) matches "
                f"the Twilio sender number ({sender_number}). Twilio does not allow sending SMS from a number to itself. "
                f"Please assign a different Twilio number to this store or update the lead's phone number."
            )
            logger.error(f"[ConsentSMS] ❌ {error_msg}")
            raise ValidationError(error_msg)
        
        # Get random template from sms_templates table (if no custom message provided)
        if message:
            # Use custom message if provided
            template = message
            logger.info(f"[ConsentSMS] Using custom message template for lead {lead_id}")
        else:
            # Select random template from database
            try:
                conn = self.repository.get_db_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT template_id, template_content 
                    FROM sms_templates 
                    WHERE is_active = 1 AND template_type = 'consent'
                """)
                templates = cursor.fetchall()
                cursor.close()
                conn.close()
                
                if templates:
                    selected = random.choice(templates)
                    selected_template_id, template_content = selected
                    template = template_content
                    logger.info(f"[ConsentSMS] Selected random template ID {selected_template_id} for lead {lead_id}")
                else:
                    # Fallback if no templates in database
                    template = "Hi {name}, " + config.brand.COMPANY_NAME + " here. We're following up on your earlier inquiry. Reply OK for details. STOP to opt out."
                    logger.warning(f"[ConsentSMS] No active templates found, using fallback for lead {lead_id}")
            except Exception as e:
                # Fallback on database error
                template = "Hi {name}, " + config.brand.COMPANY_NAME + " here. We're following up on your earlier inquiry. Reply OK for details. STOP to opt out."
                logger.error(f"[ConsentSMS] Error fetching templates: {e}, using fallback for lead {lead_id}")
        
        try:
            sms_body = template.format(name=lead.get('name') or "there")
        except (KeyError, IndexError):
            sms_body = template
        
        # Send SMS via TwilioService
        from services.twilio_service import TwilioService
        twilio_service = TwilioService(agent_id="ConsentSMS")
        sms_result = twilio_service.send_sms_message(
            to_number=normalized_phone,
            body=sms_body,
            from_number=sender_number
        )
        
        # Update lead consent requested timestamp and track sender number
        self.repository.update(lead_id, {
            'sms_consent_requested_at': datetime.now(),
            'sms_from_number': sender_number
        })
        
        # Log SMS conversation (use SMSService)
        from services.sms_service import get_sms_service
        sms_service = get_sms_service()
        sms_service.send_sms({
            'lead_id': lead_id,
            'phone_number': normalized_phone,
            'message_type': 'consent_request',
            'message_content': sms_body,
            'twilio_sid': sms_result.get('sid')
        })
        
        return {
            "lead_id": lead_id,
            "status": "sent",
            "twilio_sid": sms_result.get("sid"),
            "phone_number": normalized_phone
        }
    
    def export_leads_to_csv(
        self,
        dnc_only: Optional[bool] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get leads for CSV export.
        
        Args:
            dnc_only: Filter by DNC status
            limit: Maximum number of leads
            
        Returns:
            List of lead dictionaries
        """
        leads, _ = self.repository.get_all(
            limit=limit or 10000,
            offset=0,
            dnc_only=dnc_only
        )
        return leads
    
    def send_consent_sms_batch(
        self,
        limit: int = 100,
        store_id: Optional[int] = None,
        message: Optional[str] = None,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Send consent SMS to a batch of eligible leads.
        
        Eligibility criteria (matching campaign logic via repository):
        - dnc_flag = 0
        - Never sent consent SMS, or consent sent more than SMS_CONSENT_COOLDOWN_DAYS ago
        - Not already in a progressing campaign (batch pending/executing)
        - store_id matches (if provided); None = unassigned only
        - Ordered by priority, then created_at
        
        Args:
            limit: Maximum number of leads to process
            store_id: Filter by store ID (None = any store)
            message: Optional custom message template
            force: If True, send even if already verified
            
        Returns:
            Dict with results
        """
        # Get eligible leads using database-level filtering (matches campaign logic)
        eligible_leads = self.repository.get_eligible_for_consent(
            limit=min(limit, 500),
            store_id=store_id,
            force=force
        )
        
        if not eligible_leads:
            return {
                "requested": 0,
                "results": [],
                "message": f"No eligible leads found for store_id={store_id}" if store_id else "No eligible leads found"
            }
        
        results = []
        sms_interval = config.campaign.SMS_SEND_INTERVAL_SECONDS
        lead_count = len(eligible_leads)
        
        for idx, lead in enumerate(eligible_leads, 1):
            try:
                result = self.send_consent_sms(lead['lead_id'], message, force)
                results.append(result)
            except Exception as e:
                results.append({
                    "lead_id": lead['lead_id'],
                    "status": "error",
                    "error": str(e)
                })
            
            # Rate limiting: Wait between SMS sends (default 5 minutes)
            # This helps avoid carrier spam detection
            if idx < lead_count:
                interval_minutes = sms_interval // 60
                print(f"[ConsentSMS Batch] ⏳ Waiting {interval_minutes} minute(s) before next SMS ({idx}/{lead_count})...")
                time.sleep(sms_interval)
        
        return {
            "requested": len(eligible_leads),
            "processed": len(results),
            "results": results
        }
    
    def update_sms_verification(
        self,
        lead_id: Optional[int] = None,
        phone_number: Optional[str] = None,
        verified: bool = False,
        mark_dnc: bool = False,
        source: str = "manual"
    ) -> Dict[str, Any]:
        """
        Update SMS verification status for a lead.
        
        Args:
            lead_id: Lead ID (if provided)
            phone_number: Phone number (if lead_id not provided)
            verified: Verification status
            mark_dnc: If True, mark as DNC
            source: Source of verification
            
        Returns:
            Dict with updated lead info
            
        Raises:
            ResourceNotFoundError: If lead not found
        """
        # Find lead
        if lead_id:
            lead = self.get_lead(lead_id)
        elif phone_number:
            # Normalize phone number
            is_valid, normalized, error = validate_us_phone_number(phone_number)
            if not is_valid:
                raise ValidationError(f"Invalid phone number: {error}")
            
            lead = self.repository.get_by_phone(normalized)
            if not lead:
                # Try original format
                lead = self.repository.get_by_phone(phone_number)
            
            if not lead:
                raise ResourceNotFoundError("Lead", phone_number)
            lead_id = lead['lead_id']
        else:
            raise ValidationError("lead_id or phone_number is required")
        
        current_verified = lead.get('sms_verified', False)
        current_dnc = lead.get('dnc_flag', False)
        new_verified = verified
        
        # Check if this is a new verification
        is_new_verification = (not current_verified) and new_verified
        
        # Prepare updates
        updates = {
            'sms_verified': new_verified,
            'sms_verified_at': datetime.now() if new_verified else None
        }
        
        # Set consent requested if not set
        if not lead.get('sms_consent_requested_at'):
            updates['sms_consent_requested_at'] = datetime.now()
        
        if mark_dnc:
            updates['dnc_flag'] = True
        elif verified and current_dnc:
            updates['dnc_flag'] = False
        
        # Update lead
        self.repository.update(lead_id, updates)
        
        # If newly verified, create popup
        if is_new_verification:
            from services.popup_service import get_popup_service
            popup_service = get_popup_service()
            try:
                # Check if popup exists
                popups = popup_service.get_pending_popups()
                existing = any(
                    p.get('lead_id') == lead_id 
                    for p in popups.get('popups', [])
                )
                if not existing:
                    # Create popup (this will be handled by PopupService)
                    # For now, we'll let the repository handle it
                    from repositories.popup_repository import PopupRepository
                    popup_repo = PopupRepository()
                    popup_repo.create(lead_id)
            except Exception:
                pass  # Don't fail verification if popup creation fails
        
        # Get updated lead
        updated_lead = self.get_lead(lead_id)
        
        return {
            "lead_id": lead_id,
            "phone_number": updated_lead.get('phone_number'),
            "sms_verified": bool(new_verified),
            "marked_dnc": bool(mark_dnc),
            "dnc_flag": bool(updates.get('dnc_flag', current_dnc)),
            "source": source
        }
    
    def bulk_create_leads(self, leads: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Bulk create leads (for bulk import endpoint).
        
        Args:
            leads: List of lead dictionaries
            
        Returns:
            Dict with success/failed counts
        """
        success_count = 0
        failed_count = 0
        errors = []
        
        for lead in leads:
            try:
                # Validate phone number
                phone = lead.get('phone_number')
                if not phone:
                    failed_count += 1
                    errors.append("Missing phone_number in lead")
                    continue
                
                is_valid, normalized, error = validate_us_phone_number(phone)
                if not is_valid:
                    failed_count += 1
                    errors.append(f"{phone}: {error}")
                    continue
                
                lead['phone_number'] = normalized
                
                # Check for duplicate
                if self.repository.exists_by_phone(normalized):
                    failed_count += 1
                    errors.append(f"{normalized}: Already exists")
                    continue
                
                # Set defaults
                lead.setdefault('priority', 1)
                lead.setdefault('dnc_flag', False)
                lead['sms_verified'] = True  # Bulk import marks as verified
                lead['sms_verified_at'] = datetime.now()
                
                # Create lead
                new_lead_id = self.repository.create(lead)
                
                # Create popup
                if new_lead_id:
                    from repositories.popup_repository import PopupRepository
                    popup_repo = PopupRepository()
                    popup_repo.create(new_lead_id)
                    
                    # Broadcast popup added event
                    try:
                        from services.websocket_service import broadcast_event_sync, EventType
                        broadcast_event_sync(
                            EventType.POPUP_ADDED,
                            {"lead_id": new_lead_id, "popup_id": None}
                        )
                    except Exception:
                        pass
                
                success_count += 1
            except Exception as e:
                failed_count += 1
                phone = lead.get('phone_number', 'unknown')
                errors.append(f"{phone}: {str(e)}")
        
        return {
            "success": success_count,
            "failed": failed_count,
            "errors": errors if errors else None
        }
    
    def import_leads_from_csv(
        self,
        csv_content: str
    ) -> Dict[str, Any]:
        """
        Import leads from CSV content.
        
        Args:
            csv_content: CSV content as string
            
        Returns:
            Dict with import results
        """
        from utils.csv_parser import parse_csv_content
        
        # Get existing phone numbers for duplicate detection
        all_leads, _ = self.repository.get_all(limit=100000, offset=0)
        existing_phones = {lead.get('phone_number') for lead in all_leads if lead.get('phone_number')}
        
        # Parse CSV
        parse_result = parse_csv_content(csv_content, existing_phones)
        
        # Only raise for critical parsing errors (empty CSV, missing headers, etc.)
        # Validation errors on individual rows are handled via invalid_rows
        if parse_result.errors and not parse_result.valid_leads and not parse_result.invalid_rows:
            raise ValidationError(f"CSV parsing failed: {'; '.join(parse_result.errors)}")
        
        # Insert valid leads
        inserted_count = 0
        failed_inserts = []
        
        for lead in parse_result.valid_leads:
            try:
                # Ensure defaults
                lead.setdefault('priority', 1)
                lead.setdefault('dnc_flag', False)
                lead['sms_verified'] = False  # CRITICAL: NO SMS SENT
                lead['store_id'] = None  # Will be assigned later
                
                # Create lead
                self.repository.create(lead)
                inserted_count += 1
            except Exception as e:
                failed_inserts.append(f"{lead.get('phone_number', 'unknown')}: {str(e)}")
        
        return {
            "success": inserted_count,
            "failed": parse_result.invalid_count + len(failed_inserts),
            "duplicates": parse_result.duplicate_count,
            "invalid_rows": parse_result.to_dict()['invalid_rows'],
            "errors": failed_inserts + [f"Row {row['row']}: {row['error']}" for row in parse_result.to_dict()['invalid_rows']],
            "summary": {
                "total_rows_in_csv": parse_result.total_rows,
                "valid_and_inserted": inserted_count,
                "invalid_format": parse_result.invalid_count,
                "duplicates_skipped": parse_result.duplicate_count,
                "insert_failures": len(failed_inserts)
            },
            "message": f"✅ Import completed. {inserted_count} leads added. NO SMS SENT."
        }
    
    def get_safe_call_eligible_leads(
        self,
        store_id: Optional[int] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get leads eligible for safe calling (24 hours after SMS with no reply).
        
        Args:
            store_id: Optional store ID filter
            limit: Maximum number of leads
            
        Returns:
            List of eligible leads
        """
        # Build query
        where_clauses = [
            "sms_consent_requested_at IS NOT NULL",
            "sms_consent_requested_at < DATEADD(HOUR, -24, GETDATE())",
            "sms_verified = 0",
            "dnc_flag = 0",
            "(last_called IS NULL OR last_called < DATEADD(HOUR, -24, GETDATE()))"
        ]
        
        params = []
        if store_id is not None:
            where_clauses.append("store_id = ?")
            params.append(store_id)
        
        where_sql = " AND ".join(where_clauses)
        params.append(limit)
        
        query = f"""
            SELECT TOP (?)
                lead_id, name, phone_number, Address, City, State, Zip,
                store_id, sms_consent_requested_at, sms_verified, sms_verified_at,
                priority, last_called,
                DATEDIFF(HOUR, sms_consent_requested_at, GETDATE()) as hours_since_sms
            FROM OutboundLeads
            WHERE {where_sql}
            ORDER BY priority ASC, sms_consent_requested_at ASC
        """
        
        rows = self.repository.execute_query(query, tuple(params) if params else None, fetch_all=True)
        
        leads = []
        for row in rows:
            hours_since = row[13]
            reason = "safe_call_24h" if hours_since >= 24 else "pending"
            
            leads.append({
                "lead_id": row[0],
                "name": row[1],
                "phone_number": row[2],
                "Address": row[3],
                "City": row[4],
                "State": row[5],
                "Zip": row[6],
                "store_id": row[7],
                "call_eligible_reason": reason,
                "sms_consent_requested_at": row[8].isoformat() if row[8] else None,
                "sms_verified": bool(row[9]),
                "sms_verified_at": row[10].isoformat() if row[10] else None,
                "priority": row[11],
                "last_called": row[12].isoformat() if row[12] else None,
                "hours_since_sms": hours_since
            })
        
        return leads


def get_lead_service() -> LeadService:
    """Get singleton instance of LeadService."""
    return LeadService.get_instance()

