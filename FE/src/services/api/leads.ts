// Leads API Services
import axios from 'axios';
import { API_CONFIG } from '../config';
import type { Lead, AddLeadRequest } from '../../types/lead';

/**
 * Get all leads with optional filters
 */
export async function getLeads(params?: {
  limit?: number;
  offset?: number;
  dnc_only?: boolean;
}): Promise<Lead[]> {
  try {
    const response = await axios.get(`${API_CONFIG.DB_SERVICE}/api/leads`, { 
      params: {
        limit: params?.limit || 100,
        offset: params?.offset || 0,
        dnc_only: params?.dnc_only
      }
    });
    // Backend returns {success: true, leads: [...], total: ...}
    if (response.data && typeof response.data === 'object') {
      if (Array.isArray(response.data.leads)) {
        return response.data.leads;
      }
      // Fallback: if response.data is already an array (backward compatibility)
      if (Array.isArray(response.data)) {
        return response.data;
      }
    }
    return [];
  } catch (error) {
    console.error('Error fetching leads:', error);
    return [];
  }
}

/**
 * Add a new lead
 */
export async function addLead(lead: AddLeadRequest): Promise<Lead> {
  try {
    const response = await axios.post(`${API_CONFIG.DB_SERVICE}/api/leads`, {
      phone_number: lead.phone_number,
      name: lead.name || null,
      Address: lead.Address || null,
      City: lead.City || null,
      County: lead.County || null,
      State: lead.State || null,
      Zip: lead.Zip || null,
      priority: lead.priority || 1,
      sms_verified: lead.sms_verified || false,
      skip_consent_sms: lead.skip_consent_sms || false
    });
    return response.data;
    } catch (error: unknown) {
    console.error('Error adding lead:', error);
    const errorMessage = error instanceof Error ? error.message : 'Failed to add lead';
    throw new Error(errorMessage);
  }
}

/**
 * Update an existing lead
 */
export async function updateLead(leadId: number, updates: Partial<Lead>): Promise<Lead> {
  try {
    const response = await axios.post(
      `${API_CONFIG.DB_SERVICE}/api/leads/${leadId}/update`,
      {
        phone_number: updates.phone_number,
        name: updates.name,
        Address: updates.Address,
        City: updates.City,
        County: updates.County,
        State: updates.State,
        Zip: updates.Zip,
        priority: updates.priority,
        dnc_flag: updates.dnc_flag,
        sms_verified: updates.sms_verified
      }
    );
    return response.data;
    } catch (error: unknown) {
    console.error('Error updating lead:', error);
    const errorMessage = error instanceof Error ? error.message : 'Failed to update lead';
    throw new Error(errorMessage);
  }
}

/**
 * Delete a lead
 */
export async function deleteLead(leadId: number): Promise<void> {
  try {
    await axios.post(`${API_CONFIG.DB_SERVICE}/api/leads/${leadId}/delete`);
    } catch (error: unknown) {
    console.error('Error deleting lead:', error);
    const errorMessage = error instanceof Error ? error.message : 'Failed to delete lead';
    throw new Error(errorMessage);
  }
}

/**
 * Mark a lead as Do Not Call
 */
export async function markLeadDNC(phoneNumber: string): Promise<void> {
  try {
    await axios.post(`${API_CONFIG.DB_SERVICE}/api/leads/dnc`, {
      phone_number: phoneNumber,
    });
    } catch (error: unknown) {
    console.error('Error marking lead as DNC:', error);
    const errorMessage = error instanceof Error ? error.message : 'Failed to mark lead as DNC';
    throw new Error(errorMessage);
  }
}

/**
 * Bulk import leads
 */
export async function bulkImportLeads(leads: AddLeadRequest[]): Promise<{
  success: number;
  failed: number;
}> {
  try {
    const response = await axios.post(`${API_CONFIG.DB_SERVICE}/api/leads/bulk`, { 
      leads: leads.map(lead => ({
        phone_number: lead.phone_number,
        name: lead.name || null,
        Address: lead.Address || null,
        City: lead.City || null,
        County: lead.County || null,
        State: lead.State || null,
        Zip: lead.Zip || null,
        priority: lead.priority || 1,
        sms_verified: lead.sms_verified || false,
        skip_consent_sms: lead.skip_consent_sms || false
      }))
    });
    return {
      success: response.data.success || 0,
      failed: response.data.failed || 0
    };
    } catch (error: unknown) {
    console.error('Error bulk importing leads:', error);
    const errorMessage = error instanceof Error ? error.message : 'Failed to import leads';
    throw new Error(errorMessage);
  }
}

/**
 * Import leads from CSV file
 * ⚠️ NO SMS IS SENT DURING IMPORT ⚠️
 */
export async function importLeadsFromCSV(csvContent: string): Promise<{
  success: number;
  failed: number;
  duplicates?: number;
  errors: string[];
  invalid_rows?: Array<{row: number; phone: string; error: string}>;
  summary?: {
    total_rows_in_csv: number;
    valid_and_inserted: number;
    invalid_format: number;
    duplicates_skipped: number;
    insert_failures: number;
  };
  message?: string;
}> {
  try {
    const response = await axios.post(`${API_CONFIG.DB_SERVICE}/api/leads/import-csv`, {
      csv_content: csvContent
    });
    return response.data;
    } catch (error: unknown) {
    console.error('Error importing CSV leads:', error);
    const errorMessage = error instanceof Error ? error.message : 'Failed to import CSV leads';
    throw new Error(errorMessage);
  }
}

/**
 * Export leads to CSV
 */
export async function exportLeadsToCSV(filters?: {
  dnc_only?: boolean;
  limit?: number;
}): Promise<string> {
  try {
    console.log('📤 Exporting leads with filters:', filters);
    const response = await axios.get(`${API_CONFIG.DB_SERVICE}/api/leads/export-csv`, {
      params: filters,
      responseType: 'text' // Important: expect text response, not JSON
    });
    console.log('✅ Export response received:', response.status, response.headers);
    return response.data;
  } catch (error: unknown) {
    console.error('❌ Error exporting leads to CSV:', error);
    if (axios.isAxiosError(error)) {
      console.error('Response status:', error.response?.status);
      console.error('Response data:', error.response?.data);
      console.error('Response headers:', error.response?.headers);
    }
    const errorMessage = error instanceof Error ? error.message : 'Failed to export leads to CSV';
    throw new Error(errorMessage);
  }
}

/**
 * Delete all leads
 */
export async function deleteAllLeads(): Promise<void> {
  try {
    await axios.delete(`${API_CONFIG.DB_SERVICE}/api/leads/all`);
  } catch (error: unknown) {
    console.error('Error deleting all leads:', error);
    const errorMessage = error instanceof Error ? error.message : 'Failed to delete all leads';
    throw new Error(errorMessage);
  }
}

export default {
  getLeads,
  addLead,
  updateLead,
  deleteLead,
  markLeadDNC,
  bulkImportLeads,
  importLeadsFromCSV,
  exportLeadsToCSV,
  deleteAllLeads,
};

