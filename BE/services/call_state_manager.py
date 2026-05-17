"""
Call State Manager
Manages all state variables for an active call session.
Replaces the need for 13+ nonlocal variables in the WebSocket handler.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List
from datetime import datetime


@dataclass
class CallState:
    """Manages all state for an active call session."""
    
    # Call identification
    stream_sid: Optional[str] = None
    call_sid: Optional[str] = None
    current_lead_id: Optional[int] = None
    current_twilio_number: Optional[str] = None
    
    # Lead information
    lead_data: Dict = field(default_factory=dict)
    customer_name: Optional[str] = None
    closest_location_info: Optional[Dict] = None
    suggested_store_key: Optional[str] = None
    
    # Transcripts
    customer_transcript: str = ""
    agent_transcript: str = ""
    combined_transcript: str = ""
    
    # Call tracking
    call_start_time: datetime = field(default_factory=datetime.now)
    call_result: str = "not_interested"
    call_saved: bool = False
    
    # Language tracking
    non_english_count: int = 0
    max_non_english_attempts: int = 2
    
    # SMS tracking
    sms_permission_asked: bool = False
    sms_consent_given: bool = False
    pending_sms_type: Optional[str] = None
    directions_sms_sent: bool = False
    photo_sms_sent: bool = False
    pending_sms_requests: List[Dict] = field(default_factory=list)
    sms_processed: bool = False
    
    # OpenAI streaming state
    latest_media_timestamp: int = 0
    last_assistant_item: Optional[str] = None
    mark_queue: List[str] = field(default_factory=list)
    response_start_timestamp_twilio: Optional[int] = None
    
    def get_duration(self) -> int:
        """Get call duration in seconds."""
        return int((datetime.now() - self.call_start_time).total_seconds())
    
    def add_customer_transcript(self, text: str):
        """Add customer transcript line."""
        line = f"Customer: {text}\n"
        self.customer_transcript += line
        self.combined_transcript += line
    
    def add_agent_transcript(self, text: str):
        """Add agent transcript line."""
        line = f"Agent: {text}\n"
        self.agent_transcript += line
        self.combined_transcript += line
    
    def increment_non_english(self):
        """Increment non-English attempt counter."""
        self.non_english_count += 1
    
    def should_end_call_non_english(self) -> bool:
        """Check if call should end due to non-English."""
        return self.non_english_count >= self.max_non_english_attempts
    
    def queue_sms_request(self, sms_type: str, phone_number: str, lead_id: int,
                         twilio_number: str, default_location: str = ""):
        """Queue an SMS request to be sent after call ends.

        ``default_location`` is an optional store-name hint used to pick a
        store when transcript analysis fails. Empty string defers to the
        configured default store.
        """
        self.pending_sms_requests.append({
            'type': sms_type,
            'phone_number': phone_number,
            'lead_id': lead_id,
            'twilio_number': twilio_number,
            'default_location': default_location
        })
    
    def mark_sms_sent(self, sms_type: str):
        """Mark SMS as sent to prevent duplicates."""
        if sms_type == 'directions':
            self.directions_sms_sent = True
        elif sms_type == 'photo_request':
            self.photo_sms_sent = True
    
    def build_combined_transcript_from_parts(self) -> str:
        """Build combined transcript from customer and agent transcripts."""
        customer_lines = [
            line for line in self.customer_transcript.split('\n') 
            if line.strip() and line.strip().startswith('Customer:')
        ]
        agent_lines = [
            line for line in self.agent_transcript.split('\n') 
            if line.strip() and line.strip().startswith('Agent:')
        ]
        
        # Interleave customer and agent lines
        combined_parts = []
        max_len = max(len(customer_lines), len(agent_lines))
        
        for i in range(max_len):
            if i < len(agent_lines):
                combined_parts.append(agent_lines[i])
            if i < len(customer_lines):
                combined_parts.append(customer_lines[i])
        
        return '\n'.join(combined_parts)

