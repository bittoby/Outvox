// Campaign API Services - Milestone 13 & 14
import axios from 'axios';
import { API_CONFIG } from '../config';
import type {
  Campaign,
  CampaignDetails,
  CampaignBatch,
  StorePhoneNumbers,
  StoreDailyStats,
  CampaignPreviewRequest,
  CampaignPreviewResponse,
  StartCampaignRequest,
  StartCampaignResponse,
} from '../../types/campaign';

/**
 * Get all campaigns with optional filters
 */
export async function getCampaigns(
  storeId?: number,
  status?: string
): Promise<Campaign[]> {
  try {
    const params: any = {};
    if (storeId !== undefined) params.store_id = storeId;
    if (status) params.status = status;

    const response = await axios.get(`${API_CONFIG.DB_SERVICE}/api/campaigns`, {
      params,
    });
    return Array.isArray(response.data.campaigns) ? response.data.campaigns : [];
  } catch (error) {
    console.error('Error fetching campaigns:', error);
    return [];
  }
}

/**
 * Get detailed information about a specific campaign
 */
export async function getCampaignDetails(
  campaignId: number
): Promise<CampaignDetails | null> {
  try {
    const response = await axios.get(
      `${API_CONFIG.DB_SERVICE}/api/campaigns/${campaignId}`
    );
    return response.data;
  } catch (error) {
    console.error(`Error fetching campaign ${campaignId}:`, error);
    return null;
  }
}

/**
 * Get batches for a specific campaign
 */
export async function getCampaignBatches(
  campaignId: number
): Promise<CampaignBatch[]> {
  try {
    const response = await axios.get(
      `${API_CONFIG.DB_SERVICE}/api/campaigns/${campaignId}/batches`
    );
    return Array.isArray(response.data.batches) ? response.data.batches : [];
  } catch (error) {
    console.error(`Error fetching batches for campaign ${campaignId}:`, error);
    return [];
  }
}

/**
 * Get leads for a batch with their send status and failure reasons
 */
export async function getBatchLeads(batchId: number): Promise<any> {
  try {
    const response = await axios.get(
      `${API_CONFIG.DB_SERVICE}/api/campaigns/batches/${batchId}/leads`
    );
    return response.data;
  } catch (error) {
    console.error(`Error fetching leads for batch ${batchId}:`, error);
    return null;
  }
}

/**
 * Get phone numbers for a store with health information
 */
export async function getStorePhoneNumbers(
  storeId: number
): Promise<StorePhoneNumbers | null> {
  try {
    const response = await axios.get(
      `${API_CONFIG.DB_SERVICE}/api/stores/${storeId}/phone-numbers`
    );
    return response.data;
  } catch (error) {
    console.error(`Error fetching phone numbers for store ${storeId}:`, error);
    return null;
  }
}

/**
 * Get daily statistics for a store
 */
export async function getStoreDailyStats(
  storeId: number
): Promise<StoreDailyStats | null> {
  try {
    const response = await axios.get(
      `${API_CONFIG.DB_SERVICE}/api/stores/${storeId}/stats/daily`
    );
    return response.data;
  } catch (error) {
    console.error(`Error fetching daily stats for store ${storeId}:`, error);
    return null;
  }
}

/**
 * Preview a campaign before starting it
 * ⚠️ NO SMS IS SENT - Preview only
 */
export async function previewCampaign(
  request: CampaignPreviewRequest
): Promise<CampaignPreviewResponse | null> {
  try {
    const response = await axios.post(
      `${API_CONFIG.DB_SERVICE}/api/campaigns/preview`,
      request
    );
    return response.data;
  } catch (error: any) {
    console.error('Error previewing campaign:', error);
    // Re-throw with error message for UI handling
    const errorMessage =
      error.response?.data?.detail || error.message || 'Failed to preview campaign';
    throw new Error(errorMessage);
  }
}

/**
 * Start a new SMS campaign
 * ⚠️ This will schedule SMS batches (but not send immediately in Milestone 8)
 * In Milestone 9, this will trigger actual SMS sending
 */
export async function startCampaign(
  request: StartCampaignRequest
): Promise<StartCampaignResponse> {
  try {
    const response = await axios.post(
      `${API_CONFIG.DB_SERVICE}/api/campaigns/start`,
      request
    );
    return response.data;
  } catch (error: any) {
    console.error('Error starting campaign:', error);
    // Try multiple error response formats
    // Backend returns: { error: { code, message, timestamp } }
    const errorMessage =
      error.response?.data?.error?.message ||
      error.response?.data?.message ||
      error.response?.data?.detail ||
      error.message ||
      'Failed to start campaign';
    console.error('Error details:', error.response?.data);
    throw new Error(errorMessage);
  }
}

/**
 * Pause a running campaign (Milestone 15)
 * Stops the batch executor from executing pending batches
 */
export async function pauseCampaign(campaignId: number): Promise<void> {
  try {
    await axios.put(
      `${API_CONFIG.DB_SERVICE}/api/campaigns/${campaignId}/pause`
    );
  } catch (error: any) {
    console.error(`Error pausing campaign ${campaignId}:`, error);
    const errorMessage =
      error.response?.data?.detail || error.message || 'Failed to pause campaign';
    throw new Error(errorMessage);
  }
}

/**
 * Resume a paused campaign (Milestone 15)
 * Allows the batch executor to continue executing pending batches
 */
export async function resumeCampaign(campaignId: number): Promise<void> {
  try {
    await axios.put(
      `${API_CONFIG.DB_SERVICE}/api/campaigns/${campaignId}/resume`
    );
  } catch (error: any) {
    console.error(`Error resuming campaign ${campaignId}:`, error);
    const errorMessage =
      error.response?.data?.detail || error.message || 'Failed to resume campaign';
    throw new Error(errorMessage);
  }
}

/**
 * Delete a campaign and all related batches
 * ⚠️ This permanently deletes the campaign and cannot be undone
 */
export async function deleteCampaign(campaignId: number): Promise<void> {
  try {
    await axios.delete(
      `${API_CONFIG.DB_SERVICE}/api/campaigns/${campaignId}`
    );
  } catch (error: any) {
    console.error(`Error deleting campaign ${campaignId}:`, error);
    const errorMessage =
      error.response?.data?.detail || error.message || 'Failed to delete campaign';
    throw new Error(errorMessage);
  }
}

/**
 * Get daily report for a specific date (Milestone 16)
 */
export async function getDailyReport(date: string): Promise<any> {
  try {
    const response = await axios.get(
      `${API_CONFIG.DB_SERVICE}/api/reports/daily/${date}`
    );
    return response.data;
  } catch (error: any) {
    console.error(`Error fetching daily report for ${date}:`, error);
    throw new Error(error.response?.data?.detail || 'Failed to fetch daily report');
  }
}

/**
 * Get SMS timeline for analytics (Milestone 16)
 */
export async function getSmsTimeline(
  storeId?: number,
  startDate?: string,
  endDate?: string
): Promise<any> {
  try {
    const params: any = {};
    if (storeId !== undefined) params.store_id = storeId;
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;

    const response = await axios.get(
      `${API_CONFIG.DB_SERVICE}/api/analytics/sms-timeline`,
      { params }
    );
    return response.data;
  } catch (error: any) {
    console.error('Error fetching SMS timeline:', error);
    throw new Error(error.response?.data?.detail || 'Failed to fetch SMS timeline');
  }
}

export default {
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
};

