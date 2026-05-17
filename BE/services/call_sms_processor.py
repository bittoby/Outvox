"""
Call SMS Processor
Handles SMS processing after call ends.
Extracted from outbound_main.py for better separation of concerns.
"""

import logging
from typing import Optional, List, Dict
from utils.location_mapper import detect_location_from_transcript, default_store_key

logger = logging.getLogger(__name__)


class CallSMSProcessor:
    """Processes pending SMS requests after call ends."""
    
    def __init__(self, agent_id: str, send_directions_sms, send_photo_request_sms):
        self.agent_id = agent_id
        self.send_directions_sms = send_directions_sms
        self.send_photo_request_sms = send_photo_request_sms
    
    async def process_pending_sms(
        self,
        call_state,
        get_lead_by_id,
        full_transcript: str
    ):
        """
        Process all pending SMS requests after reviewing full conversation.
        
        Args:
            call_state: CallState object with all call state
            get_lead_by_id: Function to fetch lead by ID
            full_transcript: Full conversation transcript for location detection
        """
        logger.info(
            f"[{self.agent_id}] 📱 SMS_PROCESSING_START | Pending: {len(call_state.pending_sms_requests)} | "
            f"LeadID: {call_state.current_lead_id} | AlreadyProcessed: {call_state.sms_processed}"
        )
        
        if not call_state.pending_sms_requests:
            logger.info(f"[{self.agent_id}] SMS_PROCESSING_SKIP | No pending SMS requests")
            return
        
        if not call_state.current_lead_id:
            logger.warning(f"[{self.agent_id}] SMS_PROCESSING_SKIP | No lead ID available")
            return
        
        if call_state.sms_processed:
            logger.info(f"[{self.agent_id}] SMS_PROCESSING_SKIP | Already processed")
            return
        
        call_state.sms_processed = True
        logger.info(f"[{self.agent_id}] SMS_PROCESSING | Processing {len(call_state.pending_sms_requests)} SMS request(s)")
        
        # Get phone number
        phone_number = call_state.lead_data.get('phone_number')
        if not phone_number and call_state.current_lead_id:
            try:
                lead = await get_lead_by_id(call_state.current_lead_id)
                if lead:
                    phone_number = lead.get('phone_number')
                else:
                    logger.warning(
                        f"[{self.agent_id}] SMS_LEAD_NOT_FOUND | LeadID: {call_state.current_lead_id}"
                    )
            except Exception as e:
                logger.error(
                    f"[{self.agent_id}] SMS_FETCH_LEAD_ERROR | LeadID: {call_state.current_lead_id} | "
                    f"Error: {e}",
                    exc_info=True
                )
                return
        
        if not phone_number:
            logger.error(
                f"[{self.agent_id}] SMS_NO_PHONE | LeadID: {call_state.current_lead_id} | "
                f"Cannot process SMS - phone number not available"
            )
            return
        
        # Detect location from full conversation transcript (analyze entire conversation for accuracy)
        # This is the PRIMARY source of truth - analyze the ENTIRE conversation
        detected_location_key = None
        if full_transcript:
            detected_location_key = detect_location_from_transcript(full_transcript)
            if detected_location_key:
                logger.info(
                    f"[{self.agent_id}] 📍 LOCATION_DETECTED_FROM_TRANSCRIPT | Store: {detected_location_key} | "
                    f"TranscriptLength: {len(full_transcript)} chars"
                )
        
        # Process each SMS request
        # Priority: 1) Location from full transcript, 2) Agent-suggested store, 3) Default from area code
        for sms_request in call_state.pending_sms_requests:
            try:
                sms_type = sms_request.get('type')
                
                # Determine the best store location using priority:
                # 1. Detected from full transcript (most accurate - analyzes entire conversation)
                # 2. Agent-suggested store (from agent mentioning store name)
                # 3. Default location from SMS request (from area code)
                best_store_key = detected_location_key
                if not best_store_key and call_state.suggested_store_key:
                    best_store_key = call_state.suggested_store_key.lower()
                
                # Default location can be supplied per-request; otherwise fall back
                # to the first configured store key.
                default_location = sms_request.get('default_location')
                if default_location:
                    default_location = default_location.lower()
                else:
                    default_location = default_store_key()
                
                # Final store key: use best detected, otherwise fall back to default
                final_store_key = best_store_key or default_location
                
                # Log location selection reasoning
                location_source = "transcript_detection" if detected_location_key else \
                                 ("agent_suggestion" if call_state.suggested_store_key else "default_area_code")
                
                if sms_type == 'directions':
                    logger.info(
                        f"[{self.agent_id}] 📤 SMS_SENDING | Type: directions | "
                        f"Phone: {phone_number} | Store: {final_store_key} | "
                        f"Source: {location_source} | LeadID: {call_state.current_lead_id} | "
                        f"Detected: {detected_location_key or 'none'} | "
                        f"Suggested: {call_state.suggested_store_key or 'none'} | "
                        f"Default: {default_location}"
                    )
                    
                    # IMPORTANT: Pass final_store_key as override_store_key to ensure correct location is used
                    # Also pass full_transcript so send_directions_sms can do additional validation
                    success = await self.send_directions_sms(
                        phone_number,
                        default_location,  # This is the fallback if override_store_key fails validation
                        call_state.current_lead_id,
                        call_state.current_twilio_number,
                        full_transcript,  # Full transcript for additional location detection validation
                        override_store_key=final_store_key  # The BEST detected location
                    )
                    
                    if success:
                        logger.info(
                            f"[{self.agent_id}] ✅ SMS_SENT_SUCCESS | Type: directions | "
                            f"Phone: {phone_number} | LeadID: {call_state.current_lead_id}"
                        )
                    else:
                        logger.error(
                            f"[{self.agent_id}] ❌ SMS_SENT_FAILED | Type: directions | "
                            f"Phone: {phone_number} | LeadID: {call_state.current_lead_id}"
                        )
                
                elif sms_type == 'photo_request':
                    logger.info(
                        f"[{self.agent_id}] SMS_SENDING | Type: photo_request | "
                        f"Phone: {phone_number} | LeadID: {call_state.current_lead_id}"
                    )
                    success = await self.send_photo_request_sms(
                        phone_number,
                        call_state.current_lead_id,
                        call_state.current_twilio_number,
                        location_to_use,
                        full_transcript
                    )
                    
                    if success:
                        logger.info(
                            f"[{self.agent_id}] ✅ SMS_SENT_SUCCESS | Type: photo_request | "
                            f"Phone: {phone_number} | LeadID: {call_state.current_lead_id}"
                        )
                    else:
                        logger.error(
                            f"[{self.agent_id}] ❌ SMS_SENT_FAILED | Type: photo_request | "
                            f"Phone: {phone_number} | LeadID: {call_state.current_lead_id}"
                        )
                
                else:
                    logger.warning(
                        f"[{self.agent_id}] SMS_UNKNOWN_TYPE | Type: {sms_type}"
                    )
                    
            except Exception as sms_error:
                logger.error(
                    f"[{self.agent_id}] SMS_PROCESSING_ERROR | Type: {sms_type} | "
                    f"Error: {sms_error}",
                    exc_info=True
                )
                # Continue processing other SMS requests even if one fails
        
        logger.info(
            f"[{self.agent_id}] ✅ SMS_PROCESSING_COMPLETE | Processed {len(call_state.pending_sms_requests)} request(s)"
        )

