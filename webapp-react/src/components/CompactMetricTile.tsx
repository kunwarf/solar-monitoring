import React from 'react'

interface CompactMetricTileProps {
  label: string
  value: string | number
  unit?: string
  icon?: string
  color?: 'default' | 'green' | 'yellow' | 'red' | 'blue'
  size?: 'sm' | 'md'
}

export const CompactMetricTile: React.FC<CompactMetricTileProps> = ({
  label,
  value,
  unit,
  icon,
  color = 'default',
  size = 'sm'
}) => {
  const colorClasses = {
    default: 'text-gray-700',
    green: 'text-green-600',
    yellow: 'text-yellow-600',
    red: 'text-red-600',
    blue: 'text-blue-600',
  }

  const sizeClasses = {
    sm: 'text-xs',
    md: 'text-sm',
  }

  return (
    <div className="bg-white rounded-lg p-3 shadow-sm border border-gray-200">
      <div className="flex items-center justify-between mb-1">
        {icon && <span className="text-lg">{icon}</span>}
        <span className={`${sizeClasses[size]} font-semibold ${colorClasses[color]}`}>
          {value}{unit && <span className="text-gray-500 ml-0.5">{unit}</span>}
        </span>
      </div>
      <div className="text-xs text-gray-500 truncate">{label}</div>
    </div>
  )
}

