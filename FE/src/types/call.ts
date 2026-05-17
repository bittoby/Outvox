// Call and campaign types

export type CallStatus = 'success' | 'failed' | 'in_progress' | 'no_leads' | 'no_numbers';
export type CallResultType = 'interested' | 'not_interested' | 'dnc' | 'callback';

export interface CallResult {
  status: CallStatus;
  call_sid?: string;
  lead_id?: number;
  phone_number?: string;
  twilio_number?: string;
  agent_id?: string;
  message?: string;
  error?: string;
}

export interface CallHistoryItem {
  id: number;
  lead_id: number;
  agent_id: string;
  twilio_number: string;
  call_sid: string;
  call_duration: number;
  result_type: string;
  timestamp: string;
  lead_name: string | null;
  phone_number: string;
  lead_address: string | null;
  lead_city: string | null;
  lead_state: string | null;
}

export interface CampaignConfig {
  call_count: number;
  mode: 'smart' | 'custom';
}

export interface CampaignResult {
  status: string;
  total_calls: number;
  successful: number;
  failed: number;
  results: Array<{
    call_number: number;
    status: string;
    call_sid?: string;
    agent_id?: string;
    error?: string;
  }>;
}

export interface CampaignProgress {
  campaign_id: string;
  total_calls: number;
  completed_calls: number;
  successful_calls: number;
  failed_calls: number;
  in_progress: number;
  status: 'running' | 'paused' | 'completed' | 'stopped';
  estimated_time_remaining?: number; // seconds
}

export interface CallDetails {
  id: number;
  lead_id: number;
  agent_id: string;
  twilio_number: string;
  call_sid: string;
  call_duration: number;
  result_type: string;
  customer_transcript: string;
  agent_transcript: string;
  combined_transcript: string;  // Chronological conversation
  timestamp: string;
  lead_name: string | null;
  phone_number: string;
  lead_address: string | null;
  lead_city: string | null;
  lead_county: string | null;
  lead_state: string | null;
  lead_zip: string | null;
}

