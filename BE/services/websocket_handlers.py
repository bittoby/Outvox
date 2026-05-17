"""
WebSocket Handlers
Handles Twilio and OpenAI WebSocket message processing.
Extracted from outbound_main.py for better separation of concerns.
"""

import json
import base64
import asyncio
import logging
from typing import Optional
from datetime import datetime
from services.call_state_manager import CallState
from services.call_business_logic import CallBusinessLogic
from utils import get_language_switch_message
from utils.location_mapper import STORE_LOCATIONS
from config import config

logger = logging.getLogger(__name__)


class TwilioMessageHandler:
    """Handles messages from Twilio WebSocket."""
    
    def __init__(self, websocket, openai_ws, call_state: CallState, agent_id: str):
        self.websocket = websocket
        self.openai_ws = openai_ws
        self.call_state = call_state
        self.agent_id = agent_id
        self.business_logic = CallBusinessLogic()
    
    async def handle_start_event(self, data: dict, get_lead_by_call_sid, get_closest_location):
        """Handle call start event."""
        self.call_state.stream_sid = data['start']['streamSid']
        self.call_state.call_sid = data['start'].get('callSid', self.call_state.stream_sid)
        
        logger.info(
            f"[{self.agent_id}] 📞 CALL_START | CallSID: {self.call_state.call_sid} | "
            f"StreamSID: {self.call_state.stream_sid}"
        )
        
        # Get lead information
        if not self.call_state.current_lead_id:
            lead_data = await get_lead_by_call_sid(self.call_state.call_sid)
            if lead_data:
                self.call_state.current_lead_id = lead_data['lead_id']
                self.call_state.lead_data = lead_data
                self.call_state.customer_name = lead_data.get('name')
                phone_number = lead_data.get('phone_number')
                
                logger.info(
                    f"[{self.agent_id}] 📋 LEAD_INFO | LeadID: {self.call_state.current_lead_id} | "
                    f"Name: {self.call_state.customer_name} | Phone: {phone_number}"
                )
                
                # Get closest location
                self.call_state.closest_location_info = get_closest_location(phone_number, None)
                if self.call_state.closest_location_info:
                    logger.info(
                        f"[{self.agent_id}] 📍 LOCATION | "
                        f"Closest: {self.call_state.closest_location_info.get('name', 'Unknown')}"
                    )
    
    async def handle_media_event(self, data: dict):
        """Handle audio media event from Twilio."""
        self.call_state.latest_media_timestamp = int(data['media']['timestamp'])
        await self.openai_ws.send(json.dumps({
            "type": "input_audio_buffer.append",
            "audio": data['media']['payload']
        }))
    
    async def handle_stop_event(self, save_call_result, mark_dnc, get_lead_by_id):
        """Handle call stop event."""
        # Call result saving and SMS processing are handled in the finally block of handle_media_stream
        # to ensure full conversation transcript is available and avoid race conditions
    
    async def _save_call_result(self, save_call_result):
        """Save call result to database."""
        duration = self.call_state.get_duration()
        
        # Ensure combined transcript has content
        final_combined_tx = self.call_state.combined_transcript
        if not final_combined_tx or final_combined_tx.strip() == "":
            final_combined_tx = self._build_combined_transcript()
        
        # Determine call result
        result, reason, confidence = self.business_logic.detect_call_result(
            self.call_state.customer_transcript,
            self.call_state.agent_transcript
        )
        self.call_state.call_result = result
        
        success = await save_call_result(
            self.call_state.current_lead_id,
            self.call_state.call_sid or "unknown",
            self.call_state.current_twilio_number,
            "completed",
            self.call_state.call_result,
            self.call_state.customer_transcript,
            self.call_state.agent_transcript,
            final_combined_tx,
            duration=duration
        )
        
        if success:
            self.call_state.call_saved = True
            logger.info(
                f"[{self.agent_id}] ✅ CALL_SAVED | LeadID: {self.call_state.current_lead_id} | "
                f"CallSID: {self.call_state.call_sid} | Result: {self.call_state.call_result} | "
                f"Duration: {duration}s"
            )
        else:
            logger.error(
                f"[{self.agent_id}] ❌ CALL_SAVE_FAILED | LeadID: {self.call_state.current_lead_id} | "
                f"CallSID: {self.call_state.call_sid}"
            )
    
    # REMOVED: _process_pending_sms method
    # SMS processing is now handled in the finally block of handle_media_stream
    # in outbound_main.py using CallSMSProcessor for proper context and transcript access
    
    def _build_combined_transcript(self) -> str:
        """Build combined transcript from individual transcripts."""
        customer_lines = [
            line for line in self.call_state.customer_transcript.split('\n') 
            if line.strip() and line.strip().startswith('Customer:')
        ]
        agent_lines = [
            line for line in self.call_state.agent_transcript.split('\n') 
            if line.strip() and line.strip().startswith('Agent:')
        ]
        
        combined_parts = []
        max_len = max(len(customer_lines), len(agent_lines))
        for i in range(max_len * 2):
            if i % 2 == 0 and i // 2 < len(agent_lines):
                combined_parts.append(agent_lines[i // 2])
            elif i % 2 == 1 and i // 2 < len(customer_lines):
                combined_parts.append(customer_lines[i // 2])
            elif i // 2 < len(agent_lines):
                combined_parts.append(agent_lines[i // 2])
            elif i // 2 < len(customer_lines):
                combined_parts.append(customer_lines[i // 2])
        
        for i in range(max_len, len(agent_lines)):
            combined_parts.append(agent_lines[i])
        for i in range(max_len, len(customer_lines)):
            combined_parts.append(customer_lines[i])
        
        return '\n'.join(combined_parts)
    
    async def handle_mark_event(self, data: dict):
        """Handle mark event for interruption tracking."""
        if self.call_state.mark_queue:
            self.call_state.mark_queue.pop(0)


class OpenAIMessageHandler:
    """Handles messages from OpenAI Realtime API."""
    
    def __init__(self, websocket, openai_ws, call_state: CallState, agent_id: str,
                 send_directions_sms, send_photo_request_sms, mark_dnc):
        self.websocket = websocket
        self.openai_ws = openai_ws
        self.call_state = call_state
        self.agent_id = agent_id
        self.send_directions_sms = send_directions_sms
        self.send_photo_request_sms = send_photo_request_sms
        self.mark_dnc = mark_dnc
        self.business_logic = CallBusinessLogic()
    
    async def handle_customer_transcript(self, response: dict):
        """Handle customer transcript from OpenAI."""
        transcript = response.get('transcript', '')
        if not transcript or not transcript.strip():
            return
        
        # Normalize smart quotes
        normalized = transcript.replace('’', "'").replace('"', '"').replace('"', '"')
        self.call_state.add_customer_transcript(normalized)
        
        # Log customer speech in real-time with emoji for easy identification (full transcript)
        duration = self.call_state.get_duration()
        logger.info(
            f"[{self.agent_id}] 👤 CUSTOMER | Duration: {duration}s | "
            f"\"{normalized}\""
        )
        
        # Real-time result detection - update call_result if confidence is high enough
        if len(self.call_state.customer_transcript) > 50:
            result, reason, confidence = self.business_logic.detect_call_result(
                normalized, self.call_state.agent_transcript
            )
            
            # Update call_result if we have a positive result with good confidence
            # Only update if it's better than current (interested > callback > not_interested)
            if result in ['interested', 'callback'] and confidence >= 0.6:
                # Only update if current result is not already positive
                if self.call_state.call_result not in ['interested', 'callback']:
                    self.call_state.call_result = result
                    logger.info(
                        f"[{self.agent_id}] 📊 CALL_RESULT_UPDATED | Result: {result} | "
                        f"Confidence: {confidence:.2f} | Reason: {reason}"
                    )
            elif result == 'not_interested' and confidence >= 0.7:
                # Only set to not_interested if we're very confident and haven't seen interest
                if self.call_state.call_result not in ['interested', 'callback']:
                    self.call_state.call_result = result
        
        # Language validation
        is_valid, detected_lang, should_end = self.business_logic.validate_customer_language(
            transcript, self.call_state
        )
        
        if not is_valid:
            logger.warning(
                f"[{self.agent_id}] ⚠️ LANGUAGE_WARNING | Detected: {detected_lang} | "
                f"Attempts: {self.call_state.non_english_count} | ShouldEnd: {should_end}"
            )
            if should_end:
                logger.warning(
                    f"[{self.agent_id}] 🛑 CALL_END_TRIGGER | Reason: language_barrier | "
                    f"Too many non-English attempts"
                )
                self.call_state.call_result = "language_barrier"
                await self._send_language_end_message()
                return True  # Signal to end call
            else:
                switch_msg = get_language_switch_message(detected_lang)
                await self._send_language_reminder(switch_msg)
        
        # DNC detection
        should_end, reason = self.business_logic.check_dnc_request(transcript, self.call_state)
        if should_end:
            logger.warning(
                f"[{self.agent_id}] 🚫 DNC_DETECTED | Reason: {reason} | "
                f"Phone: {self.call_state.lead_data.get('phone_number') if self.call_state.lead_data else 'unknown'}"
            )
            if self.call_state.lead_data:
                await self.mark_dnc(self.call_state.lead_data.get('phone_number'))
            await self._send_dnc_confirmation()
            return True  # Signal to end call
        
        # SMS trigger detection
        await self._handle_sms_triggers(transcript)
        
        return False
    
    async def handle_agent_transcript(self, response: dict):
        """Handle agent transcript from OpenAI."""
        text = response.get('transcript', '') or response.get('text', '')
        if not text or not text.strip():
            return
        
        self.call_state.add_agent_transcript(text)
        
        # Log agent speech in real-time with emoji for easy identification (full transcript)
        duration = self.call_state.get_duration()
        logger.info(
            f"[{self.agent_id}] 🤖 AGENT | Duration: {duration}s | "
            f"\"{text}\""
        )
        
        # Detect suggested store from agent utterance. We match against the
        # configured store keys and names, so this stays in sync with whatever
        # locations the operator has configured.
        agent_text_lower = text.lower()
        for store_key, store in STORE_LOCATIONS.items():
            candidates = {store_key.lower(), store['name'].lower()}
            db_name = store.get('db_name')
            if db_name:
                candidates.add(db_name.lower())
            if any(candidate and candidate in agent_text_lower for candidate in candidates):
                self.call_state.suggested_store_key = store_key
                logger.info(
                    f"[{self.agent_id}] 📍 STORE_DETECTED | Store: {self.call_state.suggested_store_key}"
                )
                break
        
        # Check for SMS permission request
        permission_asked, sms_type = self.business_logic.check_sms_permission_request(text)
        if permission_asked:
            self.call_state.sms_permission_asked = True
            self.call_state.pending_sms_type = sms_type
            logger.info(
                f"[{self.agent_id}] 📱 SMS_PERMISSION_ASKED | Type: {sms_type}"
            )
    
    async def handle_audio_delta(self, response: dict):
        """Handle audio delta from OpenAI."""
        if 'delta' in response and self.call_state.stream_sid:
            audio_payload = base64.b64encode(
                base64.b64decode(response['delta'])
            ).decode('utf-8')
            
            await self.websocket.send_json({
                "event": "media",
                "streamSid": self.call_state.stream_sid,
                "media": {"payload": audio_payload}
            })
            
            if self.call_state.response_start_timestamp_twilio is None:
                self.call_state.response_start_timestamp_twilio = self.call_state.latest_media_timestamp
            
            if response.get('item_id'):
                self.call_state.last_assistant_item = response['item_id']
            
            await self._send_mark()
    
    async def handle_speech_started(self):
        """Handle interruption when customer starts speaking."""
        await self._handle_interruption()
    
    async def _handle_sms_triggers(self, transcript: str):
        """Handle SMS trigger detection and queuing."""
        # First, check for explicit SMS triggers (customer directly requests SMS)
        sms_type = self.business_logic.detect_sms_triggers(transcript, self.call_state)
        
        # Track if consent was detected via permission flow
        consent_detected_via_permission = False
        
        # If no explicit trigger but permission was asked, check for consent response
        if not sms_type and self.call_state.sms_permission_asked and self.call_state.pending_sms_type:
            # Agent asked for permission, now check if customer gave consent
            gave_consent, explicit_request = self.business_logic.check_consent_response(
                transcript, self.call_state.sms_permission_asked
            )
            
            if gave_consent or explicit_request:
                # Customer gave consent, use the pending SMS type
                sms_type = self.call_state.pending_sms_type
                consent_detected_via_permission = True
                logger.info(
                    f"[{self.agent_id}] 📱 SMS_CONSENT_DETECTED | Type: {sms_type} | "
                    f"Transcript: \"{transcript[:100]}\" | Consent: {gave_consent} | Explicit: {explicit_request}"
                )
            else:
                # No consent detected yet, wait for more customer input
                logger.debug(
                    f"[{self.agent_id}] SMS_WAITING_FOR_CONSENT | PermissionAsked: True | "
                    f"PendingType: {self.call_state.pending_sms_type} | Transcript: \"{transcript[:50]}\""
                )
                return
        
        # If still no SMS type, exit
        if not sms_type:
            return
        
        # Check if already sent
        if (sms_type == 'directions' and self.call_state.directions_sms_sent) or \
           (sms_type == 'photo_request' and self.call_state.photo_sms_sent):
            logger.debug(
                f"[{self.agent_id}] SMS_ALREADY_SENT | Type: {sms_type}"
            )
            return
        
        # Check consent (only if not already detected via permission flow)
        if not consent_detected_via_permission:
            gave_consent, explicit_request = self.business_logic.check_consent_response(
                transcript, self.call_state.sms_permission_asked
            )
            
            # For explicit requests, consent is implied. For permission-based, require consent
            if not explicit_request and not gave_consent:
                logger.debug(
                    f"[{self.agent_id}] SMS_NO_CONSENT | Type: {sms_type} | "
                    f"GaveConsent: {gave_consent} | ExplicitRequest: {explicit_request} | "
                    f"PermissionAsked: {self.call_state.sms_permission_asked}"
                )
                return
        
        # Queue SMS request (FIXED: was incorrectly indented)
        phone_number = self.call_state.lead_data.get('phone_number') if self.call_state.lead_data else None
        if not self.call_state.current_lead_id:
            logger.warning(
                f"[{self.agent_id}] ⚠️ SMS_QUEUE_FAILED | Type: {sms_type} | Reason: No lead ID"
            )
            return
        
        if not phone_number:
            logger.warning(
                f"[{self.agent_id}] ⚠️ SMS_QUEUE_FAILED | Type: {sms_type} | Reason: No phone number | LeadID: {self.call_state.current_lead_id}"
            )
            return
        
        default_location = (
            self.call_state.closest_location_info['name']
            if self.call_state.closest_location_info else ''
        )
        self.call_state.queue_sms_request(
            sms_type, phone_number, self.call_state.current_lead_id,
            self.call_state.current_twilio_number, default_location
        )
        self.call_state.mark_sms_sent(sms_type)
        self.call_state.sms_consent_given = True
        self.call_state.sms_permission_asked = False
        self.call_state.pending_sms_type = None
        
        logger.info(
            f"[{self.agent_id}] 📱 SMS_QUEUED | Type: {sms_type} | "
            f"Phone: {phone_number} | Location: {default_location} | LeadID: {self.call_state.current_lead_id} | "
            f"PendingCount: {len(self.call_state.pending_sms_requests)}"
        )
        
        # Send acknowledgment
        ack_msg = "Perfect! I'll send you the directions via text right after we hang up. Check your phone in a moment!" if sms_type == 'directions' else "Great! I'll send you a text with instructions on how to send photos of your items for a free appraisal right after we hang up."
        await self._send_acknowledgment(ack_msg)
    
    async def _send_language_end_message(self):
        """Send message to end call due to language barrier."""
        await self.openai_ws.send(json.dumps({
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "system",
                "content": [{
                    "type": "text",
                    "text": "End the call politely: 'I apologize, I can only speak English. Have a great day!'"
                }]
            }
        }))
    
    async def _send_language_reminder(self, message: str):
        """Send reminder to speak English."""
        await self.openai_ws.send(json.dumps({
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "system",
                "content": [{
                    "type": "text",
                    "text": f"Say this naturally and conversationally: '{message}'"
                }]
            }
        }))
    
    async def _send_dnc_confirmation(self):
        """Send DNC confirmation and end call."""
        await self.openai_ws.send(json.dumps({
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "system",
                "content": [{
                    "type": "text",
                    "text": "Say this naturally and empathetically: 'Oh, absolutely - no problem at all. I'll make sure you're removed from our list right away. You won't get any more calls from us. Have a great day!' Then end the call immediately."
                }]
            }
        }))
        await asyncio.sleep(2)
    
    async def _send_acknowledgment(self, message: str):
        """Send SMS acknowledgment to customer."""
        await self.openai_ws.send(json.dumps({
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "system",
                "content": [{
                    "type": "text",
                    "text": f"Say this naturally and enthusiastically: '{message}'"
                }]
            }
        }))
    
    async def _handle_interruption(self):
        """Handle customer interrupting agent."""
        if self.call_state.last_assistant_item and self.call_state.mark_queue and \
           self.call_state.response_start_timestamp_twilio:
            elapsed_time = self.call_state.latest_media_timestamp - self.call_state.response_start_timestamp_twilio
            
            await self.openai_ws.send(json.dumps({
                "type": "conversation.item.truncate",
                "item_id": self.call_state.last_assistant_item,
                "content_index": 0,
                "audio_end_ms": elapsed_time
            }))
            
            await self.websocket.send_json({
                "event": "clear",
                "streamSid": self.call_state.stream_sid
            })
            
            self.call_state.mark_queue.clear()
            self.call_state.last_assistant_item = None
            self.call_state.response_start_timestamp_twilio = None
    
    async def _send_mark(self):
        """Send mark event for interruption tracking."""
        if self.call_state.stream_sid:
            await self.websocket.send_json({
                "event": "mark",
                "streamSid": self.call_state.stream_sid,
                "mark": {"name": "responsePart"}
            })
            self.call_state.mark_queue.append('responsePart')

