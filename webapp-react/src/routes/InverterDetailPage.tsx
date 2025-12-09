import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import { useTheme } from '../contexts/ThemeContext'
import { ChevronLeft, Zap, Sun, Battery, Home, Gauge } from 'lucide-react'
import { formatPower, formatVoltage, formatCurrent } from '../utils/telemetry'

interface InverterSummary {
  inverter_id: string
  array_id?: string
  // Solar
  pv_power_w?: number
  pv_energy_today_kwh?: number
  // Battery
  batt_power_w?: number
  batt_voltage_v?: number
  batt_current_a?: number
  batt_soc_pct?: number
  // Load
  load_power_w?: number
  load_energy_today_kwh?: number
  // Grid
  grid_power_w?: number
  grid_import_energy_today_kwh?: number
  grid_export_energy_today_kwh?: number
}

export const InverterDetailPage: React.FC = () => {
  const navigate = useNavigate()
  const { theme } = useTheme()
  const [inverters, setInverters] = useState<string[]>([])
  const [inverterData, setInverterData] = useState<Record<string, InverterSummary>>({})
  const [loading, setLoading] = useState(true)

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
          const ids: string[] = Array.isArray(response.inverters)
            ? response.inverters.map((inv: any) => typeof inv === 'string' ? inv : (inv.id || inv))
            : []
          setInverters(ids)
        }
      } catch (error) {
        console.error('Error fetching inverters:', error)
      }
    }
    fetchInverters()
  }, [])

  useEffect(() => {
    const fetchInverterData = async () => {
      try {
        setLoading(true)
        const data: Record<string, InverterSummary> = {}
        
        for (const invId of inverters) {
          try {
            const response: any = await api.get(`/api/now?inverter_id=${invId}`)
            if (response?.now) {
              data[invId] = {
                inverter_id: invId,
                array_id: response.now.array_id,
                // Solar
                pv_power_w: response.now.pv_power_w || 0,
                pv_energy_today_kwh: response.now.pv_energy_today_kwh || 0,
                // Battery
                batt_power_w: response.now.batt_power_w || 0,
                batt_voltage_v: response.now.batt_voltage_v || 0,
                batt_current_a: response.now.batt_current_a || 0,
                batt_soc_pct: response.now.batt_soc_pct || 0,
                // Load
                load_power_w: response.now.load_power_w || 0,
                load_energy_today_kwh: response.now.load_energy_today_kwh || 0,
                // Grid
                grid_power_w: response.now.grid_power_w || 0,
                grid_import_energy_today_kwh: response.now.grid_import_energy_today_kwh || 0,
                grid_export_energy_today_kwh: response.now.grid_export_energy_today_kwh || 0,
              }
            }
          } catch (error) {
            console.error(`Error fetching data for inverter ${invId}:`, error)
          }
        }
        
        setInverterData(data)
      } catch (error) {
        console.error('Error fetching inverter data:', error)
      } finally {
        setLoading(false)
      }
    }

    if (inverters.length > 0) {
      fetchInverterData()
      const interval = setInterval(fetchInverterData, 5000)
      return () => clearInterval(interval)
    }
  }, [inverters])

  if (loading && Object.keys(inverterData).length === 0) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ backgroundColor: bgColor }}>
        <div className="text-lg" style={{ color: textColor }}>Loading...</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen" style={{ backgroundColor: bgColor }}>
      <div
        className="border-b sticky top-0 z-10"
        style={{
          backgroundColor: cardBg,
          borderColor: borderColor,
        }}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center">
            <button
              onClick={() => navigate(-1)}
              className="mr-4 p-2 rounded-lg hover:opacity-80 transition-opacity"
              style={{ backgroundColor: bgColor }}
            >
              <ChevronLeft className="w-5 h-5" style={{ color: textColor }} />
            </button>
            <Zap className="w-6 h-6 mr-3" style={{ color: '#0F91FF' }} />
            <h1 className="text-2xl font-bold" style={{ color: textColor }}>Inverter Details</h1>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {Object.entries(inverterData).map(([inverterId, data]) => (
            <div
              key={inverterId}
              className="rounded-lg p-6 shadow-sm"
              style={{
                backgroundColor: cardBg,
                border: `1px solid ${borderColor}`,
              }}
            >
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-semibold" style={{ color: textColor }}>
                  {inverterId}
                </h2>
                {data.array_id && (
                  <span className="px-3 py-1 rounded-lg text-sm" style={{ backgroundColor: bgColor, color: textSecondary }}>
                    Array: {data.array_id}
                  </span>
                )}
              </div>

              {/* Solar Section */}
              <div className="mb-6 pb-6 border-b" style={{ borderColor: borderColor }}>
                <div className="flex items-center mb-4">
                  <Sun className="w-5 h-5 mr-2" style={{ color: '#FFD600' }} />
                  <h3 className="text-lg font-semibold" style={{ color: textColor }}>Solar</h3>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium" style={{ color: textSecondary }}>Power</label>
                    <div className="text-xl font-bold mt-1" style={{ color: '#FFD600' }}>
                      {formatPower(data.pv_power_w || 0)}
                    </div>
                  </div>
                  <div>
                    <label className="text-sm font-medium" style={{ color: textSecondary }}>Energy Today</label>
                    <div className="text-xl font-bold mt-1" style={{ color: textColor }}>
                      {(data.pv_energy_today_kwh || 0).toFixed(2)} kWh
                    </div>
                  </div>
                </div>
              </div>

              {/* Battery Section */}
              <div className="mb-6 pb-6 border-b" style={{ borderColor: borderColor }}>
                <div className="flex items-center mb-4">
                  <Battery className="w-5 h-5 mr-2" style={{ color: '#FF5F85' }} />
                  <h3 className="text-lg font-semibold" style={{ color: textColor }}>Battery</h3>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium" style={{ color: textSecondary }}>Power</label>
                    <div className="text-xl font-bold mt-1" style={{ color: data.batt_power_w && data.batt_power_w < 0 ? '#10b981' : '#ef4444' }}>
                      {formatPower(data.batt_power_w || 0)}
                    </div>
                  </div>
                  <div>
                    <label className="text-sm font-medium" style={{ color: textSecondary }}>SOC</label>
                    <div className="text-xl font-bold mt-1" style={{ color: textColor }}>
                      {(data.batt_soc_pct || 0).toFixed(1)}%
                    </div>
                  </div>
                  <div>
                    <label className="text-sm font-medium" style={{ color: textSecondary }}>Voltage</label>
                    <div className="text-xl font-bold mt-1" style={{ color: textColor }}>
                      {formatVoltage(data.batt_voltage_v || 0)}
                    </div>
                  </div>
                  <div>
                    <label className="text-sm font-medium" style={{ color: textSecondary }}>Current</label>
                    <div className="text-xl font-bold mt-1" style={{ color: textColor }}>
                      {formatCurrent(data.batt_current_a || 0)}
                    </div>
                  </div>
                </div>
              </div>

              {/* Load Section */}
              <div className="mb-6 pb-6 border-b" style={{ borderColor: borderColor }}>
                <div className="flex items-center mb-4">
                  <Home className="w-5 h-5 mr-2" style={{ color: textColor }} />
                  <h3 className="text-lg font-semibold" style={{ color: textColor }}>Load</h3>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium" style={{ color: textSecondary }}>Power</label>
                    <div className="text-xl font-bold mt-1" style={{ color: textColor }}>
                      {formatPower(data.load_power_w || 0)}
                    </div>
                  </div>
                  <div>
                    <label className="text-sm font-medium" style={{ color: textSecondary }}>Energy Today</label>
                    <div className="text-xl font-bold mt-1" style={{ color: textColor }}>
                      {(data.load_energy_today_kwh || 0).toFixed(2)} kWh
                    </div>
                  </div>
                </div>
              </div>

              {/* Grid Section */}
              <div>
                <div className="flex items-center mb-4">
                  <Zap className="w-5 h-5 mr-2" style={{ color: '#00F17D' }} />
                  <h3 className="text-lg font-semibold" style={{ color: textColor }}>Grid</h3>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium" style={{ color: textSecondary }}>Power</label>
                    <div className="text-xl font-bold mt-1" style={{ color: data.grid_power_w && data.grid_power_w > 0 ? '#3b82f6' : '#a855f7' }}>
                      {formatPower(data.grid_power_w || 0)}
                    </div>
                  </div>
                  <div>
                    <label className="text-sm font-medium" style={{ color: textSecondary }}>Import Today</label>
                    <div className="text-xl font-bold mt-1" style={{ color: '#3b82f6' }}>
                      {(data.grid_import_energy_today_kwh || 0).toFixed(2)} kWh
                    </div>
                  </div>
                  <div>
                    <label className="text-sm font-medium" style={{ color: textSecondary }}>Export Today</label>
                    <div className="text-xl font-bold mt-1" style={{ color: '#a855f7' }}>
                      {(data.grid_export_energy_today_kwh || 0).toFixed(2)} kWh
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

