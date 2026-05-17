"""
Outbound Calling Service - AI Voice Agent
Handles outbound calls via Twilio and OpenAI Realtime API.
"""

import os
import sys
import json
import base64
import asyncio
import aiohttp
import websockets
import uvicorn
import logging
from datetime import datetime
from typing import Optional, Dict
from fastapi import FastAPI, WebSocket, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.websockets import WebSocketDisconnect
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Connect

# Setup logging - Clean format without timestamp and module name for better readability
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'  # Clean format - just the message
)
logger = logging.getLogger(__name__)

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import configuration and utilities

from config import config
from utils import (
    get_system_prompt, get_closest_location, STORE_LOCATIONS,
    get_store_info
)
# SMS Campaign Manager is imported lazily when needed to avoid ODBC dependency

# Import refactored call management modules
from services.call_state_manager import CallState
from services.websocket_handlers import TwilioMessageHandler, OpenAIMessageHandler
from services.call_sms_processor import CallSMSProcessor
from services.settings_service import get_openai_settings, get_elevenlabs_settings, get_active_provider
from services.elevenlabs_service import register_elevenlabs_call

# Global configuration

# Agent identification
AGENT_ID = config.agent.AGENT_ID
PORT = config.agent.PORT

# Twilio service
from services.twilio_service import TwilioService
twilio_service = TwilioService(AGENT_ID)

# FastAPI application
app = FastAPI(
    title=f"Outvox — Voice Agent {AGENT_ID}",
    description="Outbound voice agent (OpenAI Realtime + Twilio bridge).",
    version="2.0.0"
)

# API-key authentication. Twilio webhooks and the media-stream WebSocket are
# exempted by default (see config.security.AUTH_EXEMPT_PREFIXES) because they
# arrive without our shared secret. The webhook handlers validate Twilio's
# signature, and generated media-stream URLs carry a signed token.
from core.auth import install_api_key_auth
install_api_key_auth(app, service_name=f"outbound_agent[{AGENT_ID}]")
from core.media_stream_token import validate_media_stream_token
from core.twilio_validation import validate_twilio_request

# CORS Configuration. Override with CORS_ALLOWED_ORIGINS (comma-separated) in
# production. The "*" default exists for local development convenience.
_cors_origins_env = os.getenv("CORS_ALLOWED_ORIGINS", "*").strip()
_cors_origins = (
    ["*"] if _cors_origins_env in ("", "*")
    else [o.strip() for o in _cors_origins_env.split(",") if o.strip()]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# Database service API functions

async def get_next_lead() -> Optional[Dict]:
    """
    Get the next lead to call from Database Service
        
    Returns:
        Dict with lead data or None if no leads available
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{config.database.SERVICE_URL}/api/leads/next"
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    # Handle response format: {"success": bool, "lead": {...}, "message": ...}
                    # or direct lead dict: {"lead_id": ..., ...}
                    if isinstance(data, dict):
                        if 'lead' in data and data.get('lead'):
                            # Service layer format - extract lead
                            return data['lead']
                        elif 'lead_id' in data:
                            # Direct lead format
                            return data
                    return None
                return None
    except Exception as e:
        print(f"[{AGENT_ID}] ERROR: Error getting lead: {e}")
        return None


async def get_lead_by_id(lead_id: int) -> Optional[Dict]:
    """
    Fetch lead details by ID
    
    Args:
        lead_id: Lead identifier
        
    Returns:
        Dict with lead data or None
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{config.database.SERVICE_URL}/api/leads/{lead_id}"
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    # Handle response format: {"success": True, "lead": {...}} or just {...}
                    if isinstance(data, dict) and 'lead' in data:
                        return data['lead']
                    return data
                return None
    except Exception as e:
        print(f"[{AGENT_ID}] ERROR: Error fetching lead {lead_id}: {e}")
        return None

async def mark_lead_called(lead_id: int) -> bool:
    """
    Mark a lead as called in the database
    
    Args:
        lead_id: Lead identifier
        
    Returns:
        bool: Success status
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{config.database.SERVICE_URL}/api/leads/{lead_id}/mark-called",
                params={'agent_id': AGENT_ID}
            ) as response:
                return response.status == 200
    except Exception as e:
        print(f"[{AGENT_ID}] ERROR: Error marking lead as called: {e}")
        return False


async def save_call_result(
    lead_id: int, call_sid: str, twilio_number: str,
    call_status: str, result_type: str,
    customer_transcript: str = "", agent_transcript: str = "", combined_transcript: str = "",
    duration: int = 0
) -> bool:
    """
    Save call result to database
    
    Args:
        lead_id: Lead identifier
        call_sid: Twilio call SID
        twilio_number: Number used for the call
        call_status: Call status (completed, failed, etc.)
        result_type: Result classification (interested, dnc, etc.)
        customer_transcript: What customer said
        agent_transcript: What agent said
        combined_transcript: Chronological conversation (both speakers)
        duration: Call duration in seconds
        
    Returns:
        bool: Success status
    """
    try:
        call_data = {
            "lead_id": lead_id,
            "agent_id": config.get_formatted_agent_id(),  # Use formatted Agent1, Agent2, etc.
            "twilio_number": twilio_number,
            "call_sid": call_sid,
            "call_status": call_status,
            "call_duration": duration,
            "result_type": result_type,
            "customer_transcript": customer_transcript,
            "agent_transcript": agent_transcript,
            "combined_transcript": combined_transcript  # Chronological conversation
        }
        
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{config.database.SERVICE_URL}/api/calls/call-results",
                json=call_data,
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                success = response.status == 200
                
                if not success:
                    error_text = await response.text()
                    print(f"[{AGENT_ID}] ERROR: Database service returned error: HTTP {response.status}")
                
                return success
    except aiohttp.ClientError as e:
        print(f"[{AGENT_ID}] ERROR: Network error while saving call result: {e}")
        return False
    except Exception as e:
        print(f"[{AGENT_ID}] ERROR: Exception while saving call result: {e}")
        import traceback
        traceback.print_exc()
        return False


async def mark_dnc(phone_number: str) -> bool:
    """
    Mark a phone number as Do Not Call
    
    Args:
        phone_number: Phone number to mark as DNC
        
    Returns:
        bool: Success status
    """
    try:
        dnc_data = {"phone_number": phone_number, "agent_id": AGENT_ID}
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{config.database.SERVICE_URL}/api/leads/mark-dnc",
                json=dnc_data
            ) as response:
                return response.status == 200
    except Exception as e:
        print(f"[{AGENT_ID}] ERROR: Error marking DNC: {e}")
        return False


async def get_lead_by_call_sid(call_sid: str) -> Optional[Dict]:
    """
    Legacy fallback for call SID based lookup.

    Current TwiML passes lead_id and twilio_number directly on the Twilio Media
    Stream URL, so normal calls hydrate CallState from WebSocket query params.
    
    Args:
        call_sid: Twilio call SID (for logging purposes)
        
    Returns:
        Dict with lead data or None if not found
    """
    try:
        print(f"[{AGENT_ID}] ERROR: No WebSocket lead_id available for call: {call_sid}")
        return None
    except Exception as e:
        print(f"[{AGENT_ID}] ERROR: Error retrieving lead: {e}")
        return None


# SMS functions

# SMS functions moved to services/twilio_service.py
# Use twilio_service.send_directions_sms() and twilio_service.send_photo_request_sms()

async def send_directions_sms(phone_number: str, closest_location: str, lead_id: int, twilio_number: str, transcript: str = "", override_store_key: str = None) -> bool:
    """Wrapper for twilio_service.send_directions_sms()"""
    return await twilio_service.send_directions_sms(
        phone_number, closest_location, lead_id, twilio_number, transcript, override_store_key
    )


async def send_photo_request_sms(phone_number: str, lead_id: int, twilio_number: str, location_name: str = "", transcript: str = "") -> bool:
    """Wrapper for twilio_service.send_photo_request_sms()"""
    return await twilio_service.send_photo_request_sms(
        phone_number, lead_id, twilio_number, location_name, transcript
    )


# get_store_info moved to utils/location_mapper.py

# Twilio call management

async def make_outbound_call(lead: Dict, twilio_number: str) -> Optional[str]:
    """Wrapper for twilio_service.make_outbound_call()"""
    call_sid = await twilio_service.make_outbound_call(lead, twilio_number)
    if call_sid:
        await mark_lead_called(lead['lead_id'])
    return call_sid


# FastAPI routes

@app.get("/", response_class=JSONResponse)
async def index_page():
    """Service status endpoint"""
    return {
        "message": f"Outbound Agent {AGENT_ID} is operational",
        "agent_id": AGENT_ID,
        "status": "healthy",
        "version": "2.0.0",
        "features": {
            "english_only": config.call.ENFORCE_ENGLISH_ONLY,
            "max_duration": config.call.MAX_CALL_DURATION,
            "recording": config.call.ENABLE_CALL_RECORDING
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "agent_id": AGENT_ID,
        "service": "outbound",
        "timestamp": datetime.now().isoformat(),
        "config": {
            "max_call_duration": config.call.MAX_CALL_DURATION,
            "recording_enabled": config.call.ENABLE_CALL_RECORDING,
            "english_only": config.call.ENFORCE_ENGLISH_ONLY
        }
    }


# Campaign creation endpoint removed - now in routers/campaigns.py


# Campaign endpoints removed - now in routers/campaigns.py:
# - GET /api/campaigns/{campaign_id}
# - GET /api/campaigns/{campaign_id}/batches
# - PUT /api/campaigns/{campaign_id}/pause
# - PUT /api/campaigns/{campaign_id}/resume
# - GET /api/campaigns


# Daily reporting and analytics endpoints

@app.get("/api/stores/{store_id}/stats/daily")
async def get_store_daily_stats(store_id: int, date: Optional[str] = None):
    """
    Get daily statistics for a store (Milestone 16).
    Proxies to db_service store statistics endpoint.
    
    Query Parameters:
        date (optional): Date in YYYY-MM-DD format (default: today)
    
    Response:
        {
            "store_id": int,
            "store_name": str,
            "date": str (YYYY-MM-DD),
            "sms_sent": int,
            "sms_quota": int (daily quota),
            "sms_remaining": int,
            "calls_made": int,
            "call_quota": int (daily quota),
            "calls_remaining": int,
            "replies": {
                "yes": int,
                "stop": int,
                "other": int,
                "total": int
            },
            "phone_numbers": [
                {
                    "phone_number": str,
                    "hourly_sms_count": int,
                    "daily_sms_count": int,
                    "hourly_call_count": int,
                    "status": str (active/at_limit/cooldown)
                }
            ]
        }
    """
    try:
        # Proxy to db_service store statistics endpoint
        params = {}
        if date:
            params['date'] = date
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{config.database.SERVICE_URL}/api/stores/{store_id}/stats/daily",
                params=params,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 404:
                    raise HTTPException(status_code=404, detail=f"Store {store_id} not found")
                else:
                    error_text = await response.text()
                    raise HTTPException(status_code=response.status, detail=f"Error from db_service: {error_text}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching store stats: {str(e)}")


@app.get("/api/reports/daily/{date}")
async def get_daily_report(date: str):
    """
    Get daily report for all stores (Milestone 16).
    Proxies to db_service analytics endpoint.
    
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
        # Validate date format
        try:
            datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
        # Proxy to db_service analytics endpoint
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{config.database.SERVICE_URL}/api/analytics/daily-report/{date}",
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise HTTPException(status_code=response.status, detail=f"Error from db_service: {error_text}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating daily report: {str(e)}")


@app.get("/api/analytics/sms-timeline")
async def get_sms_timeline(
    store_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """
    Get SMS sending timeline for analytics charts (Milestone 16).
    Proxies to db_service analytics endpoint.
    
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
        # Build query parameters
        params = {}
        if store_id is not None:
            params['store_id'] = store_id
        if start_date:
            params['start_date'] = start_date
        if end_date:
            params['end_date'] = end_date
        
        # Proxy to db_service analytics endpoint
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{config.database.SERVICE_URL}/api/analytics/sms-timeline",
                params=params,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise HTTPException(status_code=response.status, detail=f"Error from db_service: {error_text}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching SMS timeline: {str(e)}")


@app.post("/manual-dial")
async def manual_dial(request: Request):
    """
    Manual dial endpoint for TCPA compliance - called from popup queue.
    Requires employee_name and lead_id from popup system.
    
    Workflow:
      1. Validate lead exists and is not DNC
      2. Check time restrictions
      3. Get available Twilio number
      4. Initiate call via Twilio
      5. Return call status (popup queue update happens AFTER success in frontend)
    """
    try:
        body = await request.json()
        lead_id = body.get('lead_id')
        employee_name = body.get('employee_name', 'Unknown')
        popup_id = body.get('popup_id')
        
        if not lead_id:
            return {
                "status": "error",
                "message": "lead_id is required",
                "agent_id": AGENT_ID
            }
        
        
        # Step 1: Get lead from database
        lead = await get_lead_by_id(lead_id)
        if not lead:
            print(f"[{AGENT_ID}] ERROR: Lead {lead_id} not found")
            return {
                "status": "error",
                "message": f"Lead {lead_id} not found",
                "agent_id": AGENT_ID
            }
        
        if lead.get('dnc_flag'):
            print(f"[{AGENT_ID}] ERROR: Lead {lead_id} is marked as DNC")
            return {
                "status": "error",
                "message": "Lead is marked as Do Not Call",
                "agent_id": AGENT_ID
            }
        
        # Check SMS verification - handle bool, int, or None
        sms_verified = lead.get('sms_verified')
        
        if sms_verified is None:
            print(f"[{AGENT_ID}] ERROR: Lead {lead_id} has no SMS verification status in response")
            return {
                "status": "error",
                "message": "Lead has not provided SMS consent. Please wait for SMS verification.",
                "agent_id": AGENT_ID
            }
        # Convert int (0/1) to bool if needed
        if isinstance(sms_verified, int):
            sms_verified = bool(sms_verified)
        if not sms_verified:
            print(f"[{AGENT_ID}] ERROR: Lead {lead_id} has not provided SMS consent")
            return {
                "status": "error",
                "message": "Lead has not provided SMS consent. Please wait for SMS verification.",
                "agent_id": AGENT_ID
            }
        
        
        # Step 2: Check time restrictions BEFORE getting Twilio number
        from zoneinfo import ZoneInfo
        local_tz = ZoneInfo('America/New_York')
        local_time = datetime.now(local_tz)
        current_hour = local_time.hour
        
        if current_hour < 9 or current_hour >= 18:
            error_msg = f"Call blocked: Outside permitted hours (current time: {local_time.strftime('%I:%M %p %Z')}). Permitted hours: 9:00 AM - 6:00 PM Eastern Time."
            print(f"[{AGENT_ID}] ⏰ {error_msg}")
            return {
                "status": "error",
                "message": error_msg,
                "agent_id": AGENT_ID
            }
        
        # Step 3: Get Twilio number with priority:
        # 1. Use same number that sent SMS (best for TCPA compliance)
        # 2. Use least-busy number from lead's assigned store
        # 3. Use any available number as fallback
        twilio_number = None
        lead_store_id = lead.get('store_id')
        sms_from_number = lead.get('sms_from_number')
        
        # Priority 1: Use the same number that sent SMS (TCPA compliance best practice)
        # Only use it if it's available (not at limits), otherwise fall back to other numbers in same store
        if sms_from_number:
            try:
                url = f"{config.database.SERVICE_URL}/api/phone-numbers/check/{sms_from_number}"
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        if response.status == 200:
                            data = await response.json()
                            exists = data.get('exists', False)
                            if exists:
                                daily_call_count = data.get('daily_call_count', 0)
                                daily_sms_count = data.get('daily_sms_count', 0)
                                is_active = data.get('is_active', False)
                                
                                # Check if number is available (under limits and active)
                                # Limits: daily_call_count < 30, daily_sms_count < 50
                                if is_active and daily_call_count < 30 and daily_sms_count < 50:
                                    twilio_number = sms_from_number
            except Exception:
                pass  # Fall through to next priority
        
        # Priority 2: Get least-busy phone number from the lead's assigned store
        if not twilio_number:
            twilio_number = await twilio_service.get_available_twilio_number(store_id=lead_store_id, for_manual_dial=True)
        
        # Priority 3: Fallback to any available number if store-specific search failed
        if not twilio_number and lead_store_id is not None:
            twilio_number = await twilio_service.get_available_twilio_number(store_id=None, for_manual_dial=True)
        
        if not twilio_number:
            print(f"[{AGENT_ID}] ERROR: No available Twilio numbers (store_id={lead_store_id}, sms_from_number={sms_from_number})")
            # Provide more helpful error message
            error_msg = "No available Twilio numbers"
            if lead_store_id:
                error_msg += f" for store {lead_store_id}. All numbers may be at their daily/hourly limits."
            elif sms_from_number:
                error_msg += f". The SMS sender number ({sms_from_number}) is not active, and no other numbers are available."
            else:
                error_msg += ". All numbers may be at their daily/hourly limits or no numbers are configured."
            return {
                "status": "error",
                "message": error_msg,
                "agent_id": AGENT_ID
            }
        
        # Step 4: Make the call
        call_sid = await make_outbound_call(lead, twilio_number)
        
        if call_sid:
            # Step 5: Update popup queue with call_sid (via DB service) - optional, frontend will also update
            try:
                import aiohttp
                db_service_url = os.getenv('DB_SERVICE_URL', 'http://localhost:8000')
                
                if popup_id:
                    async with aiohttp.ClientSession() as session:
                        async with session.post(
                            f"{db_service_url}/api/popup/update-call-sid/{popup_id}",
                            json={"call_sid": call_sid},
                            timeout=aiohttp.ClientTimeout(total=5)
                        ) as response:
                            if response.status != 200:
                                print(f"[{AGENT_ID}] WARNING: Failed to update popup queue: {response.status}")
            except Exception as e:
                print(f"[{AGENT_ID}] WARNING: Error updating popup queue (non-critical): {e}")
            
            return {
                "status": "success",
                "call_sid": call_sid,
                "lead_id": lead['lead_id'],
                "phone_number": lead['phone_number'],
                "twilio_number": twilio_number,
                "employee_name": employee_name,
                "agent_id": AGENT_ID,
                "message": f"Call initiated successfully to {lead.get('name', 'Unknown')}"
            }
        else:
            # make_outbound_call returns None if time restriction or other error
            error_msg = "Failed to initiate call. This may be due to time restrictions (calls only allowed 8 AM - 9 PM Eastern Time) or Twilio API error."
            print(f"[{AGENT_ID}] ERROR: {error_msg}")
            return {
                "status": "error",
                "message": error_msg,
                "agent_id": AGENT_ID
            }
            
    except Exception as e:
        print(f"[{AGENT_ID}] ERROR: Error in manual dial: {e}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "message": f"Error initiating call: {str(e)}",
            "agent_id": AGENT_ID
        }


@app.post("/start-calling")
async def start_calling():
    """
    Start the outbound calling process
    
    Workflow:
      1. Get next available lead
      2. Check time restrictions
      3. Get available Twilio number
      4. Initiate call via Twilio
      5. Return call status
    """
    try:
        
        # Step 1: Get next lead
        lead = await get_next_lead()
        
        if not lead or 'lead_id' not in lead:
            print(f"[{AGENT_ID}] ERROR: No available leads")
            return {
                "status": "no_leads",
                "message": "No available leads to call",
                "agent_id": AGENT_ID
            }
        
        # Check SMS verification - handle bool, int, or None
        sms_verified = lead.get('sms_verified')
        if sms_verified is None:
            print(f"[{AGENT_ID}] ERROR: Lead {lead.get('lead_id')} has no SMS verification status")
            return {
                "status": "unverified",
                "message": "Lead has not provided SMS consent. Please wait for SMS verification.",
                "agent_id": AGENT_ID
            }
        # Convert int (0/1) to bool if needed
        if isinstance(sms_verified, int):
            sms_verified = bool(sms_verified)
        if not sms_verified:
            print(f"[{AGENT_ID}] ERROR: Lead {lead.get('lead_id')} has not provided SMS consent")
            return {
                "status": "unverified",
                "message": "Lead has not provided SMS consent. Please wait for SMS verification.",
                "agent_id": AGENT_ID
            }
        
        # Step 2: Check time restrictions BEFORE getting Twilio number
        from zoneinfo import ZoneInfo
        local_tz = ZoneInfo('America/New_York')
        local_time = datetime.now(local_tz)
        current_hour = local_time.hour
        
        if current_hour < 9 or current_hour >= 18:
            error_msg = f"Call blocked: Outside permitted hours (current time: {local_time.strftime('%I:%M %p %Z')}). Permitted hours: 9:00 AM - 6:00 PM Eastern Time."
            print(f"[{AGENT_ID}] ⏰ {error_msg}")
            return {
                "status": "time_restriction",
                "message": error_msg,
                "agent_id": AGENT_ID
            }
        
        # Step 3: Get Twilio number with priority:
        # 1. Use same number that sent SMS (best for TCPA compliance)
        # 2. Use least-busy number from lead's assigned store
        # 3. Use any available number as fallback
        twilio_number = None
        lead_store_id = lead.get('store_id')
        sms_from_number = lead.get('sms_from_number')
        
        # Priority 1: Use the same number that sent SMS (TCPA compliance best practice)
        # Only use it if it's available (not at limits), otherwise fall back to other numbers in same store
        if sms_from_number:
            try:
                url = f"{config.database.SERVICE_URL}/api/phone-numbers/check/{sms_from_number}"
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        if response.status == 200:
                            data = await response.json()
                            exists = data.get('exists', False)
                            if exists:
                                daily_call_count = data.get('daily_call_count', 0)
                                daily_sms_count = data.get('daily_sms_count', 0)
                                is_active = data.get('is_active', False)
                                
                                # Check if number is available (under limits and active)
                                # Limits: daily_call_count < 30, daily_sms_count < 50
                                if is_active and daily_call_count < 30 and daily_sms_count < 50:
                                    twilio_number = sms_from_number
            except Exception:
                pass  # Fall through to next priority
        
        # Priority 2: Get least-busy phone number from the lead's assigned store
        if not twilio_number:
            twilio_number = await twilio_service.get_available_twilio_number(store_id=lead_store_id, for_manual_dial=True)
        
        # Priority 3: Fallback to any available number if store-specific search failed
        if not twilio_number and lead_store_id is not None:
            twilio_number = await twilio_service.get_available_twilio_number(store_id=None, for_manual_dial=True)
        
        if not twilio_number:
            print(f"[{AGENT_ID}] ERROR: No available Twilio numbers (store_id={lead_store_id}, sms_from_number={sms_from_number})")
            error_msg = "No available Twilio numbers"
            if lead_store_id:
                error_msg += f" for store {lead_store_id}. All numbers may be at their daily/hourly limits."
            elif sms_from_number:
                error_msg += f". The SMS sender number ({sms_from_number}) is not active, and no other numbers are available."
            else:
                error_msg += ". All numbers may be at their daily/hourly limits or no numbers are configured."
            return {
                "status": "no_numbers",
                "message": error_msg,
                "agent_id": AGENT_ID
            }
        
        # Step 4: Make the call
        call_sid = await make_outbound_call(lead, twilio_number)
        
        if call_sid:
            return {
                "status": "success",
                "call_sid": call_sid,
                "lead_id": lead['lead_id'],
                "phone_number": lead['phone_number'],
                "twilio_number": twilio_number,
                "agent_id": AGENT_ID,
                "message": f"Call initiated to {lead.get('name', 'Unknown')}"
            }
        else:
            # make_outbound_call returns None if time restriction or other error
            error_msg = "Failed to initiate call. This may be due to time restrictions (calls only allowed 8 AM - 9 PM Eastern Time) or Twilio API error."
            print(f"[{AGENT_ID}] ERROR: {error_msg}")
            return {
                "status": "failed",
                "message": error_msg,
                "agent_id": AGENT_ID
            }
            
    except Exception as e:
        print(f"[{AGENT_ID}] ERROR: Error in start_calling: {e}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "message": f"Error initiating call: {str(e)}",
            "agent_id": AGENT_ID
        }


@app.post("/start-calling-with-data")
async def start_calling_with_data(request: Request):
    """
    Start outbound call with pre-assigned lead and Twilio number
    Used for parallel calling campaigns
    
    Body:
      {
        "lead": {...},
        "twilio_number": "+1234567890"
      }
    """
    try:
        data = await request.json()
        lead = data.get('lead')
        twilio_number = data.get('twilio_number')
        
        if not lead or not twilio_number:
            return {
                "status": "error",
                "message": "Missing lead or twilio_number"
            }
        
        # Check SMS verification - handle bool, int, or None
        sms_verified = lead.get('sms_verified')
        if sms_verified is None:
            print(f"[{AGENT_ID}] ERROR: Lead {lead.get('lead_id')} has no SMS verification status")
            return {
                "status": "error",
                "message": "Lead has not provided SMS consent. Please wait for SMS verification.",
                "agent_id": AGENT_ID
            }
        # Convert int (0/1) to bool if needed
        if isinstance(sms_verified, int):
            sms_verified = bool(sms_verified)
        if not sms_verified:
            return {
                "status": "error",
                "message": "Lead is not SMS verified and cannot be called"
            }
        
        
        # Mark lead as called
        await mark_lead_called(lead['lead_id'])
        
        # NOTE: Usage tracking is now updated when call completes successfully
        # (not when call starts, to avoid counting failed/incomplete calls)
        
        # Make the call
        call_sid = await make_outbound_call(lead, twilio_number)
        
        if call_sid:
            return {
                "status": "success",
                "call_sid": call_sid,
                "lead_id": lead['lead_id'],
                "phone_number": lead['phone_number'],
                "twilio_number": twilio_number,
                "agent_id": AGENT_ID
            }
        else:
            return {
                "status": "error",
                "message": "Failed to initiate call"
            }
            
    except Exception as e:
        print(f"[{AGENT_ID}] ERROR: Error in parallel calling: {e}")
        return {
            "status": "error",
            "error": str(e)
        }



async def find_lead_by_phone(phone_number: str) -> Optional[int]:
    """
    Find lead ID by phone number
    
    Args:
        phone_number: Customer's phone number
        
    Returns:
        int: Lead ID or None if not found
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{config.database.SERVICE_URL}/api/leads/by-phone/{phone_number}"
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('lead_id')
                return None
    except Exception as e:
        print(f"[{AGENT_ID}] ERROR: Error finding lead by phone: {e}")
        return None


async def create_temporary_lead(phone_number: str) -> Optional[int]:
    """
    Create a temporary lead for SMS processing when lead doesn't exist
    
    Args:
        phone_number: Customer's phone number
        
    Returns:
        int: Lead ID or None if creation failed
    """
    try:
        # Create a temporary lead via database service
        lead_data = {
            "name": f"SMS Customer {phone_number[-4:]}",  # Use last 4 digits as identifier
            "phone_number": phone_number,
            "priority": 3,  # Low priority for SMS-only leads
            "Address": "Unknown",
            "City": "Unknown",
            "State": "Unknown",
            "Zip": "00000",
            "County": "Unknown"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{config.database.SERVICE_URL}/api/leads",
                json=lead_data
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    lead_id = data.get('lead_id')
                    return lead_id
                else:
                    response_text = await response.text()
                    print(f"[{AGENT_ID}] ERROR: Failed to create temporary lead: {response.status} - {response_text}")
                    return None
                    
    except Exception as e:
        print(f"[{AGENT_ID}] ERROR: Error creating temporary lead: {e}")
        return None


@app.api_route("/twilio-sms", methods=["GET", "POST"])
async def handle_twilio_sms_webhook(request: Request):
    """
    Handle incoming SMS webhooks from Twilio (proxy to db_service).
    
    This endpoint forwards SMS webhooks to db_service.py for processing.
    """
    try:
        # Forward to db_service for processing
        async with aiohttp.ClientSession() as session:
            # Get the form data from the request
            form_data = await request.form()
            await validate_twilio_request(request, form_data)
            
            # Forward to db_service SMS router endpoint
            async with session.post(
                f"{config.database.SERVICE_URL}/api/sms/twilio-sms",
                data=dict(form_data),
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                response_text = await response.text()
                return response_text
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        print(f"[{AGENT_ID}] ERROR: Error forwarding SMS webhook: {e}")
        import traceback
        traceback.print_exc()
        # Still return OK to Twilio to avoid retries
        return "OK"


@app.api_route("/twilio-voice", methods=["GET", "POST"])
async def handle_twilio_webhook(request: Request):
    """
    Handle Twilio webhook for outbound calls
    
    This endpoint receives the call connection from Twilio and
    returns TwiML instructions to connect the call to our WebSocket
    (nginx routes to the correct agent container)
    
    Supports both OpenAI Realtime and ElevenLabs providers based on settings.
    
    Returns:
        TwiML XML response
    """
    lead_id = request.query_params.get('lead_id')
    twilio_number = request.query_params.get('twilio_number', '')
    
    # Get form data for Twilio call info (From/To numbers)
    form_data = {}
    try:
        form_data = await request.form()
    except Exception:
        form_data = {}

    await validate_twilio_request(request, form_data)
    
    from_number = form_data.get('From', twilio_number) or twilio_number
    to_number = form_data.get('To', '')
    
    # Pre-fetch lead data if we have lead_id (needed for to_number and customer_name)
    lead_data = None
    if lead_id:
        try:
            lead_data = await get_lead_by_id(int(lead_id))
        except Exception as e:
            print(f"[{AGENT_ID}] ⚠️ Error fetching lead data: {e}")
    
    # If to_number is empty, try to get it from lead data (needed for ElevenLabs)
    if not to_number and lead_data:
        to_number = lead_data.get('phone_number', '')
    
    print(f"[{AGENT_ID}] 📞 WEBHOOK DATA: lead_id={lead_id}, twilio_number={twilio_number}")
    print(f"[{AGENT_ID}] 📞 FORM DATA: From={form_data.get('From')}, To={form_data.get('To')}")
    print(f"[{AGENT_ID}] 📞 RESOLVED: from_number={from_number}, to_number={to_number}")
    
    # Check which AI provider is selected
    active_provider = get_active_provider()
    print(f"[{AGENT_ID}] 🔊 PROVIDER CHECK: Active AI provider = '{active_provider}'")
    
    if active_provider == 'elevenlabs':
        print(f"[{AGENT_ID}] 🟣 ELEVENLABS MODE SELECTED")
        # Use ElevenLabs Conversational AI
        elevenlabs_settings = get_elevenlabs_settings()
        agent_id = elevenlabs_settings.agent_id
        
        print(f"[{AGENT_ID}] 🟣 ELEVENLABS: Agent ID from settings = '{agent_id}'")
        
        # Validate required fields for ElevenLabs
        if not agent_id:
            print(f"[{AGENT_ID}] ⚠️ ELEVENLABS: No Agent ID configured, falling back to OpenAI")
            twiml_xml = twilio_service.create_twiml_response(lead_id, twilio_number)
        elif not from_number or not to_number:
            print(f"[{AGENT_ID}] ⚠️ ELEVENLABS: Missing from_number ({from_number}) or to_number ({to_number}), falling back to OpenAI")
            twiml_xml = twilio_service.create_twiml_response(lead_id, twilio_number)
        else:
            # Get customer name for personalization (use pre-fetched lead_data)
            customer_name = lead_data.get('name') if lead_data else None
            
            # Register call with ElevenLabs
            dynamic_vars = {}
            if customer_name:
                dynamic_vars['customer_name'] = customer_name
            if lead_id:
                dynamic_vars['lead_id'] = lead_id
            
            print(f"[{AGENT_ID}] 🟣 ELEVENLABS: Calling register_elevenlabs_call with agent_id={agent_id}, from={from_number}, to={to_number}")
            
            twiml_xml = await register_elevenlabs_call(
                agent_id=agent_id,
                from_number=from_number,
                to_number=to_number,
                direction="outbound",
                dynamic_variables=dynamic_vars if dynamic_vars else None
            )
            
            if not twiml_xml:
                print(f"[{AGENT_ID}] ❌ ELEVENLABS: register_elevenlabs_call returned None, falling back to OpenAI")
                twiml_xml = twilio_service.create_twiml_response(lead_id, twilio_number)
            else:
                print(f"[{AGENT_ID}] ✅ ELEVENLABS: Successfully registered call with agent: {agent_id}")
    else:
        # Use OpenAI Realtime (default)
        twiml_xml = twilio_service.create_twiml_response(lead_id, twilio_number)
    
    return HTMLResponse(
        content=twiml_xml,
        media_type="application/xml"
    )


# WebSocket handler - core call logic

@app.websocket("/media-stream")
async def handle_media_stream(websocket: WebSocket):
    """
    Core WebSocket handler for AI-powered outbound calling.
    
    Refactored to use CallState and specialized handlers for better maintainability.
    
    This orchestrates:
    - Twilio audio streaming (customer ↔ agent)
    - OpenAI Realtime API integration (AI conversation)
    - Real-time transcript extraction (agent & customer)
    - Business logic enforcement (English-only, DNC detection, timeouts)
    - Call result persistence (database storage)
    - Parallel calling support (multiple agents)
    
    Args:
        websocket: WebSocket connection from Twilio (routed by nginx)
    """
    lead_id_param = websocket.query_params.get('lead_id')
    twilio_number_param = websocket.query_params.get('twilio_number', '')
    stream_token = websocket.query_params.get('stream_token')

    if not validate_media_stream_token(stream_token, lead_id_param, twilio_number_param, AGENT_ID):
        logger.warning(f"[{AGENT_ID}] Rejected media stream with invalid token")
        await websocket.close(code=1008)
        return

    await websocket.accept()
    
    # Initialize call state
    call_state = CallState()
    call_state.current_twilio_number = twilio_number_param

    if lead_id_param and lead_id_param.isdigit():
        try:
            lead_data = await get_lead_by_id(int(lead_id_param))
            if lead_data:
                call_state.current_lead_id = lead_data['lead_id']
                call_state.lead_data = lead_data
                call_state.customer_name = lead_data.get('name')
                phone_number = lead_data.get('phone_number')
                call_state.closest_location_info = get_closest_location(phone_number, None)
                logger.info(
                    f"[{AGENT_ID}] 📋 LEAD_INFO_FROM_WS | LeadID: {call_state.current_lead_id} | "
                    f"Name: {call_state.customer_name} | Phone: {phone_number}"
                )
        except Exception as e:
            logger.warning(f"[{AGENT_ID}] ⚠️ Failed to hydrate lead from WebSocket params: {e}")
    
    # Initialize handlers
    twilio_handler = None
    openai_handler = None
    
    # ═══════════════════════════════════════════════════════════════
    # CONNECT TO OPENAI REALTIME API
    # ═══════════════════════════════════════════════════════════════
    
    # Fetch dynamic settings from database for model selection
    openai_settings = get_openai_settings()
    realtime_model = openai_settings.model or config.openai.REALTIME_MODEL
    logger.info(f"[{AGENT_ID}] Connecting to OpenAI Realtime with model: {realtime_model}")
    
    try:
        async with websockets.connect(
            f'wss://api.openai.com/v1/realtime?model={realtime_model}',
            extra_headers={
                "Authorization": f"Bearer {config.openai.API_KEY}",
                "OpenAI-Beta": "realtime=v1"
            }
        ) as openai_ws:
            
            # Initialize handlers with connections
            twilio_handler = TwilioMessageHandler(
                websocket, openai_ws, call_state, AGENT_ID
            )
            openai_handler = OpenAIMessageHandler(
                websocket, openai_ws, call_state, AGENT_ID,
                send_directions_sms, send_photo_request_sms, mark_dnc
            )
            
            logger.info(
                f"[{AGENT_ID}] 🚀 CALL_INIT | StreamSID: {call_state.stream_sid or 'pending'} | "
                f"TwilioNumber: {call_state.current_twilio_number or 'unknown'}"
            )
            
            # Initialize session with professional prompt (pass settings to avoid re-fetching)
            await initialize_openai_session(
                openai_ws,
                openai_settings,
                customer_name=call_state.customer_name,
                closest_location=call_state.closest_location_info['name'] if call_state.closest_location_info else None
            )
            
            logger.info(
                f"[{AGENT_ID}] 🤖 OPENAI_SESSION_INIT | Customer: {call_state.customer_name or 'Unknown'} | "
                f"Location: {call_state.closest_location_info['name'] if call_state.closest_location_info else 'Unknown'}"
            )
            
            
            # Trigger AI to speak first with natural compliance message
            await asyncio.sleep(0.2)
            await openai_ws.send(json.dumps({
                "type": "response.create",
                "response": {
                    "modalities": ["text", "audio"],
                    "instructions": (
                        f"Start NOW. Say: 'Hey [name], it's {config.brand.AGENT_NAME} from "
                        f"{config.brand.COMPANY_NAME}. Quick thing - you can ask us to stop "
                        "calling anytime, and this might be recorded. Anyway, got a sec?' "
                        "Then RIGHT AWAY pivot into the offering. Keep it SHORT (1-2 sentences "
                        "max). Sound like you're texting, not giving a speech. English only."
                    )
                }
            }))
            
            # ═══════════════════════════════════════════════════════════
            # TWILIO → OPENAI HANDLER
            # ═══════════════════════════════════════════════════════════
            
            # Flag to signal call end to both handlers
            call_ended = asyncio.Event()
            
            async def receive_from_twilio():
                """Stream audio from Twilio to OpenAI"""
                try:
                    async for message in websocket.iter_text():
                        # Check if call has already ended
                        if call_ended.is_set():
                            logger.debug(f"[{AGENT_ID}] Twilio handler exiting - call ended")
                            break
                        
                        try:
                            data = json.loads(message)
                        except json.JSONDecodeError as e:
                            logger.warning(
                                f"[{AGENT_ID}] ⚠️ INVALID_JSON | Source: Twilio | Error: {e}"
                            )
                            continue
                        
                        if data.get('event') == 'media':
                            await twilio_handler.handle_media_event(data)
                        elif data.get('event') == 'start':
                            await twilio_handler.handle_start_event(
                                data, get_lead_by_call_sid, get_closest_location
                            )
                        elif data.get('event') == 'mark':
                            await twilio_handler.handle_mark_event(data)
                        elif data.get('event') == 'stop':
                            duration = call_state.get_duration()
                            logger.info(
                                f"[{AGENT_ID}] 🛑 CALL_STOP_EVENT | CallSID: {call_state.call_sid or 'unknown'} | "
                                f"Duration: {duration}s"
                            )
                            # Signal call end immediately
                            call_ended.set()
                            break
                            
                except WebSocketDisconnect:
                    duration = call_state.get_duration()
                    logger.info(
                        f"[{AGENT_ID}] 🔌 WEBSOCKET_DISCONNECT | Source: Twilio | "
                        f"CallSID: {call_state.call_sid or 'unknown'} | Duration: {duration}s"
                    )
                    call_ended.set()  # Signal call end immediately
                except Exception as e:
                    logger.error(
                        f"[{AGENT_ID}] ❌ TWILIO_HANDLER_ERROR | CallSID: {call_state.call_sid or 'unknown'} | "
                        f"Error: {e}",
                        exc_info=True
                    )
                    call_ended.set()  # Signal call end on error
            
            # ═══════════════════════════════════════════════════════════
            # OPENAI → TWILIO HANDLER
            # ═══════════════════════════════════════════════════════════
            
            async def send_to_twilio():
                """Stream responses from OpenAI to Twilio"""
                try:
                    async for openai_message in openai_ws:
                        # Check if call has ended (stop event received from Twilio)
                        if call_ended.is_set():
                            logger.debug(f"[{AGENT_ID}] OpenAI handler exiting - call ended")
                            break
                        
                        try:
                            response = json.loads(openai_message)
                        except json.JSONDecodeError as e:
                            logger.warning(
                                f"[{AGENT_ID}] ⚠️ INVALID_JSON | Source: OpenAI | Error: {e}"
                            )
                            continue
                        
                        # Handle customer transcript
                        if response.get('type') in [
                            'conversation.item.input_audio_transcription.completed',
                            'input_audio_transcription.completed'
                        ]:
                            should_end = await openai_handler.handle_customer_transcript(response)
                            if should_end:
                                duration = call_state.get_duration()
                                logger.info(
                                    f"[{AGENT_ID}] 🛑 CALL_END_TRIGGERED | Reason: Business logic | "
                                    f"Duration: {duration}s"
                                )
                                call_ended.set()  # Signal call end
                                break
                        
                        # Handle agent transcript
                        if response.get('type') in [
                            'response.audio_transcript.done',
                            'response.text.done'
                        ]:
                            await openai_handler.handle_agent_transcript(response)
                        
                        # Handle audio streaming
                        if response.get('type') == 'response.audio.delta':
                            await openai_handler.handle_audio_delta(response)
                        
                        # Handle interruption
                        if response.get('type') == 'input_audio_buffer.speech_started':
                            await openai_handler.handle_speech_started()
                        
                except websockets.exceptions.ConnectionClosed:
                    duration = call_state.get_duration()
                    logger.info(
                        f"[{AGENT_ID}] 🔌 WEBSOCKET_DISCONNECT | Source: OpenAI | "
                        f"CallSID: {call_state.call_sid or 'unknown'} | Duration: {duration}s"
                    )
                    call_ended.set()  # Signal call end immediately
                except Exception as e:
                    logger.error(
                        f"[{AGENT_ID}] ❌ OPENAI_HANDLER_ERROR | CallSID: {call_state.call_sid or 'unknown'} | "
                        f"Error: {e}",
                        exc_info=True
                    )
                    call_ended.set()  # Signal call end on error
            
            # ═══════════════════════════════════════════════════════════
            # RUN BOTH HANDLERS CONCURRENTLY
            # ═══════════════════════════════════════════════════════════
            
            
            try:
                # Run both handlers concurrently with timeout
                # Use return_exceptions=True to prevent one handler's error from stopping the other
                # IMPORTANT: Check call_ended event periodically to exit early when call ends
                async def run_with_early_exit():
                    """Run handlers but exit early when call_ended is set."""
                    tasks = [
                        asyncio.create_task(receive_from_twilio()),
                        asyncio.create_task(send_to_twilio())
                    ]
                    
                    # Wait for either all tasks to complete OR call_ended event
                    while not call_ended.is_set() and any(not t.done() for t in tasks):
                        # Check every 0.5 seconds if call has ended
                        await asyncio.sleep(0.5)
                        if call_ended.is_set():
                            # Cancel remaining tasks
                            for task in tasks:
                                if not task.done():
                                    task.cancel()
                            break
                    
                    # Wait for tasks to complete (or be cancelled)
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    return results
                
                await asyncio.wait_for(
                    run_with_early_exit(),
                    timeout=config.call.MAX_CALL_DURATION + 10  # Safety margin
                )
            except asyncio.TimeoutError:
                duration = call_state.get_duration()
                logger.warning(
                    f"[{AGENT_ID}] ⏰ CALL_TIMEOUT | CallSID: {call_state.call_sid or 'unknown'} | "
                    f"Duration: {duration}s | MaxDuration: {config.call.MAX_CALL_DURATION}s"
                )
                call_state.call_result = "timeout"
                call_ended.set()  # Signal call end on timeout
            except Exception as e:
                logger.error(
                    f"[{AGENT_ID}] ❌ STREAMING_ERROR | CallSID: {call_state.call_sid or 'unknown'} | "
                    f"Error: {e}",
                    exc_info=True
                )
                call_ended.set()  # Signal call end on error
            finally:
                
                # Ensure call_ended is set to stop any remaining handlers
                call_ended.set()
                
                # Close OpenAI connection gracefully
                try:
                    if openai_ws.open:
                        await openai_ws.close()
                        logger.debug(f"[{AGENT_ID}] OPENAI_CONNECTION_CLOSED")
                except Exception as close_error:
                    logger.warning(
                        f"[{AGENT_ID}] OPENAI_CLOSE_ERROR | Error: {close_error}"
                    )
                
                # Close Twilio WebSocket if still open
                try:
                    if websocket.client_state.name == "CONNECTED":
                        await websocket.close()
                        logger.debug(f"[{AGENT_ID}] TWILIO_WEBSOCKET_CLOSED")
                except Exception as close_error:
                    logger.warning(
                        f"[{AGENT_ID}] TWILIO_CLOSE_ERROR | Error: {close_error}"
                    )
                
                # ═══════════════════════════════════════════════════════════
                # CRITICAL: Save call result (ALWAYS runs after call ends)
                # ═══════════════════════════════════════════════════════════
                if call_state.current_lead_id and not call_state.call_saved:
                    
                    # Calculate duration
                    duration = call_state.get_duration()
                    
                    # Ensure combined_transcript has content
                    final_combined_transcript = call_state.combined_transcript
                    if not final_combined_transcript or final_combined_transcript.strip() == "":
                        final_combined_transcript = call_state.build_combined_transcript_from_parts()
                    
                    # ═══════════════════════════════════════════════════════════
                    # FINAL CALL RESULT DETECTION (analyze full conversation)
                    # ═══════════════════════════════════════════════════════════
                    # Run final detection on complete transcripts to get most accurate result
                    from services.call_business_logic import CallBusinessLogic
                    business_logic = CallBusinessLogic()
                    final_result, final_reason, final_confidence = business_logic.detect_call_result(
                        call_state.customer_transcript,
                        call_state.agent_transcript
                    )
                    
                    # Use final result if it's positive, otherwise keep current (which may have been set during call)
                    # Priority: interested > callback > not_interested
                    if final_result in ['interested', 'callback']:
                        call_state.call_result = final_result
                        logger.info(
                            f"[{AGENT_ID}] 📊 FINAL_RESULT_DETECTED | Result: {final_result} | "
                            f"Confidence: {final_confidence:.2f} | Reason: {final_reason}"
                        )
                    elif call_state.call_result not in ['interested', 'callback']:
                        # Only update to not_interested if we haven't seen interest
                        call_state.call_result = final_result
                        logger.info(
                            f"[{AGENT_ID}] 📊 FINAL_RESULT_DETECTED | Result: {final_result} | "
                            f"Confidence: {final_confidence:.2f} | Reason: {final_reason}"
                        )
                    
                    # Log call summary before saving
                    customer_len = len(call_state.customer_transcript)
                    agent_len = len(call_state.agent_transcript)
                    logger.info(
                        f"[{AGENT_ID}] 📊 CALL_SUMMARY | CallSID: {call_state.call_sid or 'unknown'} | "
                        f"LeadID: {call_state.current_lead_id} | Duration: {duration}s | "
                        f"Result: {call_state.call_result} | 👤 Customer: {customer_len} chars | "
                        f"🤖 Agent: {agent_len} chars"
                    )
                    
                    # Save call result
                    success = await save_call_result(
                        call_state.current_lead_id, 
                        call_state.call_sid or "unknown", 
                        call_state.current_twilio_number,
                        "completed",
                        call_state.call_result,
                        call_state.customer_transcript,
                        call_state.agent_transcript,
                        final_combined_transcript,
                        duration=duration
                    )
                    
                    # ═══════════════════════════════════════════════════════════
                    # AUTO-QUEUE DIRECTIONS SMS FOR INTERESTED CALLS
                    # If customer showed interest but no directions SMS was queued, queue it now
                    # Location will be detected from full transcript during SMS processing
                    # ═══════════════════════════════════════════════════════════
                    if success and call_state.current_lead_id and not call_state.directions_sms_sent:
                        # Auto-queue directions SMS for interested customers
                        if call_state.call_result in ['interested', 'callback']:
                            phone_number = None
                            if call_state.lead_data:
                                phone_number = call_state.lead_data.get('phone_number')
                            
                            if phone_number:
                                # Use closest location as default, but final location will be determined
                                # from full transcript analysis during SMS processing
                                default_location = ''
                                if call_state.closest_location_info:
                                    # The processor will fall back to the configured
                                    # default store if this is empty.
                                    default_location = call_state.closest_location_info.get('name', '') or ''
                                
                                call_state.queue_sms_request(
                                    'directions', 
                                    phone_number, 
                                    call_state.current_lead_id,
                                    call_state.current_twilio_number, 
                                    default_location
                                )
                                call_state.mark_sms_sent('directions')
                                logger.info(
                                    f"[{AGENT_ID}] 📱 SMS_AUTO_QUEUED | Type: directions | "
                                    f"Reason: Call result '{call_state.call_result}' | "
                                    f"Phone: {phone_number} | LeadID: {call_state.current_lead_id} | "
                                    f"DefaultLocation: {default_location} | "
                                    f"PendingCount: {len(call_state.pending_sms_requests)} | "
                                    f"Note: Final location will be determined from full transcript"
                                )
                            else:
                                logger.warning(
                                    f"[{AGENT_ID}] ⚠️ SMS_AUTO_QUEUE_FAILED | Reason: No phone number | "
                                    f"LeadID: {call_state.current_lead_id}"
                                )
                    
                    if success:
                        call_state.call_saved = True
                        logger.info(
                            f"[{AGENT_ID}] ✅ CALL_SAVED | CallSID: {call_state.call_sid or 'unknown'} | "
                            f"LeadID: {call_state.current_lead_id}"
                        )
                    else:
                        logger.error(
                            f"[{AGENT_ID}] ❌ CALL_SAVE_FAILED | CallSID: {call_state.call_sid or 'unknown'} | "
                            f"LeadID: {call_state.current_lead_id}"
                        )

                    # ═══════════════════════════════════════════════════════════
                    # UPDATE PHONE NUMBER USAGE AFTER SUCCESSFUL CALL
                    # (Run when call completed; independent of DB save success)
                    # ═══════════════════════════════════════════════════════════
                    if call_state.current_twilio_number:
                        try:
                            usage_success = await twilio_service.update_number_usage(call_state.current_twilio_number)
                            if usage_success:
                                # Broadcast WebSocket event to update dashboard
                                try:
                                    from services.websocket_service import broadcast_event_sync, EventType
                                    broadcast_event_sync(
                                        EventType.CALL_STATS_UPDATE,
                                        {
                                            "call_id": call_state.call_sid,
                                            "lead_id": call_state.current_lead_id,
                                            "result_type": call_state.call_result,
                                            "twilio_number": call_state.current_twilio_number,
                                            "message": "Call completed and usage updated"
                                        }
                                    )
                                except Exception as ws_error:
                                    print(f"[{AGENT_ID}] WARNING: Failed to broadcast WebSocket event: {ws_error}")
                            else:
                                print(f"[{AGENT_ID}] WARNING: Phone number usage update returned False")
                        except Exception as usage_error:
                            print(f"[{AGENT_ID}] WARNING: Failed to update phone number usage: {usage_error}")
                            import traceback
                            traceback.print_exc()
                            # Don't fail the entire process if usage update fails
                
                # ═══════════════════════════════════════════════════════════
                # PROCESS PENDING SMS REQUESTS (ALWAYS runs after call ends)
                # ═══════════════════════════════════════════════════════════
                try:
                    # Log SMS processing state for debugging
                    logger.info(
                        f"[{AGENT_ID}] 📱 SMS_PROCESSING_CHECK | CallSID: {call_state.call_sid or 'unknown'} | "
                        f"Pending: {len(call_state.pending_sms_requests) if call_state.pending_sms_requests else 0} | "
                        f"LeadID: {call_state.current_lead_id} | Processed: {call_state.sms_processed} | "
                        f"HasPending: {bool(call_state.pending_sms_requests)} | HasLeadID: {bool(call_state.current_lead_id)}"
                    )
                    
                    # Process pending SMS requests using CallSMSProcessor
                    # This should run regardless of whether call was saved
                    if call_state.pending_sms_requests and call_state.current_lead_id and not call_state.sms_processed:
                        logger.info(
                            f"[{AGENT_ID}] 📱 SMS_PROCESSING_TRIGGER | CallSID: {call_state.call_sid or 'unknown'} | "
                            f"Pending: {len(call_state.pending_sms_requests)} | LeadID: {call_state.current_lead_id}"
                        )
                        
                        from services.call_sms_processor import CallSMSProcessor
                        
                        # Create SMS processor with correct parameters (send_directions_sms, send_photo_request_sms functions)
                        sms_processor = CallSMSProcessor(
                            AGENT_ID, 
                            send_directions_sms, 
                            send_photo_request_sms
                        )
                        
                        # Get full transcript for location detection
                        full_transcript = call_state.combined_transcript
                        if not full_transcript or full_transcript.strip() == "":
                            full_transcript = call_state.build_combined_transcript_from_parts()
                        
                        logger.info(
                            f"[{AGENT_ID}] 📝 SMS_TRANSCRIPT_READY | Length: {len(full_transcript)} chars"
                        )
                        
                        # Process pending SMS with correct parameters
                        await sms_processor.process_pending_sms(
                            call_state,
                            get_lead_by_id,
                            full_transcript
                        )
                    elif call_state.pending_sms_requests:
                        logger.warning(
                            f"[{AGENT_ID}] ⚠️ SMS_PROCESSING_SKIP | CallSID: {call_state.call_sid or 'unknown'} | "
                            f"Pending: {len(call_state.pending_sms_requests)} | "
                            f"LeadID: {call_state.current_lead_id} | Processed: {call_state.sms_processed}"
                        )
                    else:
                        logger.info(
                            f"[{AGENT_ID}] ℹ️ SMS_NO_PENDING | CallSID: {call_state.call_sid or 'unknown'} | "
                            f"PendingCount: {len(call_state.pending_sms_requests) if call_state.pending_sms_requests else 0}"
                        )
                except Exception as sms_error:
                    logger.error(
                        f"[{AGENT_ID}] SMS_PROCESSING_ERROR | CallSID: {call_state.call_sid or 'unknown'} | "
                        f"Error: {sms_error}",
                        exc_info=True
                    )
    
    except Exception as e:
        print(f"[{AGENT_ID}] ERROR: Fatal error: {e}")
        try:
            await websocket.close()
        except:
            pass


# OpenAI session initialization

async def initialize_openai_session(
    openai_ws,
    openai_settings,
    customer_name: str = None,
    closest_location: str = None
):
    """
    Initialize OpenAI Realtime session with professional prompt.
    Uses dynamic settings from database (configured via frontend Settings page).
    
    Args:
        openai_ws: WebSocket connection to OpenAI
        openai_settings: OpenAI settings from database
        customer_name: Customer's name for personalization
        closest_location: Suggested closest store location
    """
    logger.info(
        f"[{AGENT_ID}] Using OpenAI settings - Voice: {openai_settings.voice}, "
        f"Model: {openai_settings.model}, VAD: {openai_settings.vad_threshold}, "
        f"Temp: {openai_settings.temperature}"
    )
    
    # Get system prompt with context
    professional_prompt = get_system_prompt(
        customer_name=customer_name,
        closest_location=closest_location,
        agent_name=f"Agent {AGENT_ID}"
    )
    
    # Determine temperature from database settings or env config
    temperature = openai_settings.temperature or config.openai.TEMPERATURE
    
    # Session configuration using dynamic settings from database
    session_config = {
        "type": "session.update",
        "session": {
            "turn_detection": {
                "type": "server_vad",
                "threshold": openai_settings.vad_threshold,
                "prefix_padding_ms": config.openai.VAD_PREFIX_PADDING_MS,
                "silence_duration_ms": config.openai.VAD_SILENCE_DURATION_MS
            },
            "input_audio_format": "g711_ulaw",
            "output_audio_format": "g711_ulaw",
            "voice": openai_settings.voice,
            "instructions": professional_prompt,
            "modalities": ["text", "audio"],
            "temperature": temperature,
            "max_response_output_tokens": openai_settings.max_tokens,
            "input_audio_transcription": {
                "model": "whisper-1",
                "language": "en"
            }
        }
    }
    
    await openai_ws.send(json.dumps(session_config))
    
    # English-only instruction
    if config.call.ENFORCE_ENGLISH_ONLY:
        await openai_ws.send(json.dumps({
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "system",
                "content": [{
                    "type": "text",
                    "text": "English only. If they speak another language, say: 'Sorry, I'm English-only, but I can have a Spanish speaker text you. That work?' If they continue, end call politely."
                }]
            }
        }))


# Run the service

if __name__ == "__main__":
    print(f"[{AGENT_ID}] Starting service on port {PORT}")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
