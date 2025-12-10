/**
 * Hooks for accessing mockData structure from API
 * 
 * These hooks provide the exact same data structure as mockData.ts,
 * but fetch from API through DataProvider. Components can use these
 * hooks instead of importing constants, with minimal changes.
 */

import { useDataContext } from './DataProvider';
import type {
  HomeHierarchy,
} from './mockData';

/**
 * Get home hierarchy (same structure as mockData.homeHierarchy)
 */
export function useHomeHierarchyData(): HomeHierarchy {
  const { homeHierarchy } = useDataContext();
  
  // Return fallback if not loaded
  if (!homeHierarchy) {
    return {
      id: "home-001",
      name: "Home Solar System",
      systems: [],
      meters: [],
    };
  }
  
  return homeHierarchy;
}

/**
 * Get energy stats (same structure as mockData.energyStats)
 */
export function useEnergyStatsData() {
  const { energyStats } = useDataContext();
  return energyStats;
}

/**
 * Get chart data (same structure as mockData.chartData)
 */
export function useChartData() {
  const { chartData } = useDataContext();
  return chartData;
}

/**
 * Get devices list (same structure as mockData.devices)
 */
export function useDevicesData() {
  const { devices } = useDataContext();
  return devices;
}

