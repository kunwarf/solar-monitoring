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

/**
 * Telemetry service - handles all telemetry-related API calls
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
    
    return normalizeTelemetry(response.now, 'inverter', inverterId)
  },

  /**
   * Get home-level aggregated telemetry
   */
  async getHomeNow(): Promise<HomeTelemetryData> {
    const response = await api.get<BackendHomeTelemetryResponse>(
      '/api/home/now',
      { ttl: CACHE_TTL.TELEMETRY, key: 'telemetry:home' }
    )
    
    if (!response.home) {
      throw new Error('No home telemetry data available')
    }
    
    return normalizeHomeTelemetry(response.home)
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
    
    return normalizeArrayTelemetry(response.now)
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
    
    // Handle multiple banks
    if (response.banks && response.banks.length > 0) {
      return response.banks.map(normalizeBatteryData)
    }
    
    // Handle single battery (backward compatibility)
    if (response.battery) {
      return normalizeBatteryData(response.battery)
    }
    
    throw new Error('No battery data available')
  },
}

