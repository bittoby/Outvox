// Lead management types

export interface Lead {
  lead_id: number;
  name: string | null;
  Address: string | null;
  City: string | null;
  County: string | null;
  State: string | null;
  Zip: string | null;
  phone_number: string;
  priority: number;
  call_count: number;
  dnc_flag: boolean;
  sms_verified: boolean;
  sms_verified_at: string | null;
  sms_consent_requested_at: string | null;
  created_at: string;
  last_called: string | null;
  // Milestone 2 & 11: Store assignment and safe-call eligibility
  store_id: number | null;
  call_eligible: boolean;
  call_eligible_reason: string | null;
  safe_call_attempted: boolean;
  safe_call_attempted_at: string | null;
}

export interface AddLeadRequest {
  phone_number: string;
  name?: string;
  Address?: string;
  City?: string;
  County?: string;
  State?: string;
  Zip?: string;
  priority?: number;
  sms_verified?: boolean;
  skip_consent_sms?: boolean;
  store_id?: number;
}

export interface LeadFilters {
  dnc_only?: boolean;
  priority?: number;
  search?: string;
  state?: string;
  city?: string;
  store_id?: number;
}

// Milestone 2: Store type
export interface Store {
  store_id: number;
  name: string;
  location: string;
  daily_sms_quota: number;
  daily_call_quota: number;
  is_active: boolean;
  created_at: string | null;
  // Optional statistics (from GET /api/stores)
  total_leads?: number;
  total_phone_numbers?: number;
}

