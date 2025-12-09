import React, { useState, useEffect } from 'react'
import { api } from '../lib/api'
import { TelemetryData, TelemetryResponse } from '../types/telemetry'
import { PowerFlowChart } from '../components/PowerFlowChart'
import { PowerFlowDiagram } from '../components/PowerFlowDiagram'
import { SolarSystemDiagram } from '../components/SolarSystemDiagram'
import { PVForecastChart } from '../components/PVForecastChart'
import { Overview24hChart } from '../components/Overview24hChart'
import { SelfSufficiencyBar } from '../components/SelfSufficiencyBar'
import { generateDemoTelemetry } from '../utils/demoData'

export const DashboardPage: React.FC = () => {
  const [dashboardType, setDashboardType] = useState<'energy' | 'detailed'>('energy')
  const [telemetry, setTelemetry] = useState<TelemetryData | null>(null)
  const [loading, setLoading] = useState(true)
  const [isDemoMode, setIsDemoMode] = useState(false)
  const [inverters, setInverters] = useState<string[]>([])
  const [selectedInverter, setSelectedInverter] = useState<string>('all')

  const fetchTelemetry = async () => {
    try {
      const response: TelemetryResponse = await api.get(`/api/now?inverter_id=${selectedInverter}`)
      setTelemetry(response.now)
      setIsDemoMode(false)
    } catch (err) {
      setTelemetry(generateDemoTelemetry())
      setIsDemoMode(true)
    } finally {
      setLoading(false)
    }
  }

  const fetchInverters = async () => {
    try {
      const resp: any = await api.get('/api/inverters')
      const ids: string[] = Array.isArray(resp?.inverters) ? resp.inverters : []
      setInverters(ids)
      // If previously selected inverter no longer exists, reset to 'all'
      if (selectedInverter !== 'all' && !ids.includes(selectedInverter)) {
        setSelectedInverter('all')
      }
    } catch (e) {
      setInverters([])
    }
  }

  useEffect(() => {
    fetchInverters()
  }, [])

  useEffect(() => {
    fetchTelemetry()
    const interval = setInterval(fetchTelemetry, 5000) // Refresh every 5 seconds
    return () => clearInterval(interval)
  }, [selectedInverter])

  const formatPower = (watts?: number) => {
    if (watts === undefined || watts === null) return '0 W'
    if (watts >= 1000) return `${(watts / 1000).toFixed(1)} kW`
    return `${watts.toFixed(0)} W`
  }

  const formatPercentage = (percent?: number) => {
    if (percent === undefined || percent === null) return '0%'
    return `${percent.toFixed(0)}%`
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-lg text-gray-700">Loading dashboard...</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b border-gray-200 p-4">
        <div className="flex gap-4 items-center flex-wrap">
          <button
            onClick={() => setDashboardType('energy')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              dashboardType === 'energy'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            Energy Dashboard
          </button>
          <button
            onClick={() => setDashboardType('detailed')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              dashboardType === 'detailed'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            Detailed Telemetry
          </button>

          {/* Inverter Selector */}
          <div className="ml-auto flex items-center gap-2">
            <label className="text-sm text-gray-700">Inverter:</label>
            <select
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white"
              value={selectedInverter}
              onChange={(e) => setSelectedInverter(e.target.value)}
            >
              <option value="all">All inverters</option>
              {inverters.map(id => (
                <option key={id} value={id}>{id}</option>
              ))}
            </select>
          </div>
        </div>
        {isDemoMode && (
          <div className="mt-2 text-sm text-orange-600 font-medium">
            🎭 Demo Mode - Using simulated data
          </div>
        )}
      </div>

      {/* Dashboard Content */}
      <div className="p-4 sm:p-6">
        {dashboardType === 'energy' ? (
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-6">Energy Dashboard</h1>
            
            {/* First section: Power Flow with key metric cards */}
            {telemetry && (
              <div className="mb-8">
                <PowerFlowDiagram telemetry={telemetry} />
              </div>
            )}

            {/* Today's Energy Self-Sufficiency */}
            {telemetry && (
              <div className="mb-8">
                <SelfSufficiencyBar telemetry={telemetry} />
              </div>
            )}

            {/* Battery Status removed as requested */}


            {/* New Charts Section */}
            <div className="space-y-8">
              {/* PV Forecast Chart */}
              <PVForecastChart inverterId={selectedInverter} telemetry={telemetry || undefined} />
              
              {/* 24-Hour Overview Chart */}
              <Overview24hChart inverterId={selectedInverter} />
            </div>
          </div>
        ) : (
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-6">Detailed Telemetry</h1>
            
            {/* Solar System Overview */}
            {telemetry && (
              <div className="mb-8">
                <SolarSystemDiagram telemetry={telemetry} />
              </div>
            )}

            {/* Power Flow Diagram */}
            {telemetry && (
              <div className="mb-8">
                <PowerFlowDiagram telemetry={telemetry} />
              </div>
            )}

            {/* Battery SOC Chart removed as requested */}

            {/* Power Flow Chart */}
            {telemetry && (
              <div className="mb-8">
                <PowerFlowChart telemetry={telemetry} />
              </div>
            )}

            {/* Today's Energy Self-Sufficiency */}
            {telemetry && (
              <div className="mb-8">
                <SelfSufficiencyBar telemetry={telemetry} />
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

