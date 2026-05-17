"""
Call Management Router (Refactored)
Handles call history, results, and call operations using service layer.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
import aiohttp
import base64

from models import CallResultCreate
from services.call_service import get_call_service, CallService
from core.exceptions import ResourceNotFoundError
from config import config

# Router instance
router = APIRouter(prefix="/api/calls", tags=["calls"])


# Dependency injection
def get_service() -> CallService:
    """Dependency injection for CallService."""
    return get_call_service()


# ============================================================================
# GET ENDPOINTS
# ============================================================================

@router.get("/call-history", summary="Get call history")
async def get_call_history(
    limit: int = 100,
    offset: int = 0,
    result_type: Optional[str] = None,
    store_id: Optional[int] = None,
    service: CallService = Depends(get_service)
):
    """
    Get call history with pagination and filtering.
    
    Args:
        limit: Number of results to return (max 500)
        offset: Number of results to skip
        result_type: Filter by result type (interested, not_interested, callback, dnc, etc.)
        store_id: Filter by store ID
    """
    # Let exceptions bubble up to global handler
    return service.get_call_history(
        limit=limit,
        offset=offset,
        result_type=result_type,
        store_id=store_id
    )


@router.get("/call-details/{result_id}", summary="Get call details")
async def get_call_details(
    result_id: int,
    service: CallService = Depends(get_service)
):
    """Get detailed information about a specific call."""
    # Let exceptions bubble up to global handler
    return service.get_call_details(result_id)


@router.get("/call-recording/{call_sid}", summary="Get call recording audio")
async def get_call_recording(call_sid: str):
    """
    Get Twilio recording audio file for a specific call.
    
    This endpoint:
    1. Fetches recordings for the call SID from Twilio
    2. Gets the first available recording
    3. Proxies the audio file with proper authentication
    """
    from twilio.rest import Client
    from twilio.base.exceptions import TwilioRestException
    
    try:
        # Initialize Twilio client
        if not config.twilio.ACCOUNT_SID or not config.twilio.AUTH_TOKEN:
            raise HTTPException(
                status_code=500,
                detail="Twilio credentials not configured"
            )
        
        client = Client(config.twilio.ACCOUNT_SID, config.twilio.AUTH_TOKEN)
        
        # Fetch recordings for this call
        recordings = client.recordings.list(call_sid=call_sid, limit=1)
        
        if not recordings:
            raise HTTPException(
                status_code=404,
                detail=f"No recording found for call {call_sid}"
            )
        
        # Get the first recording
        recording = recordings[0]
        recording_sid = recording.sid
        account_sid = config.twilio.ACCOUNT_SID
        
        # Build the Twilio recording URL
        recording_url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Recordings/{recording_sid}.mp3"
        
        # Create Basic Auth header for Twilio API
        credentials = f"{account_sid}:{config.twilio.AUTH_TOKEN}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        auth_header = f"Basic {encoded_credentials}"
        
        # Proxy the audio file with authentication
        async with aiohttp.ClientSession() as session:
            async with session.get(
                recording_url,
                headers={"Authorization": auth_header},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status != 200:
                    raise HTTPException(
                        status_code=response.status,
                        detail=f"Failed to fetch recording: {response.status}"
                    )
                
                # Stream the audio file
                audio_data = await response.read()
                
                return StreamingResponse(
                    iter([audio_data]),
                    media_type="audio/mpeg",
                    headers={
                        "Content-Disposition": f'attachment; filename="recording-{call_sid}.mp3"',
                        "Content-Length": str(len(audio_data))
                    }
                )
        
    except TwilioRestException as e:
        raise HTTPException(
            status_code=404,
            detail=f"Recording not found: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching recording: {str(e)}"
        )


# ============================================================================
# POST ENDPOINTS
# ============================================================================

@router.post("/call-results", summary="Save call result")
async def save_call_result(
    call_result: CallResultCreate,
    service: CallService = Depends(get_service)
):
    """Save the result of an outbound call."""
    # Let exceptions bubble up to global handler
    return service.save_call_result(call_result.dict())


# ============================================================================
# DELETE ENDPOINTS
# ============================================================================

@router.delete("/call-history/{result_id}", summary="Delete call result")
async def delete_call_result(
    result_id: int,
    service: CallService = Depends(get_service)
):
    """Delete a call result record."""
    # Let exceptions bubble up to global handler
    return service.delete_call_result(result_id)
