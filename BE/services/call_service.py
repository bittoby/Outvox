"""
Call Service
Business logic for call history and results.
"""

from typing import Optional, Dict, Any, List
from repositories.call_repository import CallRepository
from core.exceptions import ResourceNotFoundError, ValidationError
from services.websocket_service import broadcast_event_sync, EventType


class CallService:
    """Service for call business logic."""
    
    _instance = None
    
    @classmethod
    def get_instance(cls) -> 'CallService':
        """Get singleton instance of CallService."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """Initialize service with repository."""
        self.repository = CallRepository()
    
    def get_call_history(
        self,
        limit: int = 100,
        offset: int = 0,
        result_type: Optional[str] = None,
        store_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get call history with pagination and filtering.
        
        Args:
            limit: Maximum number of results (max 500)
            offset: Number of results to skip
            result_type: Filter by result type
            store_id: Filter by store ID
            
        Returns:
            Dict with calls list and pagination info
        """
        calls, total = self.repository.get_call_history(
            limit=limit,
            offset=offset,
            result_type=result_type,
            store_id=store_id
        )
        
        # Transform calls to match frontend CallHistoryItem interface
        formatted_calls = []
        for call in calls:
            # Handle timestamp - ensure it's a string
            timestamp = call.get("created_at")
            if timestamp is None:
                from datetime import datetime
                timestamp = datetime.now().isoformat()
            elif not isinstance(timestamp, str):
                # If it's a datetime object, convert to ISO string
                timestamp = timestamp.isoformat() if hasattr(timestamp, 'isoformat') else str(timestamp)
            
            formatted_calls.append({
                "id": call.get("result_id") or 0,
                "lead_id": call.get("lead_id") or 0,
                "agent_id": call.get("agent_id") or "",
                "twilio_number": call.get("twilio_number") or "",
                "call_sid": call.get("call_sid") or "",
                "call_duration": call.get("call_duration") or 0,
                "result_type": call.get("result_type") or "",
                "timestamp": timestamp,
                "lead_name": call.get("lead_name"),
                "phone_number": call.get("lead_phone") or "",
                "lead_address": None,  # Not included in history query
                "lead_city": None,  # Not included in history query
                "lead_state": None  # Not included in history query
            })
        
        # Return array directly (frontend expects array, not object with 'calls' property)
        return formatted_calls
    
    def get_call_details(self, result_id: int) -> Dict[str, Any]:
        """
        Get detailed information about a specific call.
        
        Args:
            result_id: Call result ID
            
        Returns:
            Dict with call details
            
        Raises:
            ResourceNotFoundError: If call not found
        """
        call = self.repository.get_call_by_id(result_id)
        
        if not call:
            raise ResourceNotFoundError("Call", result_id)
        
        # Transform call data to match frontend CallDetails interface
        # Handle timestamp - ensure it's a string
        timestamp = call.get("created_at")
        if timestamp is None:
            from datetime import datetime
            timestamp = datetime.now().isoformat()
        elif not isinstance(timestamp, str):
            # If it's a datetime object, convert to ISO string
            timestamp = timestamp.isoformat() if hasattr(timestamp, 'isoformat') else str(timestamp)
        
        # Map field names to match CallDetails interface
        formatted_call = {
            "id": call.get("result_id") or 0,
            "lead_id": call.get("lead_id") or 0,
            "agent_id": call.get("agent_id") or "",
            "twilio_number": call.get("twilio_number") or "",
            "call_sid": call.get("call_sid") or "",
            "call_duration": call.get("call_duration") or 0,
            "result_type": call.get("result_type") or "",
            "customer_transcript": call.get("customer_transcript") or "",
            "agent_transcript": call.get("agent_transcript") or "",
            "combined_transcript": call.get("combined_transcript") or "",
            "timestamp": timestamp,
            "lead_name": call.get("lead_name"),
            "phone_number": call.get("lead_phone") or "",
            "lead_address": call.get("lead_address"),
            "lead_city": call.get("lead_city"),
            "lead_county": call.get("lead_county"),
            "lead_state": call.get("lead_state"),
            "lead_zip": call.get("lead_zip")
        }
        
        # Return call data directly (frontend expects CallDetails object, not wrapped)
        return formatted_call
    
    def save_call_result(self, call_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save the result of an outbound call.
        
        Args:
            call_data: Call result data
            
        Returns:
            Dict with success status
        """
        # Validate required fields
        lead_id = call_data.get('lead_id')
        if not lead_id:
            raise ValidationError("lead_id is required in call_data")
        
        # Create call result
        result_id = self.repository.create_call_result(call_data)
        
        # Update lead after call
        result_type = call_data.get('result_type', '')
        is_dnc = result_type == 'dnc'
        
        self.repository.update_lead_after_call(
            lead_id=lead_id,
            result_type=result_type,
            is_dnc=is_dnc
        )
        
        # Broadcast call stats update (fire and forget)
        broadcast_event_sync(
            EventType.CALL_STATS_UPDATE,
            {
                "call_id": result_id,
                "lead_id": call_data.get('lead_id'),
                "result_type": result_type,
                "message": "Call completed"
            }
        )
        
        return {
            "success": True,
            "message": f"Call result saved for lead {call_data.get('lead_id')}",
            "result_id": result_id
        }
    
    def delete_call_result(self, result_id: int) -> Dict[str, Any]:
        """
        Delete a call result record.
        
        Args:
            result_id: Call result ID
            
        Returns:
            Dict with success status
            
        Raises:
            ResourceNotFoundError: If call not found
        """
        success = self.repository.delete_call_result(result_id)
        
        if not success:
            raise ResourceNotFoundError("Call", result_id)
        
        return {
            "success": True,
            "message": f"Call result {result_id} deleted successfully"
        }


def get_call_service() -> CallService:
    """Get singleton instance of CallService."""
    return CallService.get_instance()


