import React from 'react'

interface SOCRingProps {
  soc: number
  size?: number
  strokeWidth?: number
  showLabel?: boolean
}

export const SOCRing: React.FC<SOCRingProps> = ({ 
  soc, 
  size = 120, 
  strokeWidth = 12,
  showLabel = true 
}) => {
  const radius = (size - strokeWidth) / 2
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (soc / 100) * circumference

  const getColor = (soc: number) => {
    if (soc >= 80) return '#10b981' // green
    if (soc >= 50) return '#f59e0b' // yellow
    if (soc >= 20) return '#f97316' // orange
    return '#ef4444' // red
  }

  const color = getColor(soc)

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg width={size} height={size} className="transform -rotate-90">
        {/* Background circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="#e5e7eb"
          strokeWidth={strokeWidth}
          fill="none"
        />
        {/* Progress circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={color}
          strokeWidth={strokeWidth}
          fill="none"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className="transition-all duration-500 ease-out"
        />
      </svg>
      {showLabel && (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="text-center">
            <div className="text-2xl font-bold" style={{ color }}>
              {Math.round(soc)}%
            </div>
            <div className="text-xs text-gray-500">SOC</div>
          </div>
        </div>
      )}
    </div>
  )
}

