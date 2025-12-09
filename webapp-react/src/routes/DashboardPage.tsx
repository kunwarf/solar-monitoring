import React, { useState, useEffect, useContext } from 'react'
import { api } from '../lib/api'
import { TelemetryData, TelemetryResponse, ArrayTelemetryResponse, ArrayTelemetryData } from '../types/telemetry'
import { PowerFlowChart } from '../components/PowerFlowChart'
import { PowerFlowDiagram } from '../components/PowerFlowDiagram'
import { EnergyFlowPro } from '../components/EnergyFlowPro'
import { SolarSystemDiagram } from '../components/SolarSystemDiagram'
import { PVForecastChart } from '../components/PVForecastChart'
import { Overview24hChart } from '../components/Overview24hChart'
import { SelfSufficiencyBar } from '../components/SelfSufficiencyBar'
import { DetailedTelemetry } from '../components/DetailedTelemetry'
import { FilterBar } from '../components/FilterBar'
import { SummaryBar } from '../components/SummaryBar'
import { MobileSummaryBar } from '../components/MobileSummaryBar'
import { ArrayCard } from '../components/ArrayCard'
import { SchedulerTimeline } from '../components/SchedulerTimeline'
import { CompactMetricTile } from '../components/CompactMetricTile'
import { SwipeableCarousel } from '../components/SwipeableCarousel'
import { KPICard } from '../components/KPICard'
import { BatteryPackCard } from '../components/BatteryPackCard'
import { HealthStatusCard } from '../components/HealthStatusCard'
import { useMobile } from '../hooks/useMobile'
import { generateDemoTelemetry } from '../utils/demoData'
import { ArrayContext } from '../ui/AppLayout'
import { TimePeriodFilter } from '../components/NewDashboard/TimePeriodFilter'
import { EnergyDistributionDiagram } from '../components/NewDashboard/EnergyDistributionDiagram'
import { PowerGauge } from '../components/NewDashboard/PowerGauge'

type Period = 'today' | 'week' | 'month' | 'year' | 'custom'

export const DashboardPage: React.FC = () => {
  const { selectedArray } = useContext(ArrayContext)
  const { isMobile, isCompact } = useMobile()
  const [dashboardType, setDashboardType] = useState<'energy' | 'detailed'>('energy')
  const [telemetry, setTelemetry] = useState<TelemetryData | null>(null)
  const [arrayTelemetry, setArrayTelemetry] = useState<ArrayTelemetryData | null>(null)
  const [loading, setLoading] = useState(true)
  const [isDemoMode, setIsDemoMode] = useState(false)
  const [inverters, setInverters] = useState<string[]>([])
  const [selectedInverter, setSelectedInverter] = useState<string>('all')
  const [viewMode, setViewMode] = useState<'inverter' | 'array'>('inverter')
  const [arrays, setArrays] = useState<any[]>([])
  const [dailyEnergy, setDailyEnergy] = useState<{ solar: number; load: number }>({ solar: 0, load: 0 })
  const [dailyEnergyData, setDailyEnergyData] = useState<any>(null)
  const [selectedDate, setSelectedDate] = useState<string | undefined>(undefined) // Default to today (undefined = current date)
  const [selectedPeriod, setSelectedPeriod] = useState<Period>('today')

  const fetchDailyEnergy = async () => {
    try {
      if (selectedArray && viewMode === 'array') {
        // Fetch array daily energy
        const response: any = await api.get(`/api/arrays/${selectedArray}/energy/daily`)
        if (response?.daily_summary) {
          const summary = response.daily_summary
          setDailyEnergy({
            solar: summary.solar_energy_kwh || summary.solar || 0,
            load: summary.load_energy_kwh || summary.load || 0
          })
          // Set full daily energy data for SelfSufficiencyBar
          setDailyEnergyData({
            solar_energy_kwh: summary.solar_energy_kwh || summary.solar || 0,
            load_energy_kwh: summary.load_energy_kwh || summary.load || 0,
            battery_charge_energy_kwh: summary.battery_charge_energy_kwh || 0,
            battery_discharge_energy_kwh: summary.battery_discharge_energy_kwh || 0,
            grid_import_energy_kwh: summary.grid_import_energy_kwh || 0,
            grid_export_energy_kwh: summary.grid_export_energy_kwh || 0,
          })
        }
      } else {
        // Fetch inverter daily energy from telemetry or API
        // When selectedInverter is 'all', API will aggregate all inverters
        const inverterParam = selectedInverter === 'all' ? 'all' : selectedInverter
        const response: any = await api.get(
          selectedArray 
            ? `/api/now?inverter_id=${inverterParam}&array_id=${selectedArray}`
            : `/api/now?inverter_id=${inverterParam}`
        )
        if (response?.now) {
          const now = response.now
          // Helper to convert Wh to kWh if needed
          const toKwh = (val: number | undefined | null): number => {
            if (!val || val === 0) return 0;
            return val > 1000 ? val / 1000 : val;
          };
          
          const solar = toKwh(now.today_energy) || toKwh(now.today_solar_energy) || toKwh((now as any).extra?.today_energy) || 0;
          const load = toKwh(now.today_load_energy) || toKwh((now as any).extra?.today_load_energy) || 0;
          const gridImport = toKwh(now.today_import_energy) || toKwh((now as any).extra?.today_import_energy) || 0;
          const gridExport = toKwh(now.today_export_energy) || toKwh((now as any).extra?.today_export_energy) || 0;
          const battCharge = toKwh((now as any).today_battery_charge_energy) || toKwh((now as any).extra?.today_battery_charge_energy) || 0;
          const battDischarge = toKwh((now as any).today_battery_discharge_energy) || toKwh((now as any).extra?.today_battery_discharge_energy) || 0;
          
          console.log('Daily energy from API:', { solar, load, gridImport, gridExport, battCharge, battDischarge, raw: now });
          
          setDailyEnergy({
            solar,
            load
          })
          // Set full daily energy data for SelfSufficiencyBar
          setDailyEnergyData({
            solar_energy_kwh: solar,
            load_energy_kwh: load,
            battery_charge_energy_kwh: battCharge,
            battery_discharge_energy_kwh: battDischarge,
            grid_import_energy_kwh: gridImport,
            grid_export_energy_kwh: gridExport,
          })
        } else {
          console.warn('No daily energy data in response:', response);
        }
      }
    } catch (err) {
      console.warn('Failed to fetch daily energy:', err)
      // Fallback: try to get from current telemetry state
      if (telemetry) {
        setDailyEnergy({
          solar: (telemetry as any).today_energy || (telemetry as any).today_solar_energy || 0,
          load: (telemetry as any).today_load_energy || 0
        })
        setDailyEnergyData({
          solar_energy_kwh: (telemetry as any).today_energy || (telemetry as any).today_solar_energy || 0,
          load_energy_kwh: (telemetry as any).today_load_energy || 0,
          battery_charge_energy_kwh: (telemetry as any).today_battery_charge_energy || 0,
          battery_discharge_energy_kwh: (telemetry as any).today_battery_discharge_energy || 0,
          grid_import_energy_kwh: telemetry.today_import_energy || 0,
          grid_export_energy_kwh: telemetry.today_export_energy || 0,
        })
      }
    }
  }

  const fetchTelemetry = async () => {
    try {
      if (selectedArray && viewMode === 'array') {
        // Fetch array telemetry
        const response: ArrayTelemetryResponse = await api.get(`/api/arrays/${selectedArray}/now`)
        if (response.now) {
          // Convert array telemetry to TelemetryData format for compatibility
          const tel: TelemetryData = {
            ts: response.now.ts,
            pv_power_w: response.now.pv_power_w,
            load_power_w: response.now.load_power_w,
            grid_power_w: response.now.grid_power_w,
            batt_power_w: response.now.batt_power_w,
            batt_soc_pct: response.now.batt_soc_pct,
            batt_voltage_v: response.now.batt_voltage_v,
            batt_current_a: response.now.batt_current_a,
            _metadata: {
              inverter_count: response.now._metadata?.inverter_count,
              is_inverter_array: true,
            },
            extra: {
              array_id: response.now.array_id,
              inverters: response.now.inverters,
              packs: response.now.packs,
            }
          }
          setTelemetry(tel)
          setArrayTelemetry(response.now)
          // Update daily energy from telemetry
          const now = response.now as any
          // Helper to convert Wh to kWh if needed
          const toKwh = (val: number | undefined | null): number => {
            if (!val || val === 0) return 0;
            return val > 1000 ? val / 1000 : val;
          };
          
          const solar = toKwh(now.today_energy) || toKwh(now.today_solar_energy) || toKwh(now.extra?.today_energy) || 0;
          const load = toKwh(now.today_load_energy) || toKwh(now.extra?.today_load_energy) || 0;
          const gridImport = toKwh(now.today_import_energy) || toKwh(now.extra?.today_import_energy) || 0;
          const gridExport = toKwh(now.today_export_energy) || toKwh(now.extra?.today_export_energy) || 0;
          const battCharge = toKwh(now.today_battery_charge_energy) || toKwh(now.extra?.today_battery_charge_energy) || 0;
          const battDischarge = toKwh(now.today_battery_discharge_energy) || toKwh(now.extra?.today_battery_discharge_energy) || 0;
          
          console.log('Daily energy from array telemetry:', { solar, load, gridImport, gridExport, battCharge, battDischarge, raw: now });
          
          setDailyEnergy({
            solar,
            load
          })
          setDailyEnergyData({
            solar_energy_kwh: solar,
            load_energy_kwh: load,
            battery_charge_energy_kwh: battCharge,
            battery_discharge_energy_kwh: battDischarge,
            grid_import_energy_kwh: gridImport,
            grid_export_energy_kwh: gridExport,
          })
        }
        setIsDemoMode(false)
      } else {
        // Fetch inverter telemetry
        // When selectedInverter is 'all', API will aggregate all inverters
        const inverterParam = selectedInverter === 'all' ? 'all' : selectedInverter
        const url = selectedArray 
          ? `/api/now?inverter_id=${inverterParam}&array_id=${selectedArray}`
          : `/api/now?inverter_id=${inverterParam}`
        console.log('Fetching telemetry:', { selectedInverter, inverterParam, url })
        const response: TelemetryResponse = await api.get(url)
        console.log('Telemetry response:', { hasNow: !!response.now, inverterId: response.inverter_id, now: response.now })
        if (response.now) {
          setTelemetry(response.now)
        } else {
          console.warn('No telemetry data in response:', response)
        }
        setArrayTelemetry(null)
        // Update daily energy from telemetry
        if (response.now) {
          const now = response.now as any
          // Helper to convert Wh to kWh if needed
          const toKwh = (val: number | undefined | null): number => {
            if (!val || val === 0) return 0;
            return val > 1000 ? val / 1000 : val;
          };
          
          const solar = toKwh(now.today_energy) || toKwh(now.today_solar_energy) || toKwh(now.extra?.today_energy) || 0;
          const load = toKwh(now.today_load_energy) || toKwh(now.extra?.today_load_energy) || 0;
          const gridImport = toKwh(now.today_import_energy) || toKwh(now.extra?.today_import_energy) || 0;
          const gridExport = toKwh(now.today_export_energy) || toKwh(now.extra?.today_export_energy) || 0;
          const battCharge = toKwh(now.today_battery_charge_energy) || toKwh(now.extra?.today_battery_charge_energy) || 0;
          const battDischarge = toKwh(now.today_battery_discharge_energy) || toKwh(now.extra?.today_battery_discharge_energy) || 0;
          
          console.log('Daily energy from inverter telemetry (fetchTelemetry):', { solar, load, gridImport, gridExport, battCharge, battDischarge, raw: now });
          
          setDailyEnergy({
            solar,
            load
          })
          setDailyEnergyData({
            solar_energy_kwh: solar,
            load_energy_kwh: load,
            battery_charge_energy_kwh: battCharge,
            battery_discharge_energy_kwh: battDischarge,
            grid_import_energy_kwh: gridImport,
            grid_export_energy_kwh: gridExport,
          })
        }
        setIsDemoMode(false)
      }
    } catch (err) {
      console.error('Error fetching telemetry:', err)
      setTelemetry(generateDemoTelemetry())
      setArrayTelemetry(null)
      setIsDemoMode(true)
    } finally {
      setLoading(false)
    }
  }

  const fetchInverters = async () => {
    try {
      const resp: any = await api.get('/api/inverters')
      const ids: string[] = Array.isArray(resp?.inverters) 
        ? resp.inverters.map((inv: any) => typeof inv === 'string' ? inv : (inv.id || inv))
        : []
      setInverters(ids)
      // If previously selected inverter no longer exists, reset to 'all'
      if (selectedInverter !== 'all' && !ids.includes(selectedInverter)) {
        setSelectedInverter('all')
      }
    } catch (e) {
      setInverters([])
    }
  }

  const fetchArrays = async () => {
    try {
      const resp: any = await api.get('/api/arrays')
      if (resp?.arrays) {
        setArrays(resp.arrays)
      }
    } catch (e) {
      setArrays([])
    }
  }

  useEffect(() => {
    fetchInverters()
    fetchArrays()
  }, [])

  useEffect(() => {
    fetchTelemetry()
    fetchDailyEnergy()
    const interval = setInterval(() => {
      fetchTelemetry()
      fetchDailyEnergy()
    }, 5000) // Refresh every 5 seconds
    return () => clearInterval(interval)
  }, [selectedInverter, selectedArray, viewMode])

  const formatPower = (watts?: number) => {
    if (watts === undefined || watts === null) return '0 W'
    if (watts >= 1000) return `${(watts / 1000).toFixed(1)} kW`
    return `${watts.toFixed(0)} W`
  }

  const formatPercentage = (percent?: number) => {
    if (percent === undefined || percent === null) return '0%'
    return `${percent.toFixed(0)}%`
  }

  const handlePeriodChange = (period: Period) => {
    setSelectedPeriod(period)
    
    if (period === 'today') {
      setSelectedDate(undefined) // Today = current date
    } else if (period === 'week') {
      // Set to start of current week
      const today = new Date()
      const dayOfWeek = today.getDay()
      const diff = today.getDate() - dayOfWeek
      const startOfWeek = new Date(today.setDate(diff))
      startOfWeek.setHours(0, 0, 0, 0)
      setSelectedDate(startOfWeek.toISOString().split('T')[0])
    } else if (period === 'month') {
      // Set to start of current month
      const today = new Date()
      const startOfMonth = new Date(today.getFullYear(), today.getMonth(), 1)
      setSelectedDate(startOfMonth.toISOString().split('T')[0])
    } else if (period === 'year') {
      // Set to start of current year
      const today = new Date()
      const startOfYear = new Date(today.getFullYear(), 0, 1)
      setSelectedDate(startOfYear.toISOString().split('T')[0])
    } else if (period === 'custom') {
      // For custom, we could open a date picker, but for now just keep current date
      // In a full implementation, you'd show a date range picker here
    }
  }

  // Helper to convert Wh to kWh
  const toKwh = (val: number | undefined | null): number => {
    if (!val || val === 0) return 0
    return val > 1000 ? val / 1000 : val
  }

  // Energy distribution data (in kWh)
  const gridImportKwh = toKwh((telemetry as any)?.today_import_energy) || 0
  const gridExportKwh = toKwh((telemetry as any)?.today_export_energy) || 0
  const solarKwh = toKwh((telemetry as any)?.today_energy) || toKwh((telemetry as any)?.today_solar_energy) || 0
  
  const solarEnergy = solarKwh || 87.8
  const gridExport = gridExportKwh || 29.4
  const gridImport = gridImportKwh || 17.2
  const batteryCharge = toKwh((telemetry as any)?.today_battery_charge_energy) || 0.7
  const batteryDischarge = toKwh((telemetry as any)?.today_battery_discharge_energy) || 21.5
  const loadEnergy = toKwh((telemetry as any)?.today_load_energy) || 87.8

  // Current power values
  const solarPower = telemetry?.pv_power_w || 1200
  const loadPower = telemetry?.load_power_w || 1200
  const gridPower = telemetry?.grid_power_w || 1200
  const batteryPower = Math.abs(telemetry?.batt_power_w || 1200)

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-lg text-gray-700">Loading dashboard...</div>
      </div>
    )
  }

  const { setSelectedArray } = useContext(ArrayContext)

  return (
    <div 
      className={`overflow-x-hidden relative w-full min-h-screen ${isMobile ? 'p-4' : ''}`}
      style={{ 
        backgroundColor: '#1B2234',
        position: 'relative'
      }}
    >
      {/* Gradient Overlay */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: 'linear-gradient(99.07deg, rgba(0, 212, 151, 0.1) -3.97%, rgba(15, 145, 255, 0.1) 48.41%, rgba(205, 115, 255, 0.1) 97.94%)',
        }}
      />
      
      {/* Main Content */}
      {isMobile ? (
        /* Mobile Layout */
        <div className="flex flex-col gap-4 pt-4 pb-8">
          {/* Time Period Filter Bar - Mobile */}
          <div className="w-full flex justify-center px-2">
            <TimePeriodFilter
              selectedPeriod={selectedPeriod}
              onPeriodChange={handlePeriodChange}
            />
          </div>

          {/* Energy Distribution - Mobile */}
          <div className="w-full flex justify-center">
            <EnergyDistributionDiagram
              solarEnergy={solarEnergy}
              gridExport={gridExport}
              gridImport={gridImport}
              batteryCharge={batteryCharge}
              batteryDischarge={batteryDischarge}
              loadEnergy={loadEnergy}
            />
          </div>

          {/* Power Gauges - Mobile Grid */}
          <div className="grid grid-cols-2 gap-3 w-full">
            <PowerGauge
              title="Solar Generation"
              value={solarPower}
              color="#FFD600"
            />
            <PowerGauge
              title="Load"
              value={loadPower}
              color="#3b82f6"
            />
            <PowerGauge
              title="Grid"
              value={Math.abs(gridPower)}
              color="#ec4899"
            />
            <PowerGauge
              title={batteryPower >= 0 ? "Battery Charging" : "Battery Consumption"}
              value={Math.abs(batteryPower)}
              color="#10b981"
            />
          </div>
        </div>
      ) : (
        /* Desktop Layout */
        <div className="absolute" style={{ left: '0px', top: '97px', width: '1600px' }}>
          {/* Energy Distribution with Time Period Filter on top */}
          <div className="absolute" style={{ left: '195px', top: '0px' }}>
            {/* Time Period Filter Bar */}
            <div 
              style={{
                width: '628px',
                height: '32px',
                marginBottom: '32px',
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center'
              }}
            >
              <TimePeriodFilter
                selectedPeriod={selectedPeriod}
                onPeriodChange={handlePeriodChange}
              />
            </div>
            
            <EnergyDistributionDiagram
              solarEnergy={solarEnergy}
              solarPower={solarPower}
              gridPower={gridPower}
              batteryPower={telemetry?.batt_power_w || 0}
              loadPower={loadPower}
              gridExport={gridExport}
              gridImport={gridImport}
              batteryCharge={batteryCharge}
              batteryDischarge={batteryDischarge}
              loadEnergy={loadEnergy}
            />
          </div>

          {/* Bottom Row - Power Gauges */}
          <div className="absolute" style={{ left: '195px', top: '678px' }}>
            <PowerGauge
              title="Solar Generation"
              value={solarPower}
              color="#FFD600"
            />
          </div>
          <div className="absolute" style={{ left: '519px', top: '678px' }}>
            <PowerGauge
              title="Load"
              value={loadPower}
              color="#3b82f6"
            />
          </div>
          <div className="absolute" style={{ left: '843px', top: '678px' }}>
            <PowerGauge
              title="Grid"
              value={Math.abs(gridPower)}
              color="#ec4899"
            />
          </div>
          <div className="absolute" style={{ left: '1167px', top: '678px' }}>
            <PowerGauge
              title={batteryPower >= 0 ? "Battery Charging" : "Battery Discharging"}
              value={Math.abs(batteryPower)}
              color="#10b981"
            />
          </div>
        </div>
      )}
    </div>
  )
}

