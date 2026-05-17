"""
Twilio Service
Handles all Twilio-related operations including calls and SMS.
"""

import os
import aiohttp
from typing import Optional, Dict
from datetime import datetime
from zoneinfo import ZoneInfo
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Connect
from urllib.parse import quote

from config import config
from utils import (
    get_closest_location, STORE_LOCATIONS,
    detect_location_from_transcript, get_store_info
)
from utils.location_mapper import default_store_key
from core.exceptions import TwilioError, ValidationError, PhoneNumberValidationError
from twilio.base.exceptions import TwilioRestException


class TwilioService:
    """Service for Twilio operations."""
    
    def __init__(self, agent_id: Optional[str] = None):
        self.agent_id = agent_id or "System"
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Twilio client."""
        try:
            self.client = Client(config.twilio.ACCOUNT_SID, config.twilio.AUTH_TOKEN)
        except Exception as e:
            print(f"[{self.agent_id}] ERROR: Failed to initialize Twilio client: {e}")
            self.client = None
    
    async def verify_twilio_number(self, phone_number: str) -> bool:
        """
        Verify if a Twilio number exists and is active in the database.
        
        Args:
            phone_number: Twilio phone number to verify
            
        Returns:
            bool: True if number exists and is active
        """
        try:
            url = f"{config.database.SERVICE_URL}/api/phone-numbers/check/{phone_number}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        exists = data.get('exists', False)
                        is_active = data.get('is_active', False)
                        return exists and is_active
                    else:
                        print(f"[{self.agent_id}] ERROR: Failed to verify Twilio number: HTTP {response.status}")
                        return False
        except Exception as e:
            print(f"[{self.agent_id}] ERROR: Error verifying Twilio number: {e}")
            return False
    
    async def get_available_twilio_number(
        self, 
        store_id: Optional[int] = None, 
        for_manual_dial: bool = False
    ) -> Optional[str]:
        """
        Get an available Twilio number for calling.
        
        Args:
            store_id: Optional store ID to filter numbers
            for_manual_dial: If True, prioritize numbers with lower usage
            
        Returns:
            str: Available Twilio number, or None if none available
        """
        try:
            # Build URL with query parameters
            url = f"{config.database.SERVICE_URL}/api/phone-numbers/available"
            params = {}
            if store_id is not None:
                params['store_id'] = store_id
            if for_manual_dial:
                params['for_manual_dial'] = 'true'
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Handle both response formats:
                        # 1. Single number format: {"phone_number": "+1234..."}
                        # 2. List format: {"available_numbers": [...], "count": N}
                        phone_number = data.get('phone_number')
                        
                        # If single number format not found, try list format
                        if not phone_number and 'available_numbers' in data:
                            available_numbers = data.get('available_numbers', [])
                            if available_numbers and len(available_numbers) > 0:
                                phone_number = available_numbers[0].get('phone_number')
                        
                        if not phone_number:
                            print(f"[{self.agent_id}] WARNING: No available phone numbers (store_id={store_id}, for_manual_dial={for_manual_dial})")
                            print(f"[{self.agent_id}] Response data: {data}")
                        
                        return phone_number
                    else:
                        error_text = await response.text()
                        print(f"[{self.agent_id}] ERROR: Failed to get Twilio number: HTTP {response.status} - {error_text}")
                        return None
        except Exception as e:
            print(f"[{self.agent_id}] ERROR: Error getting Twilio number: {e}")
            return None
    
    async def update_number_usage(self, phone_number: str) -> bool:
        """
        Update usage statistics for a Twilio number.
        
        Args:
            phone_number: Twilio phone number to update
            
        Returns:
            bool: Success status
        """
        try:
            # Normalize phone number to E.164 format to match database
            from utils.phone_validator import validate_us_phone_number
            is_valid, normalized_phone, error = validate_us_phone_number(phone_number)
            if not is_valid:
                print(f"[{self.agent_id}] ERROR: Invalid phone number for usage update: {phone_number} - {error}")
                return False
            
            url = f"{config.database.SERVICE_URL}/api/phone-numbers/{quote(normalized_phone)}/update-usage"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        return True
                    else:
                        error_text = await response.text()
                        print(f"[{self.agent_id}] ERROR: Failed to update usage: HTTP {response.status} - {error_text}")
                        return False
        except aiohttp.ClientError as e:
            print(f"[{self.agent_id}] ERROR: Network error updating number usage: {e}")
            return False
        except Exception as e:
            print(f"[{self.agent_id}] ERROR: Error updating number usage: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def make_outbound_call(self, lead: Dict, twilio_number: str) -> Optional[str]:
        """
        Initiate an outbound call using Twilio.
        
        Args:
            lead: Lead data dictionary
            twilio_number: Twilio number to use for calling
            
        Returns:
            str: Call SID if successful, None otherwise
        """
        # Time-of-day restriction (9 AM - 6 PM local time)
        local_tz = ZoneInfo('America/New_York')
        local_time = datetime.now(local_tz)
        current_hour = local_time.hour
        
        if current_hour < 9 or current_hour >= 18:
            print(f"[{self.agent_id}] ⏰ Call blocked: Outside permitted hours (current time: {local_time.strftime('%I:%M %p %Z')})")
            print(f"[{self.agent_id}]    → Permitted hours: 9:00 AM - 6:00 PM local time")
            return None
        
        if not self.client:
            print(f"[{self.agent_id}] ERROR: Twilio client not initialized")
            return None
        
        try:
            # Build webhook URL with agent-specific routing
            webhook_url = f"{config.get_agent_url(self.agent_id)}/twilio-voice?lead_id={lead['lead_id']}&twilio_number={quote(twilio_number)}"
            
            # Create call with recording enabled if configured
            call_params = {
                'to': lead['phone_number'],
                'from_': twilio_number,
                'url': webhook_url,
                'method': 'POST',
                'timeout': config.twilio.CALL_TIMEOUT,
            }
            
            # Add recording parameters if enabled
            if config.call.ENABLE_CALL_RECORDING:
                call_params['record'] = True
                call_params['recording_status_callback_method'] = 'POST'
                if config.call.RECORDING_STATUS_CALLBACK:
                    call_params['recording_status_callback'] = config.call.RECORDING_STATUS_CALLBACK
            
            call = self.client.calls.create(**call_params)
            
            # Usage tracking is updated when call completes successfully (not when call starts)
            
            return call.sid
            
        except TwilioRestException as e:
            error_msg = f"Twilio API error: {e.msg if hasattr(e, 'msg') else str(e)}"
            print(f"[{self.agent_id}] ERROR: {error_msg}")
            raise TwilioError(error_msg, details={"twilio_code": e.code if hasattr(e, 'code') else None})
        except Exception as e:
            error_msg = f"Unexpected error during call creation: {str(e)}"
            print(f"[{self.agent_id}] ERROR: {error_msg}")
            raise TwilioError(error_msg)
    
    async def send_directions_sms(
        self, 
        phone_number: str, 
        closest_location: str, 
        lead_id: int, 
        twilio_number: str, 
        transcript: str = "", 
        override_store_key: str = None
    ) -> bool:
        """
        Send store directions via SMS with secure, backend-enforced location logic.
        
        Args:
            phone_number: Customer's phone number
            closest_location: Closest store location name (from area code)
            lead_id: Lead identifier
            twilio_number: Twilio number to send from
            transcript: Customer's spoken text (for detecting specific location mentions)
            override_store_key: Override store key if provided
            
        Returns:
            bool: Success status
        """
        if not self.client:
            print(f"[{self.agent_id}] ERROR: Twilio client not initialized")
            return False
        
        if not phone_number:
            print(f"[{self.agent_id}] ERROR: Phone number is required")
            return False
        
        if not twilio_number:
            print(f"[{self.agent_id}] ERROR: Twilio number is required")
            return False
        
        try:
            # Clean transcript
            clean_transcript = transcript
            if transcript:
                clean_transcript = transcript.replace("Customer:", "").replace("customer:", "").strip()
                if "\n" in clean_transcript:
                    clean_transcript = clean_transcript.replace("\n", " ")
            
            # Determine the correct store location
            # Priority: 1) override_store_key (from full conversation analysis), 2) transcript detection, 3) closest_location, 4) default
            store_key = None
            
            # Import logger if not already imported
            import logging
            logger = logging.getLogger(__name__)
            
            # First priority: override_store_key (already analyzed from full transcript in call_sms_processor)
            if override_store_key:
                # Normalize to lowercase
                override_key_lower = override_store_key.lower()
                if override_key_lower in STORE_LOCATIONS:
                    store_key = override_key_lower
                    logger.info(
                        f"[{self.agent_id}] 📍 STORE_SELECTED | Key: {store_key} | "
                        f"Source: override_store_key (from full conversation analysis)"
                    )
            
            # Second priority: If override_store_key not valid, detect from transcript
            if store_key is None and clean_transcript:
                detected_location = detect_location_from_transcript(clean_transcript)
                if detected_location and detected_location in STORE_LOCATIONS:
                    store_key = detected_location
                    logger.info(
                        f"[{self.agent_id}] 📍 STORE_SELECTED | Key: {store_key} | "
                        f"Source: transcript_detection"
                    )
            
            # Third priority: Use closest_location from area code (normalize to lowercase)
            if store_key is None and closest_location:
                closest_lower = closest_location.lower()
                if closest_lower in STORE_LOCATIONS:
                    store_key = closest_lower
                    logger.info(
                        f"[{self.agent_id}] 📍 STORE_SELECTED | Key: {store_key} | "
                        f"Source: closest_location (area code)"
                    )
                else:
                    # Try to find by name match
                    temp_store = get_store_info(closest_location)
                    for key, store in STORE_LOCATIONS.items():
                        if store['name'] == temp_store['name'] or store.get('db_name') == temp_store.get('db_name', ''):
                            store_key = key
                            logger.info(
                                f"[{self.agent_id}] 📍 STORE_SELECTED | Key: {store_key} | "
                                f"Source: closest_location (name match)"
                            )
                            break
            
            # Final fallback: default to the first configured store.
            if store_key is None:
                store_key = default_store_key()
                logger.warning(
                    f"[{self.agent_id}] ⚠️ STORE_DEFAULT | Key: {store_key} | "
                    f"Reason: No valid location found, using default"
                )

            # Get store details (get_store_info falls back to the default itself).
            store_info = get_store_info(store_key)
            
            # Build message
            company_name = config.brand.COMPANY_NAME
            company_tagline = config.brand.COMPANY_TAGLINE
            message = f"""Need Fast Cash Today?

Bring your valuables to {company_name} - {store_info['name']} and get a loan on the spot - no credit check, no bank hassle.

{store_info['address']}

Get directions:
{store_info['google_maps']}

Borrow cash today - keep your items safe with us until you're ready to pick them up.
Extend or renew anytime.
Low monthly rates.
Fast, friendly service in minutes.

Text us photos of your items for a free loan quote before you come in.

Hours:
{store_info['hours_weekdays']}
{store_info['hours_saturday']}
{store_info['hours_sunday']}

{company_name}
{company_tagline}

Reply STOP to opt out."""
            
            # Normalize phone number to E.164 format
            normalized_phone = phone_number
            if not normalized_phone.startswith('+'):
                clean_phone = ''.join(c for c in normalized_phone if c.isdigit())
                if clean_phone.startswith('1') and len(clean_phone) == 11:
                    normalized_phone = f"+{clean_phone}"
                elif len(clean_phone) == 10:
                    normalized_phone = f"+1{clean_phone}"
            
            # Send SMS via Twilio
            try:
                message_obj = self.client.messages.create(
                    body=message,
                    from_=twilio_number,
                    to=normalized_phone
                )
            except TwilioRestException as twilio_error:
                print(f"[{self.agent_id}] ERROR: Twilio API error sending SMS: {twilio_error}")
                import traceback
                traceback.print_exc()
                return False
            except Exception as twilio_error:
                print(f"[{self.agent_id}] ERROR: Unexpected error sending SMS: {twilio_error}")
                import traceback
                traceback.print_exc()
                return False
            
            # Log SMS to database (this will trigger WebSocket broadcast)
            sms_data = {
                "lead_id": lead_id,
                "phone_number": normalized_phone,
                "message_type": "directions",
                "message_content": message,
                "twilio_sid": message_obj.sid
            }
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{config.database.SERVICE_URL}/api/sms/send",
                        json=sms_data
                    ) as response:
                        if response.status == 200:
                            # SMS logged successfully - WebSocket broadcast should have been triggered by sms_service
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.info(
                                f"[{self.agent_id}] SMS_LOGGED | LeadID: {lead_id} | "
                                f"Phone: {normalized_phone} | TwilioSID: {message_obj.sid}"
                            )
                        else:
                            response_text = await response.text()
                            print(f"[{self.agent_id}] WARNING: Failed to log directions SMS - Status: {response.status}, Response: {response_text}")
            except Exception as db_error:
                print(f"[{self.agent_id}] WARNING: Database logging error (SMS was sent): {db_error}")
                import traceback
                traceback.print_exc()
            
            return True
        except Exception as e:
            print(f"[{self.agent_id}] ERROR: Error sending directions SMS: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def send_photo_request_sms(
        self, 
        phone_number: str, 
        lead_id: int, 
        twilio_number: str, 
        location_name: str = "",
        transcript: str = ""
    ) -> bool:
        """
        Send photo request SMS for item appraisal with secure location detection.
        
        Args:
            phone_number: Customer's phone number
            lead_id: Lead identifier
            twilio_number: Twilio number to send from
            location_name: Default store location name
            transcript: Customer's spoken text (for detecting specific location mentions)
            
        Returns:
            bool: Success status
        """
        if not self.client:
            print(f"[{self.agent_id}] ERROR: Twilio client not initialized")
            return False
        
        try:
            # Similar logic to send_directions_sms for location detection
            clean_transcript = transcript.replace("Customer:", "").replace("customer:", "").strip() if transcript else ""
            
            # Determine store (similar logic as directions SMS)
            store_key = None
            detected_location = detect_location_from_transcript(clean_transcript) if clean_transcript else None
            
            if detected_location:
                store_key = detected_location
            elif location_name and location_name in STORE_LOCATIONS:
                store_key = location_name.lower()
            else:
                store_key = default_store_key()

            store_info = get_store_info(store_key)
            
            # Build message
            message = f"""Hi! Thanks for your interest in {config.brand.COMPANY_NAME}.

To give you the best loan quote, please send us photos of your items:
• Gold jewelry
• Watches
• Electronics
• Or any valuable items

We'll review your photos and get back to you with a free loan estimate.

{store_info['name']}
{store_info['address']}
{store_info['phone']}

Reply STOP to opt out."""
            
            # Normalize phone number
            normalized_phone = phone_number
            if not normalized_phone.startswith('+'):
                clean_phone = ''.join(c for c in normalized_phone if c.isdigit())
                if clean_phone.startswith('1') and len(clean_phone) == 11:
                    normalized_phone = f"+{clean_phone}"
                elif len(clean_phone) == 10:
                    normalized_phone = f"+1{clean_phone}"
            
            # Send SMS
            try:
                message_obj = self.client.messages.create(
                    body=message,
                    from_=twilio_number,
                    to=normalized_phone
                )
            except Exception as twilio_error:
                print(f"[{self.agent_id}] ERROR: Twilio API error sending photo request SMS: {twilio_error}")
                return False
            
            # Log SMS to database (this will trigger WebSocket broadcast)
            sms_data = {
                "lead_id": lead_id,
                "phone_number": normalized_phone,
                "message_type": "photo_request",
                "message_content": message,
                "twilio_sid": message_obj.sid
            }
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{config.database.SERVICE_URL}/api/sms/send",
                        json=sms_data
                    ) as response:
                        if response.status == 200:
                            # SMS logged successfully - WebSocket broadcast should have been triggered by sms_service
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.info(
                                f"[{self.agent_id}] SMS_LOGGED | LeadID: {lead_id} | "
                                f"Phone: {normalized_phone} | TwilioSID: {message_obj.sid} | Type: photo_request"
                            )
                        else:
                            response_text = await response.text()
                            print(f"[{self.agent_id}] WARNING: Failed to log photo request SMS - Status: {response.status}, Response: {response_text}")
            except Exception as db_error:
                print(f"[{self.agent_id}] WARNING: Database logging error (SMS was sent): {db_error}")
                import traceback
                traceback.print_exc()
            
            return True
        except Exception as e:
            print(f"[{self.agent_id}] ERROR: Error sending photo request SMS: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def create_twiml_response(self, lead_id: int, twilio_number: str) -> str:
        """
        Create TwiML response to connect call to WebSocket.
        
        Args:
            lead_id: Lead ID
            twilio_number: Twilio number being used
            
        Returns:
            str: TwiML XML response
        """
        response = VoiceResponse()
        connect = Connect()
        
        # Construct WebSocket URL
        websocket_url = f"wss://{config.agent.NGROK_HOST}/agent/{self.agent_id}/media-stream?lead_id={lead_id}&twilio_number={quote(twilio_number)}"
        
        connect.stream(url=websocket_url)
        response.append(connect)
        
        return str(response)
    
    def send_sms_message(
        self,
        to_number: str,
        body: str,
        from_number: Optional[str] = None
    ) -> Dict[str, Optional[str]]:
        """
        Send a generic SMS message via Twilio.
        
        Args:
            to_number: Destination phone number (will be normalized)
            body: SMS message body
            from_number: Optional sender phone number (defaults to configured number)
            
        Returns:
            Dict with 'to' and 'sid' keys
            
        Raises:
            TwilioError: If SMS sending fails
            ValidationError: If phone numbers are invalid
        """
        if not self.client:
            raise TwilioError("Twilio client not initialized")
        
        if not body or not body.strip():
            raise ValidationError("SMS body is required")
        
        # Normalize phone numbers
        from utils.phone_validator import validate_us_phone_number
        
        is_valid_to, normalized_to, error_to = validate_us_phone_number(to_number)
        if not is_valid_to:
            raise ValidationError(f"Invalid destination phone number: {error_to}")
        
        # Get sender number
        sender_number = from_number
        if not sender_number:
            # Try to get from config
            from config import config
            sender_number = config.twilio.PHONE_NUMBER
        
        if not sender_number:
            raise TwilioError("Twilio sending phone number is not configured")
        
        is_valid_from, normalized_from, error_from = validate_us_phone_number(sender_number)
        if not is_valid_from:
            raise ValidationError(f"Invalid Twilio sender phone number: {error_from}")
        
        # ⚠️ CRITICAL VALIDATION: Prevent sending SMS from a number to itself
        # Twilio does not allow sending SMS from a number to the same number
        if normalized_from == normalized_to:
            raise ValidationError(
                f"Cannot send SMS: From number ({normalized_from}) and To number ({normalized_to}) are the same. "
                f"Twilio does not allow sending SMS from a number to itself."
            )
        
        try:
            message = self.client.messages.create(
                body=body.strip(),
                from_=normalized_from,
                to=normalized_to
            )
            
            return {
                "to": normalized_to,
                "sid": message.sid
            }
        except TwilioRestException as e:
            error_msg = f"Twilio SMS error: {e.msg if hasattr(e, 'msg') else str(e)}"
            raise TwilioError(error_msg, details={"twilio_code": e.code if hasattr(e, 'code') else None})
        except Exception as e:
            raise TwilioError(f"Unexpected error sending SMS: {str(e)}")

