import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import { useTheme } from '../contexts/ThemeContext'
import { ChevronLeft, Home, Zap, Gauge } from 'lucide-react'
import { formatPower, formatVoltage, formatCurrent, formatFrequency } from '../utils/telemetry'

interface LoadData {
  inverter_id: string
  load_power_w?: number
  load_l1_power_w?: number
  load_l2_power_w?: number
  load_l3_power_w?: number
  load_l1_voltage_v?: number
  load_l2_voltage_v?: number
  load_l3_voltage_v?: number
  load_l1_current_a?: number
  load_l2_current_a?: number
  load_l3_current_a?: number
  load_frequency_hz?: number
  load_energy_today_kwh?: number
  load_energy_total_kwh?: number
}

export const LoadDetailPage: React.FC = () => {
  const navigate = useNavigate()
  const { theme } = useTheme()
  const [inverters, setInverters] = useState<string[]>([])
  const [inverterMap, setInverterMap] = useState<Record<string, { id: string; name: string }>>({})
  const [loadData, setLoadData] = useState<Record<string, LoadData>>({})
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
    const fetchLoadData = async () => {
      try {
        setLoading(true)
        const data: Record<string, LoadData> = {}
        
        for (const invId of inverters) {
          try {
            const response: any = await api.get(`/api/now?inverter_id=${invId}`)
            if (response?.now) {
              data[invId] = {
                inverter_id: invId,
                load_power_w: response.now.load_power_w || 0,
                load_l1_power_w: response.now.load_l1_power_w || 0,
                load_l2_power_w: response.now.load_l2_power_w || 0,
                load_l3_power_w: response.now.load_l3_power_w || 0,
                load_l1_voltage_v: response.now.load_l1_voltage_v || 0,
                load_l2_voltage_v: response.now.load_l2_voltage_v || 0,
                load_l3_voltage_v: response.now.load_l3_voltage_v || 0,
                load_l1_current_a: response.now.load_l1_current_a || 0,
                load_l2_current_a: response.now.load_l2_current_a || 0,
                load_l3_current_a: response.now.load_l3_current_a || 0,
                load_frequency_hz: response.now.load_frequency_hz || 0,
                load_energy_today_kwh: response.now.load_energy_today_kwh || 0,
                load_energy_total_kwh: response.now.load_energy_total_kwh || 0,
              }
            }
          } catch (error) {
            console.error(`Error fetching load data for inverter ${invId}:`, error)
          }
        }
        
        setLoadData(data)
      } catch (error) {
        console.error('Error fetching load data:', error)
      } finally {
        setLoading(false)
      }
    }

    if (inverters.length > 0) {
      fetchLoadData()
      const interval = setInterval(fetchLoadData, 5000)
      return () => clearInterval(interval)
    }
  }, [inverters])

  const totalPower = Object.values(loadData).reduce((sum, data) => sum + (data.load_power_w || 0), 0)
  const totalEnergyToday = Object.values(loadData).reduce((sum, data) => sum + (data.load_energy_today_kwh || 0), 0)
  const totalEnergyTotal = Object.values(loadData).reduce((sum, data) => sum + (data.load_energy_total_kwh || 0), 0)

  const renderPhaseCard = (inverterId: string, phase: 'L1' | 'L2' | 'L3', data: LoadData) => {
    const power = phase === 'L1' ? data.load_l1_power_w : phase === 'L2' ? data.load_l2_power_w : data.load_l3_power_w
    const voltage = phase === 'L1' ? data.load_l1_voltage_v : phase === 'L2' ? data.load_l2_voltage_v : data.load_l3_voltage_v
    const current = phase === 'L1' ? data.load_l1_current_a : phase === 'L2' ? data.load_l2_current_a : data.load_l3_current_a
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

  if (loading && Object.keys(loadData).length === 0) {
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
            <Home className="w-6 h-6 mr-3" style={{ color: textColor }} />
            <h1 className="text-2xl font-bold" style={{ color: textColor }}>Load Details</h1>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Summary Card */}
        <div
          className="rounded-lg p-6 shadow-sm mb-6"
          style={{
            backgroundColor: cardBg,
            border: `1px solid ${borderColor}`,
          }}
        >
          <div className="flex items-center mb-4">
            <Gauge className="w-6 h-6 mr-3" style={{ color: textColor }} />
            <h2 className="text-xl font-semibold" style={{ color: textColor }}>Total Load Summary</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <label className="text-sm font-medium" style={{ color: textSecondary }}>Total Power</label>
              <div className="text-3xl font-bold mt-2" style={{ color: textColor }}>
                {formatPower(totalPower)}
              </div>
            </div>
            <div>
              <label className="text-sm font-medium" style={{ color: textSecondary }}>Energy Today</label>
              <div className="text-3xl font-bold mt-2" style={{ color: textColor }}>
                {totalEnergyToday.toFixed(2)} kWh
              </div>
            </div>
            <div>
              <label className="text-sm font-medium" style={{ color: textSecondary }}>Total Energy</label>
              <div className="text-3xl font-bold mt-2" style={{ color: textColor }}>
                {totalEnergyTotal.toFixed(2)} kWh
              </div>
            </div>
          </div>
        </div>

        {/* Inverter Cards */}
        <div className="space-y-6">
          {Object.entries(loadData).map(([inverterId, data]) => {
            const hasThreePhase = data.load_l1_power_w || data.load_l2_power_w || data.load_l3_power_w
            const avgVoltage = hasThreePhase
              ? ((data.load_l1_voltage_v || 0) + (data.load_l2_voltage_v || 0) + (data.load_l3_voltage_v || 0)) / 3
              : data.load_l1_voltage_v || 0
            const totalCurrent = hasThreePhase
              ? (data.load_l1_current_a || 0) + (data.load_l2_current_a || 0) + (data.load_l3_current_a || 0)
              : data.load_l1_current_a || 0
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
                  <h3 className="text-lg font-semibold mb-4" style={{ color: textColor }}>
                    {inverterName} - Summary
                  </h3>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div>
                      <label className="text-sm font-medium" style={{ color: textSecondary }}>Total Power</label>
                      <div className="text-xl font-bold mt-1" style={{ color: textColor }}>
                        {formatPower(data.load_power_w || 0)}
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
                        {formatFrequency(data.load_frequency_hz || 0)}
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

