import React from 'react'
import { Card } from '../Card'

interface SolarLoadComparisonProps {
  trendData?: any[]
}

export const SolarLoadComparison: React.FC<SolarLoadComparisonProps> = ({ trendData }) => {
  if (!trendData || trendData.length === 0) {
    return (
      <Card className="p-6">
        <h2 className="text-xl font-bold text-white mb-4">Solar vs Load Comparison</h2>
        <div className="text-gray-400 text-center py-8">No data available</div>
      </Card>
    )
  }

  // Extract solar and load data (would need to be added to trend data from backend)
  const chartData = trendData.map(month => ({
    month: month.billingMonth || 'N/A',
    solar: month.solar_kwh || 0, // Would need to be added to API response
    load: month.load_kwh || 0    // Would need to be added to API response
  }))

  const maxValue = Math.max(
    ...chartData.flatMap(d => [d.solar, d.load]),
    1
  )

  return (
    <Card className="p-6">
      <h2 className="text-xl font-bold text-white mb-4">Solar vs Load Comparison</h2>
      
      <div className="space-y-4">
        {chartData.map((data, idx) => {
          const solarHeight = (data.solar / maxValue) * 100
          const loadHeight = (data.load / maxValue) * 100

          return (
            <div key={idx} className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-gray-400">{data.month}</span>
                <div className="flex gap-4 text-xs">
                  <span className="text-yellow-400">Solar: {data.solar.toFixed(1)} kWh</span>
                  <span className="text-blue-400">Load: {data.load.toFixed(1)} kWh</span>
                </div>
              </div>
              <div className="flex gap-2 h-12">
                {/* Solar bar */}
                <div className="flex-1 flex flex-col justify-end">
                  <div
                    className="bg-yellow-500 rounded-t transition-all"
                    style={{ height: `${Math.max(2, solarHeight)}%` }}
                    title={`Solar: ${data.solar.toFixed(1)} kWh`}
                  />
                </div>
                {/* Load bar */}
                <div className="flex-1 flex flex-col justify-end">
                  <div
                    className="bg-blue-500 rounded-t transition-all"
                    style={{ height: `${Math.max(2, loadHeight)}%` }}
                    title={`Load: ${data.load.toFixed(1)} kWh`}
                  />
                </div>
              </div>
            </div>
          )
        })}
      </div>

      <div className="flex justify-center gap-4 mt-4 text-xs">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-yellow-500 rounded" />
          <span className="text-gray-400">Solar Generation</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-blue-500 rounded" />
          <span className="text-gray-400">Load</span>
        </div>
      </div>
    </Card>
  )
}

