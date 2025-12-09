import React from 'react'
import { TelemetryData } from '../types/telemetry'

interface MobileSummaryBarProps {
  telemetry: TelemetryData | null
  loading?: boolean
}

export const MobileSummaryBar: React.FC<MobileSummaryBarProps> = ({ telemetry, loading }) => {
  const formatPower = (watts?: number) => {
    if (!watts && watts !== 0) return '—'
    if (Math.abs(watts) >= 1000) return `${(watts / 1000).toFixed(1)}kW`
    return `${Math.round(watts)}W`
  }

  const formatSOC = (soc?: number) => {
    if (!soc && soc !== 0) return '—'
    return `${Math.round(soc)}%`
  }

  if (loading) {
    return (
      <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 shadow-lg z-50 md:hidden">
        <div className="px-3 py-2 grid grid-cols-4 gap-2">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="animate-pulse">
              <div className="h-3 bg-gray-200 rounded w-full mb-1"></div>
              <div className="h-4 bg-gray-200 rounded w-12"></div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 shadow-lg z-50 md:hidden">
      <div className="px-3 py-2 grid grid-cols-4 gap-2">
        {/* Solar */}
        <div className="text-center">
          <div className="text-xs text-gray-500 mb-0.5">☀️</div>
          <div className="text-sm font-bold text-yellow-600">{formatPower(telemetry?.pv_power_w)}</div>
        </div>

        {/* SOC */}
        <div className="text-center">
          <div className="text-xs text-gray-500 mb-0.5">🔋</div>
          <div className={`text-sm font-bold ${
            (telemetry?.batt_soc_pct || 0) >= 80 ? 'text-green-500' :
            (telemetry?.batt_soc_pct || 0) >= 50 ? 'text-yellow-500' :
            (telemetry?.batt_soc_pct || 0) >= 20 ? 'text-orange-500' : 'text-red-500'
          }`}>
            {formatSOC(telemetry?.batt_soc_pct)}
          </div>
        </div>

        {/* Load */}
        <div className="text-center">
          <div className="text-xs text-gray-500 mb-0.5">🏠</div>
          <div className="text-sm font-bold text-gray-700">{formatPower(telemetry?.load_power_w)}</div>
        </div>

        {/* Grid */}
        <div className="text-center">
          <div className="text-xs text-gray-500 mb-0.5">⚡</div>
          <div className={`text-sm font-bold ${
            (telemetry?.grid_power_w || 0) > 0 ? 'text-red-500' :
            (telemetry?.grid_power_w || 0) < 0 ? 'text-green-500' : 'text-gray-500'
          }`}>
            {formatPower(telemetry?.grid_power_w)}
          </div>
        </div>
      </div>
    </div>
  )
}

