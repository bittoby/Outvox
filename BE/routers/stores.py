"""
Store Management Router (Refactored)
Handles all store-related API endpoints using service layer.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Depends

from models import StoreCreate, StoreUpdate
from services.store_service import get_store_service, StoreService
from core.exceptions import ResourceNotFoundError, ValidationError

# Router instance
router = APIRouter(prefix="/api/stores", tags=["stores"])


# Dependency injection
def get_service() -> StoreService:
    """Dependency injection for StoreService."""
    return get_store_service()


# ============================================================================
# GET ENDPOINTS
# ============================================================================

@router.get("", summary="Get all stores")
async def get_all_stores(service: StoreService = Depends(get_service)):
    """Get list of all stores with statistics.
    
    Quotas are calculated dynamically based on assigned phone numbers:
    - Each phone number: 50 SMS/day, 30 calls/day
    - Store quota = number_of_phone_numbers * per_number_quota
    """
    # Let exceptions bubble up to global handler
    return service.get_all_stores()


@router.get("/{store_id}", summary="Get store by ID")
async def get_store_by_id(
    store_id: int,
    service: StoreService = Depends(get_service)
):
    """Get detailed information about a specific store.
    
    Quotas are calculated dynamically based on assigned phone numbers:
    - Each phone number: 50 SMS/day, 30 calls/day
    """
    # Let exceptions bubble up to global handler
    return service.get_store(store_id)


@router.get("/{store_id}/phone-numbers", summary="Get store's phone numbers")
async def get_store_phone_numbers(
    store_id: int,
    service: StoreService = Depends(get_service)
):
    """Get all phone numbers assigned to a store with health status."""
    # Let exceptions bubble up to global handler
    return service.get_store_phone_numbers(store_id)


@router.get("/{store_id}/stats/daily", summary="Get store daily statistics")
async def get_store_daily_stats(
    store_id: int,
    date: Optional[str] = None,
    service: StoreService = Depends(get_service)
):
    """
    Get daily statistics for a store.
    
    Args:
        store_id: Store ID
        date: Date in YYYY-MM-DD format (defaults to today)
    """
    # Let exceptions bubble up to global handler
    return service.get_store_daily_stats(store_id, date)


# ============================================================================
# POST ENDPOINTS
# ============================================================================

@router.post("", summary="Create new store")
async def create_store(
    store: StoreCreate,
    service: StoreService = Depends(get_service)
):
    """Create a new store."""
    # Check if store with same name already exists
    from repositories.store_repository import StoreRepository
    store_repo = StoreRepository()
    existing_stores = store_repo.get_all()
    for existing in existing_stores:
        if existing['name'].lower() == store.name.lower():
            raise HTTPException(
                status_code=400,
                detail=f"Store with name '{store.name}' already exists"
            )
    
    result = service.create_store(store.dict())
    
    # Get created store with quotas
    created_store = service.get_store(result['store_id'])
    
    return {
        "success": True,
        "message": f"Store '{store.name}' created successfully",
        "store": created_store['store']
    }


# ============================================================================
# PUT ENDPOINTS
# ============================================================================

@router.put("/{store_id}", summary="Update store")
async def update_store(
    store_id: int,
    store: StoreUpdate,
    service: StoreService = Depends(get_service)
):
    """Update store information."""
    updates = {k: v for k, v in store.dict().items() if v is not None}
    # Let exceptions bubble up to global handler
    return service.update_store(store_id, updates)


# ============================================================================
# DELETE ENDPOINTS
# ============================================================================

@router.delete("/{store_id}", summary="Delete store")
async def delete_store(
    store_id: int,
    service: StoreService = Depends(get_service)
):
    """Delete a store. Unassigns all related data (leads, phone numbers, campaigns, templates)."""
    # Let exceptions bubble up to global handler
    return service.delete_store(store_id)
