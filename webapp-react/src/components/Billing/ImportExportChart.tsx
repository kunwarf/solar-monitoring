import React from 'react'
import { Card } from '../Card'

interface ImportExportChartProps {
  trendData?: any[]
}

export const ImportExportChart: React.FC<ImportExportChartProps> = ({ trendData }) => {
  if (!trendData || trendData.length === 0) {
    return (
      <Card className="p-6">
        <h2 className="text-xl font-bold text-white mb-4">Import vs Export</h2>
        <div className="text-gray-400 text-center py-8">No data available</div>
      </Card>
    )
  }

  const maxValue = Math.max(
    ...trendData.flatMap(m => [
      m.import_off_kwh || 0,
      m.import_peak_kwh || 0,
      m.export_off_kwh || 0,
      m.export_peak_kwh || 0
    ])
  )

  return (
    <Card className="p-6">
      <h2 className="text-xl font-bold text-white mb-4">Import vs Export by Month</h2>
      <div className="space-y-4">
        {trendData.map((month, idx) => {
          const importOff = month.import_off_kwh || 0
          const importPeak = month.import_peak_kwh || 0
          const exportOff = month.export_off_kwh || 0
          const exportPeak = month.export_peak_kwh || 0
          const totalImport = importOff + importPeak
          const totalExport = exportOff + exportPeak

          return (
            <div key={idx} className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-gray-400">{month.billingMonth || `Month ${idx + 1}`}</span>
                <div className="flex gap-4 text-xs">
                  <span className="text-red-400">Import: {totalImport.toFixed(1)} kWh</span>
                  <span className="text-green-400">Export: {totalExport.toFixed(1)} kWh</span>
                </div>
              </div>
              <div className="relative h-8 bg-gray-800 rounded overflow-hidden">
                {/* Stacked bars */}
                <div className="absolute inset-0 flex">
                  {/* Off-peak import */}
                  {importOff > 0 && (
                    <div
                      className="bg-red-600"
                      style={{ width: `${(importOff / maxValue) * 100}%` }}
                      title={`Off-peak import: ${importOff.toFixed(1)} kWh`}
                    />
                  )}
                  {/* Peak import */}
                  {importPeak > 0 && (
                    <div
                      className="bg-red-800"
                      style={{ width: `${(importPeak / maxValue) * 100}%` }}
                      title={`Peak import: ${importPeak.toFixed(1)} kWh`}
                    />
                  )}
                  {/* Off-peak export */}
                  {exportOff > 0 && (
                    <div
                      className="bg-green-600 ml-auto"
                      style={{ width: `${(exportOff / maxValue) * 100}%` }}
                      title={`Off-peak export: ${exportOff.toFixed(1)} kWh`}
                    />
                  )}
                  {/* Peak export */}
                  {exportPeak > 0 && (
                    <div
                      className="bg-green-800"
                      style={{ width: `${(exportPeak / maxValue) * 100}%` }}
                      title={`Peak export: ${exportPeak.toFixed(1)} kWh`}
                    />
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>
      <div className="flex justify-center gap-6 mt-4 text-xs">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-red-600 rounded" />
          <span className="text-gray-400">Off-Peak Import</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-red-800 rounded" />
          <span className="text-gray-400">Peak Import</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-green-600 rounded" />
          <span className="text-gray-400">Off-Peak Export</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-green-800 rounded" />
          <span className="text-gray-400">Peak Export</span>
        </div>
      </div>
    </Card>
  )
}

