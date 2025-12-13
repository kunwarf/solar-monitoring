import React, { useState, useEffect, useContext } from 'react'
import { api } from '../lib/api'
import { TelemetryData } from '../types/telemetry'
import { ArrayContext } from '../ui/NewAppLayout'
import { TimePeriodFilter } from '../components/NewDashboard/TimePeriodFilter'
import { EnergyDistributionDiagram } from '../components/NewDashboard/EnergyDistributionDiagram'
import { HomeSummaryTiles } from '../components/NewDashboard/HomeSummaryTiles'
import { useMobile } from '../hooks/useMobile'

type Period = 'today' | 'week' | 'month' | 'year' | 'custom'

export const NewDashboardPage: React.FC = () => {
  const { selectedArray, setSelectedArray } = useContext(ArrayContext)
  const { isMobile } = useMobile()
  const [selectedPeriod, setSelectedPeriod] = useState<Period>('today')
  const [telemetry, setTelemetry] = useState<TelemetryData | null>(null)
  const [dailyEnergy, setDailyEnergy] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [selectedInverter, setSelectedInverter] = useState<string>('all')
  const [selectedHomeId, setSelectedHomeId] = useState<string | null>(null)

  // Fetch current telemetry (power values, SOC, etc.)
  useEffect(() => {
    let isMounted = true
    let intervalId: NodeJS.Timeout | null = null
    
    const fetchTelemetry = async () => {
      try {
        let response: any
        if (selectedArray) {
          // Array-level: use array-specific endpoint
          const inverterParam = selectedInverter === 'all' ? 'all' : selectedInverter
          response = await api.get(`/api/now?inverter_id=${inverterParam}&array_id=${selectedArray}`)
        } else {
          // System-level: use system aggregation endpoint
          response = await api.get('/api/system/now')
          if (response?.system) {
            // Map system telemetry to match expected format
            const home = response.system
            if (isMounted) {
              setTelemetry({
                ts: home.ts,
                pv_power_w: home.total_pv_power_w,
                load_power_w: home.total_load_power_w,
                grid_power_w: home.total_grid_power_w,
                batt_power_w: home.total_batt_power_w,
                batt_soc_pct: home.avg_batt_soc_pct,
                extra: {
                  arrays: home.arrays,
                  meters: home.meters,
                  _metadata: home._metadata || home.metadata,
                }
              })
            }
            return
          }
        }
        
        if (isMounted && response?.now) {
          setTelemetry(response.now)
        }
      } catch (error) {
        console.error('Error fetching telemetry:', error)
      }
    }

    fetchTelemetry()
    intervalId = setInterval(fetchTelemetry, 5000) // Update every 5 seconds
    
    return () => {
      isMounted = false
      if (intervalId) {
        clearInterval(intervalId)
      }
    }
  }, [selectedInverter, selectedArray])

  // Fetch daily energy data from dedicated endpoint
  useEffect(() => {
    const fetchDailyEnergy = async () => {
      try {
        console.log('Fetching daily energy data...')
        setLoading(true)
        // Use "all" if no specific inverter selected, or pass the specific inverter_id
        // For home-level view, use "all" to aggregate across all inverters
        const inverterParam = selectedInverter && selectedInverter !== 'all' ? selectedInverter : 'all'
        const url = `/api/energy/daily?inverter_id=${inverterParam}`
        console.log('Daily energy API URL:', url)
        
        const response: any = await api.get(url)
        
        console.log('Daily energy API response:', response)
        
        if (response?.daily_summary) {
          console.log('Daily energy summary:', response.daily_summary)
          setDailyEnergy(response.daily_summary)
        } else {
          console.warn('No daily_summary in response:', response)
        }
      } catch (error) {
        console.error('Error fetching daily energy:', error)
        // Fallback to using telemetry data if daily energy endpoint fails
        if (telemetry) {
          console.log('Falling back to telemetry data for energy values')
        }
      } finally {
        setLoading(false)
      }
    }

    console.log('Setting up daily energy fetch effect')
    fetchDailyEnergy()
    // Refresh daily energy every 30 seconds (less frequent than telemetry)
    const interval = setInterval(fetchDailyEnergy, 30000)
    return () => {
      console.log('Cleaning up daily energy interval')
      clearInterval(interval)
    }
  }, [selectedInverter, selectedArray])


  // Helper to convert Wh to kWh
  const toKwh = (val: number | undefined | null): number => {
    if (!val || val === 0) return 0
    return val > 1000 ? val / 1000 : val
  }

  // Use daily energy data from dedicated endpoint, fallback to telemetry if not available
  const solarEnergy = dailyEnergy?.total_solar_kwh ?? toKwh((telemetry as any)?.today_energy) ?? toKwh((telemetry as any)?.extra?.today_energy) ?? 0
  const gridImport = dailyEnergy?.total_grid_import_kwh ?? toKwh((telemetry as any)?.today_import_energy) ?? toKwh((telemetry as any)?.extra?.today_import_energy) ?? toKwh((telemetry as any)?.extra?.today_grid_import_energy) ?? 0
  const gridExport = dailyEnergy?.total_grid_export_kwh ?? toKwh((telemetry as any)?.today_export_energy) ?? toKwh((telemetry as any)?.extra?.today_export_energy) ?? toKwh((telemetry as any)?.extra?.today_grid_export_energy) ?? 0
  const batteryCharge = dailyEnergy?.total_battery_charge_kwh ?? toKwh((telemetry as any)?.today_battery_charge_energy) ?? toKwh((telemetry as any)?.extra?.today_battery_charge_energy) ?? toKwh((telemetry as any)?.extra?.battery_daily_charge_energy) ?? 0
  const batteryDischarge = dailyEnergy?.total_battery_discharge_kwh ?? toKwh((telemetry as any)?.today_battery_discharge_energy) ?? toKwh((telemetry as any)?.extra?.today_battery_discharge_energy) ?? toKwh((telemetry as any)?.extra?.battery_daily_discharge_energy) ?? 0
  const loadEnergy = dailyEnergy?.total_load_kwh ?? toKwh((telemetry as any)?.today_load_energy) ?? toKwh((telemetry as any)?.extra?.today_load_energy) ?? toKwh((telemetry as any)?.extra?.daily_energy_to_eps) ?? 0

  // Current power values
  const solarPower = telemetry?.pv_power_w ?? 0
  const loadPower = telemetry?.load_power_w ?? 0
  const gridPower = telemetry?.grid_power_w ?? 0
  const batteryPowerRaw = telemetry?.batt_power_w ?? 0
  const batteryPower = Math.abs(batteryPowerRaw)
  const isBatteryCharging = batteryPowerRaw > 0
  const isBatteryDischarging = batteryPowerRaw < 0
  
  // Battery SOC (State of Charge) - percentage (0-100)
  const batterySOC = telemetry?.batt_soc_pct ?? 0
  // Battery temperature - Celsius
  const batteryTemp = telemetry?.batt_temp_c
    

  const handleHomeSelect = (homeId: string | null) => {
    setSelectedHomeId(homeId)
    // When home is selected, clear array selection to show home-level data
    if (homeId) {
      setSelectedArray(null)
    }
  }

  // Update selectedHomeId when array selection changes
  useEffect(() => {
    if (selectedArray) {
      // Array is selected, clear home selection
      setSelectedHomeId(null)
    } else {
      // No array selected, show home view
      setSelectedHomeId('home')
    }
  }, [selectedArray])

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900" style={{ minHeight: '100vh', paddingBottom: '2rem' }}>
      {/* Top Bar with Time Period Filter */}
      <div className={`bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 ${isMobile ? 'px-3 py-3' : 'px-6 py-4'}`}>
        <TimePeriodFilter
          selectedPeriod={selectedPeriod}
          onPeriodChange={setSelectedPeriod}
        />
      </div>

      {/* Main Content */}
      <div className={`${isMobile ? 'p-3 pb-8' : 'p-6 pb-12'}`}>
        <div className="max-w-7xl mx-auto">
          {/* Home Summary Tiles */}
          <HomeSummaryTiles
            onHomeSelect={handleHomeSelect}
            selectedHomeId={selectedHomeId || (selectedArray === null ? 'home' : null)}
            selectedPeriod={selectedPeriod}
          />

        </div>
      </div>
    </div>
  )
}

