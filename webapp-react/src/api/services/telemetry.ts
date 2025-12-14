import { api, CACHE_TTL } from '../client'
import type {
  BackendTelemetryResponse,
  BackendHomeTelemetryResponse,
  BackendArrayTelemetryResponse,
  BackendBatteryResponse,
} from '../types/telemetry'
import {
  normalizeTelemetry,
  normalizeHomeTelemetry,
  normalizeArrayTelemetry,
  normalizeBatteryData,
} from '../normalizers/telemetry'
import type { TelemetryData, HomeTelemetryData, BatteryData } from '../types/telemetry'
import { HierarchyManager } from '../managers/HierarchyManager'

/**
 * Telemetry service - handles all telemetry-related API calls
 * Also updates hierarchy objects with telemetry data
 */
export const telemetryService = {
  /**
   * Get current telemetry for a specific inverter
   */
  async getInverterNow(inverterId: string): Promise<TelemetryData> {
    const response = await api.get<BackendTelemetryResponse>(
      `/api/now?inverter_id=${inverterId}`,
      { ttl: CACHE_TTL.TELEMETRY, key: `telemetry:inverter:${inverterId}` }
    )
    
    if (!response.now) {
      throw new Error('No telemetry data available')
    }
    
    const telemetry = normalizeTelemetry(response.now, 'inverter', inverterId)
    
    // Update hierarchy object
    const manager = HierarchyManager.getInstance()
    manager.updateTelemetry(inverterId, telemetry)
    
    return telemetry
  },

  /**
   * Get system-level aggregated telemetry
   */
  async getHomeNow(): Promise<HomeTelemetryData> {
    const response = await api.get<BackendHomeTelemetryResponse>(
      '/api/system/now',
      { ttl: CACHE_TTL.TELEMETRY, key: 'telemetry:home' }
    )
    
    if (!response.system) {
      throw new Error('No system telemetry data available')
    }
    
    const telemetry = normalizeHomeTelemetry(response.system)
    
    // Update hierarchy object (use system_id from response or default to 'system')
    const systemId = (response.system as any).system_id || 'system'
    const manager = HierarchyManager.getInstance()
    manager.updateSystemTelemetry(systemId, telemetry)
    
    // Update individual inverter telemetry from nested structure
    const systemData = response.system as any
    if (systemData.inverter_arrays && Array.isArray(systemData.inverter_arrays)) {
      for (const invArray of systemData.inverter_arrays) {
        if (invArray.inverters && Array.isArray(invArray.inverters)) {
          for (const inv of invArray.inverters) {
            if (inv.telemetry && inv.inverter_id) {
              try {
                // Backend provides telemetry with fields like pv_power_w, load_power_w, etc.
                // Convert to format expected by normalizeTelemetry
                const telemetryData = {
                  ts: inv.telemetry.ts || new Date().toISOString(),
                  pv_power_w: inv.telemetry.pv_power_w || 0,
                  load_power_w: inv.telemetry.load_power_w || 0,
                  grid_power_w: inv.telemetry.grid_power_w || 0,
                  batt_power_w: inv.telemetry.batt_power_w || 0,
                  batt_soc_pct: inv.telemetry.batt_soc_pct || null,
                  batt_voltage_v: inv.telemetry.batt_voltage_v || null,
                  batt_current_a: inv.telemetry.batt_current_a || null,
                  inverter_temp_c: inv.telemetry.inverter_temp_c || null,
                  _metadata: {},
                }
                // Normalize the telemetry data
                const invTelemetry = normalizeTelemetry(telemetryData, 'inverter', inv.inverter_id)
                // Update the hierarchy object
                manager.updateTelemetry(inv.inverter_id, invTelemetry)
              } catch (err) {
                console.warn(`[telemetryService] Failed to update inverter ${inv.inverter_id} telemetry:`, err)
              }
            }
          }
        }
      }
    }
    
    // Update battery pack telemetry from nested structure
    if (systemData.battery_arrays && Array.isArray(systemData.battery_arrays)) {
      for (const batArray of systemData.battery_arrays) {
        if (batArray.battery_packs && Array.isArray(batArray.battery_packs)) {
          for (const pack of batArray.battery_packs) {
            if (pack.telemetry && pack.pack_id) {
              try {
                // Convert pack telemetry to BatteryData format
                const packTel = pack.telemetry
                const batteryData: BatteryData = {
                  id: pack.pack_id,
                  ts: packTel.ts || new Date().toISOString(),
                  voltage: packTel.voltage || null,
                  current: packTel.current || null,
                  soc: packTel.soc || null,
                  temperature: packTel.temperature || null,
                  batteryCount: 1,
                  cellsPerBattery: 0,
                  devices: [],
                  cells: [],
                }
                manager.updateBatteryTelemetry(pack.pack_id, batteryData)
              } catch (err) {
                console.warn(`[telemetryService] Failed to update battery pack ${pack.pack_id} telemetry:`, err)
              }
            }
          }
        }
      }
    }
    
    // Update meter telemetry from system response
    if (systemData.meters && Array.isArray(systemData.meters)) {
      console.log(`[getSystemNow] Found ${systemData.meters.length} meter(s) in system response:`, systemData.meters.map(m => ({ id: m.meter_id || m.id, power_w: m.power_w, import_kwh: m.import_kwh, export_kwh: m.export_kwh })))
      for (const meter of systemData.meters) {
        // Backend returns meter_id, but also check for id as fallback
        const meterId = meter.meter_id || meter.id
        if (meterId) {
          try {
            // Convert meter data to TelemetryData format
            // Backend returns: power_w (in watts), import_kwh, export_kwh (already in kWh)
            const meterTelemetryData: any = {
              ts: meter.ts || new Date().toISOString(),
              pv_power_w: 0, // Meters don't have PV power
              load_power_w: 0, // Meters don't have load power
              grid_power_w: (meter.power_w || 0), // Meter power in watts (positive = import, negative = export)
              batt_power_w: 0, // Meters don't have battery power
              batt_soc_pct: null,
              batt_voltage_v: null,
              batt_current_a: null,
              inverter_temp_c: null,
              _metadata: {
                import_kwh: meter.import_kwh || 0,
                export_kwh: meter.export_kwh || 0,
                voltage_v: meter.voltage_v || null,
                current_a: meter.current_a || null,
                frequency_hz: meter.frequency_hz || null,
              },
            }
            console.log(`[getSystemNow] Updating meter ${meterId} telemetry:`, {
              power_w: meterTelemetryData.grid_power_w,
              import_kwh: meterTelemetryData._metadata.import_kwh,
              export_kwh: meterTelemetryData._metadata.export_kwh,
            })
            // Normalize the telemetry data
            const normalizedTelemetry = normalizeTelemetry(meterTelemetryData, 'meter', meterId)
            // Store meter-specific data in the raw field for access by Meter.getImportEnergy() and getExportEnergy()
            if (normalizedTelemetry.raw) {
              const raw = normalizedTelemetry.raw as any
              raw.import_kwh = meter.import_kwh || 0
              raw.export_kwh = meter.export_kwh || 0
            }
            // Update the hierarchy object
            manager.updateTelemetry(meterId, normalizedTelemetry)
            console.log(`[getSystemNow] Successfully updated meter ${meterId} telemetry in hierarchy`)
          } catch (err) {
            console.error(`[getSystemNow] Failed to update meter ${meterId} telemetry:`, err, meter)
          }
        } else {
          console.warn(`[getSystemNow] Meter object missing meter_id or id:`, meter)
        }
      }
    } else {
      console.warn(`[getSystemNow] No meters array in system response or not an array:`, systemData.meters)
    }
    
    return telemetry
  },

  /**
   * Get array-level telemetry
   */
  async getArrayNow(arrayId: string): Promise<TelemetryData> {
    const response = await api.get<BackendArrayTelemetryResponse>(
      `/api/arrays/${arrayId}/now`,
      { ttl: CACHE_TTL.TELEMETRY, key: `telemetry:array:${arrayId}` }
    )
    
    if (!response.now) {
      throw new Error('No array telemetry data available')
    }
    
    const telemetry = normalizeArrayTelemetry(response.now)
    
    // Update hierarchy object
    const manager = HierarchyManager.getInstance()
    manager.updateArrayTelemetry(arrayId, telemetry)
    
    return telemetry
  },

  /**
   * Get battery telemetry
   */
  async getBatteryNow(bankId?: string): Promise<BatteryData | BatteryData[]> {
    const url = bankId
      ? `/api/battery/now?bank_id=${bankId}`
      : '/api/battery/now'
    
    const response = await api.get<BackendBatteryResponse>(
      url,
      { ttl: CACHE_TTL.TELEMETRY, key: `telemetry:battery:${bankId || 'all'}` }
    )
    
    // Preserve configured_banks for name lookup - add to each battery's raw data
    const configuredBanks = response.configured_banks || []
    const manager = HierarchyManager.getInstance()
    
    // When bank_id is specified, backend returns {status: "ok", battery: {...}, banks: [...]}
    // When bank_id is not specified, backend returns {status: "ok", banks: [...]}
    // Always prefer response.battery if available (specific bank request), otherwise use banks array
    let batteriesToProcess: any[] = []
    
    if (response.battery) {
      // Specific bank requested - use response.battery
      batteriesToProcess = [response.battery]
    } else if (response.banks && response.banks.length > 0) {
      // Multiple banks or all banks - use banks array
      batteriesToProcess = response.banks
    } else {
      throw new Error('No battery data available')
    }
    
    // Normalize and update hierarchy for each battery
    const normalizedBatteries = batteriesToProcess.map(bat => {
      const normalized = normalizeBatteryData(bat)
      // Add configured_banks to raw data for name lookup
      if (normalized.raw) {
        ;(normalized.raw as any).configured_banks = configuredBanks
      }
      
      // Update hierarchy object
      manager.updateBatteryTelemetry(normalized.id, normalized)
      
      return normalized
    })
    
    // Return single battery if bankId was specified, otherwise return array
    if (bankId && normalizedBatteries.length === 1) {
      return normalizedBatteries[0]
    }
    
    return normalizedBatteries
  },

  /**
   * Get meter telemetry
   */
  async getMeterNow(meterId: string): Promise<any> {
    console.log(`[getMeterNow] Fetching meter telemetry for meterId: ${meterId}`)
    const response = await api.get<{ status: string; meter: any; error?: string }>(
      `/api/meter/now?meter_id=${meterId}`,
      { ttl: CACHE_TTL.TELEMETRY, key: `telemetry:meter:${meterId}` }
    ) as { status: string; meter: any; error?: string }
    
    console.log(`[getMeterNow] Response for ${meterId}:`, {
      status: response.status,
      hasMeter: !!response.meter,
      error: response.error,
      meterId: response.meter?.id,
    })
    
    if (response.status === 'error') {
      console.error(`[getMeterNow] Error response for ${meterId}:`, response.error)
      throw new Error(response.error || `Error fetching meter telemetry for ${meterId}`)
    }
    
    if (!response || !response.meter) {
      console.warn(`[getMeterNow] No meter data in response for ${meterId}. Response:`, response)
      // Return null instead of throwing - allows component to handle gracefully
      return null
    }
    
    // Update hierarchy object
    const manager = HierarchyManager.getInstance()
    const meterTelemetry = response.meter
    
    // Convert meter telemetry to TelemetryData format for hierarchy
    const telemetryData = {
      ts: meterTelemetry.ts || new Date().toISOString(),
      pv_power_w: 0, // Meters don't have PV power
      load_power_w: 0, // Meters don't have load power
      grid_power_w: meterTelemetry.grid_power_w || 0,
      batt_power_w: 0, // Meters don't have battery power
      batt_soc_pct: null,
      batt_voltage_v: null,
      batt_current_a: null,
      inverter_temp_c: null,
      _metadata: {
        import_kwh: meterTelemetry.grid_import_wh ? meterTelemetry.grid_import_wh / 1000 : 0,
        export_kwh: meterTelemetry.grid_export_wh ? meterTelemetry.grid_export_wh / 1000 : 0,
        voltage_v: meterTelemetry.grid_voltage_v || null,
        current_a: meterTelemetry.grid_current_a || null,
        frequency_hz: meterTelemetry.grid_frequency_hz || null,
        power_factor: meterTelemetry.power_factor || null,
        // Phase data
        voltage_phase_a: meterTelemetry.voltage_phase_a || null,
        voltage_phase_b: meterTelemetry.voltage_phase_b || null,
        voltage_phase_c: meterTelemetry.voltage_phase_c || null,
        current_phase_a: meterTelemetry.current_phase_a || null,
        current_phase_b: meterTelemetry.current_phase_b || null,
        current_phase_c: meterTelemetry.current_phase_c || null,
        power_phase_a: meterTelemetry.power_phase_a || null,
        power_phase_b: meterTelemetry.power_phase_b || null,
        power_phase_c: meterTelemetry.power_phase_c || null,
      },
    }
    
    const normalizedTelemetry = normalizeTelemetry(telemetryData, 'meter', meterId)
    
    // Store meter-specific data in raw field
    if (normalizedTelemetry.raw) {
      const raw = normalizedTelemetry.raw as any
      raw.import_kwh = meterTelemetry.grid_import_wh ? meterTelemetry.grid_import_wh / 1000 : 0
      raw.export_kwh = meterTelemetry.grid_export_wh ? meterTelemetry.grid_export_wh / 1000 : 0
    }
    
    manager.updateTelemetry(meterId, normalizedTelemetry)
    
    return response.meter
  },
}

