import React from 'react'
import { Card } from '../Card'

interface ForecastCardProps {
  forecast?: any
}

export const ForecastCard: React.FC<ForecastCardProps> = ({ forecast }) => {
  if (!forecast) {
    return (
      <Card className="p-6">
        <h2 className="text-xl font-bold text-white mb-4">Next-Month Forecast</h2>
        <div className="text-gray-400 text-center py-8">No forecast available</div>
      </Card>
    )
  }

  const predictedImport = forecast.predicted_import_kwh || 0
  const predictedExport = forecast.predicted_export_kwh || 0
  const predictedBill = forecast.predicted_bill || 0
  const confidence = forecast.confidence || 0

  const confidenceColor = confidence >= 0.7 ? 'text-green-400' : confidence >= 0.5 ? 'text-yellow-400' : 'text-red-400'
  const confidenceLabel = confidence >= 0.7 ? 'High' : confidence >= 0.5 ? 'Medium' : 'Low'

  return (
    <Card className="p-6">
      <h2 className="text-xl font-bold text-white mb-4">Next-Month Forecast</h2>
      
      <div className="space-y-4">
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-gray-400">Predicted Import</span>
            <span className="text-white">{predictedImport.toFixed(1)} kWh</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-gray-400">Predicted Export</span>
            <span className="text-green-400">{predictedExport.toFixed(1)} kWh</span>
          </div>
        </div>

        <div className="pt-3 border-t border-gray-700">
          <div className="flex justify-between items-center mb-2">
            <span className="text-gray-400">Predicted Bill</span>
            <span className="text-xl font-bold text-white">PKR {predictedBill.toFixed(2)}</span>
          </div>
        </div>

        <div className="pt-3 border-t border-gray-700">
          <div className="flex justify-between items-center">
            <span className="text-gray-400">Confidence</span>
            <span className={`font-semibold ${confidenceColor}`}>
              {confidenceLabel} ({(confidence * 100).toFixed(0)}%)
            </span>
          </div>
          <div className="w-full bg-gray-700 rounded-full h-2 mt-2">
            <div
              className={`h-2 rounded-full ${confidence >= 0.7 ? 'bg-green-500' : confidence >= 0.5 ? 'bg-yellow-500' : 'bg-red-500'}`}
              style={{ width: `${confidence * 100}%` }}
            />
          </div>
        </div>
      </div>
    </Card>
  )
}

