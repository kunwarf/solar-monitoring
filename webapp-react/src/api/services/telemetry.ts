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
   * Get home-level aggregated telemetry
   */
  async getHomeNow(): Promise<HomeTelemetryData> {
    const response = await api.get<BackendHomeTelemetryResponse>(
      '/api/home/now',
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
                // Normalize the telemetry data
                const invTelemetry = normalizeTelemetry(inv.telemetry, 'inverter', inv.inverter_id)
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
                  power: packTel.power || null,
                  soc: packTel.soc || null,
                  temperature: packTel.temperature || null,
                  status: packTel.soc !== null && packTel.soc !== undefined ? 'online' : 'offline',
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
    
    // Handle multiple banks
    if (response.banks && response.banks.length > 0) {
      return response.banks.map(bat => {
        const normalized = normalizeBatteryData(bat)
        // Add configured_banks to raw data for name lookup
        if (normalized.raw) {
          ;(normalized.raw as any).configured_banks = configuredBanks
        }
        
        // Update hierarchy object
        manager.updateBatteryTelemetry(normalized.id, normalized)
        
        return normalized
      })
    }
    
    // Handle single battery (backward compatibility)
    if (response.battery) {
      const normalized = normalizeBatteryData(response.battery)
      // Add configured_banks to raw data
      if (normalized.raw) {
        ;(normalized.raw as any).configured_banks = configuredBanks
      }
      
      // Update hierarchy object
      manager.updateBatteryTelemetry(normalized.id, normalized)
      
      return normalized
    }
    
    throw new Error('No battery data available')
  },
}

