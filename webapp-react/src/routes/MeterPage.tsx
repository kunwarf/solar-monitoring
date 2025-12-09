import React, { useEffect, useState } from 'react'
import { api } from '../lib/api'
import { useMobile } from '../hooks/useMobile'
import { useTheme } from '../contexts/ThemeContext'
import { Gauge, Copy, Check, Info, Zap, Activity, TrendingUp, TrendingDown, BarChart3, Calendar } from 'lucide-react'
import { formatPower, formatVoltage, formatCurrent, formatFrequency, formatEnergy } from '../utils/telemetry'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, LineChart, Line } from 'recharts'

interface MeterTelemetry {
  ts: string
  id: string
  grid_power_w?: number | null
  grid_voltage_v?: number | null
  grid_current_a?: number | null
  grid_frequency_hz?: number | null
  grid_import_wh?: number | null
  grid_export_wh?: number | null
  energy_kwh?: number | null
  power_factor?: number | null
  voltage_phase_a?: number | null
  voltage_phase_b?: number | null
  voltage_phase_c?: number | null
  current_phase_a?: number | null
  current_phase_b?: number | null
  current_phase_c?: number | null
  power_phase_a?: number | null
  power_phase_b?: number | null
  power_phase_c?: number | null
  array_id?: string | null
  extra?: Record<string, any>
}

interface MeterResponse {
  status: string
  meter?: MeterTelemetry
  error?: string
}

export const MeterPage: React.FC = () => {
  const { isMobile, isCompact } = useMobile()
  const { theme } = useTheme()
  const [meter, setMeter] = useState<MeterTelemetry | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedMeter, setSelectedMeter] = useState<string>('all')
  const [meters, setMeters] = useState<string[]>([])
  const [copiedId, setCopiedId] = useState(false)
  const [activeTab, setActiveTab] = useState<'current' | 'summary' | 'comparison'>('current')
  
  // Summary state
  const [summaryPeriod, setSummaryPeriod] = useState<'today' | 'yesterday' | 'week' | 'this_month' | 'last_month' | 'this_year' | 'last_year' | 'custom'>('today')
  const [summaryData, setSummaryData] = useState<any>(null)
  const [summaryLoading, setSummaryLoading] = useState(false)
  const [customStartDate, setCustomStartDate] = useState('')
  const [customEndDate, setCustomEndDate] = useState('')
  
  // Comparison state
  const [comparisonData, setComparisonData] = useState<any>(null)
  const [comparisonLoading, setComparisonLoading] = useState(false)

  // Theme-aware colors
  const textColor = theme === 'dark' ? '#FFFFFF' : '#1B2234'
  const boxShadowColor = theme === 'dark' 
    ? 'rgba(0, 0, 0, 0.08)' 
    : 'rgba(0, 0, 0, 0.1)'
  const cardBackgroundColor = theme === 'dark' 
    ? 'rgba(255, 255, 255, 0.08)' 
    : 'rgba(255, 255, 255, 1)'
  const secondaryTextColor = theme === 'dark' ? 'rgba(255, 255, 255, 0.7)' : 'rgba(27, 34, 52, 0.7)'
  const borderColor = theme === 'dark' ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)'
  const metricBgColor = theme === 'dark' ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.02)'
  const pageBackgroundColor = theme === 'dark' ? '#1B2234' : '#F9FAFB'

  const fetchMeters = async () => {
    try {
      // Fetch list of available meters
      const metersRes = await api.get('/api/meters') as any
      if (metersRes && metersRes.meters && Array.isArray(metersRes.meters)) {
        setMeters(metersRes.meters)
        if (metersRes.meters.length > 0 && selectedMeter === 'all') {
          setSelectedMeter(metersRes.meters[0])
        }
      }
    } catch (e) {
      console.error('Error fetching meters list:', e)
      // Default to 'all' if API fails
      setMeters(['all'])
    }
  }

  const fetchMeter = async () => {
    try {
      setError(null)
      const meterParam = selectedMeter === 'all' ? 'all' : selectedMeter
      const res = await api.get(`/api/meter/now?meter_id=${meterParam}`) as MeterResponse
      if (res && res.status === 'ok' && res.meter) {
        setMeter(res.meter)
        setError(null)
      } else {
        setError(res.error || 'No meter data')
      }
    } catch (e: any) {
      setError(e?.message || 'Failed to load meter data')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchMeters()
  }, [])

  useEffect(() => {
    if (meters.length > 0) {
      fetchMeter()
      const t = setInterval(fetchMeter, 5000)
      return () => clearInterval(t)
    }
  }, [selectedMeter, meters])
  
  const fetchSummary = async () => {
    if (!selectedMeter || selectedMeter === 'all') return
    setSummaryLoading(true)
    try {
      const params = new URLSearchParams({
        period: summaryPeriod,
        group_by: 'day'
      })
      if (summaryPeriod === 'custom' && customStartDate && customEndDate) {
        params.append('start_date', customStartDate)
        params.append('end_date', customEndDate)
      }
      const res = await api.get(`/api/meter/${selectedMeter}/summary?${params}`) as any
      if (res && res.status === 'ok') {
        setSummaryData(res)
      }
    } catch (e: any) {
      console.error('Error fetching summary:', e)
    } finally {
      setSummaryLoading(false)
    }
  }
  
  const fetchComparison = async () => {
    if (!selectedMeter || selectedMeter === 'all') return
    setComparisonLoading(true)
    try {
      const res = await api.get(`/api/meter/${selectedMeter}/comparison?months=12`) as any
      if (res && res.status === 'ok') {
        setComparisonData(res)
      }
    } catch (e: any) {
      console.error('Error fetching comparison:', e)
    } finally {
      setComparisonLoading(false)
    }
  }
  
  useEffect(() => {
    if (activeTab === 'summary' && selectedMeter && selectedMeter !== 'all') {
      fetchSummary()
    }
  }, [activeTab, selectedMeter, summaryPeriod, customStartDate, customEndDate])
  
  useEffect(() => {
    if (activeTab === 'comparison' && selectedMeter && selectedMeter !== 'all') {
      fetchComparison()
    }
  }, [activeTab, selectedMeter])

  const copyMeterId = async () => {
    if (meter?.id) {
      await navigator.clipboard.writeText(meter.id)
      setCopiedId(true)
      setTimeout(() => setCopiedId(false), 2000)
    }
  }

  const isThreePhase = meter && (
    (meter.voltage_phase_a !== null && meter.voltage_phase_a !== undefined) ||
    (meter.voltage_phase_b !== null && meter.voltage_phase_b !== undefined) ||
    (meter.voltage_phase_c !== null && meter.voltage_phase_c !== undefined)
  )

  const formatValue = (value: number | null | undefined, formatter: (v: number) => string, defaultText: string = 'N/A'): string => {
    if (value === null || value === undefined) return defaultText
    return formatter(value)
  }

  const getPowerDirection = (power?: number | null) => {
    if (power === null || power === undefined) return null
    if (power > 0) return 'import'
    if (power < 0) return 'export'
    return 'idle'
  }

  const powerDirection = getPowerDirection(meter?.grid_power_w)
  const powerColor = powerDirection === 'import' ? '#ef4444' : powerDirection === 'export' ? '#10b981' : secondaryTextColor

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen" style={{ backgroundColor: pageBackgroundColor }}>
        <div className="text-lg" style={{ color: textColor }}>Loading meter data...</div>
      </div>
    )
  }

  if (error || !meter) {
    return (
      <div className="flex items-center justify-center min-h-screen" style={{ backgroundColor: pageBackgroundColor }}>
        <div className="text-lg" style={{ color: textColor }}>{error || 'No meter data available'}</div>
      </div>
    )
  }

  const extra = meter.extra || {}
  const meterId = meter.id || 'N/A'
  const arrayId = meter.array_id || 'N/A'

  const greenBg = theme === 'dark' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(220, 252, 231, 1)'
  const blueBg = theme === 'dark' ? 'rgba(59, 130, 246, 0.2)' : 'rgba(219, 234, 254, 1)'
  const orangeBg = theme === 'dark' ? 'rgba(249, 115, 22, 0.2)' : 'rgba(255, 237, 213, 1)'
  const redBg = theme === 'dark' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(254, 226, 226, 1)'
  const purpleBg = theme === 'dark' ? 'rgba(168, 85, 247, 0.2)' : 'rgba(233, 213, 255, 1)'
  const indigoBg = theme === 'dark' ? 'rgba(99, 102, 241, 0.2)' : 'rgba(224, 231, 255, 1)'

  return (
    <div className="min-h-screen overflow-x-hidden p-2 sm:p-4 md:p-6" style={{ backgroundColor: pageBackgroundColor }}>
      {/* Header */}
      <div 
        className="mb-4 shadow-sm border-b p-3 sm:p-4 rounded-lg"
        style={{
          backgroundColor: cardBackgroundColor,
          boxShadow: `0px 4px 40px ${boxShadowColor}`,
          borderColor: borderColor,
        }}
      >
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center">
            <Gauge className="w-6 h-6 mr-2" style={{ color: textColor }} />
            <h1 className="text-xl sm:text-2xl font-bold" style={{ color: textColor }}>Energy Meter</h1>
          </div>
          <div className="flex items-center gap-2">
            {meters.length > 1 && (
              <select
                value={selectedMeter}
                onChange={(e) => setSelectedMeter(e.target.value)}
                className="px-3 py-2 rounded-lg text-sm"
                style={{
                  backgroundColor: metricBgColor,
                  color: textColor,
                  borderColor: borderColor,
                  borderWidth: '1px',
                }}
              >
                {meters.map((m) => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
            )}
          </div>
        </div>
        
        {/* Tabs */}
        <div className="flex gap-2 mt-4 border-b" style={{ borderColor: borderColor }}>
          <button
            onClick={() => setActiveTab('current')}
            className={`px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === 'current' ? 'border-b-2' : 'opacity-70 hover:opacity-100'
            }`}
            style={{
              color: activeTab === 'current' ? textColor : secondaryTextColor,
              borderBottomColor: activeTab === 'current' ? '#3b82f6' : 'transparent',
            }}
          >
            Current
          </button>
          <button
            onClick={() => setActiveTab('summary')}
            className={`px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === 'summary' ? 'border-b-2' : 'opacity-70 hover:opacity-100'
            }`}
            style={{
              color: activeTab === 'summary' ? textColor : secondaryTextColor,
              borderBottomColor: activeTab === 'summary' ? '#3b82f6' : 'transparent',
            }}
          >
            <Calendar className="w-4 h-4 inline mr-1" />
            Summary
          </button>
          <button
            onClick={() => setActiveTab('comparison')}
            className={`px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === 'comparison' ? 'border-b-2' : 'opacity-70 hover:opacity-100'
            }`}
            style={{
              color: activeTab === 'comparison' ? textColor : secondaryTextColor,
              borderBottomColor: activeTab === 'comparison' ? '#3b82f6' : 'transparent',
            }}
          >
            <BarChart3 className="w-4 h-4 inline mr-1" />
            Comparison
          </button>
        </div>
      </div>
      
      {/* Tab Content */}
      {activeTab === 'current' && (
        <>

      {/* Device Information Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        <div 
          className="rounded-lg p-4 sm:p-6 shadow-sm"
          style={{
            backgroundColor: cardBackgroundColor,
            boxShadow: `0px 4px 40px ${boxShadowColor}`,
            borderColor: borderColor,
            borderWidth: '1px',
            borderStyle: 'solid',
          }}
        >
          <div className="flex items-center mb-4">
            <Info className="w-5 h-5 mr-2" style={{ color: textColor }} />
            <h2 className="text-lg sm:text-xl font-semibold" style={{ color: textColor }}>Device Information</h2>
          </div>
          
          <div className="space-y-3">
            <div>
              <label className="text-xs sm:text-sm font-medium" style={{ color: secondaryTextColor }}>Meter ID</label>
              <div className="flex items-center mt-1">
                <span className="text-base sm:text-lg font-bold flex-1" style={{ color: textColor }}>{meterId}</span>
                <button
                  onClick={copyMeterId}
                  className="ml-2 p-1.5 rounded-lg hover:opacity-80 transition-opacity"
                  style={{ backgroundColor: metricBgColor }}
                  title="Copy meter ID"
                >
                  {copiedId ? (
                    <Check className="w-4 h-4" style={{ color: '#10b981' }} />
                  ) : (
                    <Copy className="w-4 h-4" style={{ color: textColor }} />
                  )}
                </button>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs sm:text-sm font-medium" style={{ color: secondaryTextColor }}>Array ID</label>
                <div className="mt-1 px-2 py-1 rounded-lg inline-block" style={{ backgroundColor: blueBg }}>
                  <span className="text-sm font-semibold" style={{ color: textColor }}>{arrayId}</span>
                </div>
              </div>
              <div>
                <label className="text-xs sm:text-sm font-medium" style={{ color: secondaryTextColor }}>Last Update</label>
                <div className="mt-1 text-sm" style={{ color: textColor }}>
                  {meter.ts ? new Date(meter.ts).toLocaleString() : 'N/A'}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Grid Overview Card */}
        <div 
          className="rounded-lg p-4 sm:p-6 shadow-sm"
          style={{
            backgroundColor: cardBackgroundColor,
            boxShadow: `0px 4px 40px ${boxShadowColor}`,
            borderColor: borderColor,
            borderWidth: '1px',
            borderStyle: 'solid',
          }}
        >
          <div className="flex items-center mb-4">
            <Zap className="w-5 h-5 mr-2" style={{ color: textColor }} />
            <h2 className="text-lg sm:text-xl font-semibold" style={{ color: textColor }}>Grid Overview</h2>
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs sm:text-sm font-medium" style={{ color: secondaryTextColor }}>Power</label>
              <div className="mt-1 flex items-center">
                <span className="text-lg sm:text-xl font-bold" style={{ color: powerColor }}>
                  {formatValue(meter.grid_power_w, formatPower)}
                </span>
                {powerDirection === 'import' && <TrendingDown className="w-4 h-4 ml-1" style={{ color: powerColor }} />}
                {powerDirection === 'export' && <TrendingUp className="w-4 h-4 ml-1" style={{ color: powerColor }} />}
              </div>
              <div className="text-xs mt-1" style={{ color: secondaryTextColor }}>
                {powerDirection === 'import' ? 'Importing from grid' : powerDirection === 'export' ? 'Exporting to grid' : 'Idle'}
              </div>
            </div>
            <div>
              <label className="text-xs sm:text-sm font-medium" style={{ color: secondaryTextColor }}>Voltage</label>
              <div className="mt-1 text-lg sm:text-xl font-bold" style={{ color: textColor }}>
                {formatValue(meter.grid_voltage_v, formatVoltage)}
              </div>
            </div>
            <div>
              <label className="text-xs sm:text-sm font-medium" style={{ color: secondaryTextColor }}>Current</label>
              <div className="mt-1 text-lg sm:text-xl font-bold" style={{ color: textColor }}>
                {formatValue(meter.grid_current_a, formatCurrent)}
              </div>
            </div>
            <div>
              <label className="text-xs sm:text-sm font-medium" style={{ color: secondaryTextColor }}>Frequency</label>
              <div className="mt-1 text-lg sm:text-xl font-bold" style={{ color: textColor }}>
                {formatValue(meter.grid_frequency_hz, formatFrequency)}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Phase Data Section (always show if phase data exists) - Compact Design */}
      {(isThreePhase || meter.voltage_phase_a || meter.voltage_phase_b || meter.voltage_phase_c) && (
        <div 
          className="rounded-lg p-4 sm:p-6 shadow-sm mb-4"
          style={{
            backgroundColor: cardBackgroundColor,
            boxShadow: `0px 4px 40px ${boxShadowColor}`,
            borderColor: borderColor,
            borderWidth: '1px',
            borderStyle: 'solid',
          }}
        >
          <div className="flex items-center mb-4">
            <Activity className="w-5 h-5 mr-2" style={{ color: textColor }} />
            <h2 className="text-lg sm:text-xl font-semibold" style={{ color: textColor }}>Three-Phase Data</h2>
          </div>
          
          <div className="space-y-3">
            {/* Phase A - Compact Line */}
            {meter.voltage_phase_a !== null && meter.voltage_phase_a !== undefined && (
              <div className="mb-1.5 last:mb-0">
                <div className="flex items-center gap-2 mb-0.5">
                  <div className="text-xs font-medium" style={{ color: textColor, minWidth: '80px' }}>
                    Phase A (L1)
                  </div>
                  <div className="w-2 h-2 rounded-full" style={{ backgroundColor: '#ef4444' }}></div>
                </div>
                <div className="grid grid-cols-4 gap-2 text-xs pl-2">
                  <div>
                    <span style={{ color: secondaryTextColor }}>Voltage: </span>
                    <span style={{ color: textColor }}>{formatValue(meter.voltage_phase_a, formatVoltage)}</span>
                  </div>
                  <div>
                    <span style={{ color: secondaryTextColor }}>Current: </span>
                    <span style={{ color: textColor }}>{formatValue(meter.current_phase_a, formatCurrent)}</span>
                  </div>
                  <div>
                    <span style={{ color: secondaryTextColor }}>Power: </span>
                    <span style={{ color: textColor }}>{formatValue(meter.power_phase_a, formatPower)}</span>
                  </div>
                  <div>
                    <span style={{ color: secondaryTextColor }}>Freq: </span>
                    <span style={{ color: textColor }}>{formatValue(meter.grid_frequency_hz, formatFrequency)}</span>
                  </div>
                </div>
              </div>
            )}

            {/* Phase B - Compact Line */}
            {meter.voltage_phase_b !== null && meter.voltage_phase_b !== undefined && (
              <div className="mb-1.5 last:mb-0">
                <div className="flex items-center gap-2 mb-0.5">
                  <div className="text-xs font-medium" style={{ color: textColor, minWidth: '80px' }}>
                    Phase B (L2)
                  </div>
                  <div className="w-2 h-2 rounded-full" style={{ backgroundColor: '#f59e0b' }}></div>
                </div>
                <div className="grid grid-cols-4 gap-2 text-xs pl-2">
                  <div>
                    <span style={{ color: secondaryTextColor }}>Voltage: </span>
                    <span style={{ color: textColor }}>{formatValue(meter.voltage_phase_b, formatVoltage)}</span>
                  </div>
                  <div>
                    <span style={{ color: secondaryTextColor }}>Current: </span>
                    <span style={{ color: textColor }}>{formatValue(meter.current_phase_b, formatCurrent)}</span>
                  </div>
                  <div>
                    <span style={{ color: secondaryTextColor }}>Power: </span>
                    <span style={{ color: textColor }}>{formatValue(meter.power_phase_b, formatPower)}</span>
                  </div>
                  <div>
                    <span style={{ color: secondaryTextColor }}>Freq: </span>
                    <span style={{ color: textColor }}>{formatValue(meter.grid_frequency_hz, formatFrequency)}</span>
                  </div>
                </div>
              </div>
            )}

            {/* Phase C - Compact Line */}
            {meter.voltage_phase_c !== null && meter.voltage_phase_c !== undefined && (
              <div className="mb-1.5 last:mb-0">
                <div className="flex items-center gap-2 mb-0.5">
                  <div className="text-xs font-medium" style={{ color: textColor, minWidth: '80px' }}>
                    Phase C (L3)
                  </div>
                  <div className="w-2 h-2 rounded-full" style={{ backgroundColor: '#3b82f6' }}></div>
                </div>
                <div className="grid grid-cols-4 gap-2 text-xs pl-2">
                  <div>
                    <span style={{ color: secondaryTextColor }}>Voltage: </span>
                    <span style={{ color: textColor }}>{formatValue(meter.voltage_phase_c, formatVoltage)}</span>
                  </div>
                  <div>
                    <span style={{ color: secondaryTextColor }}>Current: </span>
                    <span style={{ color: textColor }}>{formatValue(meter.current_phase_c, formatCurrent)}</span>
                  </div>
                  <div>
                    <span style={{ color: secondaryTextColor }}>Power: </span>
                    <span style={{ color: textColor }}>{formatValue(meter.power_phase_c, formatPower)}</span>
                  </div>
                  <div>
                    <span style={{ color: secondaryTextColor }}>Freq: </span>
                    <span style={{ color: textColor }}>{formatValue(meter.grid_frequency_hz, formatFrequency)}</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Energy Data Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        <div 
          className="rounded-lg p-4 sm:p-6 shadow-sm"
          style={{
            backgroundColor: cardBackgroundColor,
            boxShadow: `0px 4px 40px ${boxShadowColor}`,
            borderColor: borderColor,
            borderWidth: '1px',
            borderStyle: 'solid',
          }}
        >
          <div className="flex items-center mb-4">
            <TrendingUp className="w-5 h-5 mr-2" style={{ color: textColor }} />
            <h2 className="text-lg sm:text-xl font-semibold" style={{ color: textColor }}>Energy Data</h2>
          </div>
          
          <div className="space-y-4">
            <div>
              <label className="text-xs sm:text-sm font-medium" style={{ color: secondaryTextColor }}>Total Energy</label>
              <div className="mt-1 text-lg sm:text-xl font-bold" style={{ color: textColor }}>
                {formatValue(meter.energy_kwh, (v) => `${v.toFixed(2)} kWh`)}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="rounded-lg p-3" style={{ backgroundColor: redBg }}>
                <label className="text-xs font-medium" style={{ color: textColor }}>Import Energy</label>
                <div className="mt-1 text-base font-bold" style={{ color: textColor }}>
                  {formatValue(meter.grid_import_wh, (v) => formatEnergy(v / 1000))}
                </div>
              </div>
              <div className="rounded-lg p-3" style={{ backgroundColor: greenBg }}>
                <label className="text-xs font-medium" style={{ color: textColor }}>Export Energy</label>
                <div className="mt-1 text-base font-bold" style={{ color: textColor }}>
                  {formatValue(meter.grid_export_wh, (v) => formatEnergy(v / 1000))}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Power Factor Section */}
        <div 
          className="rounded-lg p-4 sm:p-6 shadow-sm"
          style={{
            backgroundColor: cardBackgroundColor,
            boxShadow: `0px 4px 40px ${boxShadowColor}`,
            borderColor: borderColor,
            borderWidth: '1px',
            borderStyle: 'solid',
          }}
        >
          <div className="flex items-center mb-4">
            <Gauge className="w-5 h-5 mr-2" style={{ color: textColor }} />
            <h2 className="text-lg sm:text-xl font-semibold" style={{ color: textColor }}>Power Quality</h2>
          </div>
          
          <div className="space-y-4">
            <div>
              <label className="text-xs sm:text-sm font-medium" style={{ color: secondaryTextColor }}>Power Factor</label>
              <div className="mt-1 text-lg sm:text-xl font-bold" style={{ color: textColor }}>
                {formatValue(meter.power_factor, (v) => v.toFixed(3))}
              </div>
            </div>
            {meter.power_factor !== null && meter.power_factor !== undefined && (
              <div className="w-full bg-gray-200 rounded-full h-2.5" style={{ backgroundColor: metricBgColor }}>
                <div 
                  className="h-2.5 rounded-full transition-all"
                  style={{
                    width: `${Math.min(100, Math.abs(meter.power_factor) * 100)}%`,
                    backgroundColor: meter.power_factor >= 0.9 ? '#10b981' : meter.power_factor >= 0.8 ? '#f59e0b' : '#ef4444'
                  }}
                />
              </div>
            )}
          </div>
        </div>
      </div>
      </>
      )}
      
      {activeTab === 'summary' && (
        <div className="space-y-4">
          {/* Period Filter */}
          <div 
            className="rounded-lg p-4 shadow-sm"
            style={{
              backgroundColor: cardBackgroundColor,
              boxShadow: `0px 4px 40px ${boxShadowColor}`,
              borderColor: borderColor,
              borderWidth: '1px',
              borderStyle: 'solid',
            }}
          >
            <div className="flex flex-wrap items-center gap-4">
              <label className="text-sm font-medium" style={{ color: textColor }}>Period:</label>
              <select
                value={summaryPeriod}
                onChange={(e) => setSummaryPeriod(e.target.value as any)}
                className="px-3 py-2 rounded-lg text-sm"
                style={{
                  backgroundColor: metricBgColor,
                  color: textColor,
                  borderColor: borderColor,
                  borderWidth: '1px',
                }}
              >
                <option value="today">Today</option>
                <option value="yesterday">Yesterday</option>
                <option value="week">Last 7 Days</option>
                <option value="this_month">This Month</option>
                <option value="last_month">Last Month</option>
                <option value="this_year">This Year</option>
                <option value="last_year">Last Year</option>
                <option value="custom">Custom Range</option>
              </select>
              
              {summaryPeriod === 'custom' && (
                <>
                  <input
                    type="date"
                    value={customStartDate}
                    onChange={(e) => setCustomStartDate(e.target.value)}
                    className="px-3 py-2 rounded-lg text-sm"
                    style={{
                      backgroundColor: metricBgColor,
                      color: textColor,
                      borderColor: borderColor,
                      borderWidth: '1px',
                    }}
                  />
                  <span style={{ color: textColor }}>to</span>
                  <input
                    type="date"
                    value={customEndDate}
                    onChange={(e) => setCustomEndDate(e.target.value)}
                    className="px-3 py-2 rounded-lg text-sm"
                    style={{
                      backgroundColor: metricBgColor,
                      color: textColor,
                      borderColor: borderColor,
                      borderWidth: '1px',
                    }}
                  />
                </>
              )}
            </div>
          </div>
          
          {summaryLoading ? (
            <div className="text-center py-8" style={{ color: textColor }}>Loading summary...</div>
          ) : summaryData ? (
            <>
              {/* Totals */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div 
                  className="rounded-lg p-4 shadow-sm"
                  style={{
                    backgroundColor: redBg,
                    boxShadow: `0px 4px 40px ${boxShadowColor}`,
                  }}
                >
                  <div className="text-sm font-medium mb-2" style={{ color: textColor }}>Total Import</div>
                  <div className="text-2xl font-bold" style={{ color: textColor }}>
                    {summaryData.totals?.import_energy_kwh?.toFixed(2) || '0.00'} kWh
                  </div>
                </div>
                <div 
                  className="rounded-lg p-4 shadow-sm"
                  style={{
                    backgroundColor: greenBg,
                    boxShadow: `0px 4px 40px ${boxShadowColor}`,
                  }}
                >
                  <div className="text-sm font-medium mb-2" style={{ color: textColor }}>Total Export</div>
                  <div className="text-2xl font-bold" style={{ color: textColor }}>
                    {summaryData.totals?.export_energy_kwh?.toFixed(2) || '0.00'} kWh
                  </div>
                </div>
                <div 
                  className="rounded-lg p-4 shadow-sm"
                  style={{
                    backgroundColor: blueBg,
                    boxShadow: `0px 4px 40px ${boxShadowColor}`,
                  }}
                >
                  <div className="text-sm font-medium mb-2" style={{ color: textColor }}>Net Energy</div>
                  <div className="text-2xl font-bold" style={{ color: textColor }}>
                    {summaryData.totals?.net_energy_kwh?.toFixed(2) || '0.00'} kWh
                  </div>
                </div>
              </div>
              
              {/* Chart */}
              {summaryData.data && summaryData.data.length > 0 && (
                <div 
                  className="rounded-lg p-4 shadow-sm"
                  style={{
                    backgroundColor: cardBackgroundColor,
                    boxShadow: `0px 4px 40px ${boxShadowColor}`,
                    borderColor: borderColor,
                    borderWidth: '1px',
                    borderStyle: 'solid',
                  }}
                >
                  <h3 className="text-lg font-semibold mb-4" style={{ color: textColor }}>Daily Energy Summary</h3>
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={summaryData.data}>
                      <CartesianGrid strokeDasharray="3 3" stroke={borderColor} />
                      <XAxis 
                        dataKey="day" 
                        stroke={secondaryTextColor}
                        tick={{ fill: secondaryTextColor }}
                      />
                      <YAxis 
                        stroke={secondaryTextColor}
                        tick={{ fill: secondaryTextColor }}
                      />
                      <Tooltip 
                        contentStyle={{
                          backgroundColor: cardBackgroundColor,
                          borderColor: borderColor,
                          color: textColor
                        }}
                      />
                      <Legend />
                      <Bar dataKey="import_energy_kwh" fill="#ef4444" name="Import (kWh)" />
                      <Bar dataKey="export_energy_kwh" fill="#10b981" name="Export (kWh)" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
              
              {/* Data Table */}
              {summaryData.data && summaryData.data.length > 0 && (
                <div 
                  className="rounded-lg p-4 shadow-sm overflow-x-auto"
                  style={{
                    backgroundColor: cardBackgroundColor,
                    boxShadow: `0px 4px 40px ${boxShadowColor}`,
                    borderColor: borderColor,
                    borderWidth: '1px',
                    borderStyle: 'solid',
                  }}
                >
                  <h3 className="text-lg font-semibold mb-4" style={{ color: textColor }}>Daily Details</h3>
                  <table className="w-full text-sm">
                    <thead>
                      <tr style={{ borderBottomColor: borderColor, borderBottomWidth: '1px' }}>
                        <th className="text-left py-2" style={{ color: textColor }}>Date</th>
                        <th className="text-right py-2" style={{ color: textColor }}>Import (kWh)</th>
                        <th className="text-right py-2" style={{ color: textColor }}>Export (kWh)</th>
                        <th className="text-right py-2" style={{ color: textColor }}>Net (kWh)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {summaryData.data.map((row: any, idx: number) => (
                        <tr key={idx} style={{ borderBottomColor: borderColor, borderBottomWidth: '1px' }}>
                          <td className="py-2" style={{ color: textColor }}>{row.day}</td>
                          <td className="text-right py-2" style={{ color: textColor }}>{row.import_energy_kwh?.toFixed(2) || '0.00'}</td>
                          <td className="text-right py-2" style={{ color: textColor }}>{row.export_energy_kwh?.toFixed(2) || '0.00'}</td>
                          <td className="text-right py-2" style={{ color: textColor }}>{row.net_energy_kwh?.toFixed(2) || '0.00'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          ) : (
            <div className="text-center py-8" style={{ color: secondaryTextColor }}>No summary data available</div>
          )}
        </div>
      )}
      
      {activeTab === 'comparison' && (
        <div className="space-y-4">
          {comparisonLoading ? (
            <div className="text-center py-8" style={{ color: textColor }}>Loading comparison...</div>
          ) : comparisonData && comparisonData.comparison ? (
            <>
              <div 
                className="rounded-lg p-4 shadow-sm"
                style={{
                  backgroundColor: cardBackgroundColor,
                  boxShadow: `0px 4px 40px ${boxShadowColor}`,
                  borderColor: borderColor,
                  borderWidth: '1px',
                  borderStyle: 'solid',
                }}
              >
                <h3 className="text-lg font-semibold mb-4" style={{ color: textColor }}>
                  Month-over-Month Comparison (Last 12 Months)
                </h3>
                <p className="text-sm mb-4" style={{ color: secondaryTextColor }}>
                  Comparing this month vs same month last year
                </p>
                <ResponsiveContainer width="100%" height={400}>
                  <BarChart data={comparisonData.comparison}>
                    <CartesianGrid strokeDasharray="3 3" stroke={borderColor} />
                    <XAxis 
                      dataKey="month_name" 
                      stroke={secondaryTextColor}
                      tick={{ fill: secondaryTextColor, fontSize: 12 }}
                      angle={-45}
                      textAnchor="end"
                      height={80}
                    />
                    <YAxis 
                      stroke={secondaryTextColor}
                      tick={{ fill: secondaryTextColor }}
                    />
                    <Tooltip 
                      contentStyle={{
                        backgroundColor: cardBackgroundColor,
                        borderColor: borderColor,
                        color: textColor
                      }}
                    />
                    <Legend />
                    <Bar dataKey="this_year.import_energy_kwh" fill="#ef4444" name="This Year Import (kWh)" />
                    <Bar dataKey="last_year.import_energy_kwh" fill="#fca5a5" name="Last Year Import (kWh)" />
                    <Bar dataKey="this_year.export_energy_kwh" fill="#10b981" name="This Year Export (kWh)" />
                    <Bar dataKey="last_year.export_energy_kwh" fill="#86efac" name="Last Year Export (kWh)" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              
              {/* Comparison Table */}
              <div 
                className="rounded-lg p-4 shadow-sm overflow-x-auto"
                style={{
                  backgroundColor: cardBackgroundColor,
                  boxShadow: `0px 4px 40px ${boxShadowColor}`,
                  borderColor: borderColor,
                  borderWidth: '1px',
                  borderStyle: 'solid',
                }}
              >
                <h3 className="text-lg font-semibold mb-4" style={{ color: textColor }}>Detailed Comparison</h3>
                <table className="w-full text-sm">
                  <thead>
                    <tr style={{ borderBottomColor: borderColor, borderBottomWidth: '1px' }}>
                      <th className="text-left py-2" style={{ color: textColor }}>Month</th>
                      <th className="text-right py-2" style={{ color: textColor }}>This Year Import</th>
                      <th className="text-right py-2" style={{ color: textColor }}>Last Year Import</th>
                      <th className="text-right py-2" style={{ color: textColor }}>Change</th>
                      <th className="text-right py-2" style={{ color: textColor }}>This Year Export</th>
                      <th className="text-right py-2" style={{ color: textColor }}>Last Year Export</th>
                      <th className="text-right py-2" style={{ color: textColor }}>Change</th>
                    </tr>
                  </thead>
                  <tbody>
                    {comparisonData.comparison.map((row: any, idx: number) => (
                      <tr key={idx} style={{ borderBottomColor: borderColor, borderBottomWidth: '1px' }}>
                        <td className="py-2" style={{ color: textColor }}>{row.month_name}</td>
                        <td className="text-right py-2" style={{ color: textColor }}>{row.this_year.import_energy_kwh?.toFixed(2) || '0.00'}</td>
                        <td className="text-right py-2" style={{ color: textColor }}>{row.last_year.import_energy_kwh?.toFixed(2) || '0.00'}</td>
                        <td className="text-right py-2" style={{ 
                          color: row.difference.import_energy_kwh >= 0 ? '#ef4444' : '#10b981' 
                        }}>
                          {row.difference.import_energy_kwh >= 0 ? '+' : ''}{row.difference.import_energy_kwh?.toFixed(2) || '0.00'} 
                          ({row.percent_change.import_energy_kwh >= 0 ? '+' : ''}{row.percent_change.import_energy_kwh?.toFixed(1) || '0.0'}%)
                        </td>
                        <td className="text-right py-2" style={{ color: textColor }}>{row.this_year.export_energy_kwh?.toFixed(2) || '0.00'}</td>
                        <td className="text-right py-2" style={{ color: textColor }}>{row.last_year.export_energy_kwh?.toFixed(2) || '0.00'}</td>
                        <td className="text-right py-2" style={{ 
                          color: row.difference.export_energy_kwh >= 0 ? '#10b981' : '#ef4444' 
                        }}>
                          {row.difference.export_energy_kwh >= 0 ? '+' : ''}{row.difference.export_energy_kwh?.toFixed(2) || '0.00'} 
                          ({row.percent_change.export_energy_kwh >= 0 ? '+' : ''}{row.percent_change.export_energy_kwh?.toFixed(1) || '0.0'}%)
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          ) : (
            <div className="text-center py-8" style={{ color: secondaryTextColor }}>No comparison data available</div>
          )}
        </div>
      )}
    </div>
  )
}

