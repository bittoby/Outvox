// Card Component - AWESOME Modern Card with Variants

import React from 'react';

interface CardProps {
  children: React.ReactNode;
  className?: string;
  title?: React.ReactNode;
  subtitle?: string;
  action?: React.ReactNode;
  noPadding?: boolean;
  variant?: 'default' | 'primary' | 'success' | 'warning' | 'danger' | 'info';
  style?: React.CSSProperties;
}

const Card: React.FC<CardProps> = ({
  children,
  className = '',
  title,
  subtitle,
  action,
  noPadding = false,
  variant = 'default',
  style,
}) => {
  const variantClasses = {
    default: 'bg-dark-surface border-dark-border hover:border-primary-light',
    primary: 'bg-gradient-to-br from-dark-surface to-dark-elevated border-primary/40 hover:border-primary/60',
    success: 'bg-gradient-to-br from-dark-surface to-dark-elevated border-success/40 hover:border-success/60',
    warning: 'bg-gradient-to-br from-dark-surface to-dark-elevated border-warning/40 hover:border-warning/60',
    danger: 'bg-gradient-to-br from-dark-surface to-dark-elevated border-danger/40 hover:border-danger/60',
    info: 'bg-gradient-to-br from-dark-surface to-dark-elevated border-info/40 hover:border-info/60',
  };

  return (
    <div 
      className={`${variantClasses[variant]} border-2 rounded-xl shadow-modern transition-all duration-300 hover:shadow-modern-lg card-glow animate-fade-in ${className}`}
      style={style}
    >
      {(title || subtitle || action) && (
        <div className="flex justify-between items-center px-6 py-4 border-b border-dark-border/70">
          <div className="flex-1">
            {title && (
              <h3 className="text-xl font-bold text-dark-text-primary">
                {title}
              </h3>
            )}
            {subtitle && (
              <p className="text-sm text-dark-text-secondary mt-1">{subtitle}</p>
            )}
          </div>
          {action && <div className="ml-4">{action}</div>}
        </div>
      )}
      <div className={noPadding ? '' : 'p-6'}>
        {children}
      </div>
    </div>
  );
};

export default Card;
