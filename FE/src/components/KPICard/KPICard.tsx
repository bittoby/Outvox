// KPICard Component - AWESOME Animated KPI Display

import React from 'react';

interface KPICardProps {
  icon: React.ReactNode;
  title: string;
  value: string | number;
  subtitle?: string;
  variant?: 'primary' | 'success' | 'warning' | 'danger' | 'info';
  trend?: {
    value: number;
    isPositive: boolean;
  };
  loading?: boolean;
}

const KPICard: React.FC<KPICardProps> = ({
  icon,
  title,
  value,
  subtitle,
  variant = 'primary',
  trend,
  loading = false,
}) => {
  const variantClasses = {
    primary: {
      gradient: 'from-primary-light to-primary-dark',
      text: 'text-primary-light',
      border: 'border-primary/40',
      glow: 'shadow-glow-primary',
      bg: 'from-primary/5 to-transparent',
    },
    success: {
      gradient: 'from-success-light to-success-dark',
      text: 'text-success-light',
      border: 'border-success/40',
      glow: 'shadow-glow-success',
      bg: 'from-success/5 to-transparent',
    },
    warning: {
      gradient: 'from-warning-light to-warning-dark',
      text: 'text-warning-light',
      border: 'border-warning/40',
      glow: 'shadow-glow-warning',
      bg: 'from-warning/5 to-transparent',
    },
    danger: {
      gradient: 'from-danger-light to-danger-dark',
      text: 'text-danger-light',
      border: 'border-danger/40',
      glow: 'shadow-glow-danger',
      bg: 'from-danger/5 to-transparent',
    },
    info: {
      gradient: 'from-info-light to-info-dark',
      text: 'text-info-light',
      border: 'border-info/40',
      glow: '',
      bg: 'from-info/5 to-transparent',
    },
  };

  const colors = variantClasses[variant];

  if (loading) {
    return (
      <div className="relative overflow-hidden flex items-start gap-4 p-6 bg-dark-surface border-2 border-dark-border rounded-xl shadow-modern min-h-[160px] animate-pulse">
        <div className="shimmer absolute inset-0"></div>
        <div className="w-14 h-14 bg-dark-elevated rounded-xl"></div>
        <div className="flex-1 space-y-3">
          <div className="h-4 bg-dark-elevated rounded w-1/2"></div>
          <div className="h-8 bg-dark-elevated rounded w-3/4"></div>
        </div>
      </div>
    );
  }

  return (
    <div className={`group relative flex items-start gap-4 p-6 bg-gradient-to-br ${colors.bg} border-2 ${colors.border} rounded-xl shadow-modern hover:shadow-modern-lg hover:border-${variant}-light card-glow transition-all duration-300 animate-bounce-in min-h-[160px] overflow-hidden`}>
      {/* Animated glow on hover */}
      <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500">
        <div className={`absolute inset-0 bg-gradient-to-br ${colors.bg}`}></div>
      </div>
      
      {/* Icon with awesome animation */}
      <div className={`relative z-10 flex items-center justify-center w-16 h-16 rounded-xl bg-gradient-to-br ${colors.gradient} ${colors.glow} group-hover:scale-110 group-hover:rotate-3 transition-all duration-300 breathing`}>
        <div className="text-white text-2xl">
          {icon}
        </div>
        {/* Pulse ring animation */}
        <div className="absolute inset-0 rounded-xl bg-current opacity-20 animate-ping pointer-events-none"></div>
      </div>

      {/* Content */}
      <div className="relative z-10 flex-1 min-w-0">
        <p className="text-sm font-semibold text-dark-text-secondary mb-2 group-hover:text-dark-text-primary transition-colors uppercase tracking-wide">
          {title}
        </p>
        <h2 className={`text-4xl font-bold ${colors.text} glow-text mb-1`}>
          {value}
        </h2>
        {subtitle && (
          <p className="text-xs text-dark-text-muted mt-2 font-medium">{subtitle}</p>
        )}
        {trend && (
          <div
            className={`inline-flex items-center gap-1.5 mt-3 px-3 py-1.5 rounded-full text-xs font-bold backdrop-blur-sm animate-scale-in ${
              trend.isPositive
                ? 'bg-success/20 text-success-light border-2 border-success/30'
                : 'bg-danger/20 text-danger-light border-2 border-danger/30'
            }`}
          >
            <span className="text-base">{trend.isPositive ? '↑' : '↓'}</span>
            <span>{trend.value.toFixed(1)}%</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default KPICard;
