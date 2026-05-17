// Popup API Services for TCPA Compliance
import axios from 'axios';
import { API_CONFIG } from '../config';

export interface PopupQueueItem {
  popup_id: number;
  lead_id: number;
  status: string;
  created_at: string | null;
  lead: {
    lead_id: number;
    name: string | null;
    phone_number: string;
    Address: string | null;
    City: string | null;
    State: string | null;
    priority: number;
    call_count: number;
    dnc_flag: boolean;
    sms_verified: boolean;
    sms_verified_at: string | null;
    sms_consent_requested_at: string | null;
  };
}

export interface PendingPopupsResponse {
  pending_popups: PopupQueueItem[];
  total: number;
  limit?: number;
  offset?: number;
}

export interface PopupQueryParams {
  limit?: number;
  offset?: number;
  sort_field?: 'created_at' | 'priority' | 'name';
  sort_direction?: 'asc' | 'desc';
  priority?: number;
}

export interface ManualDialRequest {
  lead_id: number;
  employee_name: string;
  popup_id?: number;
}

/**
 * Get all pending popup items
 */
export async function getPendingPopups(params?: PopupQueryParams): Promise<PendingPopupsResponse> {
  try {
    const response = await axios.get(`${API_CONFIG.DB_SERVICE}/api/popup/pending`, {
      params: {
        limit: params?.limit,
        offset: params?.offset,
        sort_field: params?.sort_field,
        sort_direction: params?.sort_direction,
        priority: params?.priority,
      },
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching pending popups:', error);
    throw error;
  }
}

/**
 * Dismiss a popup without dialing
 */
export async function dismissPopup(popupId: number): Promise<void> {
  try {
    await axios.post(`${API_CONFIG.DB_SERVICE}/api/popup/dismiss/${popupId}`);
  } catch (error) {
    console.error('Error dismissing popup:', error);
    throw error;
  }
}

/**
 * Prepare manual dial (updates popup queue, returns lead info)
 */
export async function prepareManualDial(request: ManualDialRequest): Promise<any> {
  try {
    const response = await axios.post(`${API_CONFIG.DB_SERVICE}/api/popup/manual-dial`, {
      lead_id: request.lead_id,
      employee_name: request.employee_name
    });
    return response.data;
  } catch (error) {
    console.error('Error preparing manual dial:', error);
    throw error;
  }
}

/**
 * Actually dial the lead (calls the outbound agent)
 * Routes through load balancer or directly to an agent
 */
export async function dialLead(request: ManualDialRequest): Promise<any> {
  let lastError: any = null;
  
  // Try load balancer first
  try {
    const response = await axios.post(`${API_CONFIG.LOAD_BALANCER}/manual-dial`, {
      lead_id: request.lead_id,
      employee_name: request.employee_name,
      popup_id: request.popup_id
    }, { timeout: 10000 });
    
    // Check if response indicates success
    if (response.data && response.data.status === 'success') {
      return response.data;
    } else {
      // Response received but indicates failure
      const errorMsg = response.data?.message || 'Call failed';
      throw new Error(errorMsg);
    }
  } catch (lbError: any) {
    lastError = lbError;
    console.warn('Load balancer failed, trying direct agents:', lbError.message);
    
    // Try each agent URL until one succeeds
    for (const agentUrl of API_CONFIG.AGENT_URLS) {
      try {
        const response = await axios.post(`${agentUrl}/manual-dial`, {
          lead_id: request.lead_id,
          employee_name: request.employee_name,
          popup_id: request.popup_id
        }, { timeout: 10000 });
        
        // Check if response indicates success
        if (response.data && response.data.status === 'success') {
          return response.data;
        } else {
          // Response received but indicates failure
          const errorMsg = response.data?.message || 'Call failed';
          throw new Error(errorMsg);
        }
      } catch (agentError: any) {
        lastError = agentError;
        // Continue to next agent
        continue;
      }
    }
  }
  
  // All attempts failed
  const errorMessage = lastError?.response?.data?.message || 
                       lastError?.response?.data?.detail || 
                       lastError?.message || 
                       'Failed to dial lead - no agents available';
  throw new Error(errorMessage);
}

export default {
  getPendingPopups,
  dismissPopup,
  prepareManualDial,
  dialLead,
};

