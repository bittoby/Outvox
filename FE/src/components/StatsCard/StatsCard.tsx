// Stats Card Component - Animated Statistics Display

import React from 'react';
import { TrendingUp, TrendingDown } from 'lucide-react';

interface StatsCardProps {
  label: string;
  value: number;
  total?: number;
  color?: 'primary' | 'success' | 'warning' | 'danger' | 'info';
  showBar?: boolean;
  trend?: {
    value: number;
    isPositive: boolean;
  };
  index?: number;
}

const StatsCard: React.FC<StatsCardProps> = ({
  label,
  value,
  total,
  color = 'primary',
  showBar = false,
  trend,
  index = 0,
}) => {
  const colorClasses = {
    primary: {
      bg: 'from-primary to-primary-dark',
      text: 'text-primary-light',
      border: 'border-primary/40',
      glow: 'shadow-glow-primary',
    },
    success: {
      bg: 'from-success to-success-dark',
      text: 'text-success-light',
      border: 'border-success/40',
      glow: 'shadow-glow-success',
    },
    warning: {
      bg: 'from-warning to-warning-dark',
      text: 'text-warning-light',
      border: 'border-warning/40',
      glow: 'shadow-glow-warning',
    },
    danger: {
      bg: 'from-danger to-danger-dark',
      text: 'text-danger-light',
      border: 'border-danger/40',
      glow: 'shadow-glow-danger',
    },
    info: {
      bg: 'from-info to-info-dark',
      text: 'text-info-light',
      border: 'border-info/40',
      glow: '',
    },
  };

  const colors = colorClasses[color];
  const percentage = total ? (value / total) * 100 : 0;

  return (
    <div
      className={`group relative bg-dark-surface border-2 ${colors.border} rounded-xl p-4 hover:scale-105 transition-all duration-300 card-glow animate-slide-in-left`}
      style={{ animationDelay: `${index * 0.1}s` }}
    >
      {/* Dot Indicator */}
      <div className="flex items-center gap-3 mb-3">
        <div className={`w-3 h-3 rounded-full bg-gradient-to-br ${colors.bg} ${colors.glow} animate-pulse-slow`}></div>
        <span className="text-sm font-semibold text-dark-text-secondary">{label}</span>
      </div>

      {/* Value */}
      <div className="flex items-end justify-between mb-2">
        <span className={`text-3xl font-bold ${colors.text} glow-text`}>
          {value.toLocaleString()}
        </span>
        {total && (
          <span className="text-lg text-dark-text-muted font-medium">
            /{total}
          </span>
        )}
      </div>

      {/* Progress Bar */}
      {showBar && total && (
        <div className="mb-3">
          <div className="h-2 bg-dark-elevated rounded-full overflow-hidden">
            <div
              className={`h-full bg-gradient-to-r ${colors.bg} rounded-full transition-all duration-1000 animate-shimmer`}
              style={{ 
                width: `${percentage}%`,
                backgroundSize: '200% 100%',
              }}
            ></div>
          </div>
          <div className="flex justify-between mt-1">
            <span className="text-xs text-dark-text-muted">{percentage.toFixed(0)}%</span>
          </div>
        </div>
      )}

      {/* Trend */}
      {trend && (
        <div className={`inline-flex items-center gap-1 ml-5 px-2 py-1 rounded-full text-xs font-bold ${
          trend.isPositive 
            ? 'bg-success/15 text-success-light border border-success/30' 
            : 'bg-danger/15 text-danger-light border border-danger/30'
        }`}>
          {trend.isPositive ? (
            <TrendingUp className="w-3 h-3" />
          ) : (
            <TrendingDown className="w-3 h-3" />
          )}
          <span>{trend.value.toFixed(1)}%</span>
        </div>
      )}

      {/* Hover Glow */}
      <div className={`absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300 rounded-xl ${colors.glow} pointer-events-none`}></div>
    </div>
  );
};

export default StatsCard;

