import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import { useTheme } from '../contexts/ThemeContext'
import { ChevronLeft, Sun, Zap, Gauge } from 'lucide-react'
import { formatPower, formatVoltage, formatCurrent } from '../utils/telemetry'

interface SolarData {
  inverter_id: string
  array_id?: string
  pv_power_w?: number
  pv1_power_w?: number
  pv2_power_w?: number
  pv3_power_w?: number
  pv4_power_w?: number
  pv1_voltage_v?: number
  pv2_voltage_v?: number
  pv3_voltage_v?: number
  pv4_voltage_v?: number
  pv1_current_a?: number
  pv2_current_a?: number
  pv3_current_a?: number
  pv4_current_a?: number
  pv_energy_today_kwh?: number
  pv_energy_total_kwh?: number
}

export const SolarDetailPage: React.FC = () => {
  const navigate = useNavigate()
  const { theme } = useTheme()
  const [inverters, setInverters] = useState<string[]>([])
  const [solarData, setSolarData] = useState<Record<string, SolarData>>({})
  const [loading, setLoading] = useState(true)

  const bgColor = theme === 'dark' ? '#111827' : '#f9fafb'
  const cardBg = theme === 'dark' ? '#1f2937' : '#ffffff'
  const borderColor = theme === 'dark' ? '#374151' : '#e5e7eb'
  const textColor = theme === 'dark' ? '#ffffff' : '#1f2937'
  const textSecondary = theme === 'dark' ? 'rgba(255, 255, 255, 0.7)' : '#6b7280'

  // Fetch inverters list
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

  // Fetch solar data for all inverters
  useEffect(() => {
    const fetchSolarData = async () => {
      try {
        setLoading(true)
        const data: Record<string, SolarData> = {}
        
        // Fetch data for each inverter
        for (const invId of inverters) {
          try {
            const response: any = await api.get(`/api/now?inverter_id=${invId}`)
            if (response?.now) {
              data[invId] = {
                inverter_id: invId,
                array_id: response.now.array_id,
                pv_power_w: response.now.pv_power_w || 0,
                pv1_power_w: response.now.pv1_power_w || response.now.extra?.pv1_power_w || 0,
                pv2_power_w: response.now.pv2_power_w || response.now.extra?.pv2_power_w || 0,
                pv3_power_w: response.now.pv3_power_w || response.now.extra?.pv3_power_w || 0,
                pv4_power_w: response.now.pv4_power_w || response.now.extra?.pv4_power_w || 0,
                pv1_voltage_v: response.now.pv1_voltage_v || response.now.extra?.pv1_voltage_v || 0,
                pv2_voltage_v: response.now.pv2_voltage_v || response.now.extra?.pv2_voltage_v || 0,
                pv3_voltage_v: response.now.pv3_voltage_v || response.now.extra?.pv3_voltage_v || 0,
                pv4_voltage_v: response.now.pv4_voltage_v || response.now.extra?.pv4_voltage_v || 0,
                pv1_current_a: response.now.pv1_current_a || response.now.extra?.pv1_current_a || 0,
                pv2_current_a: response.now.pv2_current_a || response.now.extra?.pv2_current_a || 0,
                pv3_current_a: response.now.pv3_current_a || response.now.extra?.pv3_current_a || 0,
                pv4_current_a: response.now.pv4_current_a || response.now.extra?.pv4_current_a || 0,
                pv_energy_today_kwh: response.now.pv_energy_today_kwh || 0,
                pv_energy_total_kwh: response.now.pv_energy_total_kwh || 0,
              }
            }
          } catch (error) {
            console.error(`Error fetching data for inverter ${invId}:`, error)
          }
        }
        
        setSolarData(data)
      } catch (error) {
        console.error('Error fetching solar data:', error)
      } finally {
        setLoading(false)
      }
    }

    if (inverters.length > 0) {
      fetchSolarData()
      const interval = setInterval(fetchSolarData, 5000)
      return () => clearInterval(interval)
    }
  }, [inverters])

  // Calculate totals
  const totalPower = Object.values(solarData).reduce((sum, data) => sum + (data.pv_power_w || 0), 0)
  const totalEnergyToday = Object.values(solarData).reduce((sum, data) => sum + (data.pv_energy_today_kwh || 0), 0)
  const totalEnergyTotal = Object.values(solarData).reduce((sum, data) => sum + (data.pv_energy_total_kwh || 0), 0)

  const renderArrayCard = (inverterId: string, arrayNum: number, data: SolarData) => {
    const power = arrayNum === 1 ? data.pv1_power_w : arrayNum === 2 ? data.pv2_power_w : arrayNum === 3 ? data.pv3_power_w : data.pv4_power_w
    const voltage = arrayNum === 1 ? data.pv1_voltage_v : arrayNum === 2 ? data.pv2_voltage_v : arrayNum === 3 ? data.pv3_voltage_v : data.pv4_voltage_v
    const current = arrayNum === 1 ? data.pv1_current_a : arrayNum === 2 ? data.pv2_current_a : arrayNum === 3 ? data.pv3_current_a : data.pv4_current_a

    if (!power && !voltage && !current) return null

    return (
      <div
        key={`${inverterId}-array-${arrayNum}`}
        className="rounded-lg p-4 sm:p-6 shadow-sm"
        style={{
          backgroundColor: cardBg,
          border: `1px solid ${borderColor}`,
        }}
      >
        <div className="flex items-center mb-4">
          <Sun className="w-5 h-5 mr-2" style={{ color: '#FFD600' }} />
          <h3 className="text-lg font-semibold" style={{ color: textColor }}>
            {inverterId} / Array {arrayNum}
          </h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
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

  if (loading && Object.keys(solarData).length === 0) {
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
            <Sun className="w-6 h-6 mr-3" style={{ color: '#FFD600' }} />
            <h1 className="text-2xl font-bold" style={{ color: textColor }}>Solar Details</h1>
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
            <Gauge className="w-6 h-6 mr-3" style={{ color: '#FFD600' }} />
            <h2 className="text-xl font-semibold" style={{ color: textColor }}>Total Solar Summary</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <label className="text-sm font-medium" style={{ color: textSecondary }}>Total Power</label>
              <div className="text-3xl font-bold mt-2" style={{ color: '#FFD600' }}>
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
          {Object.entries(solarData).map(([inverterId, data]) => (
            <div key={inverterId}>
              <h3 className="text-lg font-semibold mb-4" style={{ color: textColor }}>
                {inverterId} {data.array_id ? `(Array: ${data.array_id})` : ''}
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {renderArrayCard(inverterId, 1, data)}
                {renderArrayCard(inverterId, 2, data)}
                {renderArrayCard(inverterId, 3, data)}
                {renderArrayCard(inverterId, 4, data)}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

