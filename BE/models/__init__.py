"""
Data Models Package
Pydantic models for request/response validation.
"""

# Lead models
from .lead import (
    LeadBase,
    LeadCreate,
    LeadUpdate,
    LeadResponse,
    BulkAssignRequest,
    CSVImportRequest,
    CSVExportRequest,
    DNCARequest,
    BulkLeadRequest,
)

# Campaign models
from .campaign import (
    CampaignBase,
    CampaignCreate,
    CampaignPreviewRequest,
    CampaignPreviewResponse,
    CampaignResponse,
    BatchResponse,
    DailyStatsResponse,
    CampaignRequest,
)

# Call models
from .call import (
    CallResultBase,
    CallResultCreate,
    CallResultResponse,
    CallHistoryResponse,
    StartCallRequest,
    StartCampaignRequest,
)

# Store models
from .store import (
    StoreBase,
    StoreCreate,
    StoreUpdate,
    StoreResponse,
    PhoneNumberBase,
    PhoneNumberCreate,
    PhoneNumberUpdate,
    PhoneNumberResponse,
)

# SMS models
from .sms import (
    SMSMessageBase,
    SMSMessageCreate,
    SMSMessageResponse,
    SMSConversationResponse,
    SMSConversationDetailResponse,
    ConsentSMSRequest,
    ConsentBatchRequest,
    ConsentSMSBatchRequest,
    SMSVerificationRequest,
    PhotoSubmissionBase,
    PhotoSubmissionCreate,
    PhotoSubmissionResponse,
    PhotoStatusUpdate,
)

# Popup models
from .popup import (
    PopupQueueItem,
    ManualDialRequest,
    UpdateCallSIDRequest,
)

# Phone validation models
from .phone_validation import (
    LineType,
    PhoneValidationStatus,
    PhoneValidationResult,
    PhoneValidationRequest,
    PhoneValidationResponse,
    BulkPhoneValidationRequest,
    BulkPhoneValidationResponse,
)

# Settings models
from .settings import (
    OpenAISettings,
    ElevenLabsSettings,
    AIProviderSettings,
    AIProviderSettingsResponse,
    SaveSettingsRequest,
)

__all__ = [
    # Lead models
    "LeadBase",
    "LeadCreate",
    "LeadUpdate",
    "LeadResponse",
    "BulkAssignRequest",
    "CSVImportRequest",
    "CSVExportRequest",
    "DNCARequest",
    "BulkLeadRequest",
    # Campaign models
    "CampaignBase",
    "CampaignCreate",
    "CampaignPreviewRequest",
    "CampaignPreviewResponse",
    "CampaignResponse",
    "BatchResponse",
    "DailyStatsResponse",
    "CampaignRequest",
    # Call models
    "CallResultBase",
    "CallResultCreate",
    "CallResultResponse",
    "CallHistoryResponse",
    "StartCallRequest",
    "StartCampaignRequest",
    # Store models
    "StoreBase",
    "StoreCreate",
    "StoreUpdate",
    "StoreResponse",
    "PhoneNumberBase",
    "PhoneNumberCreate",
    "PhoneNumberUpdate",
    "PhoneNumberResponse",
    # SMS models
    "SMSMessageBase",
    "SMSMessageCreate",
    "SMSMessageResponse",
    "SMSConversationResponse",
    "SMSConversationDetailResponse",
    "ConsentSMSRequest",
    "ConsentBatchRequest",
    "ConsentSMSBatchRequest",
    "SMSVerificationRequest",
    "PhotoSubmissionBase",
    "PhotoSubmissionCreate",
    "PhotoSubmissionResponse",
    "PhotoStatusUpdate",
    # Popup models
    "PopupQueueItem",
    "ManualDialRequest",
    "UpdateCallSIDRequest",
    # Phone validation models
    "LineType",
    "PhoneValidationStatus",
    "PhoneValidationResult",
    "PhoneValidationRequest",
    "PhoneValidationResponse",
    "BulkPhoneValidationRequest",
    "BulkPhoneValidationResponse",
    # Settings models
    "OpenAISettings",
    "ElevenLabsSettings",
    "AIProviderSettings",
    "AIProviderSettingsResponse",
    "SaveSettingsRequest",
]
