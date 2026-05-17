"""
Phone Status Service
Business logic for phone number status tracking and suppression.
"""

from typing import Dict, Any, Optional
from repositories.phone_status_repository import PhoneStatusRepository
from utils.phone_validator import validate_us_phone_number


class PhoneStatusService:
    """Service for phone status business logic."""
    
    _instance = None
    
    @classmethod
    def get_instance(cls) -> 'PhoneStatusService':
        """Get singleton instance of PhoneStatusService."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """Initialize service with repository."""
        self.repository = PhoneStatusRepository()
    
    def track_error(self, phone_number: str, error_code: int) -> Dict[str, Any]:
        """
        Track an error for a phone number.
        
        Args:
            phone_number: Phone number in E.164 format
            error_code: Twilio error code
            
        Returns:
            Dict with success status
        """
        # Validate and normalize phone number
        is_valid, normalized_phone, error = validate_us_phone_number(phone_number)
        if not is_valid:
            return {
                'success': False,
                'error': f"Invalid phone number: {error}"
            }
        
        # Update error tracking
        self.repository.update_error(normalized_phone, error_code)
        
        return {
            'success': True,
            'phone_number': normalized_phone,
            'error_code': error_code
        }
    
    def should_allow_sms(self, phone_number: str) -> Dict[str, Any]:
        """
        Check if SMS is allowed for a phone number.
        
        Args:
            phone_number: Phone number in E.164 format
            
        Returns:
            Dict with 'allowed' boolean and reason if blocked
        """
        # Validate and normalize phone number
        is_valid, normalized_phone, error = validate_us_phone_number(phone_number)
        if not is_valid:
            return {
                'allowed': False,
                'reason': f"Invalid phone number: {error}",
                'phone_number': phone_number
            }
        
        # Check if blocked
        is_allowed = self.repository.check_allowed(normalized_phone)
        
        if not is_allowed:
            # Get status to determine reason
            status = self.repository.get_by_phone(normalized_phone)
            reason = "Unknown"
            
            if status:
                if status.get('is_opted_out', False):
                    reason = "User opted out (STOP reply)"
                elif status.get('is_hard_bounce', False):
                    reason = "Hard bounce (invalid/disconnected number)"
                elif not status.get('is_sms_allowed', True):
                    reason = "SMS not allowed (suppressed)"
            
            return {
                'allowed': False,
                'reason': reason,
                'phone_number': normalized_phone,
                'status': status
            }
        
        return {
            'allowed': True,
            'phone_number': normalized_phone
        }
    
    def suppress_number(
        self,
        phone_number: str,
        reason: str,
        is_hard_bounce: bool = False,
        is_opted_out: bool = False
    ) -> Dict[str, Any]:
        """
        Suppress a phone number (block future SMS).
        
        Args:
            phone_number: Phone number in E.164 format
            reason: Reason for suppression
            is_hard_bounce: Whether this is a hard bounce
            is_opted_out: Whether user opted out
            
        Returns:
            Dict with success status
        """
        # Validate and normalize phone number
        is_valid, normalized_phone, error = validate_us_phone_number(phone_number)
        if not is_valid:
            return {
                'success': False,
                'error': f"Invalid phone number: {error}"
            }
        
        # Suppress the number
        self.repository.set_suppressed(
            normalized_phone,
            reason,
            is_hard_bounce=is_hard_bounce,
            is_opted_out=is_opted_out
        )
        
        return {
            'success': True,
            'phone_number': normalized_phone,
            'reason': reason
        }
    
    def get_error_counts(self, phone_number: str) -> Dict[str, Any]:
        """
        Get error counts for a phone number.
        
        Args:
            phone_number: Phone number in E.164 format
            
        Returns:
            Dict with error counts
        """
        # Validate and normalize phone number
        is_valid, normalized_phone, error = validate_us_phone_number(phone_number)
        if not is_valid:
            return {
                'success': False,
                'error': f"Invalid phone number: {error}"
            }
        
        counts = self.repository.get_error_counts(normalized_phone)
        
        return {
            'success': True,
            'phone_number': normalized_phone,
            'error_counts': counts
        }
    
    def get_status(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """
        Get full status for a phone number.
        
        Args:
            phone_number: Phone number in E.164 format
            
        Returns:
            Phone status dictionary or None
        """
        # Validate and normalize phone number
        is_valid, normalized_phone, error = validate_us_phone_number(phone_number)
        if not is_valid:
            return None
        
        return self.repository.get_by_phone(normalized_phone)
    
    def update_carrier_type(self, phone_number: str, carrier_type: str) -> Dict[str, Any]:
        """
        Update carrier type for a phone number.
        
        Args:
            phone_number: Phone number in E.164 format
            carrier_type: Carrier type ('mobile', 'landline', 'voip')
            
        Returns:
            Dict with success status
        """
        # Validate and normalize phone number
        is_valid, normalized_phone, error = validate_us_phone_number(phone_number)
        if not is_valid:
            return {
                'success': False,
                'error': f"Invalid phone number: {error}"
            }
        
        self.repository.create_or_update(normalized_phone, {
            'carrier_type': carrier_type
        })
        
        return {
            'success': True,
            'phone_number': normalized_phone,
            'carrier_type': carrier_type
        }
    
    def set_opted_out(self, phone_number: str) -> Dict[str, Any]:
        """
        Mark a phone number as opted out.
        
        Args:
            phone_number: Phone number in E.164 format
            
        Returns:
            Dict with success status
        """
        return self.suppress_number(
            phone_number,
            reason='opted_out',
            is_opted_out=True
        )
    
    def set_hard_bounce(self, phone_number: str, reason: str = 'hard_bounce') -> Dict[str, Any]:
        """
        Mark a phone number as hard bounce.
        
        Args:
            phone_number: Phone number in E.164 format
            reason: Reason for hard bounce
            
        Returns:
            Dict with success status
        """
        return self.suppress_number(
            phone_number,
            reason=reason,
            is_hard_bounce=True
        )


def get_phone_status_service() -> PhoneStatusService:
    """Get singleton instance of PhoneStatusService."""
    return PhoneStatusService.get_instance()



