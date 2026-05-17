// Button Component - Awesome with Ripple Effect

import React from 'react';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  children: React.ReactNode;
  variant?: 'primary' | 'success' | 'warning' | 'danger' | 'secondary' | 'outline' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
}

const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  className = '',
  disabled,
  isLoading = false,
  ...props
}) => {
  const baseStyles = 'relative inline-flex items-center justify-center font-semibold rounded-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-dark-bg ripple overflow-hidden';
  
  const variants = {
    primary: 'bg-gradient-to-r from-primary to-primary-dark text-white hover:from-primary-light hover:to-primary shadow-md hover:shadow-glow-primary hover:scale-105 active:scale-100 focus:ring-primary gradient-shift',
    success: 'bg-gradient-to-r from-success to-success-dark text-white hover:from-success-light hover:to-success shadow-md hover:shadow-glow-success hover:scale-105 active:scale-100 focus:ring-success gradient-shift',
    warning: 'bg-gradient-to-r from-warning to-warning-dark text-white hover:from-warning-light hover:to-warning shadow-md hover:shadow-glow-warning hover:scale-105 active:scale-100 focus:ring-warning gradient-shift',
    danger: 'bg-gradient-to-r from-danger to-danger-dark text-white hover:from-danger-light hover:to-danger shadow-md hover:shadow-glow-danger hover:scale-105 active:scale-100 focus:ring-danger gradient-shift',
    secondary: 'bg-dark-elevated text-dark-text-primary hover:bg-dark-hover border-2 border-dark-border hover:border-primary/30 shadow-sm hover:shadow-md focus:ring-primary',
    outline: 'border-2 border-primary text-primary hover:bg-primary/10 hover:border-primary-light focus:ring-primary',
    ghost: 'text-dark-text-secondary hover:text-dark-text-primary hover:bg-dark-elevated',
  };
  
  const sizes = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-5 py-2.5 text-sm',
    lg: 'px-6 py-3 text-base',
  };

  return (
    <button
      className={`${baseStyles} ${variants[variant]} ${sizes[size]} ${className}`}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading ? (
        <>
          <svg className="animate-spin -ml-1 mr-2 h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          Loading...
        </>
      ) : (
        children
      )}
    </button>
  );
};

export default Button;
