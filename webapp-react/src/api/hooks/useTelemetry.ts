import { useQuery } from '@tanstack/react-query'
import { telemetryService } from '../services/telemetry'
import type { TelemetryData, HomeTelemetryData, BatteryData } from '../types/telemetry'

/**
 * Hook to fetch inverter telemetry
 */
export function useInverterTelemetry(
  inverterId: string,
  options?: {
    enabled?: boolean
    refetchInterval?: number
  }
) {
  return useQuery<TelemetryData>({
    queryKey: ['telemetry', 'inverter', inverterId],
    queryFn: () => telemetryService.getInverterNow(inverterId),
    enabled: options?.enabled !== false && !!inverterId,
    refetchInterval: options?.refetchInterval || 5000, // 5 seconds default
    staleTime: 3000, // Consider data fresh for 3 seconds
  })
}

/**
 * Hook to fetch system-level telemetry
 */
export function useSystemTelemetry(options?: {
  enabled?: boolean
  refetchInterval?: number
}) {
  return useQuery<HomeTelemetryData>({
    queryKey: ['telemetry', 'system'],
    queryFn: () => telemetryService.getSystemNow(),
    enabled: options?.enabled !== false,
    refetchInterval: options?.refetchInterval || 5000, // 5 seconds default
    staleTime: 3000,
  })
}

/**
 * @deprecated Use useSystemTelemetry instead. This is kept for backward compatibility.
 */
export const useHomeTelemetry = useSystemTelemetry

/**
 * Hook to fetch array telemetry
 */
export function useArrayTelemetry(
  arrayId: string,
  options?: {
    enabled?: boolean
    refetchInterval?: number
  }
) {
  return useQuery<TelemetryData>({
    queryKey: ['telemetry', 'array', arrayId],
    queryFn: () => telemetryService.getArrayNow(arrayId),
    enabled: options?.enabled !== false && !!arrayId,
    refetchInterval: options?.refetchInterval || 5000,
    staleTime: 3000,
  })
}

/**
 * Hook to fetch battery telemetry
 */
export function useBatteryTelemetry(
  bankId?: string,
  options?: {
    enabled?: boolean
    refetchInterval?: number
  }
) {
  return useQuery<BatteryData | BatteryData[]>({
    queryKey: ['telemetry', 'battery', bankId || 'all'],
    queryFn: () => telemetryService.getBatteryNow(bankId),
    enabled: options?.enabled !== false,
    refetchInterval: options?.refetchInterval || 5000,
    staleTime: 3000,
  })
}

