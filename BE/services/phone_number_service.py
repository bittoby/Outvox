"""
Phone Number Service
Business logic for phone number management.
"""

from typing import Optional, Dict, Any
from repositories.phone_number_repository import PhoneNumberRepository
from repositories.store_repository import StoreRepository
from core.exceptions import ResourceNotFoundError, ValidationError


class PhoneNumberService:
    """Service for phone number business logic."""
    
    _instance = None
    
    @classmethod
    def get_instance(cls) -> 'PhoneNumberService':
        """Get singleton instance of PhoneNumberService."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """Initialize service with repository."""
        self.repository = PhoneNumberRepository()
        self.store_repository = StoreRepository()
    
    def get_all_phone_numbers(self, store_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get all phone numbers with optional store filter.
        
        Args:
            store_id: Optional store ID filter
            
        Returns:
            Dict with phone numbers list
        """
        phone_numbers = self.repository.get_all(store_id=store_id)
        
        return {
            "success": True,
            "phone_numbers": phone_numbers,
            "count": len(phone_numbers)
        }
    
    def get_phone_number(self, number_id: int) -> Dict[str, Any]:
        """
        Get phone number by ID.
        
        Args:
            number_id: Phone number ID
            
        Returns:
            Dict with phone number details
            
        Raises:
            ResourceNotFoundError: If phone number not found
        """
        phone = self.repository.get_by_id(number_id)
        
        if not phone:
            raise ResourceNotFoundError("Phone Number", number_id)
        
        return {
            "success": True,
            "phone_number": phone
        }
    
    def assign_to_store(self, number_id: int, store_id: Optional[int]) -> Dict[str, Any]:
        """
        Assign phone number to a store (or unassign if store_id is None).
        
        Args:
            number_id: Phone number ID
            store_id: Store ID to assign to (None to unassign)
            
        Returns:
            Dict with success status
            
        Raises:
            ResourceNotFoundError: If phone number or store not found
        """
        # Verify phone number exists
        phone = self.repository.get_by_id(number_id)
        if not phone:
            raise ResourceNotFoundError("Phone Number", number_id)
        
        # Verify store exists if provided
        if store_id is not None:
            if not self.store_repository.get_by_id(store_id):
                raise ResourceNotFoundError("Store", store_id)
        
        success = self.repository.assign_to_store(number_id, store_id)
        
        if not success:
            raise ValidationError(f"Failed to assign phone number {number_id}")
        
        # Get updated phone number info
        updated_phone = self.repository.get_by_id(number_id)
        
        return {
            "success": True,
            "message": f"Phone number assigned to store {store_id}" if store_id else "Phone number unassigned from store",
            "phone_number_id": updated_phone['number_id'],
            "phone_number": updated_phone['phone_number'],
            "store_id": updated_phone['store_id'],
            "store_name": updated_phone.get('store_name')
        }
    
    def update_active_status(self, number_id: int, is_active: bool) -> Dict[str, Any]:
        """
        Update phone number active status.
        
        Args:
            number_id: Phone number ID
            is_active: Active status
            
        Returns:
            Dict with success status
            
        Raises:
            ResourceNotFoundError: If phone number not found
        """
        if not self.repository.get_by_id(number_id):
            raise ResourceNotFoundError("Phone Number", number_id)
        
        success = self.repository.update_active_status(number_id, is_active)
        
        if not success:
            raise ValidationError(f"Failed to update phone number {number_id}")
        
        action = "activated" if is_active else "deactivated"
        return {
            "success": True,
            "message": f"Phone number {number_id} {action}"
        }
    
    def delete_phone_number(self, number_id: int) -> Dict[str, Any]:
        """
        Delete a phone number.
        
        Args:
            number_id: Phone number ID
            
        Returns:
            Dict with success status
            
        Raises:
            ResourceNotFoundError: If phone number not found
        """
        if not self.repository.get_by_id(number_id):
            raise ResourceNotFoundError("Phone Number", number_id)
        
        success = self.repository.delete(number_id)
        
        if not success:
            raise ResourceNotFoundError("Phone Number", number_id)
        
        return {
            "success": True,
            "message": f"Phone number {number_id} deleted successfully"
        }
    
    def get_available_numbers(self, store_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get available phone numbers (under limits).
        
        Args:
            store_id: Optional store ID filter
            
        Returns:
            Dict with available numbers list
        """
        numbers = self.repository.get_available_numbers(store_id=store_id)
        
        return {
            "success": True,
            "available_numbers": numbers,
            "count": len(numbers)
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get overall statistics for all phone numbers.
        
        Returns:
            Dict with statistics
        """
        stats = self.repository.get_statistics()
        
        return {
            "success": True,
            "stats": stats
        }
    
    def check_phone_number(self, phone_number: str) -> Dict[str, Any]:
        """
        Check if a phone number exists and get its status.
        
        Args:
            phone_number: Phone number to check
            
        Returns:
            Dict with phone number info
        """
        phone = self.repository.get_by_phone(phone_number)
        
        if phone:
            return {
                "exists": True,
                "is_active": phone.get('is_active', False),
                "phone_number": phone.get('phone_number'),
                "store_id": phone.get('store_id'),
                "daily_call_count": phone.get('daily_call_count', 0),
                "hourly_call_count": phone.get('hourly_call_count', 0),
                "daily_sms_count": phone.get('daily_sms_count', 0)
            }
        else:
            return {
                "exists": False,
                "is_active": False,
                "phone_number": phone_number,
                "store_id": None,
                "daily_call_count": 0,
                "hourly_call_count": 0
            }
    
    def update_usage(self, phone_number: str) -> Dict[str, Any]:
        """
        Update usage count and timestamp for a phone number.
        
        Args:
            phone_number: Phone number to update
            
        Returns:
            Dict with success status
            
        Note:
            If phone number doesn't exist, returns success with warning (non-blocking)
        """
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            logger.info(f"[PhoneNumberService] Checking if phone number exists: {phone_number}")
            phone = self.repository.get_by_phone(phone_number)
            
            if not phone:
                # Phone number doesn't exist - log warning but don't fail
                # This can happen if number was deleted or not properly registered
                logger.warning(f"Phone number {phone_number} not found in database - skipping usage update")
                return {
                    "status": "success",
                    "message": f"Phone number {phone_number} not found - usage update skipped",
                    "warning": "Phone number not in database"
                }
            
            logger.info(f"[PhoneNumberService] Phone number found, updating usage: {phone_number}")
            logger.info(f"[PhoneNumberService] Current usage - calls: {phone.get('daily_call_count', 0)}, SMS: {phone.get('daily_sms_count', 0)}")
            
            success = self.repository.update_usage(phone_number)
            
            if not success:
                logger.error(f"[PhoneNumberService] Repository update_usage returned False for {phone_number}")
                raise ValidationError(f"Failed to update usage for {phone_number}")
            
            logger.info(f"[PhoneNumberService] ✅ Successfully updated usage for {phone_number}")
            return {
                "status": "success",
                "message": f"Updated usage for {phone_number}"
            }
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"[PhoneNumberService] ❌ Unexpected error updating usage for {phone_number}: {e}")
            import traceback
            logger.error(f"[PhoneNumberService] Traceback: {traceback.format_exc()}")
            raise
    
    def set_rotation_weight(self, phone_number: str, weight: int) -> Dict[str, Any]:
        """
        Set rotation weight for a phone number.
        
        Args:
            phone_number: Phone number
            weight: Rotation weight (non-negative)
            
        Returns:
            Dict with success status
            
        Raises:
            ResourceNotFoundError: If phone number not found
            ValidationError: If weight is invalid
        """
        if weight < 0:
            raise ValidationError("Rotation weight must be non-negative")
        
        phone = self.repository.get_by_phone(phone_number)
        if not phone:
            raise ResourceNotFoundError("Phone Number", phone_number)
        
        success = self.repository.set_rotation_weight(phone_number, weight)
        
        if not success:
            raise ValidationError(f"Failed to set rotation weight for {phone_number}")
        
        return {
            "status": "success",
            "message": f"Rotation weight set to {weight} for {phone_number}"
        }
    
    def create_phone_number(
        self,
        phone_number: str,
        rotation_weight: int = 1,
        store_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Create a new phone number.
        
        Args:
            phone_number: Phone number (E.164 format)
            rotation_weight: Rotation weight (default 1)
            store_id: Optional store ID
            
        Returns:
            Dict with success status and phone number details
            
        Raises:
            ValidationError: If store_id is invalid
        """
        # Validate store_id if provided
        if store_id is not None:
            if not self.store_repository.get_by_id(store_id):
                raise ResourceNotFoundError("Store", store_id)
        
        try:
            number_id = self.repository.create(phone_number, rotation_weight, store_id)
            
            return {
                "status": "success",
                "message": f"Twilio number {phone_number} added successfully",
                "phone_number": phone_number,
                "rotation_weight": rotation_weight,
                "is_active": True,
                "store_id": store_id,
                "number_id": number_id
            }
        except Exception as e:
            if "duplicate" in str(e).lower() or "unique" in str(e).lower():
                raise ValidationError("Phone number already exists")
            raise ValidationError(f"Error adding number: {str(e)}")
    
    def delete_phone_number_by_phone(self, phone_number: str) -> Dict[str, Any]:
        """
        Delete a phone number by phone number string.
        
        Args:
            phone_number: Phone number to delete
            
        Returns:
            Dict with success status
            
        Raises:
            ResourceNotFoundError: If phone number not found
        """
        phone = self.repository.get_by_phone(phone_number)
        if not phone:
            raise ResourceNotFoundError("Phone Number", phone_number)
        
        success = self.repository.delete_by_phone(phone_number)
        
        if not success:
            raise ResourceNotFoundError("Phone Number", phone_number)
        
        return {
            "status": "success",
            "message": f"Twilio number {phone_number} deleted"
        }
    
    def count_active_numbers(self, store_id: Optional[int] = None) -> int:
        """
        Count active phone numbers for a store or unassigned.
        
        Args:
            store_id: Optional store ID. If None, counts unassigned active numbers.
            
        Returns:
            Count of active phone numbers
        """
        return self.repository.count_active_numbers(store_id)


def get_phone_number_service() -> PhoneNumberService:
    """Get singleton instance of PhoneNumberService."""
    return PhoneNumberService.get_instance()

