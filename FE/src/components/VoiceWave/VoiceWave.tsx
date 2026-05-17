// Voice Wave Component - Animated Sound Bars

import React from 'react';

interface VoiceWaveProps {
  isActive?: boolean;
  color?: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const VoiceWave: React.FC<VoiceWaveProps> = ({
  isActive = true,
  color = 'currentColor',
  size = 'md',
  className = '',
}) => {
  const sizes = {
    sm: 'h-3',
    md: 'h-5',
    lg: 'h-7',
  };

  const barHeights = {
    sm: ['h-2', 'h-3', 'h-2.5', 'h-4', 'h-2'],
    md: ['h-3', 'h-5', 'h-4', 'h-6', 'h-3.5'],
    lg: ['h-5', 'h-7', 'h-6', 'h-9', 'h-5.5'],
  };

  return (
    <div className={`inline-flex items-center gap-0.5 ${sizes[size]} ${className}`}>
      {[...Array(5)].map((_, i) => (
        <div
          key={i}
          className={`w-0.5 bg-current rounded-full ${barHeights[size][i]} ${
            isActive ? 'voice-bar' : ''
          }`}
          style={{
            color,
            animationDelay: `${i * 0.1}s`,
          }}
        />
      ))}
    </div>
  );
};

export default VoiceWave;

