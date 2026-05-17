// Campaign management types - Milestone 13 & 14

export interface Campaign {
  campaign_id: number;
  store_id: number;
  store_name: string;
  target_count: number;
  actual_sent: number;
  status: 'pending' | 'active' | 'completed' | 'paused' | 'cancelled';
  created_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  batch_count: number;
  completed_batches: number;
  pending_batches: number;
  running_batches: number;
  failed_batches: number;
  progress_percentage: number;
}

export interface CampaignDetails extends Campaign {
  batches: CampaignBatch[];
}

export interface CampaignBatch {
  batch_id: number;
  batch_number: number;
  phone_number_id: number | null;
  phone_number?: string;
  target_count: number;
  actual_sent: number;
  status: 'pending' | 'active' | 'completed' | 'failed';
  scheduled_at: string | null;
  executed_at: string | null;
  last_batch_sent_at?: string | null;
}

export interface PhoneNumberHealth {
  phone_number_id: number;
  phone_number: string;
  hourly_sms_count: number;
  daily_sms_count: number;
  hourly_call_count: number;
  daily_call_count: number;
  last_batch_sent_at: string | null;
  last_hourly_reset: string | null;
  is_active: boolean;
  health_status: 'healthy' | 'warning' | 'exhausted';
  sms_capacity_percentage: number;
  call_capacity_percentage: number;
}

export interface StorePhoneNumbers {
  store_id: number;
  phone_numbers: PhoneNumberHealth[];
  total_count: number;
  active_count: number;
  healthy_count: number;
}

export interface StoreDailyStats {
  store_id: number;
  store_name: string;
  sms_sent_today: number;
  calls_made_today: number;
  date: string;
}

export interface CampaignPreviewRequest {
  store_id: number;
  target_count: number;
}

export interface CampaignPreviewResponse {
  store_id: number;
  store_name: string;
  leads_to_contact: number;
  estimated_cost: number;
  estimated_time_hours: number;
  estimated_batches: number;
  available_phone_numbers: number;
  batch_size: number;
  batch_spacing_minutes: number;
  preview_leads: PreviewLead[];
  warnings: string[];
  sms_sent: boolean;
}

export interface PreviewLead {
  lead_id: number;
  name: string | null;
  phone_number: string;
  Address: string | null;
  City: string | null;
  State: string | null;
}

export interface StartCampaignRequest {
  store_id: number;
  target_count: number;
  start_time?: string;
}

export interface StartCampaignResponse {
  success: boolean;
  campaign_id: number;
  store_id: number;
  store_name: string;
  target_count: number;
  actual_leads_assigned: number;
  batch_count: number;
  batch_size: number;
  batch_spacing_minutes: number;
  estimated_cost: number;
  estimated_duration_minutes: number;
  start_time: string;
  batches: Array<{
    batch_id: number;
    batch_number: number;
    scheduled_at: string;
    lead_count: number;
  }>;
  status: string;
  sms_sent: boolean;
}

