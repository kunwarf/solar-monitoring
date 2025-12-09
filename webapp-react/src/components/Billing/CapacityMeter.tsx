import React from 'react'
import { Card } from '../Card'

interface CapacityMeterProps {
  capacityStatus?: any
}

export const CapacityMeter: React.FC<CapacityMeterProps> = ({ capacityStatus }) => {
  if (!capacityStatus) {
    return (
      <Card className="p-6">
        <h2 className="text-xl font-bold text-white mb-4">Capacity Status</h2>
        <div className="text-gray-400 text-center py-8">No data available</div>
      </Card>
    )
  }

  const installedKw = capacityStatus.installed_kw || 0
  const requiredKw = capacityStatus.required_kw_for_zero_bill || 0
  const deficitKw = capacityStatus.deficit_kw || 0
  const status = capacityStatus.status || 'unknown'

  const percentage = requiredKw > 0 ? (installedKw / requiredKw) * 100 : 0
  const isOverCapacity = deficitKw < 0
  const isUnderCapacity = deficitKw > 0

  const statusColors = {
    'under-capacity': 'text-red-400',
    'over-capacity': 'text-green-400',
    'balanced': 'text-yellow-400',
    'unknown': 'text-gray-400'
  }

  const statusBgColors = {
    'under-capacity': 'bg-red-500/20',
    'over-capacity': 'bg-green-500/20',
    'balanced': 'bg-yellow-500/20',
    'unknown': 'bg-gray-500/20'
  }

  // Gauge visualization
  const gaugeAngle = Math.min(180, (percentage / 100) * 180)
  const gaugeColor = isOverCapacity ? '#10b981' : isUnderCapacity ? '#ef4444' : '#eab308'

  return (
    <Card className="p-6">
      <h2 className="text-xl font-bold text-white mb-4">Capacity Meter</h2>
      
      <div className="space-y-6">
        {/* Gauge */}
        <div className="flex justify-center">
          <div className="relative w-48 h-24">
            <svg viewBox="0 0 200 100" className="w-full h-full">
              {/* Background arc */}
              <path
                d="M 20 80 A 80 80 0 0 1 180 80"
                fill="none"
                stroke="#374151"
                strokeWidth="12"
              />
              {/* Value arc */}
              <path
                d="M 20 80 A 80 80 0 0 1 180 80"
                fill="none"
                stroke={gaugeColor}
                strokeWidth="12"
                strokeDasharray={`${(gaugeAngle / 180) * 251.2} 251.2`}
                strokeLinecap="round"
                transform="rotate(180 100 80)"
              />
              {/* Needle */}
              <line
                x1="100"
                y1="80"
                x2={100 + 70 * Math.cos((180 - gaugeAngle) * Math.PI / 180)}
                y2={80 - 70 * Math.sin((180 - gaugeAngle) * Math.PI / 180)}
                stroke={gaugeColor}
                strokeWidth="3"
                strokeLinecap="round"
              />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-center">
                <div className="text-2xl font-bold text-white">{percentage.toFixed(0)}%</div>
                <div className="text-xs text-gray-400">of required</div>
              </div>
            </div>
          </div>
        </div>

        {/* Metrics */}
        <div className="space-y-3">
          <div className="flex justify-between items-center">
            <span className="text-gray-400">Installed Capacity</span>
            <span className="text-white font-semibold">{installedKw.toFixed(1)} kW</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-gray-400">Required for Zero Bill</span>
            <span className="text-white font-semibold">{requiredKw.toFixed(1)} kW</span>
          </div>
          <div className="flex justify-between items-center pt-2 border-t border-gray-700">
            <span className="text-gray-400">Deficit/Surplus</span>
            <span className={`font-semibold ${isOverCapacity ? 'text-green-400' : isUnderCapacity ? 'text-red-400' : 'text-yellow-400'}`}>
              {isOverCapacity ? '+' : ''}{Math.abs(deficitKw).toFixed(1)} kW
            </span>
          </div>
        </div>

        {/* Status Badge */}
        <div className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-semibold ${statusBgColors[status as keyof typeof statusBgColors]} ${statusColors[status as keyof typeof statusColors]}`}>
          {status.replace('-', ' ').toUpperCase()}
        </div>
      </div>
    </Card>
  )
}

