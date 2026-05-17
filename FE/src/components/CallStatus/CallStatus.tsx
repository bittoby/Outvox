// Call Status Component - Animated Status Indicator

import React from 'react';
import { Phone, PhoneOff, Clock, CheckCircle, AlertCircle } from 'lucide-react';
import VoiceWave from '../VoiceWave/VoiceWave';

export type CallStatusType = 'calling' | 'connected' | 'disconnected' | 'failed' | 'pending';

interface CallStatusProps {
  status: CallStatusType;
  duration?: number;
  phoneNumber?: string;
  className?: string;
}

const CallStatus: React.FC<CallStatusProps> = ({
  status,
  duration,
  phoneNumber,
  className = '',
}) => {
  const statusConfig = {
    calling: {
      icon: Phone,
      color: 'text-primary-light',
      bgColor: 'bg-primary/20',
      borderColor: 'border-primary/40',
      label: 'Calling...',
      showWave: true,
    },
    connected: {
      icon: CheckCircle,
      color: 'text-success-light',
      bgColor: 'bg-success/20',
      borderColor: 'border-success/40',
      label: 'Connected',
      showWave: true,
    },
    disconnected: {
      icon: PhoneOff,
      color: 'text-dark-text-muted',
      bgColor: 'bg-dark-elevated',
      borderColor: 'border-dark-border',
      label: 'Ended',
      showWave: false,
    },
    failed: {
      icon: AlertCircle,
      color: 'text-danger-light',
      bgColor: 'bg-danger/20',
      borderColor: 'border-danger/40',
      label: 'Failed',
      showWave: false,
    },
    pending: {
      icon: Clock,
      color: 'text-warning-light',
      bgColor: 'bg-warning/20',
      borderColor: 'border-warning/40',
      label: 'Pending',
      showWave: false,
    },
  };

  const config = statusConfig[status];
  const Icon = config.icon;

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className={`inline-flex items-center gap-3 px-4 py-2 ${config.bgColor} border-2 ${config.borderColor} rounded-xl ${className} animate-scale-in`}>
      <div className={`relative ${config.color}`}>
        <Icon className={`w-5 h-5 ${status === 'calling' ? 'animate-pulse-ring' : ''}`} />
        {(status === 'calling' || status === 'connected') && (
          <div className="absolute -top-1 -right-1">
            <span className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-current opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-current"></span>
            </span>
          </div>
        )}
      </div>

      <div className="flex flex-col min-w-0">
        <span className={`text-sm font-bold ${config.color}`}>{config.label}</span>
        {phoneNumber && (
          <span className="text-xs text-dark-text-muted font-mono truncate">{phoneNumber}</span>
        )}
      </div>

      {config.showWave && (
        <VoiceWave isActive={true} color={config.color.replace('text-', '')} size="sm" />
      )}

      {duration !== undefined && status === 'connected' && (
        <span className="text-sm font-mono font-bold text-success-light">
          {formatDuration(duration)}
        </span>
      )}
    </div>
  );
};

export default CallStatus;

