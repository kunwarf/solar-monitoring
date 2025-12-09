import React from 'react';

interface SemiCircularGaugeProps {
  value: number;
  maxValue: number;
  label: string;
  color: string;
  unit?: string;
}

export const SemiCircularGauge: React.FC<SemiCircularGaugeProps> = ({
  value,
  maxValue,
  label,
  color,
  unit = 'kW'
}) => {
  const percentage = Math.min((value / maxValue) * 100, 100);
  const angle = (percentage / 100) * 180; // 180 degrees for semi-circle
  
  // Create SVG path for the gauge
  const radius = 60;
  const centerX = 80;
  const centerY = 80;
  
  // Background arc (full semi-circle)
  const backgroundArc = `M ${centerX - radius} ${centerY} A ${radius} ${radius} 0 0 1 ${centerX + radius} ${centerY}`;
  
  // Value arc
  const startAngle = 180;
  const endAngle = 180 - angle;
  const startX = centerX + radius * Math.cos((startAngle * Math.PI) / 180);
  const startY = centerY + radius * Math.sin((startAngle * Math.PI) / 180);
  const endX = centerX + radius * Math.cos((endAngle * Math.PI) / 180);
  const endY = centerY + radius * Math.sin((endAngle * Math.PI) / 180);
  
  const valueArc = `M ${startX} ${startY} A ${radius} ${radius} 0 ${angle > 180 ? 1 : 0} 0 ${endX} ${endY}`;

  return (
    <div className="bg-gray-100 rounded-lg p-6 shadow-sm text-center">
      <div className="relative inline-block">
        <svg width="160" height="100" viewBox="0 0 160 100" className="mb-4">
          {/* Background arc */}
          <path
            d={backgroundArc}
            fill="none"
            stroke="#e5e7eb"
            strokeWidth="8"
            strokeLinecap="round"
          />
          
          {/* Value arc */}
          <path
            d={valueArc}
            fill="none"
            stroke={color}
            strokeWidth="8"
            strokeLinecap="round"
          />
        </svg>
        
        {/* Value text */}
        <div className="absolute bottom-0 left-1/2 transform -translate-x-1/2">
          <div className="text-2xl font-bold text-gray-900">
            {Math.abs(value).toFixed(2)} {unit}
          </div>
          <div className="text-sm text-gray-600">{label}</div>
        </div>
      </div>
    </div>
  );
};
