import { useQuery } from '@tanstack/react-query'
import { energyService } from '../services/energy'
import type { HourlyEnergyData, DailyEnergyData, ForecastData } from '../types/energy'

/**
 * Hook to fetch hourly energy data
 */
export function useHourlyEnergy(
  options?: {
    inverterId?: string
    arrayId?: string
    date?: string
    enabled?: boolean
    refetchInterval?: number
  }
) {
  return useQuery<HourlyEnergyData[]>({
    queryKey: ['energy', 'hourly', options?.arrayId || options?.inverterId || 'all', options?.date || 'today'],
    queryFn: () =>
      energyService.getHourlyEnergy(
        options?.inverterId,
        options?.arrayId,
        options?.date
      ),
    enabled: options?.enabled !== false,
    refetchInterval: options?.refetchInterval || 300000, // 5 minutes default (300 seconds)
    staleTime: 60000, // Consider data fresh for 1 minute
  })
}

/**
 * Hook to fetch daily energy summary
 */
export function useDailyEnergy(
  options?: {
    inverterId?: string
    arrayId?: string
    date?: string
    enabled?: boolean
    refetchInterval?: number
  }
) {
  return useQuery<DailyEnergyData | null>({
    queryKey: ['energy', 'daily', options?.arrayId || options?.inverterId || 'all', options?.date || 'today'],
    queryFn: () =>
      energyService.getDailyEnergy(
        options?.inverterId,
        options?.arrayId,
        options?.date
      ),
    enabled: options?.enabled !== false,
    refetchInterval: options?.refetchInterval || 300000, // 5 minutes default
    staleTime: 60000,
  })
}

/**
 * Hook to fetch forecast data
 */
export function useForecast(
  options?: {
    inverterId?: string
    arrayId?: string
    date?: string
    enabled?: boolean
    refetchInterval?: number
  }
) {
  return useQuery<{
    forecast: ForecastData[]
    totalDailyGeneration?: number
    source?: string
  }>({
    queryKey: ['energy', 'forecast', options?.arrayId || options?.inverterId || 'all', options?.date || 'today'],
    queryFn: () =>
      energyService.getForecast(
        options?.inverterId,
        options?.arrayId,
        options?.date
      ),
    enabled: options?.enabled !== false,
    refetchInterval: options?.refetchInterval || 300000, // 5 minutes default
    staleTime: 60000,
  })
}

