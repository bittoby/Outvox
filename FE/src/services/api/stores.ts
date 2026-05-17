// Store API Services - Milestone 2
import axios from 'axios';
import { API_CONFIG } from '../config';
import type { Store } from '../../types/lead';

/**
 * Get all stores
 */
export async function getStores(): Promise<Store[]> {
  try {
    const response = await axios.get(`${API_CONFIG.DB_SERVICE}/api/stores`);
    // Backend returns: {success: true, stores: [], count: X}
    if (response.data && response.data.stores && Array.isArray(response.data.stores)) {
      return response.data.stores;
    }
    return Array.isArray(response.data) ? response.data : [];
  } catch (error) {
    console.error('Error fetching stores:', error);
    return [];
  }
}

/**
 * Get store by ID
 */
export async function getStore(storeId: number): Promise<Store | null> {
  try {
    const response = await axios.get(`${API_CONFIG.DB_SERVICE}/api/stores/${storeId}`);
    return response.data?.store || response.data || null;
  } catch (error) {
    console.error(`Error fetching store ${storeId}:`, error);
    return null;
  }
}

/**
 * Create a new store
 */
export async function createStore(store: {
  name: string;
  location?: string;
  daily_sms_quota?: number;
  daily_call_quota?: number;
}): Promise<Store> {
  try {
    const response = await axios.post(`${API_CONFIG.DB_SERVICE}/api/stores`, store);
    return response.data?.store || response.data;
  } catch (error: unknown) {
    console.error('Error creating store:', error);
    const errorMessage = error instanceof Error ? error.message : 'Failed to create store';
    throw new Error(errorMessage);
  }
}

/**
 * Update a store
 */
export async function updateStore(
  storeId: number,
  updates: {
    name?: string;
    location?: string;
    daily_sms_quota?: number;
    daily_call_quota?: number;
    is_active?: boolean;
  }
): Promise<{ success: boolean; message: string }> {
  try {
    const response = await axios.put(`${API_CONFIG.DB_SERVICE}/api/stores/${storeId}`, updates);
    return response.data;
  } catch (error: unknown) {
    console.error(`Error updating store ${storeId}:`, error);
    const errorMessage = error instanceof Error ? error.message : 'Failed to update store';
    throw new Error(errorMessage);
  }
}

/**
 * Delete a store
 */
export async function deleteStore(storeId: number): Promise<{
  success: boolean;
  message: string;
  unassigned: {
    leads: number;
    phone_numbers: number;
    campaigns: number;
    templates: number;
  };
}> {
  try {
    const response = await axios.delete(`${API_CONFIG.DB_SERVICE}/api/stores/${storeId}`);
    return response.data;
  } catch (error: unknown) {
    console.error(`Error deleting store ${storeId}:`, error);
    const errorMessage = error instanceof Error ? error.message : 'Failed to delete store';
    throw new Error(errorMessage);
  }
}

/**
 * Bulk assign leads to a store
 * ⚠️ NO SMS IS SENT DURING ASSIGNMENT ⚠️
 */
export async function bulkAssignLeadsToStore(
  leadIds: number[],
  storeId: number
): Promise<{
  assigned_count: number;
  skipped_count: number;
  skipped_leads: Array<{ lead_id: number; phone_number: string; reason: string }>;
  store_id: number;
  store_name: string;
  message: string;
}> {
  try {
    const response = await axios.put(`${API_CONFIG.DB_SERVICE}/api/leads/bulk-assign`, {
      lead_ids: leadIds,
      store_id: storeId
    });
    return response.data;
  } catch (error: unknown) {
    console.error('Error bulk assigning leads:', error);
    const errorMessage = error instanceof Error ? error.message : 'Failed to assign leads';
    throw new Error(errorMessage);
  }
}

/**
 * Get safe-call eligible leads
 * Milestone 11: 24-Hour Safe-Call Window
 */
export async function getSafeCallEligibleLeads(
  storeId?: number,
  limit: number = 100
): Promise<Array<{
  lead_id: number;
  name: string | null;
  phone_number: string;
  Address: string | null;
  City: string | null;
  State: string | null;
  Zip: string | null;
  store_id: number | null;
  call_eligible: boolean;
  call_eligible_reason: string | null;
  safe_call_attempted: boolean;
  safe_call_attempted_at: string | null;
  sms_consent_requested_at: string | null;
  sms_verified: boolean;
  sms_verified_at: string | null;
  priority: number;
  hours_since_sms: number;
}>> {
  try {
    const params: any = { limit };
    if (storeId !== undefined) {
      params.store_id = storeId;
    }
    
    const response = await axios.get(`${API_CONFIG.DB_SERVICE}/api/leads/safe-call-eligible`, {
      params
    });
    return Array.isArray(response.data) ? response.data : [];
  } catch (error) {
    console.error('Error fetching safe-call eligible leads:', error);
    return [];
  }
}

/**
 * Auto-assign unassigned leads to stores based on location
 */
export async function autoAssignLeads(): Promise<{
  success: boolean;
  assigned_count: number;
  skipped_count: number;
  total_processed: number;
  message: string;
  assignments: Array<{
    lead_id: number;
    store_id: number | null;
    store_name: string | null;
    match_reason: string;
  }>;
}> {
  try {
    const response = await axios.post(`${API_CONFIG.DB_SERVICE}/api/leads/auto-assign`);
    return response.data;
  } catch (error: unknown) {
    console.error('Error auto-assigning leads:', error);
    const errorMessage = error instanceof Error ? error.message : 'Failed to auto-assign leads';
    throw new Error(errorMessage);
  }
}

export default {
  getStores,
  getStore,
  bulkAssignLeadsToStore,
  getSafeCallEligibleLeads,
  autoAssignLeads,
};
