// Badge Component - Brighter Awesome Design

import React from 'react';

export type BadgeVariant = 'success' | 'warning' | 'error' | 'info' | 'primary' | 'neutral';
export type BadgeSize = 'sm' | 'md' | 'lg';

interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  size?: BadgeSize;
  dot?: boolean;
  className?: string;
}

const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'neutral',
  size = 'md',
  dot = false,
  className = '',
}) => {
  const variants = {
    primary: 'bg-primary/20 text-primary-light border-primary/40 shadow-sm',
    success: 'bg-success/20 text-success-light border-success/40 shadow-sm',
    warning: 'bg-warning/20 text-warning-light border-warning/40 shadow-sm',
    error: 'bg-danger/20 text-danger-light border-danger/40 shadow-sm',
    info: 'bg-info/20 text-info-light border-info/40 shadow-sm',
    neutral: 'bg-dark-elevated text-dark-text-secondary border-dark-border',
  };

  const sizes = {
    sm: 'text-xs px-2.5 py-0.5',
    md: 'text-sm px-3 py-1',
    lg: 'text-sm px-4 py-1.5',
  };

  const dotColors = {
    primary: 'bg-primary-light shadow-glow-primary',
    success: 'bg-success-light shadow-glow-success',
    warning: 'bg-warning-light shadow-glow-warning',
    error: 'bg-danger-light shadow-glow-danger',
    info: 'bg-info-light',
    neutral: 'bg-dark-text-muted',
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-semibold rounded-full border-2 transition-all duration-200 ${variants[variant]} ${sizes[size]} ${className}`}
    >
      {dot && (
        <span className={`w-2 h-2 rounded-full animate-pulse ${dotColors[variant]}`}></span>
      )}
      {children}
    </span>
  );
};

export default Badge;
