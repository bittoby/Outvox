"""
Popup Service
Business logic for popup queue management.
"""

from typing import Optional, Dict, Any
from repositories.popup_repository import PopupRepository
from repositories.lead_repository import LeadRepository
from core.exceptions import ResourceNotFoundError, ValidationError
from services.websocket_service import broadcast_event_sync, EventType


class PopupService:
    """Service for popup business logic."""
    
    _instance = None
    
    @classmethod
    def get_instance(cls) -> 'PopupService':
        """Get singleton instance of PopupService."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """Initialize service with repository."""
        self.repository = PopupRepository()
        self.lead_repository = LeadRepository()
    
    def get_pending_popups(
        self,
        limit: int = 50,
        offset: int = 0,
        sort_field: Optional[str] = None,
        sort_direction: Optional[str] = None,
        priority: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get pending popup notifications with pagination and sorting.
        
        Args:
            limit: Maximum number of results
            offset: Number of results to skip
            sort_field: Field to sort by (created_at, priority, name)
            sort_direction: Sort direction (asc, desc)
            priority: Filter by priority level
            
        Returns:
            Dict with popups list and pagination info
        """
        popups, total = self.repository.get_pending_popups(
            limit=limit,
            offset=offset,
            sort_field=sort_field,
            sort_direction=sort_direction,
            priority=priority
        )
        
        return {
            'pending_popups': popups,
            'total': total,
            'limit': limit,
            'offset': offset
        }
    
    def dismiss_popup(self, popup_id: int) -> Dict[str, Any]:
        """
        Dismiss a popup notification.
        
        Args:
            popup_id: Popup ID
            
        Returns:
            Dict with success status
            
        Raises:
            ResourceNotFoundError: If popup not found
        """
        success = self.repository.dismiss_popup(popup_id)
        
        if not success:
            raise ResourceNotFoundError("Popup", popup_id)
        
        # Broadcast popup dismissed event
        broadcast_event_sync(
            EventType.POPUP_DISMISSED,
            {"popup_id": popup_id}
        )
        
        return {
            "success": True,
            "message": f"Popup {popup_id} dismissed"
        }
    
    def prepare_manual_dial(self, lead_id: int, employee_name: str) -> Dict[str, Any]:
        """
        Prepare a manual dial for a lead.
        
        Args:
            lead_id: Lead ID
            employee_name: Name of employee making the call
            
        Returns:
            Dict with lead information
            
        Raises:
            ResourceNotFoundError: If lead not found
            ValidationError: If lead is on DNC or not SMS verified
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # Get lead info
        lead = self.lead_repository.get_by_id(lead_id)
        
        if not lead:
            raise ResourceNotFoundError("Lead", lead_id)
        
        # Check if lead is on DNC
        if lead.get('dnc_flag'):
            raise ValidationError(f"Lead {lead_id} is on Do Not Call list")
        
        # Check if lead is SMS verified
        # Handle BIT type from SQL Server (can be 0, 1, or None)
        sms_verified = lead.get('sms_verified')
        
        # Debug logging to help diagnose issues
        logger.info(f"[PopupService] Checking lead {lead_id}: sms_verified={sms_verified} (type: {type(sms_verified)}, raw value: {repr(sms_verified)})")
        logger.info(f"[PopupService] Full lead data keys: {list(lead.keys()) if lead else 'None'}")
        logger.info(f"[PopupService] Full lead data: {lead}")
        
        # The _row_to_dict converts BIT (0/1) to bool (False/True)
        # So sms_verified should be True if verified, False if not
        # But handle edge cases: None, 0, False all mean not verified
        # Only True or 1 mean verified
        
        # First check if the key exists
        if 'sms_verified' not in lead:
            logger.error(f"[PopupService] Lead {lead_id} missing 'sms_verified' key in response!")
            # Try direct database query as fallback
            try:
                import pyodbc
                import os
                conn_str = (
                    f"DRIVER={{ODBC Driver 18 for SQL Server}};TrustServerCertificate=yes;"
                    f"SERVER={os.getenv('SQLServer')};"
                    f"DATABASE={os.getenv('SQLDatabase')};"
                    f"UID={os.getenv('SQLUser')};"
                    f"PWD={os.getenv('SQLPassword')}"
                )
                conn = pyodbc.connect(conn_str)
                cursor = conn.cursor()
                cursor.execute("SELECT sms_verified FROM OutboundLeads WHERE lead_id = ?", (lead_id,))
                db_row = cursor.fetchone()
                if db_row:
                    db_sms_verified = bool(db_row[0]) if db_row[0] is not None else False
                    logger.info(f"[PopupService] Direct DB query: sms_verified={db_row[0]} (type: {type(db_row[0])}), converted={db_sms_verified}")
                    sms_verified = db_sms_verified
                conn.close()
            except Exception as e:
                logger.error(f"[PopupService] Error querying database directly: {e}")
        
        if sms_verified is None:
            logger.warning(f"[PopupService] Lead {lead_id} SMS verification is None")
            raise ValidationError("Lead has not provided SMS consent")
        
        # Convert to bool if it's an int (0 or 1)
        if isinstance(sms_verified, int):
            sms_verified = bool(sms_verified)
            logger.info(f"[PopupService] Converted int to bool: {sms_verified}")
        
        # Now check if it's truthy (True)
        if not sms_verified:
            logger.warning(f"[PopupService] Lead {lead_id} SMS verification check failed: sms_verified={sms_verified} (type: {type(sms_verified)})")
            raise ValidationError("Lead has not provided SMS consent")
        
        logger.info(f"[PopupService] ✅ Lead {lead_id} is SMS verified, proceeding with dial")
        
        # Mark popup as dialed
        self.repository.mark_as_dialed(lead_id, employee_name)
        
        return {
            "success": True,
            "lead": {
                "lead_id": lead['lead_id'],
                "name": lead.get('name'),
                "phone_number": lead.get('phone_number'),
                "store_id": lead.get('store_id'),
                "sms_verified": lead.get('sms_verified', False)
            }
        }
    
    def update_call_sid(self, popup_id: int, call_sid: str) -> Dict[str, Any]:
        """
        Update popup with call SID after call is initiated.
        
        Args:
            popup_id: Popup ID
            call_sid: Twilio call SID
            
        Returns:
            Dict with success status
            
        Raises:
            ResourceNotFoundError: If popup not found
        """
        success = self.repository.update_call_sid(popup_id, call_sid)
        
        if not success:
            raise ResourceNotFoundError("Popup", popup_id)
        
        return {
            "success": True,
            "message": f"Popup {popup_id} updated with call SID",
            "popup_id": popup_id,
            "call_sid": call_sid
        }


def get_popup_service() -> PopupService:
    """Get singleton instance of PopupService."""
    return PopupService.get_instance()


