import React from 'react'
import { ArrayInfo } from '../types/telemetry'

interface ArrayCardProps {
  array: ArrayInfo
  isSelected: boolean
  onClick: () => void
  totalPower?: number
}

export const ArrayCard: React.FC<ArrayCardProps> = ({ 
  array, 
  isSelected, 
  onClick,
  totalPower 
}) => {
  const formatPower = (watts?: number) => {
    if (!watts && watts !== 0) return '—'
    if (Math.abs(watts) >= 1000) return `${(watts / 1000).toFixed(1)} kW`
    return `${Math.round(watts)} W`
  }

  return (
    <div
      onClick={onClick}
      className={`
        relative p-4 rounded-xl border-2 cursor-pointer transition-all duration-200
        ${isSelected 
          ? 'border-blue-500 bg-blue-50 shadow-lg scale-105' 
          : 'border-gray-200 bg-white hover:border-blue-300 hover:shadow-md'
        }
      `}
    >
      {/* Selection indicator */}
      {isSelected && (
        <div className="absolute top-2 right-2 w-3 h-3 bg-blue-500 rounded-full"></div>
      )}

      {/* Array Name */}
      <div className="flex items-center justify-between mb-2">
        <h3 className="font-semibold text-gray-900 text-lg">{array.name || array.id}</h3>
        {totalPower !== undefined && (
          <span className="text-sm font-medium text-yellow-600">
            {formatPower(totalPower)}
          </span>
        )}
      </div>

      {/* Stats */}
      <div className="space-y-1 text-sm text-gray-600">
        <div className="flex items-center justify-between">
          <span className="flex items-center">
            <span className="mr-1">⚡</span>
            Inverters
          </span>
          <span className="font-medium">{array.inverter_count}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="flex items-center">
            <span className="mr-1">🔋</span>
            Packs
          </span>
          <span className="font-medium">{array.pack_count}</span>
        </div>
      </div>

      {/* Status badge */}
      <div className="mt-3 pt-3 border-t border-gray-200">
        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
          <span className="w-1.5 h-1.5 bg-green-500 rounded-full mr-1.5"></span>
          Active
        </span>
      </div>
    </div>
  )
}

