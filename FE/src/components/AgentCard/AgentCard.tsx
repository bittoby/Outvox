// Agent Card - Modern, Clear, Simple & User-Friendly with Color

import React from 'react';
import { Phone, Wifi, WifiOff, Clock } from 'lucide-react';
import VoiceWave from '../VoiceWave/VoiceWave';
import type { Agent } from '../../types/agent';

interface AgentCardProps {
  agent: Agent;
  index?: number;
}

const AgentCard: React.FC<AgentCardProps> = ({ agent, index = 0 }) => {
  const isOnline = agent.status === 'healthy';
  const isOnCall = agent.current_call !== undefined && agent.current_call !== null;
  
  // Simple, clear status config
  const statusConfig = {
    healthy: {
      icon: Wifi,
      iconColor: 'text-success',
      dot: 'bg-success',
      text: 'text-success',
      border: 'border-success/20',
      accentBg: 'bg-gradient-to-br from-success/10 to-transparent',
      label: 'Online',
    },
    idle: {
      icon: Clock,
      iconColor: 'text-warning',
      dot: 'bg-warning',
      text: 'text-warning',
      border: 'border-warning/20',
      accentBg: 'bg-gradient-to-br from-warning/10 to-transparent',
      label: 'Idle',
    },
    offline: {
      icon: WifiOff,
      iconColor: 'text-dark-text-muted',
      dot: 'bg-dark-text-muted',
      text: 'text-dark-text-muted',
      border: 'border-dark-border',
      accentBg: 'bg-dark-elevated/30',
      label: 'Offline',
    },
  };

  const config = statusConfig[agent.status as keyof typeof statusConfig] || statusConfig.offline;

  // Format time simply
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div
      className={`group relative bg-dark-surface hover:bg-dark-elevated border ${config.border} hover:border-primary/30 rounded-xl overflow-hidden transition-all duration-300 hover:shadow-modern animate-scale-in`}
      style={{ animationDelay: `${index * 0.05}s` }}
    >
      {/* Subtle color accent background */}
      <div className={`absolute inset-0 ${config.accentBg} transition-opacity duration-300`}></div>
      
      {/* Content */}
      <div className="relative p-4 flex flex-col gap-3">
        {/* Agent Info */}
        <div className="flex justify-between min-w-0">
            <div className="flex items-center gap-2 mb-0.5">
              {/* Status Dot */}
              <div className={`w-2 h-2 rounded-full ${config.dot} flex-shrink-0 ${isOnline ? 'animate-pulse' : ''}`}></div>
              {/* Agent Name */}
              <span className="text-sm font-bold text-dark-text-primary truncate">
                {agent.agent_id}
              </span>
            </div>
            {/* Status Label */}
            <div className="flex items-center justify-between">
              {/* Port */}
              <span className="text-xs font-mono text-dark-text-muted">:{agent.port}</span>
            </div>
          </div>

        {/* Content Area - Clean & Focused */}
        <div className="space-y-3">
          {/* ON CALL */}
          {isOnCall && agent.current_call ? (
            <div className="space-y-3 pt-3 border-t border-dark-border/50">
              {/* Call Status Header */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Phone className="w-3.5 h-3.5 text-success animate-pulse" />
                  <span className="text-xs font-semibold text-success">Active Call</span>
                </div>
                <VoiceWave isActive={true} color="#10b981" size="sm" />
              </div>

              {/* Caller Info */}
              <div className="p-2.5 bg-dark-elevated/50 rounded-lg border border-success/10">
                <div className="text-sm font-bold text-dark-text-primary truncate mb-0.5">
                  {agent.current_call.lead_name}
                </div>
                <div className="text-xs font-mono text-dark-text-muted truncate">
                  {agent.current_call.phone_number}
                </div>
              </div>

              {/* Duration Bar */}
              <div className="flex items-center gap-2">
                <div className="flex-1 h-1.5 bg-dark-elevated rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-gradient-to-r from-success to-success-light rounded-full transition-all duration-500"
                    style={{ width: '70%' }}
                  ></div>
                </div>
                <span className="text-xs font-mono font-bold text-success tabular-nums min-w-[35px] text-right">
                  {formatTime(agent.current_call.duration)}
                </span>
              </div>
            </div>
          ) : isOnline ? (
            /* READY */
            <div className="text-center py-3 pt-4 border-t border-dark-border/50">
              <div className={`inline-flex items-center justify-center w-10 h-10 rounded-full bg-primary/10 border border-primary/20 mb-2 transition-transform duration-300 group-hover:scale-110`}>
                <Phone className="w-5 h-5 text-primary" />
              </div>
              <div className="text-xs font-semibold text-dark-text-primary mb-1">
                Ready for calls
              </div>
              {agent.total_calls !== undefined && agent.total_calls > 0 && (
                <div className="text-xs text-dark-text-muted">
                  {agent.total_calls} {agent.total_calls === 1 ? 'call' : 'calls'} today
                </div>
              )}
            </div>
          ) : (
            /* OFFLINE */
            <div className="text-center py-3 pt-4 border-t border-dark-border/50">
              <div className="inline-flex items-center justify-center w-10 h-10 rounded-full bg-dark-elevated border border-dark-border mb-2">
                <WifiOff className="w-5 h-5 text-dark-text-muted" />
              </div>
              <div className="text-xs font-medium text-dark-text-muted">
                Agent offline
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Subtle left accent bar */}
      <div className={`absolute left-0 top-0 bottom-0 w-1 ${isOnCall ? 'bg-success' : isOnline ? 'bg-primary' : 'bg-dark-border'} transition-all duration-300`}></div>
    </div>
  );
};

export default AgentCard;
