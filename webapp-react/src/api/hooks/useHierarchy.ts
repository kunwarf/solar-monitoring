import { useQuery } from '@tanstack/react-query'
import { hierarchyService } from '../services/hierarchy'
import type { InverterArray, HomeHierarchy, SystemConfig } from '../types/hierarchy'

/**
 * Hook to fetch all arrays
 */
export function useArrays(options?: {
  enabled?: boolean
  refetchInterval?: number
}) {
  return useQuery<InverterArray[]>({
    queryKey: ['hierarchy', 'arrays'],
    queryFn: () => hierarchyService.getArrays(),
    enabled: options?.enabled !== false,
    refetchInterval: options?.refetchInterval || 60000, // 1 minute default
    staleTime: 30000, // Consider data fresh for 30 seconds
  })
}

/**
 * Hook to fetch system configuration
 */
export function useConfig(options?: {
  enabled?: boolean
}) {
  return useQuery<SystemConfig>({
    queryKey: ['hierarchy', 'config'],
    queryFn: () => hierarchyService.getConfig(),
    enabled: options?.enabled !== false,
    // Config is on-demand only (no polling)
    staleTime: Infinity,
    gcTime: 5 * 60 * 1000, // Keep in cache for 5 minutes
  })
}

/**
 * Hook to fetch complete home hierarchy
 */
export function useHomeHierarchy(options?: {
  enabled?: boolean
  refetchInterval?: number
}) {
  return useQuery<HomeHierarchy>({
    queryKey: ['hierarchy', 'home'],
    queryFn: () => hierarchyService.getHomeHierarchy(),
    enabled: options?.enabled !== false,
    refetchInterval: options?.refetchInterval || 60000, // 1 minute default
    staleTime: 30000,
  })
}

