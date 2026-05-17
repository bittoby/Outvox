"""
SMS Service
Business logic for SMS conversations and photo submissions.
"""

import logging
from typing import Optional, List, Dict, Any
from repositories.sms_repository import SMSRepository
from repositories.lead_repository import LeadRepository
from core.exceptions import ResourceNotFoundError
from services.websocket_service import broadcast_event_sync, EventType

logger = logging.getLogger(__name__)


class SMSService:
    """Service for SMS business logic."""
    
    _instance = None
    
    @classmethod
    def get_instance(cls) -> 'SMSService':
        """Get singleton instance of SMSService."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """Initialize service with repository."""
        self.repository = SMSRepository()
        self.lead_repository = LeadRepository()
    
    def get_conversation(self, lead_id: int) -> Dict[str, Any]:
        """
        Get SMS conversation for a specific lead.
        
        Args:
            lead_id: Lead ID
            
        Returns:
            Dict with lead info and conversations
            
        Raises:
            ResourceNotFoundError: If lead not found
        """
        # Verify lead exists
        if not self.lead_repository.get_by_id(lead_id):
            raise ResourceNotFoundError("Lead", lead_id)
        
        result = self.repository.get_conversation_by_lead(lead_id)
        if not result:
            raise ResourceNotFoundError("SMS Conversation", lead_id)
        
        return result
    
    def get_conversation_by_phone(self, phone_number: str) -> Dict[str, Any]:
        """
        Get SMS conversation by phone number (for conversations without lead_id).
        
        Args:
            phone_number: Phone number in E.164 format
            
        Returns:
            Dict with conversations and phone info
            
        Raises:
            ResourceNotFoundError: If no conversations found
        """
        result = self.repository.get_conversation_by_phone(phone_number)
        if not result:
            raise ResourceNotFoundError("SMS Conversation", phone_number)
        
        return result
    
    def get_all_conversations(
        self,
        limit: int = 100,
        offset: int = 0,
        direction: Optional[str] = None,
        store_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get all SMS conversations with optional filtering.
        
        Args:
            limit: Maximum number of results
            offset: Number of results to skip
            direction: Filter by direction (inbound/outbound)
            store_id: Filter by store ID
            
        Returns:
            Dict with conversations list and pagination info
        """
        conversations, total_count = self.repository.get_all_conversations(
            limit=limit,
            offset=offset,
            direction=direction,
            store_id=store_id
        )
        
        return {
            "success": True,
            "conversations": conversations,
            "total_count": total_count,
            "limit": limit,
            "offset": offset
        }
    
    def delete_conversation(self, lead_id: int) -> Dict[str, Any]:
        """
        Delete all SMS conversations for a specific lead.
        
        Args:
            lead_id: Lead ID
            
        Returns:
            Dict with success status
        """
        deleted_count = self.repository.delete_conversation_by_lead(lead_id)
        
        return {
            "success": True,
            "message": f"Deleted {deleted_count} SMS conversation(s) for lead {lead_id}",
            "deleted_count": deleted_count
        }
    
    def clear_all_conversations(self) -> Dict[str, Any]:
        """
        Delete all SMS conversations.
        
        Returns:
            Dict with success status
        """
        deleted_count = self.repository.delete_all_conversations()
        
        return {
            "success": True,
            "message": f"Deleted {deleted_count} SMS conversation(s)",
            "deleted_count": deleted_count
        }
    
    def get_all_photo_submissions(
        self,
        limit: int = 100,
        offset: int = 0,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get all photo submissions with optional status filter.
        
        Args:
            limit: Maximum number of results
            offset: Number of results to skip
            status: Filter by status (pending/reviewed/appraised)
            
        Returns:
            Dict with photos list and pagination info
        """
        photos, total_count = self.repository.get_all_photo_submissions(
            limit=limit,
            offset=offset,
            status=status
        )
        
        return {
            "success": True,
            "photos": photos,
            "total_count": total_count,
            "limit": limit,
            "offset": offset
        }
    
    def delete_photo_submission(self, photo_id: int) -> Dict[str, Any]:
        """
        Delete a photo submission.
        
        Args:
            photo_id: Photo ID
            
        Returns:
            Dict with success status
            
        Raises:
            ResourceNotFoundError: If photo not found
        """
        success = self.repository.delete_photo_submission(photo_id)
        
        if not success:
            raise ResourceNotFoundError("Photo", photo_id)
        
        return {
            "success": True,
            "message": f"Deleted photo submission {photo_id}",
            "photo_id": photo_id
        }
    
    def clear_all_photos(self) -> Dict[str, Any]:
        """
        Delete all photo submissions.
        
        Returns:
            Dict with success status
        """
        deleted_count = self.repository.delete_all_photos()
        
        return {
            "success": True,
            "message": f"Deleted {deleted_count} photo submission(s)",
            "deleted_count": deleted_count
        }
    
    def send_sms(self, sms_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Log an outbound SMS message.
        
        Args:
            sms_data: SMS message data (lead_id, phone_number, message_type, message_content, twilio_sid)
            
        Returns:
            Dict with success status
        """
        sms_id = self.repository.create_sms_conversation(
            lead_id=sms_data['lead_id'],
            phone_number=sms_data['phone_number'],
            message_type=sms_data['message_type'],
            message_content=sms_data['message_content'],
            twilio_sid=sms_data.get('twilio_sid'),
            direction='outbound'
        )
        
        # Broadcast SMS sent event via WebSocket
        try:
            broadcast_event_sync(
                EventType.SMS_SENT,
                {
                    "lead_id": sms_data['lead_id'],
                    "phone_number": sms_data['phone_number'],
                    "message_type": sms_data['message_type'],
                    "twilio_sid": sms_data.get('twilio_sid'),
                    "message_content": sms_data.get('message_content', '')[:100]  # First 100 chars for preview
                }
            )
            logger.info(
                f"SMS_SENT_BROADCAST | LeadID: {sms_data['lead_id']} | "
                f"Phone: {sms_data['phone_number']} | Type: {sms_data['message_type']}"
            )
        except Exception as ws_error:
            logger.warning(
                f"SMS_BROADCAST_FAILED | LeadID: {sms_data['lead_id']} | Error: {ws_error}"
            )
            # Don't fail SMS logging if broadcast fails
        
        return {
            "status": "success",
            "message": "SMS logged successfully",
            "sms_id": sms_id
        }
    
    def receive_sms(self, sms_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Log an inbound SMS message.
        
        Args:
            sms_data: SMS message data (lead_id, phone_number, message_type, message_content, twilio_sid)
            
        Returns:
            Dict with success status
        """
        sms_id = self.repository.create_sms_conversation(
            lead_id=sms_data['lead_id'],
            phone_number=sms_data['phone_number'],
            message_type=sms_data['message_type'],
            message_content=sms_data['message_content'],
            twilio_sid=sms_data.get('twilio_sid'),
            direction='inbound'
        )
        
        # Broadcast SMS received event via WebSocket
        try:
            broadcast_event_sync(
                EventType.SMS_RECEIVED,
                {
                    "lead_id": sms_data['lead_id'],
                    "phone_number": sms_data['phone_number'],
                    "message_type": sms_data['message_type'],
                    "message_content": sms_data['message_content'],
                    "twilio_sid": sms_data.get('twilio_sid')
                }
            )
            logger.info(
                f"SMS_RECEIVED_BROADCAST | LeadID: {sms_data['lead_id']} | "
                f"Phone: {sms_data['phone_number']} | Type: {sms_data['message_type']}"
            )
        except Exception as ws_error:
            logger.warning(
                f"SMS_BROADCAST_FAILED | LeadID: {sms_data['lead_id']} | Error: {ws_error}"
            )
            # Don't fail SMS logging if broadcast fails
        
        return {
            "status": "success",
            "message": "Incoming SMS logged successfully",
            "sms_id": sms_id
        }
    
    def submit_photo(self, photo_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Submit a photo for appraisal.
        
        Args:
            photo_data: Photo submission data (lead_id, phone_number, photo_url, status)
            
        Returns:
            Dict with success status
        """
        photo_id = self.repository.create_photo_submission(
            lead_id=photo_data['lead_id'],
            phone_number=photo_data['phone_number'],
            photo_url=photo_data['photo_url'],
            status=photo_data.get('status', 'pending')
        )
        
        # Broadcast photo submitted event
        try:
            broadcast_event_sync(
                EventType.PHOTO_SUBMITTED,
                {
                    "lead_id": photo_data['lead_id'],
                    "phone_number": photo_data['phone_number'],
                    "photo_url": photo_data['photo_url']
                }
            )
        except Exception:
            pass  # Don't fail photo submission if broadcast fails
        
        return {
            "status": "success",
            "message": "Photo submitted successfully",
            "photo_id": photo_id
        }
    
    def get_pending_photos(self) -> Dict[str, Any]:
        """
        Get all pending photo submissions.
        
        Returns:
            Dict with photos list
        """
        photos = self.repository.get_pending_photos()
        
        return {
            "success": True,
            "photos": photos
        }
    
    def update_photo_status(
        self,
        photo_id: int,
        status: str,
        reviewed_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update photo submission status.
        
        Args:
            photo_id: Photo ID
            status: New status (reviewed, appraised, etc.)
            reviewed_by: Optional reviewer name
            
        Returns:
            Dict with success status
            
        Raises:
            ResourceNotFoundError: If photo not found
        """
        success = self.repository.update_photo_status(photo_id, status, reviewed_by)
        
        if not success:
            raise ResourceNotFoundError("Photo", photo_id)
        
        # Broadcast photo updated event
        try:
            broadcast_event_sync(
                EventType.PHOTO_UPDATED,
                {
                    "photo_id": photo_id,
                    "status": status,
                    "reviewed_by": reviewed_by
                }
            )
        except Exception:
            pass  # Don't fail photo update if broadcast fails
        
        return {
            "status": "success",
            "message": f"Photo status updated to {status}",
            "photo_id": photo_id
        }


def get_sms_service() -> SMSService:
    """Get singleton instance of SMSService."""
    return SMSService.get_instance()


