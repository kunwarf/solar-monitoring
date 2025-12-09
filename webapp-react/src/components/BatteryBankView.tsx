import React, { useEffect, useState } from 'react'
import { api } from '../lib/api'
import { SOCRing } from './SOCRing'
import { useMobile } from '../hooks/useMobile'
import { useTheme } from '../contexts/ThemeContext'
import { ChevronDown } from 'lucide-react'
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
  format?: (val: number) => string,
  theme?: 'dark' | 'light'
}> = ({ value, max, unit, color = "bg-blue-500", format = (v) => v.toFixed(1), theme = 'light' }) => {
  if (value === undefined || value === null) {
    const emptyColor = theme === 'dark' ? 'rgba(255, 255, 255, 0.3)' : 'rgba(0, 0, 0, 0.3)'
    return <span style={{ color: emptyColor }}>-</span>
  }
  
  const percentage = Math.min((value / max) * 100, 100)
  const displayValue = format(value)
  const bgColor = theme === 'dark' ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)'
  const textColor = theme === 'dark' ? '#FFFFFF' : '#1B2234'
  
  return (
    <div className="flex items-center space-x-2">
      <div className="flex-1 rounded-full h-2" style={{ backgroundColor: bgColor }}>
        <div 
          className={`h-2 rounded-full ${color}`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      <span className="text-sm font-medium min-w-[60px]" style={{ color: textColor }}>{displayValue} {unit}</span>
    </div>
  )
}

export const BatteryBankView: React.FC<{ refreshInterval?: number }> = ({ refreshInterval = 5000 }) => {
  const { isMobile, isCompact } = useMobile()
  const { theme } = useTheme()
  const [bank, setBank] = useState<BatteryBank | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expandedCellVoltages, setExpandedCellVoltages] = useState<{ [key: number]: boolean }>({})

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

  const renderBatteryCard = (battery: BatteryUnit, cellData: BatteryCellsEntry | undefined, isMobile: boolean, isCompact: boolean) => {
    // Theme-aware colors for card content
    const textColor = theme === 'dark' ? '#FFFFFF' : '#1B2234'
    const secondaryTextColor = theme === 'dark' ? 'rgba(255, 255, 255, 0.7)' : 'rgba(27, 34, 52, 0.7)'
    const metricBgColor = theme === 'dark' ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.02)'
    const greenBg = theme === 'dark' ? 'rgba(34, 197, 94, 0.2)' : 'rgba(220, 252, 231, 1)'
    const blueBg = theme === 'dark' ? 'rgba(59, 130, 246, 0.2)' : 'rgba(219, 234, 254, 1)'
    const orangeBg = theme === 'dark' ? 'rgba(249, 115, 22, 0.2)' : 'rgba(255, 237, 213, 1)'
    const redBg = theme === 'dark' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(254, 226, 226, 1)'
    const purpleBg = theme === 'dark' ? 'rgba(168, 85, 247, 0.2)' : 'rgba(233, 213, 255, 1)'
    const indigoBg = theme === 'dark' ? 'rgba(99, 102, 241, 0.2)' : 'rgba(224, 231, 255, 1)'
    
    // Determine charging/discharging state
    const isCharging = battery.current && battery.current > 0
    const isDischarging = battery.current && battery.current < 0
    
    // Theme-aware badge colors
    const chargingBg = theme === 'dark' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(254, 226, 226, 1)'
    const chargingText = theme === 'dark' ? '#fca5a5' : '#b91c1c'
    const chargingBorder = theme === 'dark' ? 'rgba(239, 68, 68, 0.3)' : 'rgba(185, 28, 28, 0.2)'
    
    const dischargingBg = theme === 'dark' ? 'rgba(34, 197, 94, 0.2)' : 'rgba(220, 252, 231, 1)'
    const dischargingText = theme === 'dark' ? '#86efac' : '#166534'
    const dischargingBorder = theme === 'dark' ? 'rgba(34, 197, 94, 0.3)' : 'rgba(22, 101, 52, 0.2)'
    
    return (
      <>
        {/* Charging/Discharging Badge - Top Right Corner */}
        {(isCharging || isDischarging) && (
          <div 
            className={`absolute ${isMobile ? 'top-2 right-2' : 'top-4 right-4'} ${isMobile ? 'px-2 py-1 text-[10px]' : 'px-3 py-1.5 text-xs'} rounded-full font-semibold shadow-sm whitespace-nowrap z-10`}
            style={{
              backgroundColor: isCharging ? chargingBg : dischargingBg,
              color: isCharging ? chargingText : dischargingText,
              border: `1px solid ${isCharging ? chargingBorder : dischargingBorder}`,
            }}
          >
            {isCharging ? '⚡ CHARGING' : '🔋 DISCHARGING'}
          </div>
        )}
        {/* Header with status */}
        <div className={`flex items-center ${isMobile ? 'mb-3' : 'mb-6'}`}>
          <div className="flex items-center flex-1 min-w-0" style={{ paddingRight: isMobile ? '80px' : '100px' }}>
            <div 
              className={`${isMobile ? 'w-8 h-8' : 'w-10 h-10'} ${isMobile ? 'rounded-lg' : 'rounded-xl'} flex items-center justify-center ${isMobile ? 'mr-2' : 'mr-3'} flex-shrink-0`}
              style={{ backgroundColor: greenBg }}
            >
              <img src={getBatteryIcon(battery.soc)} alt={`Battery ${battery.power}`} className={`${isMobile ? 'w-4 h-4' : 'w-6 h-6'}`} />
            </div>
            <h3 className={`${isMobile ? 'text-base' : 'text-2xl'} font-bold truncate`} style={{ color: textColor }}>Battery #{battery.power}</h3>
          </div>
        </div>

        {/* Main SOC Ring with Metrics beside it */}
        <div className={`flex flex-row items-start ${isMobile ? 'gap-3 mb-4' : 'gap-6 mb-8'}`}>
          {/* SOC Ring */}
          <div className="flex flex-col items-center flex-shrink-0">
            <SOCRing soc={battery.soc || 0} size={isMobile ? 100 : 140} strokeWidth={isMobile ? 10 : 14} />
            {!isCompact && (
              <div className="mt-4 text-center">
                <div className={`${isMobile ? 'text-[10px]' : 'text-sm'} mb-1 whitespace-nowrap`} style={{ color: secondaryTextColor }}>State of Charge</div>
                <div className={`${isMobile ? 'text-[10px]' : 'text-xs'} whitespace-nowrap`} style={{ color: secondaryTextColor }}>
                  {battery.soc && battery.soc >= 80 ? '🟢 Excellent' :
                   battery.soc && battery.soc >= 50 ? '🟡 Good' :
                   battery.soc && battery.soc >= 20 ? '🟠 Low' : '🔴 Critical'}
                </div>
              </div>
            )}
          </div>

          {/* Metrics Grid beside SOC */}
          <div className={`grid grid-cols-2 ${isMobile ? 'gap-2' : 'gap-3'} flex-1`}>
            <div className={`${isMobile ? 'flex flex-col items-center justify-center py-2 px-2' : 'flex justify-between items-center py-2 px-2'} rounded-xl`} style={{ backgroundColor: metricBgColor }}>
              <div className={`flex items-center ${isMobile ? 'mb-1' : 'min-w-0 flex-shrink'}`}>
                <div className={`${isMobile ? 'w-5 h-5' : 'w-6 h-6'} rounded-lg flex items-center justify-center ${isMobile ? 'mr-1.5' : 'mr-2'} flex-shrink-0`} style={{ backgroundColor: greenBg }}>
                  <img src={MetricPowerIcon} alt="Voltage" className={`${isMobile ? 'w-2.5 h-2.5' : 'w-3 h-3'}`} />
                </div>
                <span className={`${isMobile ? 'text-[9px]' : 'text-xs'} font-medium whitespace-nowrap`} style={{ color: secondaryTextColor }}>Voltage</span>
              </div>
              <span className={`${isMobile ? 'text-[10px]' : 'text-sm'} text-green-600 font-bold whitespace-nowrap ${isMobile ? 'mt-0.5' : 'ml-1 flex-shrink-0'}`}>
                {battery.voltage?.toFixed(2) || '0.00'} V
              </span>
            </div>
            <div className={`${isMobile ? 'flex flex-col items-center justify-center py-2 px-2' : 'flex justify-between items-center py-2 px-2'} rounded-xl`} style={{ backgroundColor: metricBgColor }}>
              <div className={`flex items-center ${isMobile ? 'mb-1' : 'min-w-0 flex-shrink'}`}>
                <div className={`${isMobile ? 'w-5 h-5' : 'w-6 h-6'} rounded-lg flex items-center justify-center ${isMobile ? 'mr-1.5' : 'mr-2'} flex-shrink-0`} style={{ backgroundColor: blueBg }}>
                  <img src={MetricCurrentIcon} alt="Current" className={`${isMobile ? 'w-2.5 h-2.5' : 'w-3 h-3'}`} />
                </div>
                <span className={`${isMobile ? 'text-[9px]' : 'text-xs'} font-medium whitespace-nowrap`} style={{ color: secondaryTextColor }}>Current</span>
              </div>
              <span className={`${isMobile ? 'text-[10px]' : 'text-sm'} text-blue-600 font-bold whitespace-nowrap ${isMobile ? 'mt-0.5' : 'ml-1 flex-shrink-0'}`}>
                {Math.abs(battery.current || 0).toFixed(2)} A
              </span>
            </div>
            <div className={`${isMobile ? 'flex flex-col items-center justify-center py-2 px-2' : 'flex justify-between items-center py-2 px-2'} rounded-xl`} style={{ backgroundColor: metricBgColor }}>
              <div className={`flex items-center ${isMobile ? 'mb-1' : 'min-w-0 flex-shrink'}`}>
                <div className={`${isMobile ? 'w-5 h-5' : 'w-6 h-6'} rounded-lg flex items-center justify-center ${isMobile ? 'mr-1.5' : 'mr-2'} flex-shrink-0`} style={{ backgroundColor: orangeBg }}>
                  <img src={MetricTemperatureIcon} alt="Temperature" className={`${isMobile ? 'w-2.5 h-2.5' : 'w-3 h-3'}`} />
                </div>
                <span className={`${isMobile ? 'text-[9px]' : 'text-xs'} font-medium whitespace-nowrap`} style={{ color: secondaryTextColor }}>Temp</span>
              </div>
              <span className={`${isMobile ? 'text-[10px]' : 'text-sm'} text-orange-600 font-bold whitespace-nowrap ${isMobile ? 'mt-0.5' : 'ml-1 flex-shrink-0'}`}>{battery.temperature?.toFixed(2) || '0.00'} °C</span>
            </div>
            <div className={`${isMobile ? 'flex flex-col items-center justify-center py-2 px-2' : 'flex justify-between items-center py-2 px-2'} rounded-xl`} style={{ backgroundColor: metricBgColor }}>
              <div className={`flex items-center ${isMobile ? 'mb-1' : 'min-w-0 flex-shrink'}`}>
                <div className={`${isMobile ? 'w-5 h-5' : 'w-6 h-6'} rounded-lg flex items-center justify-center ${isMobile ? 'mr-1.5' : 'mr-2'} flex-shrink-0`} style={{ backgroundColor: redBg }}>
                  <img src={MetricVoltageDeltaIcon} alt="Voltage Delta" className={`${isMobile ? 'w-2.5 h-2.5' : 'w-3 h-3'}`} />
                </div>
                <span className={`${isMobile ? 'text-[9px]' : 'text-xs'} font-medium whitespace-nowrap`} style={{ color: secondaryTextColor }}>Delta V</span>
              </div>
              <span className={`${isMobile ? 'text-[10px]' : 'text-sm'} text-red-600 font-bold whitespace-nowrap ${isMobile ? 'mt-0.5' : 'ml-1 flex-shrink-0'}`}>
                {cellData?.voltage_delta?.toFixed(3) || '0.000'} V
              </span>
            </div>
            <div className={`${isMobile ? 'flex flex-col items-center justify-center py-2 px-2' : 'flex justify-between items-center py-2 px-2'} rounded-xl`} style={{ backgroundColor: metricBgColor }}>
              <div className={`flex items-center ${isMobile ? 'mb-1' : 'min-w-0 flex-shrink'}`}>
                <div className={`${isMobile ? 'w-5 h-5' : 'w-6 h-6'} rounded-lg flex items-center justify-center ${isMobile ? 'mr-1.5' : 'mr-2'} flex-shrink-0`} style={{ backgroundColor: purpleBg }}>
                  <img src={MetricPowerIcon} alt="Power" className={`${isMobile ? 'w-2.5 h-2.5' : 'w-3 h-3'}`} />
                </div>
                <span className={`${isMobile ? 'text-[9px]' : 'text-xs'} font-medium whitespace-nowrap`} style={{ color: secondaryTextColor }}>Power</span>
              </div>
              <span className={`${isMobile ? 'text-[10px]' : 'text-sm'} text-purple-600 font-bold whitespace-nowrap ${isMobile ? 'mt-0.5' : 'ml-1 flex-shrink-0'}`}>
                {Math.abs((battery.voltage || 0) * (battery.current || 0)).toFixed(0)} W
              </span>
            </div>
          </div>
        </div>


        {/* Cell voltage grid */}
        {cellData && cellData.cells && cellData.cells.length > 0 && (
          <div className="mt-10">
            <button
              onClick={() => setExpandedCellVoltages(prev => ({ ...prev, [battery.power]: !prev[battery.power] }))}
              className="flex items-center justify-between w-full mb-6 hover:opacity-80 transition-opacity"
            >
              <div className="flex items-center">
                <div className="w-8 h-8 rounded-lg flex items-center justify-center mr-3" style={{ backgroundColor: indigoBg }}>
                  <img src={BatteryCellIcon} alt="Cell Voltages" className="w-5 h-5" />
                </div>
                <h4 className={`${isMobile ? 'text-base' : 'text-lg'} font-semibold whitespace-nowrap`} style={{ color: textColor }}>Cell Voltages</h4>
              </div>
              <ChevronDown 
                className={`${isMobile ? 'w-4 h-4' : 'w-5 h-5'} transition-transform duration-300`}
                style={{ 
                  color: textColor,
                  transform: expandedCellVoltages[battery.power] ? 'rotate(180deg)' : 'rotate(0deg)'
                }}
              />
            </button>
            <div 
              className={`grid grid-cols-5 ${isMobile ? 'gap-2' : 'gap-4'} overflow-hidden transition-all duration-300 ease-in-out ${
                expandedCellVoltages[battery.power] 
                  ? 'max-h-[500px] opacity-100' 
                  : 'max-h-0 opacity-0'
              }`}
            >
              {cellData.cells.map((cell) => {
                const isLowVoltage = cell.voltage && cellData.voltage_min && 
                  (cell.voltage - cellData.voltage_min) > (cellData.voltage_delta || 0) * 0.3
                
                // Calculate cell SOC based on voltage (simplified)
                const cellSoc = cell.voltage ? Math.min(100, Math.max(0, ((cell.voltage - 3.0) / 0.4) * 100)) : 0
                const fillWidth = (cellSoc / 100) * 12
                const cellBgColor = theme === 'dark' ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.02)'
                const cellHoverBgColor = theme === 'dark' ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.05)'
                const cellBadgeBg = theme === 'dark' ? 'rgba(255, 255, 255, 0.1)' : 'rgba(255, 255, 255, 1)'
                const cellBadgeBorder = theme === 'dark' ? 'rgba(99, 102, 241, 0.3)' : 'rgba(199, 210, 254, 1)'
                
                return (
                  <div 
                    key={cell.cell} 
                    className={`flex flex-col items-center space-y-2 ${isMobile ? 'p-2' : 'p-3'} rounded-xl transition-colors duration-200`}
                    style={{ 
                      backgroundColor: cellBgColor,
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.backgroundColor = cellHoverBgColor
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.backgroundColor = cellBgColor
                    }}
                  >
                    <div className="relative">
                      <img src={BatteryCellIcon} alt={`Cell ${cell.cell}`} className={isMobile ? 'w-10 h-10' : 'w-12 h-12'} style={{ marginTop: isMobile ? '4px' : '6px' }} />
                      <div 
                        className={`absolute ${isMobile ? '-top-0.5 -right-0.5' : '-top-1 -right-1'} ${isMobile ? 'w-5 h-5' : 'w-6 h-6'} rounded-full flex items-center justify-center ${isMobile ? 'text-[8px]' : 'text-xs'} font-bold border-2`}
                        style={{
                          backgroundColor: cellBadgeBg,
                          borderColor: cellBadgeBorder,
                          color: theme === 'dark' ? '#818cf8' : '#4f46e5',
                        }}
                      >
                        {cell.cell}
                      </div>
                    </div>
                    <div className={`${isMobile ? 'text-[9px]' : 'text-xs'} font-mono font-semibold whitespace-nowrap ${isLowVoltage ? 'text-red-600' : 'text-indigo-600'}`}>
                      {cell.voltage?.toFixed(3) || '0.000'} V
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </>
    )
  }

  if (loading) {
    return (
      <div className="p-6" style={{ color: textColor }}>
        Loading battery data…
      </div>
    )
  }
  if (error || !bank) {
    return (
      <div className="p-6" style={{ color: secondaryTextColor }}>
        {error || 'No battery data available'}
      </div>
    )
  }

  return (
    <div className="space-y-6" style={{ backgroundColor: pageBackgroundColor }}>
      <div 
        className="rounded-2xl p-8 shadow-lg border"
        style={{
          backgroundColor: cardBackgroundColor,
          boxShadow: `0px 4px 40px ${boxShadowColor}`,
          borderColor: borderColor,
        }}
      >
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center">
            <div 
              className="w-12 h-12 rounded-xl flex items-center justify-center mr-4"
              style={{ backgroundColor: theme === 'dark' ? 'rgba(59, 130, 246, 0.2)' : 'rgba(219, 234, 254, 1)' }}
            >
              <img src={BatteryPackIcon} alt="Battery Pack" className="w-8 h-8" />
            </div>
            <h2 className={`${isMobile ? 'text-lg' : 'text-2xl'} font-bold whitespace-nowrap`} style={{ color: textColor }}>Overview</h2>
          </div>
          <div className="text-sm">
            <span 
              className={`${isMobile ? 'px-2 py-1 text-[10px]' : 'px-4 py-2 text-sm'} rounded-full font-semibold shadow-sm whitespace-nowrap`}
              style={{
                backgroundColor: bank.current && bank.current > 0 
                  ? (theme === 'dark' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(254, 226, 226, 1)')
                  : (theme === 'dark' ? 'rgba(59, 130, 246, 0.2)' : 'rgba(219, 234, 254, 1)'),
                color: bank.current && bank.current > 0
                  ? (theme === 'dark' ? '#fca5a5' : '#b91c1c')
                  : (theme === 'dark' ? '#93c5fd' : '#1e40af'),
                border: bank.current && bank.current > 0
                  ? (theme === 'dark' ? '1px solid rgba(239, 68, 68, 0.3)' : '1px solid rgba(185, 28, 28, 0.2)')
                  : (theme === 'dark' ? '1px solid rgba(59, 130, 246, 0.3)' : '1px solid rgba(30, 64, 175, 0.2)'),
              }}
            >
              {bank.current && bank.current > 0 ? 'CHARGING' : 'DISCHARGING'}
            </span>
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="space-y-2">
            <div className={`${isMobile ? 'text-xs' : 'text-sm'} whitespace-nowrap`} style={{ color: secondaryTextColor }}>Voltage</div>
            <ProgressBar 
              value={bank.voltage} 
              max={60} 
              unit="V" 
              color="bg-green-500"
              format={(v) => v.toFixed(2)}
              theme={theme}
            />
          </div>
          <div className="space-y-2">
            <div className={`${isMobile ? 'text-xs' : 'text-sm'} whitespace-nowrap`} style={{ color: secondaryTextColor }}>SOC</div>
            <ProgressBar 
              value={bank.soc} 
              max={100} 
              unit="%" 
              color={bank.soc && bank.soc < 20 ? "bg-red-500" : bank.soc && bank.soc < 50 ? "bg-yellow-500" : "bg-green-500"}
              format={(v) => v.toFixed(0)}
              theme={theme}
            />
          </div>
          <div className="space-y-2">
            <div className={`${isMobile ? 'text-xs' : 'text-sm'} whitespace-nowrap`} style={{ color: secondaryTextColor }}>Temperature</div>
            <ProgressBar 
              value={bank.temperature} 
              max={60} 
              unit="°C" 
              color={bank.temperature && bank.temperature > 40 ? "bg-red-500" : "bg-orange-500"}
              format={(v) => v.toFixed(1)}
              theme={theme}
            />
          </div>
          <div className="space-y-2">
            <div className={`${isMobile ? 'text-xs' : 'text-sm'} whitespace-nowrap`} style={{ color: secondaryTextColor }}>Power</div>
            <ProgressBar 
              value={Math.abs((bank.voltage || 0) * (bank.current || 0))} 
              max={5000} 
              unit="W" 
              color="bg-red-500"
              format={(v) => v.toFixed(0)}
              theme={theme}
            />
          </div>
        </div>
        <div className={`mt-4 grid grid-cols-2 md:grid-cols-4 gap-4 ${isMobile ? 'text-xs' : 'text-sm'}`}>
          <div className="whitespace-nowrap" style={{ color: secondaryTextColor }}>
            Batteries: <span className="font-semibold" style={{ color: textColor }}>{bank.batteries_count}</span>
          </div>
          <div className="whitespace-nowrap" style={{ color: secondaryTextColor }}>
            Cells/Battery: <span className="font-semibold" style={{ color: textColor }}>{bank.cells_per_battery}</span>
          </div>
          <div className="whitespace-nowrap" style={{ color: secondaryTextColor }}>
            Total Cells: <span className="font-semibold" style={{ color: textColor }}>{bank.batteries_count * bank.cells_per_battery}</span>
          </div>
          <div className="whitespace-nowrap" style={{ color: secondaryTextColor }}>
            Last Update: <span className="font-semibold" style={{ color: textColor }}>{new Date(bank.ts).toLocaleTimeString()}</span>
          </div>
        </div>
      </div>

      {isMobile ? (
        <div className="flex flex-col gap-4">
          {bank.devices.map((battery) => {
            // Find corresponding cell data for this battery
            const cellData = bank.cells_data?.find(cd => cd.power === battery.power)
            
            return (
              <div 
                key={battery.power} 
                className="relative rounded-lg p-4 shadow-lg border w-full"
                style={{
                  backgroundColor: cardBackgroundColor,
                  boxShadow: `0px 4px 40px ${boxShadowColor}`,
                  borderColor: borderColor,
                }}
              >
                {renderBatteryCard(battery, cellData, isMobile, isCompact)}
              </div>
            )
          })}
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {bank.devices.map((battery) => {
            // Find corresponding cell data for this battery
            const cellData = bank.cells_data?.find(cd => cd.power === battery.power)
            
            return (
              <div 
                key={battery.power} 
                className="relative rounded-2xl p-8 shadow-lg border hover:shadow-xl transition-shadow duration-300"
                style={{
                  backgroundColor: cardBackgroundColor,
                  boxShadow: `0px 4px 40px ${boxShadowColor}`,
                  borderColor: borderColor,
                }}
              >
                {renderBatteryCard(battery, cellData, isMobile, isCompact)}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}



