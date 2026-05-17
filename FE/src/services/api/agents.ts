// Agents API Services
import axios from 'axios';
import { API_CONFIG } from '../config';
import type { Agent, AgentStatus } from '../../types/agent';

/**
 * Get health status of all agents
 */
export async function getAllAgentHealth(): Promise<Agent[]> {
  try {
    const agentPromises = Array.from({ length: 10 }, async (_, i) => {
      const agentId = i + 1;
      const port = 5100 + agentId;
      
      try {
        const url = API_CONFIG.AGENT_URLS[i];
        const response = await axios.get(`${url}/health`, { timeout: 2000 });
        
        // Use backend's agent_id format directly (Agent1, Agent2, etc. - no space)
        const backendAgentId = response.data.agent_id || `Agent${agentId}`;
        
        return {
          agent_id: backendAgentId,
          status: (response.data.status === 'healthy' ? 'healthy' : 'idle') as AgentStatus,
          url,
          port,
          current_call: response.data.current_call || null,
          total_calls: response.data.total_calls || 0,
        };
      } catch {
        return {
          agent_id: `Agent${agentId}`,  // Match backend format (no space)
          status: 'offline' as AgentStatus,
          url: API_CONFIG.AGENT_URLS[i],
          port,
          current_call: null,
          total_calls: 0,
        };
      }
    });
    
    return await Promise.all(agentPromises);
  } catch (error) {
    console.error('Error fetching agent health:', error);
    return [];
  }
}

export default {
  getAllAgentHealth,
};

