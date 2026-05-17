// Statistics and analytics types

export interface TwilioNumber {
  phone: string;
  shop: string;  // Store name (for backward compatibility with Dashboard - uses store_name from JOIN)
  daily_calls: number;
  last_call: string | null;
  rotation_weight?: number;
  is_active?: boolean;
}

export interface CallStats {
  total_calls: number;
  interested: number;
  not_interested: number;
  dnc: number;
  callback: number;
  pending_leads: number;
  numbers: TwilioNumber[];
}

export interface DashboardKPIs {
  active_agents: number;
  total_agents: number;
  today_calls: number;
  success_rate: number;
  pending_leads: number;
}

