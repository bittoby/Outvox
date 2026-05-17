"""
ElevenLabs Conversational AI Service
Handles integration with ElevenLabs for voice calls via Twilio.

ElevenLabs uses a "register call" approach where:
1. Twilio initiates/receives a call
2. We register the call with ElevenLabs API
3. ElevenLabs returns TwiML that connects the call to their agent via WebSocket
4. The TwiML is returned to Twilio to establish the connection

This is different from OpenAI Realtime which uses direct WebSocket streaming.
"""

import os
import logging
import aiohttp
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# ElevenLabs API configuration
ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1"


def get_elevenlabs_api_key() -> Optional[str]:
    """Get ElevenLabs API key from environment."""
    return os.getenv('ELEVENLABS_API_KEY')


async def register_elevenlabs_call(
    agent_id: str,
    from_number: str,
    to_number: str,
    direction: str = "outbound",
    dynamic_variables: Optional[Dict[str, Any]] = None
) -> Optional[str]:
    """
    Register a call with ElevenLabs Conversational AI.
    
    This endpoint returns TwiML that connects the Twilio call to an ElevenLabs agent.
    
    Args:
        agent_id: The ElevenLabs Agent ID (from the Agents Platform dashboard)
        from_number: The caller's phone number (Twilio number for outbound)
        to_number: The destination phone number (customer for outbound)
        direction: "inbound" or "outbound"
        dynamic_variables: Optional dict of variables to pass to the agent
        
    Returns:
        TwiML string to return to Twilio, or None on error
    """
    api_key = get_elevenlabs_api_key()
    if not api_key:
        logger.error("ElevenLabs API key not configured")
        return None
    
    if not agent_id:
        logger.error("ElevenLabs Agent ID not configured")
        return None
    
    try:
        url = f"{ELEVENLABS_API_URL}/convai/twilio/register-call"
        
        headers = {
            "xi-api-key": api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "agent_id": agent_id,
            "from_number": from_number,
            "to_number": to_number,
            "direction": direction
        }
        
        # Add dynamic variables if provided
        if dynamic_variables:
            payload["conversation_initiation_client_data"] = {
                "dynamic_variables": dynamic_variables
            }
        
        print(f"🟣 ELEVENLABS: Registering call - {direction} from {from_number} to {to_number}")
        print(f"🟣 ELEVENLABS: Agent ID: {agent_id}")
        print(f"🟣 ELEVENLABS: API URL: {url}")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    # ElevenLabs returns TwiML directly
                    twiml = await response.text()
                    print(f"🟣 ELEVENLABS: ✅ Call registered successfully!")
                    print(f"🟣 ELEVENLABS: TwiML response (first 500 chars): {twiml[:500]}")
                    return twiml
                else:
                    error_text = await response.text()
                    print(f"🟣 ELEVENLABS: ❌ Register call failed: {response.status} - {error_text}")
                    logger.error(f"ElevenLabs register call failed: {response.status} - {error_text}")
                    return None
                    
    except Exception as e:
        print(f"🟣 ELEVENLABS: ❌ Exception during register call: {e}")
        import traceback
        traceback.print_exc()
        logger.error(f"Error registering ElevenLabs call: {e}")
        return None


async def get_elevenlabs_agent_info(agent_id: str) -> Optional[Dict[str, Any]]:
    """
    Get information about an ElevenLabs agent.
    
    Args:
        agent_id: The ElevenLabs Agent ID
        
    Returns:
        Agent info dict or None on error
    """
    api_key = get_elevenlabs_api_key()
    if not api_key:
        logger.error("ElevenLabs API key not configured")
        return None
    
    try:
        url = f"{ELEVENLABS_API_URL}/convai/agents/{agent_id}"
        
        headers = {
            "xi-api-key": api_key
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to get ElevenLabs agent info: {response.status} - {error_text}")
                    return None
                    
    except Exception as e:
        logger.error(f"Error getting ElevenLabs agent info: {e}")
        return None


def generate_elevenlabs_twiml_response(
    agent_id: str,
    from_number: str,
    to_number: str,
    customer_name: Optional[str] = None
) -> str:
    """
    Generate TwiML for ElevenLabs call (fallback if register_call fails).
    
    This creates a TwiML response that connects to ElevenLabs via their WebSocket.
    
    Note: This is a fallback - prefer using register_elevenlabs_call() which
    handles the connection setup on ElevenLabs' side.
    """
    api_key = get_elevenlabs_api_key()
    
    # Build the WebSocket URL for ElevenLabs
    ws_url = f"wss://api.elevenlabs.io/v1/convai/conversation?agent_id={agent_id}"
    
    # Add customer context as query params if available
    if customer_name:
        ws_url += f"&customer_name={customer_name}"
    
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="{ws_url}">
            <Parameter name="from_number" value="{from_number}" />
            <Parameter name="to_number" value="{to_number}" />
        </Stream>
    </Connect>
</Response>"""
    
    return twiml
