import React, { useState, useEffect } from 'react'
import { api } from '../../lib/api'
import { useTheme } from '../../contexts/ThemeContext'
import { useMobile } from '../../hooks/useMobile'
import { Home, Zap, Battery, Sun, Activity, Gauge } from 'lucide-react'
import { EnergyDistributionDiagram } from './EnergyDistributionDiagram'

interface InverterData {
  inverter_id: string
  name?: string
  pv_power_w?: number
  load_power_w?: number
  grid_power_w?: number
  batt_power_w?: number
  batt_soc_pct?: number
}

interface ArrayData {
  array_id: string
  name?: string
  pv_power_w?: number
  load_power_w?: number
  grid_power_w?: number
  batt_power_w?: number
  batt_soc_pct?: number
  inverter_count?: number
  inverter_ids?: string[]  // List of inverter IDs in this array
  inverters?: InverterData[]  // Individual inverter telemetry
}

interface BatteryBankTelemetry {
  bank_id: string
  voltage?: number
  current?: number
  soc?: number
  temperature?: number
  batteries_count?: number
  charge_power_w?: number  // Positive = charging
  discharge_power_w?: number  // Positive = discharging
  time_to_charge_h?: number
  time_to_discharge_h?: number
}

interface BatteryBankArrayData {
  id: string
  name?: string
  battery_bank_ids: string[]
  attached_inverter_array_id?: string
  telemetry?: BatteryBankTelemetry
}

interface MeterData {
  meter_id: string
  power_w?: number
  voltage_v?: number
  current_a?: number
  frequency_hz?: number
}

interface SystemGroup {
  inverter_array: ArrayData
  battery_bank_array?: BatteryBankArrayData
}

interface DailyEnergy {
  solar_energy_kwh?: number
  load_energy_kwh?: number
  battery_charge_energy_kwh?: number
  battery_discharge_energy_kwh?: number
  grid_import_energy_kwh?: number
  grid_export_energy_kwh?: number
}

interface MonthlyEnergy {
  solar_energy_kwh?: number
  grid_import_energy_kwh?: number
  grid_export_energy_kwh?: number
}

interface FinancialMetrics {
  total_bill_pkr?: number
  total_saved_pkr?: number
  co2_prevented_kg?: number
}

interface HomeSummary {
  id: string
  name: string
  description?: string
  total_pv_power_w?: number
  total_load_power_w?: number
  total_grid_power_w?: number
  total_batt_power_w?: number
  avg_batt_soc_pct?: number
  daily_energy?: DailyEnergy
  monthly_energy?: MonthlyEnergy
  financial_metrics?: FinancialMetrics
  arrays?: ArrayData[]
  battery_bank_arrays?: BatteryBankArrayData[]
  meters?: MeterData[]
  systems?: SystemGroup[]
  array_count?: number
  inverter_count?: number
  battery_bank_count?: number
}

interface HomeSummaryTilesProps {
  onHomeSelect: (homeId: string | null) => void
  selectedHomeId: string | null
  selectedPeriod?: 'today' | 'week' | 'month' | 'year' | 'custom'
  customStartDate?: string | null
  customEndDate?: string | null
}

export const HomeSummaryTiles: React.FC<HomeSummaryTilesProps> = ({
  onHomeSelect,
  selectedHomeId,
  selectedPeriod = 'today',
  customStartDate = null,
  customEndDate = null
}) => {
  const { theme } = useTheme()
  const { isMobile } = useMobile()
  const [homes, setHomes] = useState<HomeSummary[]>([])
  const [loading, setLoading] = useState(true)

  const textColor = theme === 'dark' ? '#ffffff' : '#1f2937'
  const textSecondary = theme === 'dark' ? 'rgba(255, 255, 255, 0.7)' : '#6b7280'
  const cardBg = theme === 'dark' ? '#1f2937' : '#ffffff'
  const borderColor = theme === 'dark' ? '#374151' : '#e5e7eb'
  const selectedBorderColor = theme === 'dark' ? '#3b82f6' : '#2563eb'
  const hoverBg = theme === 'dark' ? '#374151' : '#f9fafb'

  useEffect(() => {
    let isMounted = true
    let intervalId: ReturnType<typeof setInterval> | null = null
    
    const fetchHomes = async () => {
      try {
        // Get home config from API
        const configRes: any = await api.get('/api/config')
        const config = configRes?.config || configRes
        
        // Get home telemetry for summary with period filter
        const periodParams = new URLSearchParams()
        periodParams.append('period', selectedPeriod)
        if (selectedPeriod === 'custom' && customStartDate && customEndDate) {
          periodParams.append('start_date', customStartDate)
          periodParams.append('end_date', customEndDate)
        }
        const systemTelemetryRes: any = await api.get(`/api/system/now?${periodParams.toString()}`).catch(() => null)
        
        if (!isMounted) return
        
        const homesList: HomeSummary[] = []
        
        if (config?.home) {
          const homeConfig = config.home
          const systemTel = systemTelemetryRes?.system
          
          // Count arrays, inverters, and battery banks
          const arrayCount = config?.arrays?.length || 0
          const inverterCount = config?.inverters?.length || 0
          const batteryBankCount = config?.battery_banks?.length || 0
          
          // Get array data from home telemetry
          const arrays: ArrayData[] = []
          if (systemTel?.arrays && Array.isArray(systemTel.arrays)) {
            for (const arr of systemTel.arrays) {
              const arrayConfig = config?.arrays?.find((a: any) => a.id === arr.array_id)
              const inverterIds = arrayConfig?.inverter_ids || []
              
              // Fetch individual inverter telemetry
              const inverters: InverterData[] = []
              if (inverterIds.length > 0) {
                for (const invId of inverterIds) {
                  try {
                    const invResponse: any = await api.get(`/api/now?inverter_id=${invId}`).catch(() => null)
                    if (invResponse?.now) {
                      const invConfig = config?.inverters?.find((inv: any) => inv.id === invId)
                      inverters.push({
                        inverter_id: invId,
                        name: invConfig?.name,
                        pv_power_w: invResponse.now.pv_power_w,
                        load_power_w: invResponse.now.load_power_w,
                        grid_power_w: invResponse.now.grid_power_w,
                        batt_power_w: invResponse.now.batt_power_w,
                        batt_soc_pct: invResponse.now.batt_soc_pct,
                      })
                    }
                  } catch (error) {
                    console.error(`Error fetching telemetry for inverter ${invId}:`, error)
                  }
                }
              }
              
              arrays.push({
                array_id: arr.array_id,
                name: arrayConfig?.name,
                pv_power_w: arr.pv_power_w,
                load_power_w: arr.load_power_w,
                grid_power_w: arr.grid_power_w,
                batt_power_w: arr.batt_power_w,
                batt_soc_pct: arr.batt_soc_pct,
                inverter_count: arr.inverter_count,
                inverter_ids: inverterIds,
                inverters: inverters,
              })
            }
          }
          
          // Get battery bank telemetry
          const batteryTelemetryRes: any = await api.get('/api/battery/now').catch(() => null)
          const batteryBanksData = batteryTelemetryRes?.banks || []
          
          // Get battery bank arrays from config
          const batteryBankArrays: BatteryBankArrayData[] = []
          if (config?.battery_bank_arrays && Array.isArray(config.battery_bank_arrays)) {
            config.battery_bank_arrays.forEach((bba: any) => {
              // Find attached inverter array
              const attachment = config?.battery_bank_array_attachments?.find(
                (att: any) => att.battery_bank_array_id === bba.id && !att.detached_at
              )
              
              // Get telemetry for all banks in this array
              const bankTelemetries: BatteryBankTelemetry[] = []
              if (bba.battery_bank_ids && Array.isArray(bba.battery_bank_ids)) {
                bba.battery_bank_ids.forEach((bankId: string) => {
                  // Try multiple ways to match the bank ID
                  const bankData = batteryBanksData.find((b: any) => {
                    const bid = b.id || b.bank_id || b.battery_id
                    return bid === bankId
                  })
                  if (bankData) {
                    console.debug(`[HomeSummaryTiles] Matched battery bank ${bankId} for array ${bba.id}:`, {
                      bankId,
                      foundId: bankData.id || bankData.bank_id,
                      soc: bankData.soc,
                      voltage: bankData.voltage,
                      current: bankData.current
                    })
                    const voltage = bankData.voltage
                    const current = bankData.current
                    const soc = bankData.soc
                    const power = voltage && current ? voltage * current : null
                    const isCharging = power && power > 0
                    const isDischarging = power && power < 0
                    
                    // Calculate time to charge/discharge (assuming 20kWh capacity per bank, can be made configurable)
                    const batteryCapacityKwh = 20 // TODO: Get from config
                    let timeToCharge = 0
                    let timeToDischarge = 0
                    
                    if (isCharging && soc !== null && soc !== undefined && soc < 100 && power) {
                      const energyNeededKwh = ((100 - soc) / 100) * batteryCapacityKwh
                      const chargingPowerKw = power / 1000
                      if (chargingPowerKw > 0) {
                        timeToCharge = energyNeededKwh / chargingPowerKw
                      }
                    }
                    
                    if (isDischarging && soc !== null && soc !== undefined && soc > 10 && power) {
                      const energyAvailableKwh = ((soc - 10) / 100) * batteryCapacityKwh
                      const dischargingPowerKw = Math.abs(power) / 1000
                      if (dischargingPowerKw > 0) {
                        timeToDischarge = energyAvailableKwh / dischargingPowerKw
                      }
                    }
                    
                    bankTelemetries.push({
                      bank_id: bankId,
                      voltage,
                      current,
                      soc,
                      temperature: bankData.temperature,
                      batteries_count: bankData.batteries_count,
                      charge_power_w: isCharging ? power : 0,
                      discharge_power_w: isDischarging ? Math.abs(power) : 0,
                      time_to_charge_h: timeToCharge,
                      time_to_discharge_h: timeToDischarge,
                    })
                  }
                })
              }
              
              // Aggregate telemetry for the array
              let aggregatedTelemetry: BatteryBankTelemetry | undefined
              if (bankTelemetries.length > 0) {
                const totalVoltage = bankTelemetries.reduce((sum, bt) => sum + (bt.voltage || 0), 0)
                const totalCurrent = bankTelemetries.reduce((sum, bt) => sum + (bt.current || 0), 0)
                const avgSOC = bankTelemetries.reduce((sum, bt) => sum + (bt.soc || 0), 0) / bankTelemetries.length
                const avgTemp = bankTelemetries.reduce((sum, bt) => sum + (bt.temperature || 0), 0) / bankTelemetries.length
                const totalChargePower = bankTelemetries.reduce((sum, bt) => sum + (bt.charge_power_w || 0), 0)
                const totalDischargePower = bankTelemetries.reduce((sum, bt) => sum + (bt.discharge_power_w || 0), 0)
                const maxTimeToCharge = Math.max(...bankTelemetries.map(bt => bt.time_to_charge_h || 0))
                const maxTimeToDischarge = Math.max(...bankTelemetries.map(bt => bt.time_to_discharge_h || 0))
                
                aggregatedTelemetry = {
                  bank_id: bba.id,
                  voltage: totalVoltage,
                  current: totalCurrent,
                  soc: avgSOC,
                  temperature: avgTemp,
                  batteries_count: bankTelemetries.reduce((sum, bt) => sum + (bt.batteries_count || 0), 0),
                  charge_power_w: totalChargePower,
                  discharge_power_w: totalDischargePower,
                  time_to_charge_h: maxTimeToCharge,
                  time_to_discharge_h: maxTimeToDischarge,
                }
              }
              
              batteryBankArrays.push({
                id: bba.id,
                name: bba.name,
                battery_bank_ids: bba.battery_bank_ids || [],
                attached_inverter_array_id: attachment?.inverter_array_id,
                telemetry: aggregatedTelemetry,
              })
            })
          }
          
          // Group arrays into systems (inverter array + attached battery bank array)
          // Match battery bank arrays to inverter arrays using battery_bank_array_attachments
          const systems: SystemGroup[] = []
          arrays.forEach((invArray) => {
            // Find the battery bank array attached to this inverter array
            const attachment = config?.battery_bank_array_attachments?.find(
              (att: any) => att.inverter_array_id === invArray.array_id && !att.detached_at
            )
            const attachedBatteryArray = attachment 
              ? batteryBankArrays.find((bba) => bba.id === attachment.battery_bank_array_id)
              : undefined
            systems.push({
              inverter_array: invArray,
              battery_bank_array: attachedBatteryArray,
            })
          })
          
          // Get meter data from home telemetry
          const meters: MeterData[] = []
          if (systemTel?.meters && Array.isArray(systemTel.meters)) {
            systemTel.meters.forEach((meter: any) => {
              meters.push({
                meter_id: meter.meter_id,
                power_w: meter.power_w,
                voltage_v: meter.voltage_v,
                current_a: meter.current_a,
                frequency_hz: meter.frequency_hz,
              })
            })
          }
          
          homesList.push({
            id: homeConfig.id || 'home',
            name: homeConfig.name || 'My Solar Home',
            description: homeConfig.description,
            total_pv_power_w: systemTel?.total_pv_power_w,
            total_load_power_w: systemTel?.total_load_power_w,
            total_grid_power_w: systemTel?.total_grid_power_w,
            total_batt_power_w: systemTel?.total_batt_power_w,
            avg_batt_soc_pct: systemTel?.avg_batt_soc_pct,
            daily_energy: systemTel?.daily_energy,
            monthly_energy: systemTel?.monthly_energy,
            financial_metrics: systemTel?.financial_metrics,
            arrays,
            battery_bank_arrays: batteryBankArrays,
            meters,
            systems,
            array_count: arrayCount,
            inverter_count: inverterCount,
            battery_bank_count: batteryBankCount,
          })
        } else {
          // Fallback: create a default home if none configured
          homesList.push({
            id: 'home',
            name: 'My Solar Home',
            array_count: config?.arrays?.length || 0,
            inverter_count: config?.inverters?.length || 0,
            battery_bank_count: config?.battery_banks?.length || 0,
          })
        }
        
        if (isMounted) {
          setHomes(homesList)
          setLoading(false)
        }
      } catch (error) {
        console.error('Error fetching homes:', error)
        if (isMounted) {
          setLoading(false)
        }
      }
    }

    // Initial load
    fetchHomes()
    
    // Refresh home summaries every 5 seconds (only telemetry, not config)
    intervalId = setInterval(async () => {
      try {
        if (!isMounted) return
        
        // Get home telemetry with period filter
        const periodParams = new URLSearchParams()
        periodParams.append('period', selectedPeriod)
        if (selectedPeriod === 'custom' && customStartDate && customEndDate) {
          periodParams.append('start_date', customStartDate)
          periodParams.append('end_date', customEndDate)
        }
        const systemTelemetryRes: any = await api.get(`/api/system/now?${periodParams.toString()}`).catch(() => null)
        if (!isMounted) return
        
        const systemTel = systemTelemetryRes?.system
        if (systemTel) {
          // Get config to map array names
          const configRes: any = await api.get('/api/config').catch(() => null)
          const config = configRes?.config || configRes
          
          // Update arrays data with individual inverter telemetry
          const updatedArrays: ArrayData[] = []
          if (systemTel?.arrays && Array.isArray(systemTel.arrays)) {
            for (const arr of systemTel.arrays) {
              const arrayConfig = config?.arrays?.find((a: any) => a.id === arr.array_id)
              const inverterIds = arrayConfig?.inverter_ids || []
              
              // Fetch individual inverter telemetry
              const inverters: InverterData[] = []
              if (inverterIds.length > 0) {
                for (const invId of inverterIds) {
                  try {
                    const invResponse: any = await api.get(`/api/now?inverter_id=${invId}`).catch(() => null)
                    if (invResponse?.now) {
                      const invConfig = config?.inverters?.find((inv: any) => inv.id === invId)
                      
                      // Verify the response is for the correct inverter
                      const returnedInverterId = invResponse.now.inverter_id || invResponse.now.id
                      if (returnedInverterId && returnedInverterId !== invId) {
                        console.warn(`[HomeSummaryTiles] Refresh: Warning: Requested ${invId} but got ${returnedInverterId}`)
                      }
                      
                      // Log for debugging
                      console.debug(`[HomeSummaryTiles] Refresh: Fetched telemetry for inverter ${invId} (${invConfig?.name || 'unknown'}):`, {
                        requested_id: invId,
                        returned_id: returnedInverterId,
                        pv_power_w: invResponse.now.pv_power_w,
                        batt_power_w: invResponse.now.batt_power_w,
                        batt_soc_pct: invResponse.now.batt_soc_pct,
                        batt_voltage_v: invResponse.now.batt_voltage_v,
                        batt_current_a: invResponse.now.batt_current_a,
                      })
                      
                      inverters.push({
                        inverter_id: invId,
                        name: invConfig?.name,
                        pv_power_w: invResponse.now.pv_power_w,
                        load_power_w: invResponse.now.load_power_w,
                        grid_power_w: invResponse.now.grid_power_w,
                        batt_power_w: invResponse.now.batt_power_w,
                        batt_soc_pct: invResponse.now.batt_soc_pct,
                      })
                    } else {
                      console.warn(`[HomeSummaryTiles] Refresh: No telemetry data returned for inverter ${invId}`)
                    }
                  } catch (error) {
                    console.error(`[HomeSummaryTiles] Refresh: Error fetching telemetry for inverter ${invId}:`, error)
                  }
                }
              }
              
              updatedArrays.push({
                array_id: arr.array_id,
                name: arrayConfig?.name,
                pv_power_w: arr.pv_power_w,
                load_power_w: arr.load_power_w,
                grid_power_w: arr.grid_power_w,
                batt_power_w: arr.batt_power_w,
                batt_soc_pct: arr.batt_soc_pct,
                inverter_count: arr.inverter_count,
                inverter_ids: inverterIds,
                inverters: inverters,
              })
            }
          }
          
          // Update meters data
          const updatedMeters: MeterData[] = []
          if (systemTel?.meters && Array.isArray(systemTel.meters) && systemTel.meters.length > 0) {
            systemTel.meters.forEach((meter: any) => {
              // Handle both power_w and grid_power_w field names
              const power = meter.power_w !== undefined ? meter.power_w : meter.grid_power_w
              const voltage = meter.voltage_v !== undefined ? meter.voltage_v : meter.grid_voltage_v
              const current = meter.current_a !== undefined ? meter.current_a : meter.grid_current_a
              const frequency = meter.frequency_hz !== undefined ? meter.frequency_hz : meter.grid_frequency_hz
              
              updatedMeters.push({
                meter_id: meter.meter_id || meter.id,
                power_w: power,
                voltage_v: voltage,
                current_a: current,
                frequency_hz: frequency,
              })
            })
          }
          
          // Only update telemetry, not the entire list
          // Fetch updated battery telemetry first
          const batteryTelemetryRes: any = await api.get('/api/battery/now').catch(() => null)
          const batteryBanksData = batteryTelemetryRes?.banks || []
          
          setHomes(prevHomes => {
            // If no homes exist, don't update
            if (prevHomes.length === 0) return prevHomes
            
            return prevHomes.map(home => {
              // Update battery bank arrays with latest telemetry
              // Rebuild from config to ensure correct IDs and matching
              const updatedBatteryBankArrays = config?.battery_bank_arrays?.map((bba: any) => {
              const bankTelemetries: BatteryBankTelemetry[] = []
              if (bba.battery_bank_ids && Array.isArray(bba.battery_bank_ids)) {
                bba.battery_bank_ids.forEach((bankId: string) => {
                  // Try multiple ways to match the bank ID - check id, bank_id, and battery_id fields
                  const bankData = batteryBanksData.find((b: any) => {
                    const bid = b.id || b.bank_id || b.battery_id
                    return bid === bankId
                  })
                  if (bankData) {
                    console.debug(`[HomeSummaryTiles] Matched battery bank ${bankId} for array ${bba.id}:`, {
                      bankId,
                      foundId: bankData.id || bankData.bank_id || bankData.battery_id,
                      soc: bankData.soc,
                      voltage: bankData.voltage,
                      current: bankData.current,
                      allBanksAvailable: batteryBanksData.map((b: any) => b.id || b.bank_id || b.battery_id)
                    })
                    const voltage = bankData.voltage
                    const current = bankData.current
                    const soc = bankData.soc
                    const power = voltage && current ? voltage * current : null
                    const isCharging = power && power > 0
                    const isDischarging = power && power < 0
                    
                    const batteryCapacityKwh = 20 // TODO: Get from config
                    let timeToCharge = 0
                    let timeToDischarge = 0
                    
                    if (isCharging && soc !== null && soc !== undefined && soc < 100 && power) {
                      const energyNeededKwh = ((100 - soc) / 100) * batteryCapacityKwh
                      const chargingPowerKw = power / 1000
                      if (chargingPowerKw > 0) {
                        timeToCharge = energyNeededKwh / chargingPowerKw
                      }
                    }
                    
                    if (isDischarging && soc !== null && soc !== undefined && soc > 10 && power) {
                      const energyAvailableKwh = ((soc - 10) / 100) * batteryCapacityKwh
                      const dischargingPowerKw = Math.abs(power) / 1000
                      if (dischargingPowerKw > 0) {
                        timeToDischarge = energyAvailableKwh / dischargingPowerKw
                      }
                    }
                    
                    bankTelemetries.push({
                      bank_id: bankId,
                      voltage,
                      current,
                      soc,
                      temperature: bankData.temperature,
                      batteries_count: bankData.batteries_count,
                      charge_power_w: isCharging ? power : 0,
                      discharge_power_w: isDischarging ? Math.abs(power) : 0,
                      time_to_charge_h: timeToCharge,
                      time_to_discharge_h: timeToDischarge,
                    })
                  }
                })
              }
              
              let aggregatedTelemetry: BatteryBankTelemetry | undefined
              if (bankTelemetries.length > 0) {
                const totalVoltage = bankTelemetries.reduce((sum, bt) => sum + (bt.voltage || 0), 0)
                const totalCurrent = bankTelemetries.reduce((sum, bt) => sum + (bt.current || 0), 0)
                const avgSOC = bankTelemetries.reduce((sum, bt) => sum + (bt.soc || 0), 0) / bankTelemetries.length
                const avgTemp = bankTelemetries.reduce((sum, bt) => sum + (bt.temperature || 0), 0) / bankTelemetries.length
                const totalChargePower = bankTelemetries.reduce((sum, bt) => sum + (bt.charge_power_w || 0), 0)
                const totalDischargePower = bankTelemetries.reduce((sum, bt) => sum + (bt.discharge_power_w || 0), 0)
                const maxTimeToCharge = Math.max(...bankTelemetries.map(bt => bt.time_to_charge_h || 0))
                const maxTimeToDischarge = Math.max(...bankTelemetries.map(bt => bt.time_to_discharge_h || 0))
                
                aggregatedTelemetry = {
                  bank_id: bba.id,
                  voltage: totalVoltage,
                  current: totalCurrent,
                  soc: avgSOC,
                  temperature: avgTemp,
                  batteries_count: bankTelemetries.reduce((sum, bt) => sum + (bt.batteries_count || 0), 0),
                  charge_power_w: totalChargePower,
                  discharge_power_w: totalDischargePower,
                  time_to_charge_h: maxTimeToCharge,
                  time_to_discharge_h: maxTimeToDischarge,
                }
              }
              
              // Find attached inverter array
              const attachment = config?.battery_bank_array_attachments?.find(
                (att: any) => att.battery_bank_array_id === bba.id && !att.detached_at
              )
              
              return {
                id: bba.id,
                name: bba.name,
                battery_bank_ids: bba.battery_bank_ids || [],
                attached_inverter_array_id: attachment?.inverter_array_id,
                telemetry: aggregatedTelemetry,
              }
            }) || home.battery_bank_arrays
          
          // Rebuild systems with updated arrays
          // Match battery bank arrays to inverter arrays using battery_bank_array_attachments from config
          const updatedSystems: SystemGroup[] = []
          if (updatedArrays.length > 0) {
            updatedArrays.forEach((invArray) => {
              // Find the battery bank array attached to this inverter array using config
              const attachment = config?.battery_bank_array_attachments?.find(
                (att: any) => att.inverter_array_id === invArray.array_id && !att.detached_at
              )
              const attachedBatteryArray = attachment 
                ? updatedBatteryBankArrays?.find((bba: any) => bba.id === attachment.battery_bank_array_id)
                : undefined
              updatedSystems.push({
                inverter_array: invArray,
                battery_bank_array: attachedBatteryArray,
              })
            })
          }
            
            return {
              ...home,
              total_pv_power_w: systemTel?.total_pv_power_w,
              total_load_power_w: systemTel?.total_load_power_w,
              total_grid_power_w: systemTel?.total_grid_power_w,
              total_batt_power_w: systemTel?.total_batt_power_w,
              avg_batt_soc_pct: systemTel?.avg_batt_soc_pct,
              daily_energy: systemTel?.daily_energy,
              monthly_energy: systemTel?.monthly_energy,
              financial_metrics: systemTel?.financial_metrics,
              arrays: updatedArrays.length > 0 ? updatedArrays : home.arrays,
              battery_bank_arrays: updatedBatteryBankArrays || home.battery_bank_arrays,
              meters: updatedMeters.length > 0 ? updatedMeters : home.meters,
              systems: updatedSystems.length > 0 ? updatedSystems : home.systems,
            }
          })
          })
        }
      } catch (error) {
        // Silently fail for telemetry updates
        console.debug('Error updating home telemetry:', error)
      }
    }, 5000)
    
    return () => {
      isMounted = false
      if (intervalId) {
        clearInterval(intervalId)
      }
    }
  }, [selectedPeriod, customStartDate, customEndDate])

  const formatPower = (w: number | undefined | null): string => {
    if (!w && w !== 0) return '—'
    if (Math.abs(w) >= 1000) {
      return `${(w / 1000).toFixed(1)} kW`
    }
    return `${Math.round(w)} W`
  }

  const formatSOC = (soc: number | undefined | null): string => {
    if (soc === null || soc === undefined) return '—'
    return `${Math.round(soc)}%`
  }

  const formatTime = (hours: number | undefined | null): string => {
    if (!hours || hours === 0) return '—'
    const h = Math.floor(hours)
    const m = Math.round((hours - h) * 60)
    if (h > 0 && m > 0) {
      return `${h}h ${m}m`
    } else if (h > 0) {
      return `${h}h`
    } else {
      return `${m}m`
    }
  }

  const formatEnergy = (kwh: number | undefined | null): string => {
    if (kwh === null || kwh === undefined) return '—'
    if (kwh === 0) return '0 kWh'
    if (kwh < 0.1) {
      return `${(kwh * 1000).toFixed(0)} Wh`
    }
    return `${kwh.toFixed(1)} kWh`
  }

  // Get period label for display
  const getPeriodLabel = (): string => {
    switch (selectedPeriod) {
      case 'today':
        return 'today'
      case 'week':
        return 'this week'
      case 'month':
        return 'this month'
      case 'year':
        return 'this year'
      case 'custom':
        if (customStartDate && customEndDate) {
          return `${customStartDate} to ${customEndDate}`
        }
        return 'custom period'
      default:
        return 'today'
    }
  }

  if (loading) {
    return (
      <div className="mb-6 p-4 rounded-lg" style={{ backgroundColor: cardBg, border: `1px solid ${borderColor}` }}>
        <div className="text-sm" style={{ color: textSecondary }}>Loading homes...</div>
      </div>
    )
  }

  // Don't return null - show a message instead to prevent flickering
  if (homes.length === 0) {
    return (
      <div className="mb-6 p-4 rounded-lg" style={{ backgroundColor: cardBg, border: `1px solid ${borderColor}` }}>
        <div className="text-sm" style={{ color: textSecondary }}>No homes configured. Please configure a home in Settings.</div>
      </div>
    )
  }

  return (
    <div className="mb-6 max-w-7xl mx-auto">
      <h2 className="text-lg font-semibold mb-4" style={{ color: textColor }}>
        Homes
      </h2>
      <div className={`grid gap-4 ${homes.length === 1 ? 'grid-cols-1' : 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3'}`}>
        {homes.map((home) => {
          const isSelected = selectedHomeId === home.id
          const gridPower = home.total_grid_power_w || 0
          const isExporting = gridPower < 0
          const isImporting = gridPower > 0
          
          return (
            <div
              key={home.id}
              onClick={() => onHomeSelect(isSelected ? null : home.id)}
              className="p-4 rounded-lg cursor-pointer transition-all hover:shadow-lg"
              style={{
                backgroundColor: cardBg,
                border: '2px solid transparent',
                boxShadow: isSelected ? (theme === 'dark' ? '0 0 0 3px rgba(59, 130, 246, 0.1)' : '0 0 0 3px rgba(37, 99, 235, 0.1)') : 'none',
              }}
              onMouseEnter={(e) => {
                if (!isSelected) {
                  e.currentTarget.style.backgroundColor = hoverBg
                }
              }}
              onMouseLeave={(e) => {
                if (!isSelected) {
                  e.currentTarget.style.backgroundColor = cardBg
                }
              }}
            >
              {/* Header */}
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2 flex-1">
                  <Home className="w-5 h-5 flex-shrink-0" style={{ color: isSelected ? selectedBorderColor : textColor }} />
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 sm:gap-4">
                      <div className="flex-1 min-w-0">
                        <h3 className="font-semibold text-base" style={{ color: textColor }}>
                          {home.name}
                        </h3>
                        {home.description && (
                          <p className="text-xs mt-0.5" style={{ color: textSecondary }}>
                            {home.description}
                          </p>
                        )}
                      </div>
                      {/* Financial and Environmental Metrics */}
                      {home.financial_metrics && (
                        <div className="flex items-center gap-3 sm:gap-4 text-xs flex-shrink-0">
                          {home.financial_metrics.total_bill_pkr !== undefined && (
                            <div className="text-right">
                              <div className="font-medium" style={{ color: textSecondary }}>Bill This Month</div>
                              <div className="font-bold text-sm" style={{ color: home.financial_metrics.total_bill_pkr >= 0 ? '#ef4444' : '#10b981' }}>
                                {home.financial_metrics.total_bill_pkr >= 0 ? '+' : ''}{home.financial_metrics.total_bill_pkr.toFixed(0)} PKR
                              </div>
                            </div>
                          )}
                          {home.financial_metrics.total_saved_pkr !== undefined && (
                            <div className="text-right">
                              <div className="font-medium" style={{ color: textSecondary }}>Saved This Month</div>
                              <div className="font-bold text-sm" style={{ color: '#10b981' }}>
                                {home.financial_metrics.total_saved_pkr.toFixed(0)} PKR
                              </div>
                            </div>
                          )}
                          {home.financial_metrics.co2_prevented_kg !== undefined && (
                            <div className="text-right">
                              <div className="font-medium" style={{ color: textSecondary }}>CO₂ Prevented</div>
                              <div className="font-bold text-sm" style={{ color: '#10b981' }}>
                                {home.financial_metrics.co2_prevented_kg >= 1000 
                                  ? `${(home.financial_metrics.co2_prevented_kg / 1000).toFixed(1)} t`
                                  : `${home.financial_metrics.co2_prevented_kg.toFixed(1)} kg`}
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
                {isSelected && (
                  <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: selectedBorderColor }} />
                )}
              </div>

              {/* Self-Sufficiency Bar */}
              {home.daily_energy && (
                <div className="mb-3">
                  {(() => {
                    const totalLoad = home.daily_energy.load_energy_kwh || 0
                    const gridImport = home.daily_energy.grid_import_energy_kwh || 0
                    const selfServedEnergy = Math.max(0, totalLoad - gridImport)
                    const selfSufficiencyPct = totalLoad > 0 ? (selfServedEnergy / totalLoad) * 100 : 0
                    const clampedSelfSufficiency = Math.min(100, Math.max(0, selfSufficiencyPct))
                    
                    return (
                      <div className="space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-medium" style={{ color: textSecondary }}>
                            Self-Sufficiency {getPeriodLabel().charAt(0).toUpperCase() + getPeriodLabel().slice(1)}
                          </span>
                          <span className="text-sm font-bold" style={{ color: clampedSelfSufficiency >= 80 ? '#10b981' : clampedSelfSufficiency >= 50 ? '#f59e0b' : '#ef4444' }}>
                            {Math.round(clampedSelfSufficiency)}%
                          </span>
                        </div>
                        <div className="w-full rounded-full overflow-hidden" style={{ backgroundColor: theme === 'dark' ? '#374151' : '#e5e7eb', height: '8px' }}>
                          <div
                            className="h-full transition-all duration-500"
                            style={{
                              width: `${clampedSelfSufficiency}%`,
                              backgroundColor: clampedSelfSufficiency >= 80 ? '#10b981' : clampedSelfSufficiency >= 50 ? '#f59e0b' : '#ef4444',
                            }}
                          />
                        </div>
                      </div>
                    )
                  })()}
                </div>
              )}

              {/* Summary Stats and Energy Distribution Diagram - Side by Side on Web, Stacked on Mobile */}
              <div className={`mt-4 ${isMobile ? 'space-y-4' : 'grid grid-cols-2 gap-4'}`}>
                {/* Summary Stats - 2x2 Grid */}
                <div className="grid grid-cols-2 gap-3">
                  {/* PV Power */}
                  <div className="flex items-center gap-2">
                    <Sun className="w-4 h-4" style={{ color: '#f59e0b' }} />
                    <div className="flex-1">
                      <div className="text-xs" style={{ color: textSecondary }}>Solar</div>
                      <div className="text-sm font-medium" style={{ color: textColor }}>
                        {formatPower(home.total_pv_power_w)}
                      </div>
                      {home.daily_energy?.solar_energy_kwh !== undefined && (
                        <div className="text-xs mt-0.5" style={{ color: textSecondary }}>
                          {formatEnergy(home.daily_energy.solar_energy_kwh)} {getPeriodLabel()}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Load Power */}
                  <div className="flex items-center gap-2">
                    <Activity className="w-4 h-4" style={{ color: '#3b82f6' }} />
                    <div className="flex-1">
                      <div className="text-xs" style={{ color: textSecondary }}>Load</div>
                      <div className="text-sm font-medium" style={{ color: textColor }}>
                        {formatPower(home.total_load_power_w)}
                      </div>
                      {home.daily_energy?.load_energy_kwh !== undefined && (
                        <div className="text-xs mt-0.5" style={{ color: textSecondary }}>
                          {formatEnergy(home.daily_energy.load_energy_kwh)} {getPeriodLabel()}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Battery SOC */}
                  <div className="flex items-center gap-2">
                    <Battery className="w-4 h-4" style={{ color: '#10b981' }} />
                    <div className="flex-1">
                      <div className="text-xs" style={{ color: textSecondary }}>Battery</div>
                      {/* Battery Power - shown above SOC */}
                      {home.total_batt_power_w !== undefined && home.total_batt_power_w !== null && (
                        <div className="text-sm font-medium" style={{ 
                          color: home.total_batt_power_w > 0 ? '#10b981' : home.total_batt_power_w < 0 ? '#ef4444' : textColor 
                        }}>
                          {formatPower(Math.abs(home.total_batt_power_w))}
                        </div>
                      )}
                      <div className="text-sm font-medium" style={{ color: textColor }}>
                        {formatSOC(home.avg_batt_soc_pct)}
                      </div>
                      {home.daily_energy && (
                        <div className="text-xs mt-0.5 space-y-0.5" style={{ color: textSecondary }}>
                          {home.daily_energy.battery_charge_energy_kwh && home.daily_energy.battery_charge_energy_kwh > 0 && (
                            <div style={{ color: '#10b981' }}>Charge: {formatEnergy(home.daily_energy.battery_charge_energy_kwh)}</div>
                          )}
                          {home.daily_energy.battery_discharge_energy_kwh && home.daily_energy.battery_discharge_energy_kwh > 0 && (
                            <div style={{ color: '#ef4444' }}>Discharge: {formatEnergy(home.daily_energy.battery_discharge_energy_kwh)}</div>
                          )}
                          {(!home.daily_energy.battery_charge_energy_kwh || home.daily_energy.battery_charge_energy_kwh === 0) &&
                           (!home.daily_energy.battery_discharge_energy_kwh || home.daily_energy.battery_discharge_energy_kwh === 0) && (
                            <div>—</div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Grid Power */}
                  <div className="flex items-center gap-2">
                    <Zap className="w-4 h-4" style={{ color: isExporting ? '#10b981' : isImporting ? '#ef4444' : textSecondary }} />
                    <div className="flex-1">
                      <div className="text-xs" style={{ color: textSecondary }}>Grid</div>
                      <div className="text-sm font-medium" style={{ 
                        color: isExporting ? '#10b981' : isImporting ? '#ef4444' : textColor 
                      }}>
                        {formatPower(home.total_grid_power_w)}
                      </div>
                      {home.daily_energy && (
                        <div className="text-xs mt-0.5 space-y-0.5" style={{ color: textSecondary }}>
                          {home.daily_energy.grid_import_energy_kwh && home.daily_energy.grid_import_energy_kwh > 0 && (
                            <div style={{ color: '#ef4444' }}>Import: {formatEnergy(home.daily_energy.grid_import_energy_kwh)}</div>
                          )}
                          {home.daily_energy.grid_export_energy_kwh && home.daily_energy.grid_export_energy_kwh > 0 && (
                            <div style={{ color: '#10b981' }}>Export: {formatEnergy(home.daily_energy.grid_export_energy_kwh)}</div>
                          )}
                          {(!home.daily_energy.grid_import_energy_kwh || home.daily_energy.grid_import_energy_kwh === 0) &&
                           (!home.daily_energy.grid_export_energy_kwh || home.daily_energy.grid_export_energy_kwh === 0) && (
                            <div>—</div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Energy Distribution Diagram - Side by side on web, below on mobile */}
                <div className="flex items-center justify-center" style={{ backgroundColor: 'transparent' }}>
                  <div style={{ backgroundColor: 'transparent', border: 'none', boxShadow: 'none' }}>
                    <EnergyDistributionDiagram
                      solarEnergy={home.daily_energy?.solar_energy_kwh || 0}
                      solarPower={home.total_pv_power_w || 0}
                      gridPower={home.total_grid_power_w || 0}
                      batteryPower={home.total_batt_power_w || 0}
                      loadPower={home.total_load_power_w || 0}
                      gridExport={home.daily_energy?.grid_export_energy_kwh || 0}
                      gridImport={home.daily_energy?.grid_import_energy_kwh || 0}
                      batteryCharge={home.daily_energy?.battery_charge_energy_kwh || 0}
                      batteryDischarge={home.daily_energy?.battery_discharge_energy_kwh || 0}
                      loadEnergy={home.daily_energy?.load_energy_kwh || 0}
                      batterySOC={home.avg_batt_soc_pct || 0}
                      batteryTemp={home.battery_bank_arrays?.[0]?.telemetry?.temperature}
                    />
                  </div>
                </div>
              </div>

              {/* Systems (Grouped Arrays) */}
              {home.systems && home.systems.length > 0 ? (
                <div className="mt-4 pt-3 border-t" style={{ borderColor: borderColor }}>
                  <div className="text-xs font-semibold mb-3" style={{ color: textColor }}>
                    Systems
                  </div>
                  <div className="space-y-3">
                    {home.systems.map((system, idx) => {
                      const invArray = system.inverter_array
                      const battArray = system.battery_bank_array
                      
                      return (
                        <div 
                          key={invArray.array_id} 
                          className="p-2 rounded border" 
                          style={{ 
                            backgroundColor: theme === 'dark' ? '#111827' : '#f9fafb',
                            borderColor: borderColor 
                          }}
                        >
                          <div className="text-xs font-semibold mb-2" style={{ color: textColor }}>
                            System {idx + 1}
                          </div>
                          
                          {/* Inverter Array */}
                          <div className="mb-2">
                            <div className="flex items-center justify-between mb-1">
                              <span className="text-xs font-medium" style={{ color: textColor }}>
                                Inverter Array: {invArray.name || invArray.array_id}
                              </span>
                              <span className="text-xs" style={{ color: textSecondary }}>
                                {invArray.inverter_count || 0} inverters
                              </span>
                            </div>
                            
                            {/* Individual Inverters */}
                            {invArray.inverters && invArray.inverters.length > 0 && (
                              <div className="mb-2 pl-2 border-l-2" style={{ borderColor: borderColor }}>
                                {invArray.inverters.map((inv) => (
                                  <div key={inv.inverter_id} className="mb-1.5 last:mb-0">
                                    <div className="text-xs font-medium mb-0.5" style={{ color: textSecondary }}>
                                      {inv.name || inv.inverter_id}
                                    </div>
                                    <div className="grid grid-cols-4 gap-2 text-xs">
                                      <div>
                                        <span style={{ color: textSecondary }}>PV: </span>
                                        <span style={{ color: textColor }}>{formatPower(inv.pv_power_w)}</span>
                                      </div>
                                      <div>
                                        <span style={{ color: textSecondary }}>Load: </span>
                                        <span style={{ color: textColor }}>{formatPower(inv.load_power_w)}</span>
                                      </div>
                                      <div>
                                        <span style={{ color: textSecondary }}>Grid: </span>
                                        <span style={{ color: textColor }}>{formatPower(inv.grid_power_w)}</span>
                                      </div>
                                      <div>
                                        <span style={{ color: textSecondary }}>Batt: </span>
                                        <span style={{ color: textColor }}>
                                          {formatPower(inv.batt_power_w)} {inv.batt_soc_pct !== undefined && `(${formatSOC(inv.batt_soc_pct)})`}
                                        </span>
                                      </div>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            )}
                            
                            {/* Cumulative Array Values */}
                            <div className="pt-1 border-t" style={{ borderColor: borderColor }}>
                              <div className="text-xs font-medium mb-1" style={{ color: textSecondary }}>
                                Total (Cumulative)
                              </div>
                              <div className="grid grid-cols-4 gap-2 text-xs">
                                <div>
                                  <span style={{ color: textSecondary }}>PV: </span>
                                  <span style={{ color: textColor }}>{formatPower(invArray.pv_power_w)}</span>
                                </div>
                                <div>
                                  <span style={{ color: textSecondary }}>Load: </span>
                                  <span style={{ color: textColor }}>{formatPower(invArray.load_power_w)}</span>
                                </div>
                                <div>
                                  <span style={{ color: textSecondary }}>Grid: </span>
                                  <span style={{ color: textColor }}>{formatPower(invArray.grid_power_w)}</span>
                                </div>
                                <div>
                                  <span style={{ color: textSecondary }}>Batt: </span>
                                  <span style={{ color: textColor }}>
                                    {(() => {
                                      // If battery bank array is attached, use its power instead of inverter array battery power
                                      // This ensures we show the actual battery connected to this inverter array
                                      if (battArray?.telemetry) {
                                        // Calculate battery power: positive = charging, negative = discharging
                                        let battPower: number | null = null
                                        
                                        // Prefer charge_power_w or discharge_power_w if available
                                        if (battArray.telemetry.charge_power_w !== undefined && battArray.telemetry.charge_power_w > 0) {
                                          battPower = battArray.telemetry.charge_power_w
                                        } else if (battArray.telemetry.discharge_power_w !== undefined && battArray.telemetry.discharge_power_w > 0) {
                                          battPower = -battArray.telemetry.discharge_power_w
                                        } else if (battArray.telemetry.voltage !== undefined && battArray.telemetry.current !== undefined) {
                                          // Calculate from voltage * current (positive current = charging, negative = discharging)
                                          battPower = battArray.telemetry.voltage * battArray.telemetry.current
                                        }
                                        
                                        const battSOC = battArray.telemetry.soc
                                        return `${formatPower(battPower)} ${battSOC !== undefined ? `(${formatSOC(battSOC)})` : ''}`
                                      }
                                      // Otherwise, use inverter array's battery power (from inverters themselves)
                                      return `${formatPower(invArray.batt_power_w)} ${invArray.batt_soc_pct !== undefined ? `(${formatSOC(invArray.batt_soc_pct)})` : ''}`
                                    })()}
                                  </span>
                                </div>
                              </div>
                            </div>
                          </div>
                          
                          {/* Battery Bank Array */}
                          {battArray && (
                            <div className="pt-2 border-t" style={{ borderColor: borderColor }}>
                              <div className="flex items-center justify-between mb-2">
                                <span className="text-xs font-medium" style={{ color: textColor }}>
                                  Battery Array: {battArray.name || battArray.id}
                                </span>
                                <span className="text-xs" style={{ color: textSecondary }}>
                                  {battArray.battery_bank_ids?.length || 0} banks
                                </span>
                              </div>
                              {battArray.telemetry && (
                                <div className="space-y-1">
                                  <div className="grid grid-cols-2 gap-2 text-xs">
                                    <div>
                                      <span style={{ color: textSecondary }}>SOC: </span>
                                      <span style={{ color: textColor }}>
                                        {formatSOC(battArray.telemetry.soc)}
                                      </span>
                                    </div>
                                    <div>
                                      <span style={{ color: textSecondary }}>Voltage: </span>
                                      <span style={{ color: textColor }}>
                                        {battArray.telemetry.voltage ? `${battArray.telemetry.voltage.toFixed(1)} V` : '—'}
                                      </span>
                                    </div>
                                    <div>
                                      <span style={{ color: textSecondary }}>Current: </span>
                                      <span style={{ color: textColor }}>
                                        {battArray.telemetry.current ? `${battArray.telemetry.current.toFixed(2)} A` : '—'}
                                      </span>
                                    </div>
                                    <div>
                                      <span style={{ color: textSecondary }}>Temp: </span>
                                      <span style={{ color: textColor }}>
                                        {battArray.telemetry.temperature ? `${battArray.telemetry.temperature.toFixed(1)}°C` : '—'}
                                      </span>
                                    </div>
                                  </div>
                                  {((battArray.telemetry?.charge_power_w !== undefined && battArray.telemetry.charge_power_w > 0) || 
                                    (battArray.telemetry?.discharge_power_w !== undefined && battArray.telemetry.discharge_power_w > 0)) && (
                                    <div className="grid grid-cols-2 gap-2 text-xs pt-1 border-t" style={{ borderColor: borderColor }}>
                                      {battArray.telemetry?.charge_power_w !== undefined && battArray.telemetry.charge_power_w > 0 && (
                                        <>
                                          <div>
                                            <span style={{ color: textSecondary }}>Charge: </span>
                                            <span style={{ color: '#10b981' }}>
                                              {formatPower(battArray.telemetry.charge_power_w)}
                                            </span>
                                          </div>
                                          <div>
                                            <span style={{ color: textSecondary }}>Time to Full: </span>
                                            <span style={{ color: textColor }}>
                                              {formatTime(battArray.telemetry.time_to_charge_h)}
                                            </span>
                                          </div>
                                        </>
                                      )}
                                      {battArray.telemetry?.discharge_power_w !== undefined && battArray.telemetry.discharge_power_w > 0 && (
                                        <>
                                          <div>
                                            <span style={{ color: textSecondary }}>Discharge: </span>
                                            <span style={{ color: '#ef4444' }}>
                                              {formatPower(battArray.telemetry.discharge_power_w)}
                                            </span>
                                          </div>
                                          <div>
                                            <span style={{ color: textSecondary }}>Time to 10%: </span>
                                            <span style={{ color: textColor }}>
                                              {formatTime(battArray.telemetry.time_to_discharge_h)}
                                            </span>
                                          </div>
                                        </>
                                      )}
                                    </div>
                                  )}
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      )
                    })}
                  </div>
                </div>
              ) : (
                /* Fallback: Show separate arrays if no systems */
                (home.arrays && home.arrays.length > 0) || (home.battery_bank_arrays && home.battery_bank_arrays.length > 0) ? (
                  <div className="mt-4 pt-3 border-t" style={{ borderColor: borderColor }}>
                    {home.arrays && home.arrays.length > 0 && (
                      <div className="mb-3">
                        <div className="text-xs font-semibold mb-2" style={{ color: textColor }}>
                          Inverter Arrays
                        </div>
                        <div className="space-y-2">
                          {home.arrays.map((arr) => (
                            <div key={arr.array_id} className="text-xs" style={{ color: textSecondary }}>
                              <div className="flex items-center justify-between mb-1">
                                <span className="font-medium" style={{ color: textColor }}>
                                  {arr.name || arr.array_id}
                                </span>
                                <span>{arr.inverter_count || 0} inverters</span>
                              </div>
                              <div className="grid grid-cols-4 gap-2 text-xs">
                                <div>
                                  <span style={{ color: textSecondary }}>PV: </span>
                                  <span style={{ color: textColor }}>{formatPower(arr.pv_power_w)}</span>
                                </div>
                                <div>
                                  <span style={{ color: textSecondary }}>Load: </span>
                                  <span style={{ color: textColor }}>{formatPower(arr.load_power_w)}</span>
                                </div>
                                <div>
                                  <span style={{ color: textSecondary }}>Grid: </span>
                                  <span style={{ color: textColor }}>{formatPower(arr.grid_power_w)}</span>
                                </div>
                                <div>
                                  <span style={{ color: textSecondary }}>Batt: </span>
                                  <span style={{ color: textColor }}>
                                    {formatPower(arr.batt_power_w)} ({formatSOC(arr.batt_soc_pct)})
                                  </span>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="mt-4 pt-3 border-t" style={{ borderColor: borderColor }}>
                    <div className="flex items-center justify-between text-xs" style={{ color: textSecondary }}>
                      <span>{home.array_count || 0} Arrays</span>
                      <span>{home.inverter_count || 0} Inverters</span>
                      <span>{home.battery_bank_count || 0} Battery Banks</span>
                    </div>
                  </div>
                )
              )}
              
              {/* Smart Meters */}
              {home.meters && home.meters.length > 0 && (
                <div className="mt-4 pt-3 border-t" style={{ borderColor: borderColor }}>
                  <div className="text-xs font-semibold mb-2 flex items-center gap-1" style={{ color: textColor }}>
                    <Gauge className="w-3 h-3" />
                    Smart Meters
                  </div>
                  <div className="space-y-2">
                    {home.meters.map((meter) => (
                      <div key={meter.meter_id} className="text-xs" style={{ color: textSecondary }}>
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-medium" style={{ color: textColor }}>
                            {meter.meter_id}
                          </span>
                        </div>
                        <div className="grid grid-cols-4 gap-2 text-xs">
                          <div>
                            <span style={{ color: textSecondary }}>Power: </span>
                            <span style={{ color: textColor }}>{formatPower(meter.power_w)}</span>
                          </div>
                          <div>
                            <span style={{ color: textSecondary }}>Voltage: </span>
                            <span style={{ color: textColor }}>
                              {meter.voltage_v ? `${meter.voltage_v.toFixed(1)} V` : '—'}
                            </span>
                          </div>
                          <div>
                            <span style={{ color: textSecondary }}>Current: </span>
                            <span style={{ color: textColor }}>
                              {meter.current_a ? `${meter.current_a.toFixed(2)} A` : '—'}
                            </span>
                          </div>
                          <div>
                            <span style={{ color: textSecondary }}>Freq: </span>
                            <span style={{ color: textColor }}>
                              {meter.frequency_hz ? `${meter.frequency_hz.toFixed(2)} Hz` : '—'}
                            </span>
                          </div>
                        </div>
                      </div>
                    ))}
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

