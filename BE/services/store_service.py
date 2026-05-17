"""
Store Service
Business logic for store management.
"""

from typing import Optional, List, Dict, Any
from repositories.store_repository import StoreRepository
from repositories.phone_number_repository import PhoneNumberRepository
from repositories.lead_repository import LeadRepository
from repositories.call_repository import CallRepository
from repositories.base import BaseRepository
from core.exceptions import ResourceNotFoundError, ValidationError


class StoreService:
    """Service for store business logic."""
    
    _instance = None
    
    # Constants for per-number quotas
    SMS_PER_NUMBER = 50
    CALLS_PER_NUMBER = 30
    
    @classmethod
    def get_instance(cls) -> 'StoreService':
        """Get singleton instance of StoreService."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """Initialize service with repositories."""
        self.repository = StoreRepository()
        self.phone_repository = PhoneNumberRepository()
        self.lead_repository = LeadRepository()
    
    def get_all_stores(self) -> Dict[str, Any]:
        """
        Get list of all stores with statistics.
        
        Quotas are calculated dynamically based on assigned phone numbers.
        
        Returns:
            Dict with stores list
        """
        stores = self.repository.get_stores_with_statistics()
        
        # Enrich with quotas and usage
        enriched_stores = []
        for store in stores:
            store_id = store['store_id']
            phone_count = store['total_phone_numbers']
            
            # Calculate quotas
            calculated_sms_quota = phone_count * self.SMS_PER_NUMBER
            calculated_call_quota = phone_count * self.CALLS_PER_NUMBER
            
            # Get usage statistics
            usage = self.repository.get_store_usage_today(store_id)
            
            store['daily_sms_quota'] = calculated_sms_quota
            store['daily_call_quota'] = calculated_call_quota
            store['sms_sent_today'] = usage['sms_sent_today']
            store['calls_made_today'] = usage['calls_made_today']
            
            enriched_stores.append(store)
        
        return {
            "success": True,
            "stores": enriched_stores,
            "count": len(enriched_stores)
        }
    
    def get_store(self, store_id: int) -> Dict[str, Any]:
        """
        Get detailed information about a specific store.
        
        Args:
            store_id: Store ID
            
        Returns:
            Dict with store details
            
        Raises:
            ResourceNotFoundError: If store not found
        """
        store = self.repository.get_store_with_statistics(store_id)
        
        if not store:
            raise ResourceNotFoundError("Store", store_id)
        
        # Enrich with quotas
        phone_count = store['total_phone_numbers']
        calculated_sms_quota = phone_count * self.SMS_PER_NUMBER
        calculated_call_quota = phone_count * self.CALLS_PER_NUMBER
        
        store['daily_sms_quota'] = calculated_sms_quota
        store['daily_call_quota'] = calculated_call_quota
        
        return {
            "success": True,
            "store": store
        }
    
    def create_store(self, store_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new store.
        
        Args:
            store_data: Store information
            
        Returns:
            Dict with created store ID
        """
        store_id = self.repository.create(store_data)
        
        return {
            "success": True,
            "message": "Store created successfully",
            "store_id": store_id
        }
    
    def update_store(self, store_id: int, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing store.
        
        Args:
            store_id: Store ID
            updates: Fields to update
            
        Returns:
            Dict with success status
            
        Raises:
            ResourceNotFoundError: If store not found
        """
        if not self.repository.get_by_id(store_id):
            raise ResourceNotFoundError("Store", store_id)
        
        success = self.repository.update(store_id, updates)
        
        if not success:
            raise ValidationError("No valid fields to update")
        
        return {
            "success": True,
            "message": f"Store {store_id} updated successfully"
        }
    
    def delete_store(self, store_id: int) -> Dict[str, Any]:
        """
        Delete a store. Unassigns all related data.
        
        Args:
            store_id: Store ID
            
        Returns:
            Dict with success status and unassigned counts
            
        Raises:
            ResourceNotFoundError: If store not found
        """
        store = self.repository.get_by_id(store_id)
        if not store:
            raise ResourceNotFoundError("Store", store_id)
        
        store_name = store['name']
        
        # Count related data
        lead_repo = LeadRepository()
        call_repo = CallRepository()
        
        # Count leads
        leads, _ = lead_repo.get_all(store_id=store_id, limit=1)
        leads_count = len(leads)
        
        # Count phone numbers
        phone_count = self.phone_repository.count_by_store(store_id)
        
        # Unassign related data - update leads to set store_id to NULL
        if leads_count > 0:
            # Use direct SQL update to set store_id to NULL for all leads
            base_repo = BaseRepository()
            base_repo.execute_non_query(
                "UPDATE OutboundLeads SET store_id = NULL WHERE store_id = ?",
                (store_id,)
            )
        
        if phone_count > 0:
            # Unassign phone numbers
            phone_numbers = self.phone_repository.get_all(store_id=store_id)
            for phone in phone_numbers:
                self.phone_repository.assign_to_store(phone['number_id'], None)
        
        # Delete the store
        success = self.repository.delete(store_id)
        
        if not success:
            raise ResourceNotFoundError("Store", store_id)
        
        return {
            "success": True,
            "message": f"Store '{store_name}' deleted successfully",
            "unassigned": {
                "leads": leads_count,
                "phone_numbers": phone_count
            }
        }
    
    def get_store_phone_numbers(self, store_id: int) -> Dict[str, Any]:
        """
        Get all phone numbers assigned to a store with health status.
        
        Args:
            store_id: Store ID
            
        Returns:
            Dict with phone numbers list
        """
        # Verify store exists
        if not self.repository.get_by_id(store_id):
            raise ResourceNotFoundError("Store", store_id)
        
        phone_numbers = self.repository.get_store_phone_numbers_with_health(store_id)
        
        return {
            "success": True,
            "store_id": store_id,
            "phone_numbers": phone_numbers,
            "count": len(phone_numbers)
        }
    
    def get_store_daily_stats(self, store_id: int, date: Optional[str] = None) -> Dict[str, Any]:
        """
        Get daily statistics for a store.
        
        Args:
            store_id: Store ID
            date: Optional date in YYYY-MM-DD format (defaults to today)
            
        Returns:
            Dict with daily statistics
            
        Raises:
            ResourceNotFoundError: If store not found
        """
        if not self.repository.get_by_id(store_id):
            raise ResourceNotFoundError("Store", store_id)
        
        stats = self.repository.get_store_daily_stats(store_id, date)
        
        if not stats:
            raise ResourceNotFoundError("Store", store_id)
        
        return {
            "success": True,
            **stats
        }


def get_store_service() -> StoreService:
    """Get singleton instance of StoreService."""
    return StoreService.get_instance()

