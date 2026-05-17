"""
Repository Layer
Handles all database access operations using the Repository Pattern.
"""

from .base import BaseRepository
from .lead_repository import LeadRepository
from .campaign_repository import CampaignRepository
from .store_repository import StoreRepository
from .phone_number_repository import PhoneNumberRepository
from .sms_repository import SMSRepository
from .popup_repository import PopupRepository
from .call_repository import CallRepository
from .template_repository import TemplateRepository
from .phone_status_repository import PhoneStatusRepository

__all__ = [
    "BaseRepository",
    "LeadRepository",
    "CampaignRepository",
    "StoreRepository",
    "PhoneNumberRepository",
    "SMSRepository",
    "PopupRepository",
    "CallRepository",
    "TemplateRepository",
    "PhoneStatusRepository",
]
