// Phone Numbers API Services
import axios from 'axios';
import { API_CONFIG } from '../config';

export interface PhoneNumber {
  phone_number_id: number;
  phone_number: string;
  store_id: number | null;
  store_name: string | null;
  is_active: boolean;
  daily_sms_count: number;
  hourly_sms_count: number;
  daily_call_count: number;
  hourly_call_count: number;
  last_batch_sent_at: string | null;
  last_call_at: string | null;
  last_hourly_reset: string | null;
}

export interface PhoneNumbersResponse {
  success: boolean;
  phone_numbers: PhoneNumber[];
  count: number;
}

export interface AddPhoneNumberRequest {
  phone_number: string;
  store_id?: number | null;
  rotation_weight?: number;
}

export interface AddPhoneNumberResponse {
  status: string;
  message: string;
  phone_number: string;
  rotation_weight: number;
  is_active: boolean;
  store_id: number | null;
  number_id: number;
}

/**
 * Add a new Twilio phone number to the system.
 *
 * The backend normalizes the input to E.164 (e.g. "+15551234567"), so the UI
 * can accept common US formats like "(555) 123-4567" or "5551234567" too.
 */
export async function addPhoneNumber(
  request: AddPhoneNumberRequest
): Promise<AddPhoneNumberResponse> {
  try {
    const payload: AddPhoneNumberRequest = {
      phone_number: request.phone_number,
      rotation_weight: request.rotation_weight ?? 1,
    };
    if (request.store_id !== undefined && request.store_id !== null) {
      payload.store_id = request.store_id;
    }

    const response = await axios.post<AddPhoneNumberResponse>(
      `${API_CONFIG.DB_SERVICE}/api/phone-numbers`,
      payload
    );
    return response.data;
  } catch (error: any) {
    console.error('Error adding phone number:', error);
    const detail = error.response?.data?.detail;
    const errorMessage =
      typeof detail === 'string'
        ? detail
        : Array.isArray(detail) && detail.length > 0
          ? detail[0]?.msg || 'Invalid phone number'
          : error.message || 'Failed to add phone number';
    throw new Error(errorMessage);
  }
}

/**
 * Get all phone numbers with optional store filter
 */
export async function getAllPhoneNumbers(storeId?: number): Promise<PhoneNumber[]> {
  try {
    const params = storeId ? { store_id: storeId } : {};
    const response = await axios.get<PhoneNumbersResponse>(
      `${API_CONFIG.DB_SERVICE}/api/phone-numbers`,
      { params }
    );
    return response.data.phone_numbers || [];
  } catch (error) {
    console.error('Error fetching phone numbers:', error);
    return [];
  }
}

/**
 * Assign a phone number to a store
 */
export async function assignPhoneToStore(
  phoneNumberId: number,
  storeId: number
): Promise<{ success: boolean; message: string }> {
  try {
    const response = await axios.put(
      `${API_CONFIG.DB_SERVICE}/api/phone-numbers/${phoneNumberId}/assign-store`,
      { store_id: storeId }
    );
    return response.data;
  } catch (error: any) {
    console.error('Error assigning phone to store:', error);
    const errorMessage = error.response?.data?.detail || error.message || 'Failed to assign phone number';
    throw new Error(errorMessage);
  }
}

/**
 * Unassign a phone number from store (set store_id to null)
 */
export async function unassignPhoneFromStore(
  phoneNumberId: number
): Promise<{ success: boolean; message: string }> {
  try {
    const response = await axios.put(
      `${API_CONFIG.DB_SERVICE}/api/phone-numbers/${phoneNumberId}/assign-store`,
      { store_id: null }
    );
    return response.data;
  } catch (error: any) {
    console.error('Error unassigning phone from store:', error);
    const errorMessage = error.response?.data?.detail || error.message || 'Failed to unassign phone number';
    throw new Error(errorMessage);
  }
}

/**
 * Activate a phone number
 */
export async function activatePhoneNumber(
  phoneNumber: string
): Promise<{ success: boolean; message: string }> {
  try {
    const response = await axios.put(
      `${API_CONFIG.DB_SERVICE}/api/phone-numbers/${phoneNumber}/activate`
    );
    return response.data;
  } catch (error: any) {
    console.error('Error activating phone number:', error);
    const errorMessage = error.response?.data?.detail || error.message || 'Failed to activate phone number';
    throw new Error(errorMessage);
  }
}

/**
 * Deactivate a phone number
 */
export async function deactivatePhoneNumber(
  phoneNumber: string
): Promise<{ success: boolean; message: string }> {
  try {
    const response = await axios.put(
      `${API_CONFIG.DB_SERVICE}/api/phone-numbers/${phoneNumber}/deactivate`
    );
    return response.data;
  } catch (error: any) {
    console.error('Error deactivating phone number:', error);
    const errorMessage = error.response?.data?.detail || error.message || 'Failed to deactivate phone number';
    throw new Error(errorMessage);
  }
}

/**
 * Delete a phone number by phone number string
 */
export async function deletePhoneNumber(
  phoneNumber: string
): Promise<{ status: string; message: string }> {
  try {
    const response = await axios.delete(
      `${API_CONFIG.DB_SERVICE}/api/phone-numbers/${phoneNumber}`
    );
    return response.data;
  } catch (error: any) {
    console.error('Error deleting phone number:', error);
    const errorMessage = error.response?.data?.detail || error.message || 'Failed to delete phone number';
    throw new Error(errorMessage);
  }
}

/**
 * Delete multiple phone numbers
 */
export async function deletePhoneNumbers(
  phoneNumbers: string[]
): Promise<{ success: number; failed: number; errors: string[] }> {
  const results = { success: 0, failed: 0, errors: [] as string[] };
  
  for (const phoneNumber of phoneNumbers) {
    try {
      await deletePhoneNumber(phoneNumber);
      results.success++;
    } catch (error: any) {
      results.failed++;
      results.errors.push(`${phoneNumber}: ${error.message}`);
    }
  }
  
  return results;
}

