import React, { useState, useEffect, useContext } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import { TelemetryData } from '../types/telemetry'
import { ArrayContext } from '../ui/AppLayout'
import { useTheme } from '../contexts/ThemeContext'
import { ChevronLeft, Zap, Thermometer, Activity, Gauge } from 'lucide-react'
import { formatPower, formatVoltage, formatFrequency, formatCurrent } from '../utils/telemetry'

interface GridData {
  inverter_id: string
  array_id?: string
  grid_power_w?: number
  grid_l1_power_w?: number
  grid_l2_power_w?: number
  grid_l3_power_w?: number
  grid_l1_voltage_v?: number
  grid_l2_voltage_v?: number
  grid_l3_voltage_v?: number
  grid_l1_current_a?: number
  grid_l2_current_a?: number
  grid_l3_current_a?: number
  grid_frequency_hz?: number
  grid_import_energy_today_kwh?: number
  grid_export_energy_today_kwh?: number
  grid_import_energy_total_kwh?: number
  grid_export_energy_total_kwh?: number
  inverter_mode?: string
  inverter_temp_c?: number
}

export const GridDetailPage: React.FC = () => {
  const navigate = useNavigate()
  const { selectedArray } = useContext(ArrayContext)
  const { theme } = useTheme()
  const [inverters, setInverters] = useState<string[]>([])
  const [inverterMap, setInverterMap] = useState<Record<string, { id: string; name: string }>>({})
  const [gridData, setGridData] = useState<Record<string, GridData>>({})
  const [loading, setLoading] = useState(true)

  // Theme-aware colors
  const bgColor = theme === 'dark' ? '#111827' : '#f9fafb'
  const cardBg = theme === 'dark' ? '#1f2937' : '#ffffff'
  const borderColor = theme === 'dark' ? '#374151' : '#e5e7eb'
  const textColor = theme === 'dark' ? '#ffffff' : '#1f2937'
  const textSecondary = theme === 'dark' ? 'rgba(255, 255, 255, 0.7)' : '#6b7280'

  useEffect(() => {
    const fetchInverters = async () => {
      try {
        const response: any = await api.get('/api/inverters')
        if (response?.inverters) {
          const ids: string[] = []
          const map: Record<string, { id: string; name: string }> = {}
          
          if (Array.isArray(response.inverters)) {
            response.inverters.forEach((inv: any) => {
              if (typeof inv === 'string') {
                ids.push(inv)
                map[inv] = { id: inv, name: inv }
              } else {
                const id = inv.id || inv
                const name = inv.name || id
                ids.push(id)
                map[id] = { id, name }
              }
            })
          }
          
          setInverters(ids)
          setInverterMap(map)
        }
      } catch (error) {
        console.error('Error fetching inverters:', error)
      }
    }
    fetchInverters()
  }, [])

  useEffect(() => {
    const fetchGridData = async () => {
      try {
        setLoading(true)
        const data: Record<string, GridData> = {}
        
        for (const invId of inverters) {
          try {
            const response: any = await api.get(
              selectedArray
                ? `/api/now?inverter_id=${invId}&array_id=${selectedArray}`
                : `/api/now?inverter_id=${invId}`
            )
            if (response?.now) {
              data[invId] = {
                inverter_id: invId,
                array_id: response.now.array_id,
                grid_power_w: response.now.grid_power_w || 0,
                grid_l1_power_w: response.now.grid_l1_power_w || 0,
                grid_l2_power_w: response.now.grid_l2_power_w || 0,
                grid_l3_power_w: response.now.grid_l3_power_w || 0,
                grid_l1_voltage_v: response.now.grid_l1_voltage_v || 0,
                grid_l2_voltage_v: response.now.grid_l2_voltage_v || 0,
                grid_l3_voltage_v: response.now.grid_l3_voltage_v || 0,
                grid_l1_current_a: response.now.grid_l1_current_a || 0,
                grid_l2_current_a: response.now.grid_l2_current_a || 0,
                grid_l3_current_a: response.now.grid_l3_current_a || 0,
                grid_frequency_hz: response.now.grid_frequency_hz || 0,
                grid_import_energy_today_kwh: response.now.grid_import_energy_today_kwh || 0,
                grid_export_energy_today_kwh: response.now.grid_export_energy_today_kwh || 0,
                grid_import_energy_total_kwh: response.now.grid_import_energy_total_kwh || 0,
                grid_export_energy_total_kwh: response.now.grid_export_energy_total_kwh || 0,
                inverter_mode: response.now.inverter_mode || 'Unknown',
                inverter_temp_c: response.now.inverter_temp_c || 0,
              }
            }
          } catch (error) {
            console.error(`Error fetching grid data for inverter ${invId}:`, error)
          }
        }
        
        setGridData(data)
      } catch (error) {
        console.error('Error fetching grid data:', error)
      } finally {
        setLoading(false)
      }
    }

    if (inverters.length > 0) {
      fetchGridData()
      const interval = setInterval(fetchGridData, 5000)
      return () => clearInterval(interval)
    }
  }, [inverters, selectedArray])

  // Calculate totals
  const totalPower = Object.values(gridData).reduce((sum, data) => sum + (data.grid_power_w || 0), 0)
  const totalImportToday = Object.values(gridData).reduce((sum, data) => sum + (data.grid_import_energy_today_kwh || 0), 0)
  const totalExportToday = Object.values(gridData).reduce((sum, data) => sum + (data.grid_export_energy_today_kwh || 0), 0)
  const totalImportTotal = Object.values(gridData).reduce((sum, data) => sum + (data.grid_import_energy_total_kwh || 0), 0)
  const totalExportTotal = Object.values(gridData).reduce((sum, data) => sum + (data.grid_export_energy_total_kwh || 0), 0)

  const renderPhaseCard = (inverterId: string, phase: 'L1' | 'L2' | 'L3', data: GridData) => {
    const power = phase === 'L1' ? data.grid_l1_power_w : phase === 'L2' ? data.grid_l2_power_w : data.grid_l3_power_w
    const voltage = phase === 'L1' ? data.grid_l1_voltage_v : phase === 'L2' ? data.grid_l2_voltage_v : data.grid_l3_voltage_v
    const current = phase === 'L1' ? data.grid_l1_current_a : phase === 'L2' ? data.grid_l2_current_a : data.grid_l3_current_a
    const phaseColor = phase === 'L1' ? '#ef4444' : phase === 'L2' ? '#f59e0b' : '#3b82f6'
    const inverterName = inverterMap[inverterId]?.name || inverterId

    if (!power && !voltage && !current) return null

    return (
      <div
        key={`${inverterId}-${phase}`}
        className="rounded-lg p-4 sm:p-6 shadow-sm"
        style={{
          backgroundColor: cardBg,
          border: `2px solid ${phaseColor}`,
        }}
      >
        <div className="flex items-center mb-4">
          <div className="w-3 h-3 rounded-full mr-2" style={{ backgroundColor: phaseColor }}></div>
          <h3 className="text-lg font-semibold" style={{ color: textColor }}>
            {inverterName} / Phase {phase}
          </h3>
        </div>
        <div className="grid grid-cols-1 gap-4">
          <div>
            <label className="text-sm font-medium" style={{ color: textSecondary }}>Power</label>
            <div className="text-xl font-bold mt-1" style={{ color: textColor }}>
              {formatPower(power || 0)}
            </div>
          </div>
          <div>
            <label className="text-sm font-medium" style={{ color: textSecondary }}>Voltage</label>
            <div className="text-xl font-bold mt-1" style={{ color: textColor }}>
              {formatVoltage(voltage || 0)}
            </div>
          </div>
          <div>
            <label className="text-sm font-medium" style={{ color: textSecondary }}>Current</label>
            <div className="text-xl font-bold mt-1" style={{ color: textColor }}>
              {formatCurrent(current || 0)}
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (loading && Object.keys(gridData).length === 0) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ backgroundColor: bgColor }}>
        <div className="text-lg" style={{ color: textColor }}>Loading...</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen" style={{ backgroundColor: bgColor }}>
      {/* Header */}
      <div 
        className="border-b sticky top-0 z-10"
        style={{
          backgroundColor: cardBg,
          borderColor: borderColor
        }}
      >
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate(-1)}
              className="p-2 rounded-lg hover:bg-opacity-10 hover:bg-gray-500 transition-colors"
              style={{ color: textColor }}
            >
              <ChevronLeft className="w-6 h-6" />
            </button>
            <div>
              <div className="text-sm" style={{ color: textSecondary }}>
                Dashboard {'>'} Grid
              </div>
              <h1 className="text-2xl font-bold mt-1" style={{ color: textColor }}>
                Grid Details
              </h1>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-6 py-6">
        {/* Summary Card */}
        <div
          className="rounded-lg p-6 shadow-sm mb-6"
          style={{
            backgroundColor: cardBg,
            border: `1px solid ${borderColor}`,
          }}
        >
          <div className="flex items-center mb-4">
            <Gauge className="w-6 h-6 mr-3" style={{ color: '#00F17D' }} />
            <h2 className="text-xl font-semibold" style={{ color: textColor }}>Total Grid Summary</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
            <div>
              <label className="text-sm font-medium" style={{ color: textSecondary }}>Total Power</label>
              <div className="text-2xl font-bold mt-2" style={{ color: totalPower > 0 ? '#3b82f6' : '#a855f7' }}>
                {formatPower(totalPower)}
              </div>
            </div>
            <div>
              <label className="text-sm font-medium" style={{ color: textSecondary }}>Import Today</label>
              <div className="text-2xl font-bold mt-2" style={{ color: '#3b82f6' }}>
                {totalImportToday.toFixed(2)} kWh
              </div>
            </div>
            <div>
              <label className="text-sm font-medium" style={{ color: textSecondary }}>Export Today</label>
              <div className="text-2xl font-bold mt-2" style={{ color: '#a855f7' }}>
                {totalExportToday.toFixed(2)} kWh
              </div>
            </div>
            <div>
              <label className="text-sm font-medium" style={{ color: textSecondary }}>Total Import</label>
              <div className="text-2xl font-bold mt-2" style={{ color: textColor }}>
                {totalImportTotal.toFixed(2)} kWh
              </div>
            </div>
            <div>
              <label className="text-sm font-medium" style={{ color: textSecondary }}>Total Export</label>
              <div className="text-2xl font-bold mt-2" style={{ color: textColor }}>
                {totalExportTotal.toFixed(2)} kWh
              </div>
            </div>
          </div>
        </div>

        {/* Inverter Cards */}
        <div className="space-y-6">
          {Object.entries(gridData).map(([inverterId, data]) => {
            const hasThreePhase = data.grid_l1_power_w || data.grid_l2_power_w || data.grid_l3_power_w
            const avgVoltage = hasThreePhase
              ? ((data.grid_l1_voltage_v || 0) + (data.grid_l2_voltage_v || 0) + (data.grid_l3_voltage_v || 0)) / 3
              : data.grid_l1_voltage_v || 0
            const totalCurrent = hasThreePhase
              ? (data.grid_l1_current_a || 0) + (data.grid_l2_current_a || 0) + (data.grid_l3_current_a || 0)
              : data.grid_l1_current_a || 0
            const inverterName = inverterMap[inverterId]?.name || inverterId

            return (
              <div key={inverterId}>
                <div
                  className="rounded-lg p-6 shadow-sm mb-4"
                  style={{
                    backgroundColor: cardBg,
                    border: `1px solid ${borderColor}`,
                  }}
                >
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold" style={{ color: textColor }}>
                      {inverterName} - Summary {data.array_id ? `(Array: ${data.array_id})` : ''}
                    </h3>
                    <div className="flex items-center gap-4">
                      <div>
                        <label className="text-xs font-medium" style={{ color: textSecondary }}>Mode</label>
                        <div className="text-sm font-semibold mt-1" style={{ color: textColor }}>
                          {data.inverter_mode || 'Unknown'}
                        </div>
                      </div>
                      {data.inverter_temp_c !== undefined && (
                        <div>
                          <label className="text-xs font-medium" style={{ color: textSecondary }}>Temp</label>
                          <div className="text-sm font-semibold mt-1" style={{ color: textColor }}>
                            {data.inverter_temp_c.toFixed(1)}°C
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div>
                      <label className="text-sm font-medium" style={{ color: textSecondary }}>Total Power</label>
                      <div className="text-xl font-bold mt-1" style={{ color: data.grid_power_w && data.grid_power_w > 0 ? '#3b82f6' : '#a855f7' }}>
                        {formatPower(data.grid_power_w || 0)}
                      </div>
                    </div>
                    <div>
                      <label className="text-sm font-medium" style={{ color: textSecondary }}>Avg Voltage</label>
                      <div className="text-xl font-bold mt-1" style={{ color: textColor }}>
                        {formatVoltage(avgVoltage)}
                      </div>
                    </div>
                    <div>
                      <label className="text-sm font-medium" style={{ color: textSecondary }}>Total Current</label>
                      <div className="text-xl font-bold mt-1" style={{ color: textColor }}>
                        {formatCurrent(totalCurrent)}
                      </div>
                    </div>
                    <div>
                      <label className="text-sm font-medium" style={{ color: textSecondary }}>Frequency</label>
                      <div className="text-xl font-bold mt-1" style={{ color: textColor }}>
                        {formatFrequency(data.grid_frequency_hz || 0)}
                      </div>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4 mt-4 pt-4" style={{ borderTop: `1px solid ${borderColor}` }}>
                    <div>
                      <label className="text-sm font-medium" style={{ color: textSecondary }}>Import Today</label>
                      <div className="text-lg font-semibold mt-1" style={{ color: '#3b82f6' }}>
                        {(data.grid_import_energy_today_kwh || 0).toFixed(2)} kWh
                      </div>
                    </div>
                    <div>
                      <label className="text-sm font-medium" style={{ color: textSecondary }}>Export Today</label>
                      <div className="text-lg font-semibold mt-1" style={{ color: '#a855f7' }}>
                        {(data.grid_export_energy_today_kwh || 0).toFixed(2)} kWh
                      </div>
                    </div>
                  </div>
                </div>
                {hasThreePhase && (
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {renderPhaseCard(inverterId, 'L1', data)}
                    {renderPhaseCard(inverterId, 'L2', data)}
                    {renderPhaseCard(inverterId, 'L3', data)}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

