"""
Call Business Logic
Handles business rules and logic during active calls.
Extracted from outbound_main.py for better separation of concerns.
"""

from typing import Tuple, Optional
from utils import (
    validate_language, get_language_switch_message,
    check_dnc_request, should_end_call_now,
    determine_call_result
)
from config import config


class CallBusinessLogic:
    """Handles business logic during calls."""
    
    @staticmethod
    def validate_customer_language(transcript: str, call_state) -> Tuple[bool, Optional[str], bool]:
        """
        Validate customer language and check if call should end.
        
        Returns:
            (is_valid, detected_language, should_end)
        """
        if not config.call.ENFORCE_ENGLISH_ONLY:
            return True, None, False
        
        is_english, detected_lang = validate_language(transcript)
        
        if not is_english:
            call_state.increment_non_english()
            should_end = call_state.should_end_call_non_english()
            return False, detected_lang, should_end
        
        return True, None, False
    
    @staticmethod
    def check_dnc_request(transcript: str, call_state) -> Tuple[bool, Optional[str]]:
        """
        Check if customer requested Do Not Call.
        
        Returns:
            (should_end, reason)
        """
        should_end, reason = should_end_call_now(transcript)
        if should_end:
            call_state.call_result = "dnc"
        return should_end, reason
    
    @staticmethod
    def detect_call_result(customer_tx: str, agent_tx: str) -> Tuple[str, str, float]:
        """
        Determine call result using intelligent detection.
        
        Returns:
            (result_type, reason, confidence)
        """
        return determine_call_result(customer_tx, agent_tx)
    
    @staticmethod
    def detect_sms_triggers(transcript: str, call_state) -> Optional[str]:
        """
        Detect if customer is requesting SMS (directions or photo).
        
        Returns:
            'directions', 'photo_request', or None
        """
        transcript_lower = transcript.lower()
        
        # Explicit request keywords
        explicit_request_keywords = [
            'send me', 'text me', 'can you send', 'can you text', 
            'please send', 'please text', 'go ahead and send', 'go ahead and text',
            'yes send', 'yes text', 'sure send', 'sure text', 'okay send', 'okay text',
            'that would be great', 'that sounds good', 'yes please', 'sure thing'
        ]
        
        explicit_sms_request = any(keyword in transcript_lower for keyword in explicit_request_keywords)
        
        # Directions keywords
        directions_keywords_explicit = [
            'send me directions', 'text me directions', 'send me the address', 
            'text me the address', 'send me location', 'text me location', 
            'send address', 'text address'
        ]
        directions_keywords_implicit = [
            'directions', 'where are you', 'location', 'address', 'how do i get'
        ]
        
        # Photo keywords
        photo_keywords_explicit = [
            'send me picture', 'text me picture', 'send me photo', 'text me photo',
            'send picture', 'text picture', 'send photos', 'text photos'
        ]
        photo_keywords_implicit = [
            'pictures', 'photos', 'show', 'appraisal', 'evaluate', 'worth'
        ]
        
        # Check for directions
        if explicit_sms_request and any(kw in transcript_lower for kw in ['direction', 'address', 'location', 'where']):
            return 'directions'
        if any(kw in transcript_lower for kw in directions_keywords_explicit):
            return 'directions'
        if any(kw in transcript_lower for kw in directions_keywords_implicit) and explicit_sms_request:
            return 'directions'
        
        # Check for photo request
        if explicit_sms_request and any(kw in transcript_lower for kw in ['picture', 'photo', 'appraisal', 'item']):
            return 'photo_request'
        if any(kw in transcript_lower for kw in photo_keywords_explicit):
            return 'photo_request'
        if any(kw in transcript_lower for kw in photo_keywords_implicit) and ('text me' in transcript_lower or 'send me' in transcript_lower):
            return 'photo_request'
        
        return None
    
    @staticmethod
    def check_sms_permission_request(agent_text: str) -> Tuple[bool, Optional[str]]:
        """
        Check if agent asked for SMS permission.
        
        Returns:
            (permission_asked, sms_type)
        """
        agent_text_lower = agent_text.lower().replace('’', "'").replace('"', '"').replace('"', '"')
        
        sms_permission_phrases = [
            'can i send', 'can i text', 'can i send you', 'can i text you',
            'would you like me to send', 'would you like me to text',
            'may i send', 'may i text', 'should i send', 'should i text',
            'i can send you', 'i can text you', "i'll send you", "i'll text you"
        ]
        
        if any(phrase in agent_text_lower for phrase in sms_permission_phrases):
            if any(word in agent_text_lower for word in ['direction', 'location', 'address', 'addresses']):
                return True, 'directions'
            elif any(word in agent_text_lower for word in ['picture', 'photo', 'appraisal', 'item']):
                return True, 'photo_request'
        
        return False, None
    
    @staticmethod
    def check_consent_response(transcript: str, permission_asked: bool) -> Tuple[bool, bool]:
        """
        Check if customer gave consent for SMS.
        
        Returns:
            (gave_consent, explicit_request)
        """
        transcript_lower = transcript.lower()
        
        explicit_request_keywords = [
            'send me', 'text me', 'can you send', 'can you text', 
            'please send', 'please text', 'go ahead and send', 'go ahead and text',
            'yes send', 'yes text', 'sure send', 'sure text', 'okay send', 'okay text',
            'that would be great', 'that sounds good', 'yes please', 'sure thing'
        ]
        
        consent_keywords = [
            'yes', 'yeah', 'yep', 'sure', 'okay', 'ok', 'alright', 'sounds good',
            'that would be great', 'that sounds good', 'go ahead', 'please do',
            'send it', 'text it', 'yes please', 'sure thing', 'absolutely', 'definitely',
            'no problem', 'that works', 'perfect', 'great', 'fine', 'sounds good to me'
        ]
        
        explicit_request = any(kw in transcript_lower for kw in explicit_request_keywords)
        explicit_consent = any(kw in transcript_lower for kw in consent_keywords) and permission_asked
        
        return explicit_consent or explicit_request, explicit_request

