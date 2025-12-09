import React, { useEffect, useState } from 'react'
import { api } from '../lib/api'
import BatteryLowIcon from '../assets/battery-low.svg'
import BatteryMediumIcon from '../assets/battery-medium.svg'
import BatteryHighIcon from '../assets/battery-high.svg'
import BatteryPackIcon from '../assets/battery-pack.svg'
import BatteryCellIcon from '../assets/battery-cell.svg'
import MetricPowerIcon from '../assets/metric-power.svg'
import MetricCurrentIcon from '../assets/metric-current.svg'
import MetricTemperatureIcon from '../assets/metric-temperature.svg'
import MetricVoltageDeltaIcon from '../assets/metric-voltage-delta.svg'
import MetricSocIcon from '../assets/metric-soc.svg'

type BatteryUnit = {
  power: number
  voltage?: number
  current?: number
  temperature?: number
  soc?: number
  basic_st?: string
  volt_st?: string
  temp_st?: string
  current_st?: string
  coul_st?: string
  soh_st?: string
  heater_st?: string
  bat_events?: number
  power_events?: number
  sys_events?: number
}

type BatteryCell = {
  power: number
  cell: number
  voltage?: number
  temperature?: number
  soc?: number
  volt_st?: string
  temp_st?: string
}

type BatteryCellsEntry = {
  power: number
  voltage_min?: number
  voltage_max?: number
  voltage_delta?: number
  temperature_min?: number
  temperature_max?: number
  temperature_delta?: number
  cells: BatteryCell[]
}

type BatteryBank = {
  ts: string
  id: string
  batteries_count: number
  cells_per_battery: number
  voltage?: number
  current?: number
  temperature?: number
  soc?: number
  devices: BatteryUnit[]
  cells_data?: BatteryCellsEntry[]
}

// Helper function to get battery icon based on SOC
const getBatteryIcon = (soc?: number) => {
  if (!soc) return BatteryLowIcon
  if (soc < 30) return BatteryLowIcon
  if (soc < 70) return BatteryMediumIcon
  return BatteryHighIcon
}

// Helper component for progress bars
const ProgressBar: React.FC<{ 
  value: number | undefined, 
  max: number, 
  unit: string, 
  color?: string,
  format?: (val: number) => string 
}> = ({ value, max, unit, color = "bg-blue-500", format = (v) => v.toFixed(1) }) => {
  if (value === undefined || value === null) return <span className="text-gray-400">-</span>
  
  const percentage = Math.min((value / max) * 100, 100)
  const displayValue = format(value)
  
  return (
    <div className="flex items-center space-x-2">
      <div className="flex-1 bg-gray-200 rounded-full h-2">
        <div 
          className={`h-2 rounded-full ${color}`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      <span className="text-sm font-medium min-w-[60px]">{displayValue} {unit}</span>
    </div>
  )
}

export const BatteryBankView: React.FC<{ refreshInterval?: number }> = ({ refreshInterval = 5000 }) => {
  const [bank, setBank] = useState<BatteryBank | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchBattery = async () => {
    try {
      const res = await api.get('/api/battery/now') as any
      if (res && res.status === 'ok') {
        setBank(res.battery as BatteryBank)
        setError(null)
      } else {
        setError('No battery data')
      }
    } catch (e: any) {
      setError(e?.message || 'Failed to load battery')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchBattery()
    const t = setInterval(fetchBattery, refreshInterval)
    return () => clearInterval(t)
  }, [refreshInterval])

  if (loading) {
    return <div className="p-6">Loading battery data…</div>
  }
  if (error || !bank) {
    return <div className="p-6 text-gray-600">{error || 'No battery data available'}</div>
  }

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-2xl p-8 shadow-lg border border-gray-100">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center">
            <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center mr-4">
              <img src={BatteryPackIcon} alt="Battery Pack" className="w-8 h-8" />
            </div>
            <h2 className="text-2xl font-bold text-gray-900">Battery Bank Overview</h2>
          </div>
          <div className="text-sm">
            <span className={`px-4 py-2 rounded-full font-semibold text-sm shadow-sm ${
              bank.current && bank.current > 0 
                ? 'bg-red-100 text-red-700 border border-red-200' 
                : 'bg-blue-100 text-blue-700 border border-blue-200'
            }`}>
              {bank.current && bank.current > 0 ? 'CHARGING' : 'DISCHARGING'}
            </span>
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="space-y-2">
            <div className="text-sm text-gray-600">Voltage</div>
            <ProgressBar 
              value={bank.voltage} 
              max={60} 
              unit="V" 
              color="bg-green-500"
              format={(v) => v.toFixed(2)}
            />
          </div>
          <div className="space-y-2">
            <div className="text-sm text-gray-600">SOC</div>
            <ProgressBar 
              value={bank.soc} 
              max={100} 
              unit="%" 
              color={bank.soc && bank.soc < 20 ? "bg-red-500" : bank.soc && bank.soc < 50 ? "bg-yellow-500" : "bg-green-500"}
              format={(v) => v.toFixed(0)}
            />
          </div>
          <div className="space-y-2">
            <div className="text-sm text-gray-600">Temperature</div>
            <ProgressBar 
              value={bank.temperature} 
              max={60} 
              unit="°C" 
              color={bank.temperature && bank.temperature > 40 ? "bg-red-500" : "bg-orange-500"}
              format={(v) => v.toFixed(1)}
            />
          </div>
          <div className="space-y-2">
            <div className="text-sm text-gray-600">Power</div>
            <ProgressBar 
              value={Math.abs((bank.voltage || 0) * (bank.current || 0))} 
              max={5000} 
              unit="W" 
              color="bg-red-500"
              format={(v) => v.toFixed(0)}
            />
          </div>
        </div>
        <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4 text-sm text-gray-600">
          <div>Batteries: <span className="font-semibold text-gray-900">{bank.batteries_count}</span></div>
          <div>Cells/Battery: <span className="font-semibold text-gray-900">{bank.cells_per_battery}</span></div>
          <div>Total Cells: <span className="font-semibold text-gray-900">{bank.batteries_count * bank.cells_per_battery}</span></div>
          <div>Last Update: <span className="font-semibold text-gray-900">{new Date(bank.ts).toLocaleTimeString()}</span></div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {bank.devices.map((battery) => {
          // Find corresponding cell data for this battery
          const cellData = bank.cells_data?.find(cd => cd.power === battery.power)
          
          return (
            <div key={battery.power} className="bg-white rounded-2xl p-8 shadow-lg border border-gray-100 hover:shadow-xl transition-shadow duration-300">
              {/* Header with status */}
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center">
                  <div className="w-10 h-10 bg-green-100 rounded-xl flex items-center justify-center mr-3">
                    <img src={getBatteryIcon(battery.soc)} alt={`Battery ${battery.power}`} className="w-6 h-6" />
                  </div>
                  <h3 className="text-2xl font-bold text-gray-900">Battery #{battery.power}</h3>
                </div>
                <div className="text-sm">
                  <span className={`px-4 py-2 rounded-full font-semibold text-sm shadow-sm ${
                    battery.current && battery.current > 0 
                      ? 'bg-red-100 text-red-700 border border-red-200' 
                      : 'bg-blue-100 text-blue-700 border border-blue-200'
                  }`}>
                    {battery.current && battery.current > 0 ? 'CHARGE' : 'DISCHARGE'}
                  </span>
                </div>
              </div>

              {/* Main power and SOC horizontal gauges */}
              <div className="space-y-6 mb-10">
                {/* Power Gauge */}
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium text-gray-600">Power</span>
                    <span className="text-lg font-bold text-red-600">
                      {Math.abs((battery.voltage || 0) * (battery.current || 0)).toFixed(0)} W
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-3">
                    <div 
                      className="bg-red-500 h-3 rounded-full transition-all duration-500"
                      style={{ 
                        width: `${Math.min(Math.abs((battery.voltage || 0) * (battery.current || 0)) / 5000 * 100, 100)}%` 
                      }}
                    ></div>
                  </div>
                  <div className="text-xs text-gray-500">0 - 5000W</div>
                </div>

                {/* SOC Gauge */}
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium text-gray-600">SOC</span>
                    <span className="text-lg font-bold text-green-600">
                      {(battery.soc || 0).toFixed(1)}%
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-3">
                    <div 
                      className="bg-green-500 h-3 rounded-full transition-all duration-500"
                      style={{ 
                        width: `${Math.min((battery.soc || 0), 100)}%` 
                      }}
                    ></div>
                  </div>
                  <div className="text-xs text-gray-500">0 - 100%</div>
                </div>
              </div>

              {/* Detailed metrics in two columns */}
              <div className="grid grid-cols-2 gap-8 mb-10">
                <div className="space-y-4">
                  <div className="flex justify-between items-center py-3 px-4 bg-gray-50 rounded-xl">
                    <div className="flex items-center">
                      <div className="w-8 h-8 bg-green-100 rounded-lg flex items-center justify-center mr-3">
                        <img src={MetricPowerIcon} alt="Voltage" className="w-4 h-4" />
                      </div>
                      <span className="text-gray-600 font-medium">Voltage</span>
                    </div>
                    <span className="text-green-600 font-bold text-lg">
                      {battery.voltage?.toFixed(2) || '0.00'} V
                    </span>
                  </div>
                  <div className="flex justify-between items-center py-3 px-4 bg-gray-50 rounded-xl">
                    <div className="flex items-center">
                      <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center mr-3">
                        <img src={MetricCurrentIcon} alt="Current" className="w-4 h-4" />
                      </div>
                      <span className="text-gray-600 font-medium">Current</span>
                    </div>
                    <span className="text-blue-600 font-bold text-lg">
                      {Math.abs(battery.current || 0).toFixed(2)} A
                    </span>
                  </div>
                </div>
                
                <div className="space-y-4">
                  <div className="flex justify-between items-center py-3 px-4 bg-gray-50 rounded-xl">
                    <div className="flex items-center">
                      <div className="w-8 h-8 bg-orange-100 rounded-lg flex items-center justify-center mr-3">
                        <img src={MetricTemperatureIcon} alt="Temperature" className="w-4 h-4" />
                      </div>
                      <span className="text-gray-600 font-medium">Temperature</span>
                    </div>
                    <span className="text-orange-600 font-bold text-lg">{battery.temperature?.toFixed(2) || '0.00'} °C</span>
                  </div>
                  <div className="flex justify-between items-center py-3 px-4 bg-gray-50 rounded-xl">
                    <div className="flex items-center">
                      <div className="w-8 h-8 bg-red-100 rounded-lg flex items-center justify-center mr-3">
                        <img src={MetricVoltageDeltaIcon} alt="Voltage Delta" className="w-4 h-4" />
                      </div>
                      <span className="text-gray-600 font-medium">Delta V</span>
                    </div>
                    <span className="text-red-600 font-bold text-lg">
                      {cellData?.voltage_delta?.toFixed(3) || '0.000'} V
                    </span>
                  </div>
                </div>
              </div>

              {/* Cell voltage grid */}
              {cellData && cellData.cells && cellData.cells.length > 0 && (
                <div className="mt-10">
                  <div className="flex items-center mb-6">
                    <div className="w-8 h-8 bg-indigo-100 rounded-lg flex items-center justify-center mr-3">
                      <img src={BatteryCellIcon} alt="Cell Voltages" className="w-5 h-5" />
                    </div>
                    <h4 className="text-lg font-semibold text-gray-700">Cell Voltages</h4>
                  </div>
                  <div className="grid grid-cols-5 gap-4">
                    {cellData.cells.map((cell) => {
                      const isLowVoltage = cell.voltage && cellData.voltage_min && 
                        (cell.voltage - cellData.voltage_min) > (cellData.voltage_delta || 0) * 0.3
                      
                      // Calculate cell SOC based on voltage (simplified)
                      const cellSoc = cell.voltage ? Math.min(100, Math.max(0, ((cell.voltage - 3.0) / 0.4) * 100)) : 0
                      const fillWidth = (cellSoc / 100) * 12
                      
                      return (
                        <div key={cell.cell} className="flex flex-col items-center space-y-2 p-3 bg-gray-50 rounded-xl hover:bg-gray-100 transition-colors duration-200">
                          <div className="relative">
                            <img src={BatteryCellIcon} alt={`Cell ${cell.cell}`} className="w-12 h-12" />
                            <div className="absolute -top-1 -right-1 w-6 h-6 bg-white rounded-full flex items-center justify-center text-xs font-bold text-indigo-600 border-2 border-indigo-200">
                              {cell.cell}
                            </div>
                          </div>
                          <div className={`text-xs font-mono font-semibold ${isLowVoltage ? 'text-red-600' : 'text-indigo-600'}`}>
                            {cell.voltage?.toFixed(3) || '0.000'} V
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>

    </div>
  )
}



