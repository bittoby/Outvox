"""
Services Module
Business logic layer for campaign management, consent tracking, and lead management.
"""

# NOTE: Services that require database access (pyodbc) are NOT imported here
# to avoid dependency issues in Docker agents.
# 
# Agents don't need database access - they use API.
# Routers and db_service should import services directly from their modules:
#   - from services.lead_service import LeadService, get_lead_service
#   - from services.campaign_service import CampaignService, get_campaign_service
#   - from services.sms_campaign_manager import SMSCampaignManager
#   - from services.consent_tracker import ConsentTracker
#   - etc.

# Only import services that don't require database access
from .twilio_service import TwilioService
from .websocket_service import get_websocket_manager, broadcast_event, broadcast_event_sync, EventType

__all__ = [
    # Services requiring database access are not imported - import directly from modules
    'TwilioService',
    'get_websocket_manager',
    'broadcast_event',
    'broadcast_event_sync',
    'EventType',
]

