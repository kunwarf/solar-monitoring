import React from 'react'
import { TelemetryData } from '../types/telemetry'

interface SummaryBarProps {
  telemetry: TelemetryData | null
  loading?: boolean
}

export const SummaryBar: React.FC<SummaryBarProps> = ({ telemetry, loading }) => {
  const formatPower = (watts?: number) => {
    if (!watts && watts !== 0) return '—'
    if (Math.abs(watts) >= 1000) return `${(watts / 1000).toFixed(1)} kW`
    return `${Math.round(watts)} W`
  }

  const formatSOC = (soc?: number) => {
    if (!soc && soc !== 0) return '—'
    return `${Math.round(soc)}%`
  }

  const getGridColor = (power?: number) => {
    if (!power) return 'text-gray-500'
    if (power > 0) return 'text-red-500' // Import
    if (power < 0) return 'text-green-500' // Export
    return 'text-gray-500'
  }

  const getGridIcon = (power?: number) => {
    if (!power) return '⚡'
    if (power > 0) return '⬇️' // Import
    if (power < 0) return '⬆️' // Export
    return '⚡'
  }

  const getSOCColor = (soc?: number) => {
    if (!soc && soc !== 0) return 'text-gray-500'
    if (soc >= 80) return 'text-green-500'
    if (soc >= 50) return 'text-yellow-500'
    if (soc >= 20) return 'text-orange-500'
    return 'text-red-500'
  }

  if (loading) {
    return (
      <div className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="py-4 grid grid-cols-2 md:grid-cols-4 gap-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="animate-pulse">
                <div className="h-4 bg-gray-200 rounded w-20 mb-2"></div>
                <div className="h-8 bg-gray-200 rounded w-24"></div>
              </div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white border-b border-gray-200 shadow-sm sticky top-0 z-10">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="py-4 grid grid-cols-2 md:grid-cols-4 gap-4 md:gap-6">
          {/* Solar Generation */}
          <div className="flex items-center space-x-3">
            <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-yellow-100 flex items-center justify-center">
              <span className="text-2xl">☀️</span>
            </div>
            <div>
              <div className="text-xs text-gray-500 uppercase tracking-wide">Solar</div>
              <div className="text-xl font-bold text-yellow-600">
                {formatPower(telemetry?.pv_power_w)}
              </div>
            </div>
          </div>

          {/* Battery SOC */}
          <div className="flex items-center space-x-3">
            <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center">
              <span className="text-2xl">🔋</span>
            </div>
            <div>
              <div className="text-xs text-gray-500 uppercase tracking-wide">SOC</div>
              <div className={`text-xl font-bold ${getSOCColor(telemetry?.batt_soc_pct)}`}>
                {formatSOC(telemetry?.batt_soc_pct)}
              </div>
            </div>
          </div>

          {/* Load */}
          <div className="flex items-center space-x-3">
            <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-gray-100 flex items-center justify-center">
              <span className="text-2xl">🏠</span>
            </div>
            <div>
              <div className="text-xs text-gray-500 uppercase tracking-wide">Load</div>
              <div className="text-xl font-bold text-gray-700">
                {formatPower(telemetry?.load_power_w)}
              </div>
            </div>
          </div>

          {/* Grid */}
          <div className="flex items-center space-x-3">
            <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-gray-100 flex items-center justify-center">
              <span className="text-xl">{getGridIcon(telemetry?.grid_power_w)}</span>
            </div>
            <div>
              <div className="text-xs text-gray-500 uppercase tracking-wide">Grid</div>
              <div className={`text-xl font-bold ${getGridColor(telemetry?.grid_power_w)}`}>
                {formatPower(telemetry?.grid_power_w)}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

