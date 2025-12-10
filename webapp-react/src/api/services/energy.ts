import { api, CACHE_TTL } from '../client'
import type {
  BackendHourlyEnergyResponse,
  BackendDailyEnergyResponse,
  BackendForecastResponse,
} from '../types/energy'
import {
  normalizeHourlyEnergy,
  normalizeDailyEnergy,
  normalizeForecast,
} from '../normalizers/energy'
import type { HourlyEnergyData, DailyEnergyData, ForecastData } from '../types/energy'

/**
 * Energy service - handles historical energy data
 */
export const energyService = {
  /**
   * Get hourly energy data
   */
  async getHourlyEnergy(
    inverterId?: string,
    arrayId?: string,
    date?: string
  ): Promise<HourlyEnergyData[]> {
    let url: string
    
    if (arrayId) {
      url = `/api/arrays/${arrayId}/energy/hourly`
      if (date) {
        url += `?date=${date}`
      }
    } else {
      const invParam = inverterId || 'all'
      url = `/api/energy/hourly?inverter_id=${invParam}`
      if (date) {
        url += `&date=${date}`
      }
    }
    
    const response = await api.get<BackendHourlyEnergyResponse>(
      url,
      { ttl: CACHE_TTL.ENERGY, key: `energy:hourly:${arrayId || inverterId || 'all'}:${date || 'today'}` }
    )
    
    return normalizeHourlyEnergy(response)
  },

  /**
   * Get daily energy summary
   */
  async getDailyEnergy(
    inverterId?: string,
    arrayId?: string,
    date?: string
  ): Promise<DailyEnergyData | null> {
    let url: string
    
    if (arrayId) {
      url = `/api/arrays/${arrayId}/energy/daily`
      if (date) {
        url += `?date=${date}`
      }
    } else {
      const invParam = inverterId || 'all'
      url = `/api/energy/daily?inverter_id=${invParam}`
      if (date) {
        url += `&date=${date}`
      }
    }
    
    const response = await api.get<BackendDailyEnergyResponse>(
      url,
      { ttl: CACHE_TTL.ENERGY, key: `energy:daily:${arrayId || inverterId || 'all'}:${date || 'today'}` }
    )
    
    return normalizeDailyEnergy(response)
  },

  /**
   * Get forecast data
   */
  async getForecast(
    inverterId?: string,
    arrayId?: string,
    date?: string
  ): Promise<{ forecast: ForecastData[]; totalDailyGeneration?: number; source?: string }> {
    let url: string
    
    if (arrayId) {
      url = `/api/arrays/${arrayId}/forecast`
      if (date) {
        url += `?date=${date}`
      }
    } else {
      const invParam = inverterId || 'all'
      url = `/api/forecast?inverter_id=${invParam}`
      if (date) {
        url += `&date=${date}`
      }
    }
    
    const response = await api.get<BackendForecastResponse>(
      url,
      { ttl: CACHE_TTL.ENERGY, key: `energy:forecast:${arrayId || inverterId || 'all'}:${date || 'today'}` }
    )
    
    return {
      forecast: normalizeForecast(response),
      totalDailyGeneration: response.total_daily_generation_kwh,
      source: response.source,
    }
  },
}

