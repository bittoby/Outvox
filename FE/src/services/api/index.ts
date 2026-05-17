/**
 * Central API Service - Re-exports all API functions
 * 
 * API Services are organized by feature/page:
 * - dashboard.ts: Dashboard stats and metrics
 * - agents.ts: Agent health and status
 * - leads.ts: Lead management (CRUD)
 * - calls.ts: Call operations
 * 
 * Usage:
 *   import { getCallStats, getAllAgentHealth } from '@/services/api';
 *   OR
 *   import { getCallStats } from '@/services/api/dashboard';
 */

// Re-export Dashboard APIs
export { getCallStats, getStoreLocations, getLeadPriorityStats } from './dashboard';

// Re-export Agent APIs
export { getAllAgentHealth } from './agents';

// Re-export Lead APIs
export {
  getLeads,
  addLead,
  updateLead,
  deleteLead,
  markLeadDNC,
  bulkImportLeads,
  importLeadsFromCSV,
  exportLeadsToCSV,
  deleteAllLeads,
} from './leads';

// Re-export Call APIs
export { startSingleCall, getCallHistory, getCallDetails, deleteCallHistory, startCallCampaign } from './calls';

// Re-export Store APIs (Milestone 2 & 11)
export { 
  getStores, 
  getStore,
  createStore,
  updateStore,
  deleteStore,
  bulkAssignLeadsToStore,
  getSafeCallEligibleLeads,
  autoAssignLeads
} from './stores';

// Re-export SMS APIs
export { 
  getAllSMSConversations, 
  getSMSConversations,
  getSMSConversationDetails,
  deleteSMSConversation,
  deletePhotoSubmission,
  getAllPhotoSubmissions, 
  updatePhotoStatus,
  clearSMSHistory,
  clearConversations,
  clearPhotoSubmissions,
  type SMSConversation,
  type PhotoSubmission,
  type SMSResponse,
  type PhotosResponse,
  type SMSConversationDetails
} from './sms';

// Re-export Settings APIs
export { 
  getAIProvider, 
  saveAIProvider, 
  isElevenLabsEnabled, 
  isOpenAIEnabled,
  getAIProviderSettings,
  saveAIProviderSettings,
  getActiveProvider,
  fetchElevenLabsVoices,
  fetchOpenAIVoices,
  type OpenAISettings,
  type ElevenLabsSettings,
  type AIProviderSettingsResponse,
  type SaveSettingsRequest,
} from './settings';

// Re-export Popup APIs
export {
  getPendingPopups,
  dismissPopup,
  prepareManualDial,
  dialLead,
  type PopupQueueItem,
  type PendingPopupsResponse,
  type ManualDialRequest
} from './popup';

// Re-export Campaign APIs (Milestone 13, 14, 15 & 16)
export {
  getCampaigns,
  getCampaignDetails,
  getCampaignBatches,
  getBatchLeads,
  getStorePhoneNumbers,
  getStoreDailyStats,
  previewCampaign,
  startCampaign,
  pauseCampaign,
  resumeCampaign,
  deleteCampaign,
  getDailyReport,
  getSmsTimeline,
} from './campaigns';

// Re-export Phone Numbers APIs
export {
  getAllPhoneNumbers,
  assignPhoneToStore,
  unassignPhoneFromStore,
  deletePhoneNumber,
  deletePhoneNumbers,
} from './phoneNumbers';