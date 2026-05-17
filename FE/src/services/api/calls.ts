// Calls API Services
import axios from 'axios';
import { API_CONFIG } from '../config';
import type { CallResult, CallStatus, CallHistoryItem, CampaignResult, CallDetails } from '../../types/call';

/**
 * Start a single outbound call
 */
export async function startSingleCall(): Promise<CallResult> {
  try {
    console.log('🚀 Starting single call...');
    
    const response = await axios.post(`${API_CONFIG.DB_SERVICE}/api/calls/start-call`);
    
    console.log('✅ Response from backend:', response.data);
    
    // Check if we got a valid call_sid
    if (!response.data.call_sid) {
      console.error('❌ No call_sid in response:', response.data);
      return {
        status: 'failed' as CallStatus,
        message: response.data.message || 'Call failed - no SID returned',
        agent_id: response.data.agent_id,
      };
    }
    
    return {
      status: 'success' as CallStatus,
      message: response.data.message || 'Call initiated successfully',
      call_sid: response.data.call_sid,
      agent_id: response.data.agent_id,
    };
    } catch (error: unknown) {
    console.error('❌ Error starting call:', error);
    const errorMessage = error instanceof Error ? error.message : 'Failed to start call';
    return {
      status: 'failed' as CallStatus,
      message: errorMessage,
    };
  }
}

/**
 * Get call history with optional filtering
 */
export async function getCallHistory(params?: {
  limit?: number;
  offset?: number;
  result_type?: string;
}): Promise<CallHistoryItem[]> {
  try {
    const response = await axios.get(`${API_CONFIG.DB_SERVICE}/api/calls/call-history`, {
      params: {
        limit: params?.limit || 50,
        offset: params?.offset || 0,
        result_type: params?.result_type
      }
    });
    
    // Handle both formats: direct array or object with 'calls' property
    let data = response.data;
    if (data && typeof data === 'object' && !Array.isArray(data)) {
      // Backend returns { success: true, calls: [...], total: ... }
      data = data.calls || [];
    }
    
    return Array.isArray(data) ? data : [];
  } catch (error) {
    console.error('Error fetching call history:', error);
    return [];
  }
}

/**
 * Get detailed call information including transcripts
 */
export async function getCallDetails(resultId: number): Promise<CallDetails> {
  try {
    const response = await axios.get(`${API_CONFIG.DB_SERVICE}/api/calls/call-details/${resultId}`);
    
    // Handle both formats: direct CallDetails object or wrapped in { success, call }
    let data = response.data;
    if (data && typeof data === 'object' && !Array.isArray(data)) {
      // Backend might return { success: true, call: {...} }
      if (data.call) {
        data = data.call;
      }
    }
    
    return data as CallDetails;
  } catch (error) {
    console.error('Error fetching call details:', error);
    throw error;
  }
}

/**
 * Delete a call history record
 */
export async function deleteCallHistory(resultId: number): Promise<void> {
  try {
    await axios.delete(`${API_CONFIG.DB_SERVICE}/api/calls/call-history/${resultId}`);
  } catch (error) {
    console.error('Error deleting call history:', error);
    throw error;
  }
}

/**
 * Start a voice calling campaign
 */
export async function startCallCampaign(callCount: number): Promise<CampaignResult> {
  try {
    console.log(`🚀 Starting voice call campaign with ${callCount} calls...`);
    
    const response = await axios.post(`${API_CONFIG.DB_SERVICE}/api/calls/start-campaign`, {
      call_count: callCount
    });
    
    console.log('✅ Campaign result:', response.data);
    return response.data;
    } catch (error: unknown) {
    console.error('❌ Campaign error:', error);
    const errorMessage = error instanceof Error ? error.message : 'Failed to start campaign';
    throw new Error(errorMessage);
  }
}

export default {
  startSingleCall,
  getCallHistory,
  getCallDetails,
  deleteCallHistory,
  startCallCampaign,
};

