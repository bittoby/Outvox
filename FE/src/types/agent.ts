// Agent and system types

export type AgentStatus = 'healthy' | 'idle' | 'offline';

export interface Agent {
  agent_id: string;
  status: AgentStatus;
  url: string;
  port: number;
  current_call?: {
    lead_name: string;
    phone_number: string;
    duration: number; // seconds
  };
  uptime?: string;
  total_calls?: number;
}

export interface AgentHealthData {
  status: string;
  agent_id: string;
  service: string;
  timestamp: string;
  config?: {
    max_call_duration: number;
    recording_enabled: boolean;
    english_only: boolean;
  };
}

export interface SystemHealth {
  database: boolean;
  load_balancer: boolean;
  agents: {
    healthy: number;
    total: number;
  };
}

