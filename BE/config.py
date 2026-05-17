"""
Configuration Management System
Centralized configuration for the outbound calling system.
All settings are loaded from environment variables with sensible defaults.
"""

import os
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class CallConfig:
    """Call behavior configuration"""
    # Maximum call duration in seconds (default: 5 minutes)
    MAX_CALL_DURATION: int = int(os.getenv('MAX_CALL_DURATION', '300'))
    
    # Enable call recording (saves audio to Twilio)
    ENABLE_CALL_RECORDING: bool = os.getenv('ENABLE_CALL_RECORDING', 'true').lower() == 'true'
    
    # Recording status callback URL (optional)
    RECORDING_STATUS_CALLBACK: Optional[str] = os.getenv('RECORDING_STATUS_CALLBACK')
    
    # Enforce English-only conversations
    ENFORCE_ENGLISH_ONLY: bool = os.getenv('ENFORCE_ENGLISH_ONLY', 'true').lower() == 'true'
    
    # Maximum response length in words
    MAX_RESPONSE_WORDS: int = int(os.getenv('MAX_RESPONSE_WORDS', '30'))
    
    # Voice selection (echo, nova, sage, onyx, etc.)
    VOICE: str = os.getenv('VOICE_SELECTION', 'sage')


@dataclass
class OpenAIConfig:
    """OpenAI API configuration"""
    API_KEY: str = os.getenv('OPENAI_API_KEY', '')
    REALTIME_MODEL: str = os.getenv('REALTIME_MODEL', 'gpt-4o-realtime-preview-2024-12-17')
    TEMPERATURE: float = float(os.getenv('TEMPERATURE', '0.8'))
    
    # Voice Activity Detection settings
    VAD_THRESHOLD: float = float(os.getenv('VAD_THRESHOLD', '0.5'))
    VAD_PREFIX_PADDING_MS: int = int(os.getenv('VAD_PREFIX_PADDING_MS', '300'))
    VAD_SILENCE_DURATION_MS: int = int(os.getenv('VAD_SILENCE_DURATION_MS', '500'))


@dataclass
class TwilioConfig:
    """Twilio API configuration"""
    ACCOUNT_SID: str = os.getenv('TWILIO_ACCOUNT_SID', '')
    AUTH_TOKEN: str = os.getenv('TWILIO_AUTH_TOKEN', '')
    CALL_TIMEOUT: int = int(os.getenv('TWILIO_CALL_TIMEOUT', '30'))
    PHONE_NUMBER: str = os.getenv('TWILIO_PHONE_NUMBER', '')  # For SMS sending


@dataclass
class DatabaseConfig:
    """Database configuration"""
    BACKEND: str = os.getenv('DATABASE_BACKEND', 'sqlserver').lower()
    URL: str = os.getenv('DATABASE_URL', 'postgresql://outvox:outvox@localhost:5432/outvox')
    SERVICE_URL: str = os.getenv('DB_SERVICE_URL', 'http://localhost:8000')
    # Supported SQL Server runtime path. Postgres support is still experimental.
    SQL_SERVER: str = os.getenv('SQLServer', '')
    SQL_USER: str = os.getenv('SQLUser', '')
    SQL_PASSWORD: str = os.getenv('SQLPassword', '')
    SQL_DATABASE: str = os.getenv('SQLDatabase', '')


@dataclass
class AgentConfig:
    """Agent-specific configuration"""
    AGENT_ID: str = os.getenv('AGENT_ID', '1')
    PORT: int = int(os.getenv('PORT', '5001'))
    NGROK_HOST: str = os.getenv('NGROK_HOST', 'your-subdomain.ngrok.app')
    
    def get_formatted_agent_id(self) -> str:
        """
        Get agent ID in standard format: Agent1, Agent2, etc. (NO SPACE)
        Converts OUT1/OUT2 format or numeric format to AgentN format.
        
        Examples:
            OUT1 -> Agent1
            OUT10 -> Agent10
            1 -> Agent1
            agent5 -> Agent5
        
        Note: This standardized format is used consistently across:
            - Backend logging and webhooks
            - Database records (agent_id field)
            - Frontend agent displays
        """
        agent_id = self.AGENT_ID.upper().strip()
        
        # If already in Agent format (Agent1, Agent2, etc.), return as is
        if agent_id.startswith('AGENT'):
            # Extract number if present (e.g., "Agent1" -> "1")
            number = agent_id.replace('AGENT', '').strip()
            if number.isdigit():
                return f"Agent{number}"
        
        # If in OUT format (OUT1, OUT2, etc.), convert to Agent format
        if agent_id.startswith('OUT'):
            number = agent_id.replace('OUT', '').strip()
            if number.isdigit():
                return f"Agent{number}"
        
        # If just a number, convert to Agent format
        if agent_id.isdigit():
            return f"Agent{agent_id}"
        
        # If it's "agent1", "agent2" (lowercase), capitalize
        if agent_id.lower().startswith('agent'):
            number = agent_id.lower().replace('agent', '').strip()
            if number.isdigit():
                return f"Agent{number}"
        
        # Default: assume it's a number and prefix with "Agent"
        return f"Agent{agent_id}"


@dataclass
class DNCConfig:
    """Do Not Call detection configuration"""
    # Phrases that trigger DNC
    DNC_PHRASES: list = None
    
    # Sentiment threshold for negative responses (-1 to 1, lower = more negative)
    SENTIMENT_THRESHOLD: float = float(os.getenv('SENTIMENT_THRESHOLD', '-0.3'))
    
    def __post_init__(self):
        """Initialize DNC phrases list"""
        if self.DNC_PHRASES is None:
            self.DNC_PHRASES = [
                'stop calling',
                'please stop calling',
                'stop contacting',
                'stop texting',
                'stop messaging',
                'remove me',
                'take me off',
                "don't call",
                'do not call',
                'leave me alone',
                'remove my number',
                'unsubscribe',
                'never call',
                'don\'t ever call',
                'take me off your list',
                'remove from list',
                'stop calling me',
                'stop contacting me',
                'do not call me',
                'don\'t call me again',
                'never contact me'
            ]


@dataclass
class CampaignConfig:
    """SMS Campaign configuration"""
    # SMS consent cooldown period in days
    # After this period, leads become eligible again regardless of verified status
    SMS_CONSENT_COOLDOWN_DAYS: int = int(os.getenv('SMS_CONSENT_COOLDOWN_DAYS', '7'))
    
    # Interval between SMS sends in seconds (default: 300 = 5 minutes)
    # This helps avoid carrier spam detection and ensures compliance
    SMS_SEND_INTERVAL_SECONDS: int = int(os.getenv('SMS_SEND_INTERVAL_SECONDS', '300'))


@dataclass
class BrandConfig:
    """
    Tenant/brand configuration.

    Every customer-facing string the AI agent speaks or writes — the company
    name, the agent's persona name, the products on offer, the tagline used in
    SMS — flows from these values. The shipped defaults are deliberately
    generic placeholders ("Acme Pawn", "Alex"). Set these in your .env to make
    the agent speak as your business.

    See docs/customization.md for a list of every prompt and template that
    consumes these values.
    """
    COMPANY_NAME: str = os.getenv('COMPANY_NAME', 'Acme Pawn')
    COMPANY_SHORT_NAME: str = os.getenv('COMPANY_SHORT_NAME', 'Acme')
    AGENT_NAME: str = os.getenv('AGENT_NAME', 'Alex')
    COMPANY_TAGLINE: str = os.getenv(
        'COMPANY_TAGLINE',
        'Trusted local pawn loans and appraisals.'
    )
    # Free-form description of what the business offers — interpolated into the
    # base prompt. Keep it short; the model uses this to pitch the visit.
    COMPANY_OFFERING: str = os.getenv(
        'COMPANY_OFFERING',
        'pawn loans and quick cash for gold, jewelry, watches, and electronics'
    )


@dataclass
class SecurityConfig:
    """
    Authentication / API key configuration.

    When API_KEY is non-empty, the FastAPI services require requests to
    mutating routes to include the matching key in the ``X-API-Key`` header
    (or as a Bearer token). When unset, the middleware logs a warning and
    allows all requests — DO NOT run this way in production. See SECURITY.md.
    """
    API_KEY: str = os.getenv('API_KEY', '')
    # Comma-separated list of path prefixes that bypass auth even when API_KEY
    # is set (e.g., Twilio webhooks that arrive with their own signature, never
    # with our shared secret). The defaults below cover:
    #   - health probes (/health, /nginx-health)
    #   - Twilio voice and SMS webhooks on the voice agent (/twilio-voice,
    #     /twilio-sms) — these endpoints validate Twilio's X-Twilio-Signature
    #     before doing anything else.
    #   - Twilio SMS webhooks on db_service (/api/sms/twilio-sms and the
    #     /sms/twilio-sms legacy redirect) for operators who configure Twilio
    #     to call db_service directly.
    #   - the media-stream WebSocket, which is HMAC-protected instead.
    #   - the OpenAPI documentation routes.
    AUTH_EXEMPT_PREFIXES: str = os.getenv(
        'AUTH_EXEMPT_PREFIXES',
        (
            '/health,/nginx-health,'
            '/twilio-voice,/twilio-sms,'
            '/sms/twilio-sms,/api/sms/twilio-sms,'
            '/media-stream,'
            '/docs,/redoc,/openapi.json'
        )
    )


@dataclass
class TrestleConfig:
    """Trestle API configuration for phone validation"""
    API_KEY: str = os.getenv('TRESTLE_API_KEY', '')
    API_URL: str = os.getenv('TRESTLE_API_URL', 'https://api.trestleiq.com/3.1/caller_id')
    
    # Enable/disable phone validation on lead creation
    VALIDATE_ON_LEAD_CREATE: bool = os.getenv('TRESTLE_VALIDATE_ON_CREATE', 'true').lower() == 'true'
    
    # Enable/disable phone validation before SMS
    VALIDATE_BEFORE_SMS: bool = os.getenv('TRESTLE_VALIDATE_BEFORE_SMS', 'true').lower() == 'true'
    
    # Block invalid numbers (if False, just warn but allow)
    BLOCK_INVALID_NUMBERS: bool = os.getenv('TRESTLE_BLOCK_INVALID', 'true').lower() == 'true'
    
    # Block landline numbers for SMS (can't receive SMS)
    BLOCK_LANDLINE_FOR_SMS: bool = os.getenv('TRESTLE_BLOCK_LANDLINE_SMS', 'true').lower() == 'true'
    
    # Cache duration in hours
    CACHE_DURATION_HOURS: int = int(os.getenv('TRESTLE_CACHE_HOURS', '24'))


class Config:
    """
    Main configuration class
    Access all configuration through this class
    """
    def __init__(self):
        self.call = CallConfig()
        self.openai = OpenAIConfig()
        self.twilio = TwilioConfig()
        self.database = DatabaseConfig()
        self.agent = AgentConfig()
        self.brand = BrandConfig()
        self.security = SecurityConfig()
        self.dnc = DNCConfig()
        self.campaign = CampaignConfig()
        self.trestle = TrestleConfig()
        
        # Validate critical settings
        self._validate()
    
    def _validate(self):
        """Validate that critical configuration is present"""
        # Skip validation if running setup scripts or workers
        # These scripts only need database credentials
        import sys
        script_name = sys.argv[0] if sys.argv else ""
        
        # Skip validation for setup scripts and workers
        if any(x in script_name.lower() for x in ['setup_', 'worker', 'migration', 'verify_', 'assign_', 'execute_']):
            return
        
        errors = []
        
        if not self.openai.API_KEY:
            errors.append("OPENAI_API_KEY is required")
        
        if not self.twilio.ACCOUNT_SID:
            errors.append("TWILIO_ACCOUNT_SID is required")
        
        if not self.twilio.AUTH_TOKEN:
            errors.append("TWILIO_AUTH_TOKEN is required")
        
        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")
    
    def get_agent_url(self, agent_id: str = None) -> str:
        """Get agent-specific URL for webhooks"""
        aid = agent_id or self.agent.AGENT_ID
        return f"https://{self.agent.NGROK_HOST}/agent/{aid}"
    
    def get_formatted_agent_id(self) -> str:
        """Get formatted agent ID (Agent1, Agent2, etc.)"""
        return self.agent.get_formatted_agent_id()
    
    def __str__(self):
        """String representation for debugging (hides sensitive data)"""
        return f"""
Config:
  Agent: {self.agent.get_formatted_agent_id()} on port {self.agent.PORT}
  Max Call Duration: {self.call.MAX_CALL_DURATION}s
  Recording Enabled: {self.call.ENABLE_CALL_RECORDING}
  English Only: {self.call.ENFORCE_ENGLISH_ONLY}
  Voice: {self.call.VOICE}
"""


# Global configuration instance
config = Config()


# Convenience function for backward compatibility
def get_config() -> Config:
    """Get the global configuration instance"""
    return config
