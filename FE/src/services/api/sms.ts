import axios from 'axios';
import { API_CONFIG } from '../config';

export interface SMSConversation {
  sms_id: number;
  lead_id: number;
  phone_number: string;
  message_type: string;
  message_content: string;
  direction: 'inbound' | 'outbound';
  created_at: string;
  lead_name?: string;
  address?: string;
  city?: string;
  state?: string;
}

export interface PhotoSubmission {
  photo_id: number;
  lead_id: number;
  phone_number: string;
  photo_url: string;
  status: 'pending' | 'reviewed' | 'appraised';
  created_at: string;
  reviewed_at?: string;
  reviewed_by?: string;
  lead_name?: string;
  address?: string;
  city?: string;
  state?: string;
}

export interface SMSResponse {
  conversations: SMSConversation[];
  total_count: number;
  limit: number;
  offset: number;
}

export interface PhotosResponse {
  photos: PhotoSubmission[];
  total_count: number;
  limit: number;
  offset: number;
}

/**
 * Get all SMS conversations with pagination and filtering
 */
export async function getAllSMSConversations(
  limit: number = 50,
  offset: number = 0,
  direction?: 'inbound' | 'outbound'
): Promise<SMSResponse> {
  try {
    const params = new URLSearchParams({
      limit: limit.toString(),
      offset: offset.toString(),
    });
    
    if (direction) {
      params.append('direction', direction);
    }
    
    const response = await axios.get(`${API_CONFIG.DB_SERVICE}/api/sms/all-conversations?${params}`);
    
    // Handle different response formats
    if (response.data.conversations) {
      return {
        conversations: response.data.conversations || [],
        total_count: response.data.total_count || response.data.count || 0,
        limit: response.data.limit || limit,
        offset: response.data.offset || offset
      };
    }
    
    return response.data;
  } catch (error) {
    console.error('Error fetching SMS conversations:', error);
    return {
      conversations: [],
      total_count: 0,
      limit,
      offset
    };
  }
}

/**
 * Get SMS conversations for a specific lead
 */
export async function getSMSConversations(leadId: number): Promise<{ conversations: SMSConversation[] }> {
  try {
    const response = await axios.get(`${API_CONFIG.DB_SERVICE}/api/sms/conversations/${leadId}`);
    return response.data;
  } catch (error) {
    console.error('Error fetching SMS conversations for lead:', error);
    return { conversations: [] };
  }
}

/**
 * Get SMS conversation details including lead info and all messages
 */
export interface SMSConversationDetails {
  lead_info: {
    lead_id: number | null;
    name?: string | null;
    address?: string | null;
    city?: string | null;
    county?: string | null;
    state?: string | null;
    zip?: string | null;
    phone_number: string;
    priority?: number | null;
    dnc_flag: boolean;
    created_at?: string | null;
    last_called?: string | null;
  } | null;
  conversations: Array<{
    sms_id: number;
    message_type: string;
    message_content: string;
    direction: 'inbound' | 'outbound';
    created_at?: string;
    twilio_sid?: string;
  }>;
  total_messages: number;
}

export async function getSMSConversationDetails(leadId: number): Promise<SMSConversationDetails> {
  try {
    const response = await axios.get(`${API_CONFIG.DB_SERVICE}/api/sms/conversations/${leadId}`);
    return response.data;
  } catch (error) {
    console.error('Error fetching SMS conversation details:', error);
    throw error;
  }
}

/**
 * Get SMS conversation details by phone number (for conversations without lead_id)
 */
export async function getSMSConversationDetailsByPhone(phoneNumber: string): Promise<SMSConversationDetails> {
  try {
    // URL encode the phone number (it may contain +)
    const encodedPhone = encodeURIComponent(phoneNumber);
    const response = await axios.get(`${API_CONFIG.DB_SERVICE}/api/sms/conversations/phone/${encodedPhone}`);
    return response.data;
  } catch (error) {
    console.error('Error fetching SMS conversation details by phone:', error);
    throw error;
  }
}

/**
 * Get all photo submissions with pagination and filtering
 */
export async function getAllPhotoSubmissions(
  limit: number = 50,
  offset: number = 0,
  status?: 'pending' | 'reviewed' | 'appraised'
): Promise<PhotosResponse> {
  try {
    const params = new URLSearchParams({
      limit: limit.toString(),
      offset: offset.toString(),
    });
    
    if (status) {
      params.append('status', status);
    }
    
    const response = await axios.get(`${API_CONFIG.DB_SERVICE}/api/sms/photos/all-submissions?${params}`);
    
    // Handle different response formats
    if (response.data.photos !== undefined) {
      return {
        photos: response.data.photos || [],
        total_count: response.data.total_count || response.data.count || 0,
        limit: response.data.limit || limit,
        offset: response.data.offset || offset
      };
    }
    
    return response.data;
  } catch (error) {
    console.error('Error fetching photo submissions:', error);
    return {
      photos: [],
      total_count: 0,
      limit,
      offset
    };
  }
}

/**
 * Update photo submission status
 */
export async function updatePhotoStatus(
  photoId: number,
  status: 'pending' | 'reviewed' | 'appraised',
  reviewedBy: string
): Promise<{ status: string; message: string }> {
  try {
    const response = await axios.put(`${API_CONFIG.DB_SERVICE}/api/sms/photos/${photoId}/status`, {
      status,
      reviewed_by: reviewedBy
    });
    return response.data;
  } catch (error) {
    console.error('Error updating photo status:', error);
    throw error;
  }
}

export async function clearSMSHistory(): Promise<{ status: string; message: string }> {
  try {
    // Clear both conversations and photos (legacy endpoint behavior)
    const response = await axios.delete(`${API_CONFIG.DB_SERVICE}/api/sms/conversations/clear-all`);
    return response.data;
  } catch (error) {
    console.error('Error clearing SMS history:', error);
    throw error;
  }
}

export async function clearConversations(): Promise<{ success: boolean; message: string; deleted_count: number }> {
  try {
    const response = await axios.delete(`${API_CONFIG.DB_SERVICE}/api/sms/conversations/clear-all`);
    return response.data;
  } catch (error) {
    console.error('Error clearing conversations:', error);
    throw error;
  }
}

export async function clearPhotoSubmissions(): Promise<{ success: boolean; message: string; deleted_count: number }> {
  try {
    const response = await axios.delete(`${API_CONFIG.DB_SERVICE}/api/sms/photos/clear-all`);
    return response.data;
  } catch (error) {
    console.error('Error clearing photo submissions:', error);
    throw error;
  }
}

/**
 * Delete SMS conversation for a specific lead
 */
export async function deleteSMSConversation(leadId: number): Promise<{ success: boolean; message: string; deleted_count: number }> {
  try {
    const response = await axios.delete(`${API_CONFIG.DB_SERVICE}/api/sms/conversations/${leadId}`);
    return response.data;
  } catch (error) {
    console.error('Error deleting SMS conversation:', error);
    throw error;
  }
}

/**
 * Delete a photo submission
 */
export async function deletePhotoSubmission(photoId: number): Promise<{ success: boolean; message: string; photo_id: number }> {
  try {
    const response = await axios.delete(`${API_CONFIG.DB_SERVICE}/api/sms/photos/${photoId}`);
    return response.data;
  } catch (error) {
    console.error('Error deleting photo submission:', error);
    throw error;
  }
}