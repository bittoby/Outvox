"""
Analytics Router
API endpoints for analytics and statistics.
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, Dict, Any
from datetime import datetime
from services.analytics_service import get_analytics_service, AnalyticsService

# Main router with /api/analytics prefix
router = APIRouter(prefix="/api/analytics", tags=["analytics"])


# Dependency injection
def get_service() -> AnalyticsService:
    """Dependency injection for AnalyticsService."""
    return get_analytics_service()


@router.get("/sms-timeline", summary="Get SMS timeline")
async def get_sms_timeline(
    store_id: Optional[int] = Query(None, description="Filter by store ID"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    service: AnalyticsService = Depends(get_service)
) -> Dict[str, Any]:
    """
    Get SMS sending timeline for analytics charts.
    
    Query Parameters:
        store_id (optional): Filter by store ID
        start_date (optional): Start date in YYYY-MM-DD format (default: 7 days ago)
        end_date (optional): End date in YYYY-MM-DD format (default: today)
    
    Response:
        {
            "timeline": [
                {
                    "date": str (YYYY-MM-DD),
                    "sms_sent": int,
                    "replies_received": int,
                    "calls_made": int
                }
            ]
        }
    """
    try:
        # Parse dates
        end = None
        start = None
        
        if end_date:
            try:
                end = datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid end_date format. Use YYYY-MM-DD")
        
        if start_date:
            try:
                start = datetime.strptime(start_date, '%Y-%m-%d').date()
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD")
        
        return service.get_sms_timeline(store_id, start, end)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching SMS timeline: {str(e)}")


@router.get("/daily-report/{date}", summary="Get daily report for all stores")
async def get_daily_report(
    date: str,
    service: AnalyticsService = Depends(get_service)
) -> Dict[str, Any]:
    """
    Get daily report for all stores.
    
    Path Parameters:
        date: Date in YYYY-MM-DD format
    
    Response:
        {
            "date": str (YYYY-MM-DD),
            "summary": {
                "total_sms_sent": int,
                "total_calls_made": int,
                "total_replies": int,
                "reply_rate": float (percentage),
                "stores_active": int
            },
            "stores": [
                {
                    "store_id": int,
                    "store_name": str,
                    "sms_sent": int,
                    "calls_made": int,
                    "replies_yes": int,
                    "replies_stop": int,
                    "replies_other": int
                }
            ]
        }
    """
    try:
        # Parse date
        try:
            target_date = datetime.strptime(date, '%Y-%m-%d').date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
        return service.get_daily_report(target_date)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating daily report: {str(e)}")


@router.get("/stats", summary="Get call statistics for today")
@router.get("/stats/today", summary="Get call statistics for today")
async def get_call_stats(service: AnalyticsService = Depends(get_service)):
    """Get statistics about outbound calling for today."""
    return service.get_call_stats()


@router.get("/stats/priority-stats", summary="Get lead count by priority level")
async def get_lead_priority_stats(service: AnalyticsService = Depends(get_service)):
    """Get lead count by priority level."""
    return service.get_priority_stats()


@router.get("/store-locations", summary="Get all store locations with call statistics")
async def get_store_locations(service: AnalyticsService = Depends(get_service)):
    """Get all store locations with call statistics."""
    return service.get_store_locations()

