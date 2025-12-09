import React from 'react'

interface SOHRingProps {
  soh: number
  size?: number
  strokeWidth?: number
  showLabel?: boolean
}

export const SOHRing: React.FC<SOHRingProps> = ({ 
  soh, 
  size = 120, 
  strokeWidth = 12,
  showLabel = true 
}) => {
  const radius = (size - strokeWidth) / 2
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (soh / 100) * circumference

  const getColor = (soh: number) => {
    if (soh >= 80) return '#10b981' // green - Excellent
    if (soh >= 60) return '#f59e0b' // yellow - Good
    if (soh >= 40) return '#f97316' // orange - Fair
    return '#ef4444' // red - Poor
  }

  const getStatus = (soh: number) => {
    if (soh >= 80) return 'Excellent'
    if (soh >= 60) return 'Good'
    if (soh >= 40) return 'Fair'
    return 'Poor'
  }

  const color = getColor(soh)
  const status = getStatus(soh)

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
              {Math.round(soh)}%
            </div>
            <div className="text-xs text-gray-500">SOH</div>
            <div className="text-xs font-medium mt-1" style={{ color }}>
              {status}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

