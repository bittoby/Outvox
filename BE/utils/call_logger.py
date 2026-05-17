"""
Call Logger
Structured logging for call events, transcripts, and status updates.
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any
from services.call_state_manager import CallState


class CallLogger:
    """Structured logger for call events."""
    
    def __init__(self, agent_id: str, call_state: CallState):
        """
        Initialize call logger.
        
        Args:
            agent_id: Agent identifier
            call_state: Call state manager instance
        """
        self.agent_id = agent_id
        self.call_state = call_state
        self.logger = logging.getLogger(f"call.{agent_id}")
        
        # Track call session
        self.call_start_time = datetime.now()
        self.last_log_time = self.call_start_time
    
    def _format_message(self, event_type: str, message: str, **kwargs) -> str:
        """Format log message with call context."""
        duration = (datetime.now() - self.call_start_time).total_seconds()
        call_sid = self.call_state.call_sid or "unknown"
        lead_id = self.call_state.current_lead_id or "unknown"
        
        context = f"[CALL:{call_sid}|LEAD:{lead_id}|DUR:{duration:.1f}s]"
        
        # Add extra context if provided
        extra = ""
        if kwargs:
            extra_parts = [f"{k}={v}" for k, v in kwargs.items()]
            extra = f" | {' | '.join(extra_parts)}"
        
        return f"{context} [{event_type}] {message}{extra}"
    
    def log_call_start(self, lead_data: Optional[Dict] = None):
        """Log call start event."""
        lead_info = ""
        if lead_data:
            name = lead_data.get('name', 'Unknown')
            phone = lead_data.get('phone_number', 'Unknown')
            lead_info = f" | Name={name} | Phone={phone}"
        
        self.logger.info(
            self._format_message(
                "CALL_START",
                f"Call initiated{lead_info}",
                twilio_number=self.call_state.current_twilio_number or "unknown",
                stream_sid=self.call_state.stream_sid or "unknown"
            )
        )
    
    def log_call_end(self, reason: str = "completed"):
        """Log call end event."""
        duration = self.call_state.get_duration()
        self.logger.info(
            self._format_message(
                "CALL_END",
                f"Call ended: {reason}",
                duration_seconds=duration,
                result_type=self.call_state.call_result,
                saved=self.call_state.call_saved
            )
        )
    
    def log_customer_speech(self, transcript: str):
        """Log customer speech/transcript."""
        self.logger.info(
            self._format_message(
                "CUSTOMER",
                transcript[:200],  # Limit length for readability
                transcript_length=len(transcript)
            )
        )
    
    def log_agent_speech(self, transcript: str):
        """Log agent speech/transcript."""
        self.logger.info(
            self._format_message(
                "AGENT",
                transcript[:200],  # Limit length for readability
                transcript_length=len(transcript)
            )
        )
    
    def log_call_status(self, status: str, details: Optional[str] = None):
        """Log call status change."""
        msg = f"Status: {status}"
        if details:
            msg += f" - {details}"
        
        self.logger.info(
            self._format_message("STATUS", msg)
        )
    
    def log_state_change(self, field: str, old_value: Any, new_value: Any):
        """Log call state change."""
        self.logger.debug(
            self._format_message(
                "STATE_CHANGE",
                f"{field}: {old_value} → {new_value}"
            )
        )
    
    def log_error(self, error_type: str, message: str, exception: Optional[Exception] = None):
        """Log error with context."""
        error_msg = f"{error_type}: {message}"
        if exception:
            error_msg += f" | Exception: {type(exception).__name__}: {str(exception)}"
        
        self.logger.error(
            self._format_message("ERROR", error_msg)
        )
    
    def log_warning(self, warning_type: str, message: str):
        """Log warning with context."""
        self.logger.warning(
            self._format_message("WARNING", f"{warning_type}: {message}")
        )
    
    def log_business_event(self, event: str, details: Optional[Dict] = None):
        """Log business logic events (DNC, SMS, etc.)."""
        detail_str = ""
        if details:
            detail_parts = [f"{k}={v}" for k, v in details.items()]
            detail_str = f" | {' | '.join(detail_parts)}"
        
        self.logger.info(
            self._format_message("BUSINESS", f"{event}{detail_str}")
        )
    
    def log_transcript_summary(self):
        """Log transcript summary at call end."""
        customer_len = len(self.call_state.customer_transcript)
        agent_len = len(self.call_state.agent_transcript)
        combined_len = len(self.call_state.combined_transcript)
        
        self.logger.info(
            self._format_message(
                "TRANSCRIPT_SUMMARY",
                f"Customer: {customer_len} chars | Agent: {agent_len} chars | Combined: {combined_len} chars",
                customer_lines=len(self.call_state.customer_transcript.split('\n')),
                agent_lines=len(self.call_state.agent_transcript.split('\n'))
            )
        )
    
    def log_sms_event(self, event_type: str, sms_type: Optional[str] = None, details: Optional[str] = None):
        """Log SMS-related events."""
        msg = event_type
        if sms_type:
            msg += f" | Type: {sms_type}"
        if details:
            msg += f" | {details}"
        
        self.logger.info(
            self._format_message("SMS", msg)
        )
    
    def log_duration_check(self):
        """Log periodic duration check."""
        duration = self.call_state.get_duration()
        if duration % 30 == 0 or duration > 0:  # Log every 30 seconds or at start
            self.logger.debug(
                self._format_message(
                    "DURATION",
                    f"Call duration: {duration}s",
                    customer_chars=len(self.call_state.customer_transcript),
                    agent_chars=len(self.call_state.agent_transcript)
                )
            )



