import React, { useState, useEffect, useRef, useContext } from 'react'
import { api } from '../lib/api'
import { TelemetryData, TelemetryResponse } from '../types/telemetry'
import { ArrayContext } from '../ui/AppLayout'

interface DetailedTelemetryProps {
  selectedInverter: string
  inverters: string[]
  onInverterChange: (inverterId: string) => void
}

export const DetailedTelemetry: React.FC<DetailedTelemetryProps> = ({
  selectedInverter,
  inverters,
  onInverterChange
}) => {
  const { selectedArray } = useContext(ArrayContext)
  const [telemetry, setTelemetry] = useState<TelemetryData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const prevTelemetryRef = useRef<TelemetryData | null>(null)

  useEffect(() => {
    const fetchTelemetry = async () => {
      try {
        // Only show loading spinner on initial load, not on refresh
        if (!telemetry) {
          setLoading(true)
        } else {
          setIsRefreshing(true)
        }
        setError(null)
        const url = selectedArray
          ? `/api/now?inverter_id=${selectedInverter}&array_id=${selectedArray}`
          : `/api/now?inverter_id=${selectedInverter}`
        const response: TelemetryResponse = await api.get(url)
        if (response.now) {
          prevTelemetryRef.current = telemetry
          setTelemetry(response.now)
        }
      } catch (err: any) {
        setError(err.message || 'Failed to load telemetry data')
        // Don't clear telemetry on error to prevent flickering
      } finally {
        setLoading(false)
        setIsRefreshing(false)
      }
    }

    fetchTelemetry()
    const interval = setInterval(fetchTelemetry, 5000) // Refresh every 5 seconds
    return () => clearInterval(interval)
  }, [selectedInverter, selectedArray])

  // Detect if inverter is three-phase based on metadata or phase-specific data
  const isThreePhase = (tel: TelemetryData | null): boolean => {
    if (!tel) return false
    
    // First check metadata (most reliable)
    if (tel._metadata?.is_three_phase !== undefined) {
      return tel._metadata.is_three_phase
    }
    
    // Fallback: Check if we have any phase-specific load or grid data
    return !!(
      tel.load_l1_power_w !== undefined ||
      tel.load_l2_power_w !== undefined ||
      tel.load_l3_power_w !== undefined ||
      tel.grid_l1_power_w !== undefined ||
      tel.grid_l2_power_w !== undefined ||
      tel.grid_l3_power_w !== undefined ||
      (tel.extra && (
        tel.extra.load_l1_power_w !== undefined ||
        tel.extra.load_l2_power_w !== undefined ||
        tel.extra.load_l3_power_w !== undefined ||
        tel.extra.grid_l1_power_w !== undefined ||
        tel.extra.grid_l2_power_w !== undefined ||
        tel.extra.grid_l3_power_w !== undefined
      ))
    )
  }

  const formatPower = (watts?: number): string => {
    if (watts === undefined || watts === null) return 'N/A'
    if (Math.abs(watts) >= 1000) return `${(watts / 1000).toFixed(2)} kW`
    return `${watts.toFixed(0)} W`
  }

  const formatVoltage = (volts?: number): string => {
    if (volts === undefined || volts === null) return 'N/A'
    return `${volts.toFixed(1)} V`
  }

  const formatCurrent = (amps?: number): string => {
    if (amps === undefined || amps === null) return 'N/A'
    return `${amps.toFixed(2)} A`
  }

  const formatTemperature = (temp?: number): string => {
    if (temp === undefined || temp === null) return 'N/A'
    return `${temp.toFixed(1)} °C`
  }

  const formatPercentage = (percent?: number): string => {
    if (percent === undefined || percent === null) return 'N/A'
    return `${percent.toFixed(1)}%`
  }

  const formatEnergy = (kwh?: number): string => {
    if (kwh === undefined || kwh === null) return 'N/A'
    return `${kwh.toFixed(2)} kWh`
  }

  const formatFrequency = (hz?: number): string => {
    if (hz === undefined || hz === null) return 'N/A'
    return `${hz.toFixed(2)} Hz`
  }

  // Helper to get value from telemetry or extra
  const getValue = (key: string, tel: TelemetryData | null): number | undefined => {
    if (!tel) return undefined
    // Check direct property first (case-sensitive)
    const directVal = tel[key as keyof TelemetryData]
    if (directVal !== undefined && directVal !== null && typeof directVal === 'number') {
      return directVal
    }
    // Check extra dict
    if (tel.extra && typeof tel.extra === 'object') {
      // Try exact key first
      if (key in tel.extra) {
        const extraVal = tel.extra[key]
        if (extraVal !== undefined && extraVal !== null && typeof extraVal === 'number') {
          return extraVal
        }
      }
      // Try alternative names for energy fields
      if (key === 'today_import_energy' && 'today_grid_import_energy' in tel.extra) {
        const val = tel.extra['today_grid_import_energy']
        if (val !== undefined && val !== null && typeof val === 'number') return val
      }
      if (key === 'today_export_energy' && 'today_grid_export_energy' in tel.extra) {
        const val = tel.extra['today_grid_export_energy']
        if (val !== undefined && val !== null && typeof val === 'number') return val
      }
      // Try computed load current from power/voltage if not directly available
      if (key === 'load_l1_current_a' && !('load_l1_current_a' in tel.extra)) {
        const power = tel.extra['load_l1_power_w']
        const voltage = tel.extra['load_l1_voltage_v']
        if (power && voltage && voltage > 0) {
          return Math.abs(power) / voltage
        }
      }
      if (key === 'load_l2_current_a' && !('load_l2_current_a' in tel.extra)) {
        const power = tel.extra['load_l2_power_w']
        const voltage = tel.extra['load_l2_voltage_v']
        if (power && voltage && voltage > 0) {
          return Math.abs(power) / voltage
        }
      }
      if (key === 'load_l3_current_a' && !('load_l3_current_a' in tel.extra)) {
        const power = tel.extra['load_l3_power_w']
        const voltage = tel.extra['load_l3_voltage_v']
        if (power && voltage && voltage > 0) {
          return Math.abs(power) / voltage
        }
      }
    }
    return undefined
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-lg text-gray-700">Loading telemetry data...</div>
      </div>
    )
  }

  if (error && !telemetry) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <div className="text-red-800 font-medium">Error loading telemetry</div>
        <div className="text-red-600 text-sm mt-1">{error}</div>
      </div>
    )
  }

  if (!telemetry) {
    return (
      <div className="text-center p-8 text-gray-500">
        No telemetry data available
      </div>
    )
  }

  const threePhase = isThreePhase(telemetry)

  // Section component for consistent styling
  const Section: React.FC<{ title: string; children: React.ReactNode }> = ({ title, children }) => (
    <div className="bg-white rounded-lg shadow p-4 mb-4 transition-opacity duration-300">
      <h2 className="text-lg font-bold text-gray-900 mb-3 border-b border-gray-200 pb-1.5">{title}</h2>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-2">
        {children}
      </div>
    </div>
  )

  // Parameter card component with smooth transitions
  const ParameterCard: React.FC<{ label: string; value: string; unit?: string }> = ({ label, value, unit }) => (
    <div className="bg-gray-50 rounded-lg p-2.5 border border-gray-200 transition-all duration-200 hover:shadow-sm">
      <div className="text-xs text-gray-600 mb-0.5">{label}</div>
      <div className="text-sm font-semibold text-gray-900 transition-colors duration-200">
        {value} {unit && <span className="text-xs text-gray-500">{unit}</span>}
      </div>
    </div>
  )

  // Phase group component for three-phase data
  const PhaseGroup: React.FC<{ 
    phase: 'L1' | 'L2' | 'L3'
    power?: number
    voltage?: number
    current?: number
  }> = ({ phase, power, voltage, current }) => (
    <div className="bg-blue-50 rounded-lg p-2.5 border-2 border-blue-200 transition-all duration-200 hover:shadow-sm">
      <div className="text-xs font-semibold text-blue-800 mb-2">Phase {phase}</div>
      <div className="space-y-1">
        <div className="flex justify-between items-center">
          <span className="text-xs text-gray-600">Power:</span>
          <span className="text-xs font-semibold text-gray-900">{formatPower(power)}</span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-xs text-gray-600">Voltage:</span>
          <span className="text-xs font-semibold text-gray-900">{formatVoltage(voltage)}</span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-xs text-gray-600">Current:</span>
          <span className="text-xs font-semibold text-gray-900">{formatCurrent(current)}</span>
        </div>
      </div>
    </div>
  )

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="bg-white rounded-lg shadow p-4 mb-4">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Detailed Telemetry</h1>
          <p className="text-xs text-gray-600 mt-0.5">
            {threePhase ? 'Three-Phase Inverter' : 'Single-Phase Inverter'} • 
            Last updated: {telemetry.ts ? new Date(telemetry.ts).toLocaleTimeString() : 'N/A'}
            {isRefreshing && <span className="ml-2 text-blue-600">(Refreshing...)</span>}
          </p>
        </div>
      </div>

      {/* Load Section */}
      <Section title="Load">
        {threePhase ? (
          <>
            <ParameterCard label="Total Power" value={formatPower(getValue('load_power_w', telemetry))} />
            <PhaseGroup 
              phase="L1"
              power={getValue('load_l1_power_w', telemetry)}
              voltage={getValue('load_l1_voltage_v', telemetry)}
              current={getValue('load_l1_current_a', telemetry)}
            />
            <PhaseGroup 
              phase="L2"
              power={getValue('load_l2_power_w', telemetry)}
              voltage={getValue('load_l2_voltage_v', telemetry)}
              current={getValue('load_l2_current_a', telemetry)}
            />
            <PhaseGroup 
              phase="L3"
              power={getValue('load_l3_power_w', telemetry)}
              voltage={getValue('load_l3_voltage_v', telemetry)}
              current={getValue('load_l3_current_a', telemetry)}
            />
            <ParameterCard label="Frequency" value={formatFrequency(getValue('load_frequency_hz', telemetry))} />
            <ParameterCard label="Today Energy" value={formatEnergy(getValue('today_load_energy', telemetry) || getValue('daily_energy_to_eps', telemetry))} />
          </>
        ) : (
          <>
            <ParameterCard label="Power" value={formatPower(getValue('load_power_w', telemetry))} />
            <ParameterCard label="Today Energy" value={formatEnergy(getValue('today_load_energy', telemetry) || getValue('daily_energy_to_eps', telemetry))} />
          </>
        )}
      </Section>

      {/* Grid Section */}
      <Section title="Grid">
        {threePhase ? (
          <>
            <ParameterCard label="Total Power" value={formatPower(getValue('grid_power_w', telemetry))} />
            <PhaseGroup 
              phase="L1"
              power={getValue('grid_l1_power_w', telemetry)}
              voltage={getValue('grid_l1_voltage_v', telemetry)}
              current={getValue('grid_l1_current_a', telemetry)}
            />
            <PhaseGroup 
              phase="L2"
              power={getValue('grid_l2_power_w', telemetry)}
              voltage={getValue('grid_l2_voltage_v', telemetry)}
              current={getValue('grid_l2_current_a', telemetry)}
            />
            <PhaseGroup 
              phase="L3"
              power={getValue('grid_l3_power_w', telemetry)}
              voltage={getValue('grid_l3_voltage_v', telemetry)}
              current={getValue('grid_l3_current_a', telemetry)}
            />
            <ParameterCard label="Line Voltage AB" value={formatVoltage(getValue('grid_line_voltage_ab_v', telemetry))} />
            <ParameterCard label="Line Voltage BC" value={formatVoltage(getValue('grid_line_voltage_bc_v', telemetry))} />
            <ParameterCard label="Line Voltage CA" value={formatVoltage(getValue('grid_line_voltage_ca_v', telemetry))} />
            <ParameterCard label="Frequency" value={formatFrequency(getValue('grid_frequency_hz', telemetry))} />
            <ParameterCard label="Import Energy" value={formatEnergy(getValue('today_import_energy', telemetry) || getValue('today_grid_import_energy', telemetry))} />
            <ParameterCard label="Export Energy" value={formatEnergy(getValue('today_export_energy', telemetry) || getValue('today_grid_export_energy', telemetry))} />
            <ParameterCard label="Off-Grid Mode" value={telemetry.off_grid_mode ? 'Yes' : 'No'} />
          </>
        ) : (
          <>
            <ParameterCard label="Power" value={formatPower(getValue('grid_power_w', telemetry))} />
            <ParameterCard label="Import Energy" value={formatEnergy(getValue('today_import_energy', telemetry) || getValue('today_grid_import_energy', telemetry))} />
            <ParameterCard label="Export Energy" value={formatEnergy(getValue('today_export_energy', telemetry) || getValue('today_grid_export_energy', telemetry))} />
            <ParameterCard label="Off-Grid Mode" value={telemetry.off_grid_mode ? 'Yes' : 'No'} />
          </>
        )}
      </Section>

      {/* Solar Section */}
      <Section title="Solar">
        <ParameterCard label="Total Power" value={formatPower(getValue('pv_power_w', telemetry))} />
        <ParameterCard label="PV1 Power" value={formatPower(getValue('pv1_power_w', telemetry) || getValue('mppt1_power', telemetry))} />
        <ParameterCard label="PV2 Power" value={formatPower(getValue('pv2_power_w', telemetry) || getValue('mppt2_power', telemetry))} />
        <ParameterCard label="Today Energy" value={formatEnergy(getValue('today_energy', telemetry))} />
        <ParameterCard label="Total Energy" value={formatEnergy(getValue('total_energy', telemetry))} />
        <ParameterCard label="Peak Power" value={formatPower(getValue('today_peak_power', telemetry))} />
      </Section>

      {/* Battery Section */}
      <Section title="Battery">
        <ParameterCard label="State of Charge" value={formatPercentage(getValue('batt_soc_pct', telemetry))} />
        <ParameterCard label="Voltage" value={formatVoltage(getValue('batt_voltage_v', telemetry))} />
        <ParameterCard label="Current" value={formatCurrent(getValue('batt_current_a', telemetry))} />
        <ParameterCard label="Power" value={formatPower(getValue('batt_power_w', telemetry))} />
        <ParameterCard label="Temperature" value={formatTemperature(getValue('batt_temp_c', telemetry))} />
        <ParameterCard label="Charge Energy" value={formatEnergy(getValue('today_battery_charge_energy', telemetry))} />
        <ParameterCard label="Discharge Energy" value={formatEnergy(getValue('today_battery_discharge_energy', telemetry))} />
      </Section>

      {/* Inverter Section */}
      <Section title="Inverter">
        <ParameterCard label="Mode" value={telemetry.inverter_mode || 'Unknown'} />
        <ParameterCard label="Temperature" value={formatTemperature(getValue('inverter_temp_c', telemetry))} />
        <ParameterCard label="Error Code" value={telemetry.error_code?.toString() || 'None'} />
        <ParameterCard label="Model" value={telemetry.device_model || 'N/A'} />
        <ParameterCard label="Serial Number" value={telemetry.device_serial_number || 'N/A'} />
        <ParameterCard label="Rated Power" value={formatPower(getValue('rated_power_w', telemetry) || getValue('rated_power', telemetry))} />
      </Section>
    </div>
  )
}
