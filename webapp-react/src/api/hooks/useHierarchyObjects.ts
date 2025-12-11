/**
 * React Hooks for Hierarchy Objects
 * Provides easy access to hierarchy objects in React components
 */

import { useQuery } from '@tanstack/react-query'
import { useMemo } from 'react'
import { HierarchyManager } from '../managers/HierarchyManager'
import { hierarchyService } from '../services/hierarchy'
import type { System, Inverter, BatteryPack, Meter } from '../models'

/**
 * Hook to load hierarchy and get manager instance
 */
export function useHierarchyManager() {
  const { data: manager, isLoading, error } = useQuery({
    queryKey: ['hierarchy', 'manager'],
    queryFn: async () => {
      await hierarchyService.loadHierarchy()
      return HierarchyManager.getInstance()
    },
    staleTime: 60000, // Consider fresh for 1 minute
    gcTime: 5 * 60 * 1000, // Keep in cache for 5 minutes
    refetchOnMount: false, // Don't refetch on mount if data is fresh
    refetchOnWindowFocus: false, // Don't refetch on window focus
  })

  return { 
    manager: manager || null, 
    isLoading, 
    error 
  }
}

/**
 * Hook to get a system by ID
 */
export function useSystem(systemId: string): System | null {
  const { manager } = useHierarchyManager()
  return useMemo(() => {
    return manager?.getSystem(systemId) || null
  }, [manager, systemId])
}

/**
 * Hook to get an inverter by ID
 */
export function useInverter(inverterId: string): Inverter | null {
  const { manager } = useHierarchyManager()
  return useMemo(() => {
    return manager?.getInverter(inverterId) || null
  }, [manager, inverterId])
}

/**
 * Hook to get a battery pack by ID
 */
export function useBatteryPack(packId: string): BatteryPack | null {
  const { manager } = useHierarchyManager()
  return useMemo(() => {
    return manager?.getBatteryPack(packId) || null
  }, [manager, packId])
}

/**
 * Hook to get a meter by ID
 */
export function useMeter(meterId: string): Meter | null {
  const { manager } = useHierarchyManager()
  return useMemo(() => {
    return manager?.getMeter(meterId) || null
  }, [manager, meterId])
}

/**
 * Hook to get all systems
 */
export function useAllSystems(): System[] {
  const { manager } = useHierarchyManager()
  return useMemo(() => {
    return manager?.getAllSystems() || []
  }, [manager])
}

/**
 * Hook to get all inverters
 */
export function useAllInverters(): Inverter[] {
  const { manager } = useHierarchyManager()
  return useMemo(() => {
    return manager?.getAllInverters() || []
  }, [manager])
}

/**
 * Hook to get all battery packs
 */
export function useAllBatteryPacks(): BatteryPack[] {
  const { manager } = useHierarchyManager()
  return useMemo(() => {
    return manager?.getAllBatteryPacks() || []
  }, [manager])
}

/**
 * Hook to get all meters
 */
export function useAllMeters(): Meter[] {
  const { manager } = useHierarchyManager()
  return useMemo(() => {
    return manager?.getAllMeters() || []
  }, [manager])
}

/**
 * Hook to get system total power
 */
export function useSystemTotalPower(systemId: string): number {
  const system = useSystem(systemId)
  return useMemo(() => {
    return system?.getTotalPower() || 0
  }, [system])
}

/**
 * Hook to get system total battery SOC
 */
export function useSystemTotalBatterySOC(systemId: string): number | null {
  const system = useSystem(systemId)
  return useMemo(() => {
    return system?.getTotalBatterySOC() || null
  }, [system])
}

