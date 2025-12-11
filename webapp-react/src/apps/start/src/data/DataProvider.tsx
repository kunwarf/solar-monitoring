/**
 * Data Provider Component
 * 
 * This component fetches data from API and provides it through context
 * in the exact same structure as mockData. Components can use the data
 * through hooks exported from mockData.ts without any changes.
 */

import React, { createContext, useContext, ReactNode } from 'react';
import { useQueries } from '@tanstack/react-query';
import { useHomeHierarchy, useHomeTelemetry, useBatteryTelemetry, useDailyEnergy, useHourlyEnergy } from '../../../../api/hooks';
import { telemetryService } from '../../../../api/services/telemetry';
import type {
  BatteryBank,
  BatteryArray,
  Inverter,
  InverterArray,
  Meter,
  System,
  HomeHierarchy,
} from './mockData';

interface DataContextValue {
  homeHierarchy: HomeHierarchy | null;
  energyStats: {
    solarPower: number;
    batteryPower: number;
    batteryLevel: number;
    consumption: number;
    gridPower: number;
    isGridExporting: boolean;
    dailyProduction: number;
    dailyConsumption: number;
    selfConsumption: number;
    gridExported: number;
    batteryChargeEnergy: number;
    batteryDischargeEnergy: number;
    loadEnergy: number;
    gridImportEnergy: number;
    gridExportEnergy: number;
    co2Saved: number;
    moneySaved: number;
    monthlyBillAmount: number;
    dailyPrediction: number;
    avgKwPerKwp: number;
    installedCapacity: number;
  };
  chartData: Array<{
    time: string;
    solar: number;
    consumption: number;
    battery: number;
    grid: number;
  }>;
  devices: Array<{
    id: string;
    name: string;
    type: "inverter" | "battery" | "meter";
    status: "online" | "offline" | "warning";
    model: string;
    serialNumber: string;
    value: string;
    unit: string;
    metrics: Array<{ label: string; value: string; unit: string }>;
  }>;
}

const DataContext = createContext<DataContextValue | null>(null);

export function DataProvider({ children }: { children: ReactNode }) {
  const { data: apiHierarchy } = useHomeHierarchy();
  const { data: homeTelemetry, error: homeTelemetryError, isLoading: homeTelemetryLoading } = useHomeTelemetry();
  const { data: allBatteryData } = useBatteryTelemetry();
  const { data: dailyEnergy } = useDailyEnergy();
  const { data: hourlyData } = useHourlyEnergy();
  
  // DEBUG: Log home telemetry status
  React.useEffect(() => {
    if (homeTelemetryError) {
      console.error('[DataProvider] Home telemetry error:', homeTelemetryError);
    }
    if (homeTelemetryLoading) {
      console.log('[DataProvider] Home telemetry loading...');
    }
    if (homeTelemetry) {
      console.log('[DataProvider] Home telemetry loaded:', {
        pvPower: homeTelemetry.pvPower,
        batteryPower: homeTelemetry.batteryPower,
        loadPower: homeTelemetry.loadPower,
        gridPower: homeTelemetry.gridPower,
        hasDailyEnergy: !!homeTelemetry.dailyEnergy,
        hasFinancialMetrics: !!homeTelemetry.financialMetrics,
      });
    } else {
      console.warn('[DataProvider] Home telemetry is null/undefined', {
        error: homeTelemetryError,
        loading: homeTelemetryLoading,
      });
    }
  }, [homeTelemetry, homeTelemetryError, homeTelemetryLoading]);

  // Fetch array telemetry for all arrays
  const arrayTelemetryQueries = useQueries({
    queries: (apiHierarchy?.inverterArrays || []).map(array => ({
      queryKey: ['telemetry', 'array', array.id],
      queryFn: () => telemetryService.getArrayNow(array.id),
      enabled: !!apiHierarchy && !!array.id,
      refetchInterval: 5000,
      staleTime: 3000,
    })),
  });

  // Build array telemetry map
  const arrayTelemetryMap = React.useMemo(() => {
    const map = new Map<string, any>();
    arrayTelemetryQueries.forEach((query, index) => {
      if (query.data && apiHierarchy?.inverterArrays[index]) {
        map.set(apiHierarchy.inverterArrays[index].id, query.data);
      }
    });
    return map;
  }, [arrayTelemetryQueries, apiHierarchy]);

  // Transform API hierarchy to match mockData structure
  const homeHierarchy: HomeHierarchy | null = React.useMemo(() => {
    if (!apiHierarchy) {
      console.log('[DataProvider] No apiHierarchy available');
      return null;
    }

    // DEBUG: Log device name maps
    const deviceNames = (apiHierarchy as any)?._deviceNames;
    if (deviceNames) {
      console.log('[DataProvider] Device name maps:', {
        inverters: deviceNames.inverters ? Array.from(deviceNames.inverters.entries()) : 'none',
        batteries: deviceNames.batteries ? Array.from(deviceNames.batteries.entries()) : 'none',
        meters: deviceNames.meters ? Array.from(deviceNames.meters.entries()) : 'none',
      });
    } else {
      console.warn('[DataProvider] No _deviceNames found in apiHierarchy');
    }

    // DEBUG: Log home telemetry meters
    console.log('[DataProvider] Home telemetry meters:', {
      hasHomeTelemetry: !!homeTelemetry,
      metersCount: homeTelemetry?.meters?.length || 0,
      meters: homeTelemetry?.meters || [],
    });

    // DEBUG: Log battery data
    console.log('[DataProvider] Battery data:', {
      hasBatteryData: !!allBatteryData,
      isArray: Array.isArray(allBatteryData),
      batteryIds: allBatteryData 
        ? (Array.isArray(allBatteryData) ? allBatteryData.map(b => b.id) : [allBatteryData.id])
        : [],
    });

    // Build battery data map and configured banks map (for names)
    const batteryDataMap = new Map<string, any>();
    const configuredBanksMap = new Map<string, { name?: string; id: string }>();
    
    if (allBatteryData) {
      const batteries = Array.isArray(allBatteryData) ? allBatteryData : [allBatteryData];
      batteries.forEach(bat => {
        batteryDataMap.set(bat.id, bat);
        console.log(`[DataProvider] Mapped battery data: id=${bat.id}, hasDevices=${!!bat.devices}, devicesCount=${bat.devices?.length || 0}`);
      });
      
      // Also extract configured_banks from raw data if available (from /api/battery/now)
      batteries.forEach(bat => {
        const raw = (bat as any).raw;
        if (raw?.configured_banks && Array.isArray(raw.configured_banks)) {
          raw.configured_banks.forEach((bank: any) => {
            if (bank.id && bank.name) {
              configuredBanksMap.set(bank.id, { name: bank.name, id: bank.id });
              console.log(`[DataProvider] Found configured bank: ${bank.id} -> ${bank.name}`);
            }
          });
        }
      });
    }

    // Transform arrays with real telemetry data
    const inverterArrays: InverterArray[] = apiHierarchy.inverterArrays.map(array => {
      const arrayTelemetry = arrayTelemetryMap.get(array.id);
      const rawArrayData = arrayTelemetry?.raw as any;

      // Get individual inverters from array telemetry
      // The raw data should contain the inverters array from BackendArrayTelemetry
      const rawData = arrayTelemetry?.raw as any;
      const invertersData = rawData?.inverters || [];
      
      const inverters: Inverter[] = array.inverterIds.map((invId, idx) => {
        // Try to find inverter data from array telemetry
        const inverterData = invertersData.find((inv: any) => inv.inverter_id === invId);
        
        // Get device name from config (preferred) or fallback to ID
        const deviceName = (apiHierarchy as any)?._deviceNames?.inverters?.get(invId) || 
                          (invId.includes('_') 
                            ? invId.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())
                            : invId);
        
        // Calculate per-inverter values: use individual data if available, otherwise divide array total
        const inverterCount = array.inverterIds.length || 1;
        const solarPower = inverterData 
          ? (inverterData.pv_power_w || 0) / 1000 
          : (arrayTelemetry?.pvPower || 0) / inverterCount;
        const gridPower = inverterData 
          ? (inverterData.grid_power_w || 0) / 1000 
          : (arrayTelemetry?.gridPower || 0) / inverterCount;
        const loadPower = inverterData 
          ? (inverterData.load_power_w || 0) / 1000 
          : (arrayTelemetry?.loadPower || 0) / inverterCount;
        const batteryPower = inverterData 
          ? (inverterData.batt_power_w || 0) / 1000 
          : (arrayTelemetry?.batteryPower || 0) / inverterCount;
        
        // Get model from raw data if available
        const rawInverterData = arrayTelemetry?.raw as any;
        const model = rawInverterData?._metadata?.device_model || 
                     rawInverterData?._metadata?.model_name || 
                     "Unknown";
        
        return {
          id: invId,
          name: deviceName, // Use actual device name (e.g., "powdrive1", "senergy1")
          model: model,
          serialNumber: invId,
          status: "online" as const,
          metrics: {
            solarPower,
            gridPower,
            loadPower,
            batteryPower,
            efficiency: 97.0, // Default efficiency
            dcVoltage: 580, // Default DC voltage
            temperature: arrayTelemetry?.inverterTemperature || 0,
          },
        };
      });

      // Get battery array if attached - ALWAYS create if batteryArrayId exists
      let batteryArray: BatteryArray | undefined;
      if (array.batteryArrayId) {
        const batteryArrayConfig = apiHierarchy.batteryArrays.find(ba => ba.id === array.batteryArrayId);
        
        // Try to find battery data - check both by ID and by battery bank IDs
        let batteryData: any = batteryDataMap.get(array.batteryArrayId);
        
        // If not found by battery array ID, try to find by battery bank IDs
        if (!batteryData && batteryArrayConfig) {
          for (const bankId of batteryArrayConfig.batteryBankIds) {
            const found = batteryDataMap.get(bankId);
            if (found) {
              batteryData = found;
              break;
            }
          }
        }
        
        // Also check if battery data is in array telemetry (packs)
        const rawData = arrayTelemetry?.raw as any;
        const packs = rawData?.packs || [];
        
        // ALWAYS create battery array if batteryArrayId exists (even without data)
        // This ensures battery arrays show up in the UI
        let batteries: BatteryBank[] = [];
        
        // Get battery bank name from device name map (from database via /api/config)
        // No fallbacks - all configs should be in database
        const deviceNames = (apiHierarchy as any)?._deviceNames;
        
        // DEBUG: Log battery name lookup
        console.log(`[DataProvider] Battery name lookup for array ${array.id}:`, {
          batteryArrayId: array.batteryArrayId,
          batteryBankIds: batteryArrayConfig?.batteryBankIds,
          availableBatteryIds: deviceNames?.batteries ? Array.from(deviceNames.batteries.keys()) : [],
        });
        
        // Try all battery bank IDs in the array to find name from multiple sources:
        // 1. Device name map from /api/config (preferred)
        // 2. Configured banks from /api/battery/now response
        // 3. Battery data raw configured_banks
        let batteryBankName: string | undefined;
        if (batteryArrayConfig?.batteryBankIds) {
          for (const bankId of batteryArrayConfig.batteryBankIds) {
            // First try device name map from /api/config
            if (deviceNames?.batteries) {
              const name = deviceNames.batteries.get(bankId);
              if (name) {
                batteryBankName = name;
                console.log(`[DataProvider] Found battery name from config: ${bankId} -> ${name}`);
                break;
              }
            }
            
            // Second try configured banks map (from /api/battery/now)
            const configuredBank = configuredBanksMap.get(bankId);
            if (configuredBank?.name) {
              batteryBankName = configuredBank.name;
              console.log(`[DataProvider] Found battery name from configured_banks: ${bankId} -> ${batteryBankName}`);
              break;
            }
            
            // Third try battery data raw configured_banks
            if (batteryData?.raw?.configured_banks) {
              const rawBank = batteryData.raw.configured_banks.find((b: any) => b.id === bankId);
              if (rawBank?.name) {
                batteryBankName = rawBank.name;
                console.log(`[DataProvider] Found battery name from battery data raw: ${bankId} -> ${batteryBankName}`);
                break;
              }
            }
          }
        }
        
        if (!batteryBankName) {
          console.warn(`[DataProvider] No battery name found for array ${array.id}, batteryBankIds: ${batteryArrayConfig?.batteryBankIds}`);
          // Only use "Battery Bank" as absolute last resort
          batteryBankName = "Battery Bank";
        }
        
        console.log(`[DataProvider] Final battery bank name for array ${array.id}: ${batteryBankName}`);
        
        // Get actual battery bank IDs from config
        const actualBankIds = batteryArrayConfig?.batteryBankIds || [];
        const primaryBankId = actualBankIds[0] || batteryData?.id || `${array.batteryArrayId}-bank`;
        
        if (packs.length > 0) {
          // Use pack data from array telemetry (preferred - most accurate)
          // For multiple packs, use the bank ID with pack index
          batteries = packs.map((pack: any, idx: number) => {
            // Use actual bank ID if available, otherwise use pack_id or fallback
            const bankId = actualBankIds[idx] || actualBankIds[0] || pack.pack_id || primaryBankId;
            return {
              id: bankId, // Use actual bank ID from config
              name: `${batteryBankName} #${idx + 1}`, // Use battery bank name (e.g., "Pylontech Battery Bank #1")
              model: batteryData?.info?.model || batteryData?.raw?.model || "Unknown",
              serialNumber: batteryData?.info?.serialNumber || `${bankId}-${idx + 1}`,
              status: "online" as const,
              metrics: {
                soc: pack.soc_pct ?? batteryData?.soc ?? arrayTelemetry?.batterySoc ?? 0,
                power: (pack.power_w || 0) / 1000, // Convert W to kW (positive = charging, negative = discharging)
                voltage: pack.voltage_v ?? batteryData?.voltage ?? arrayTelemetry?.batteryVoltage ?? 0,
                temperature: pack.temperature_c ?? pack.temperature ?? batteryData?.temperature ?? arrayTelemetry?.batteryTemperature ?? 0,
              },
              // Context fields for API calls
              batteryBankId: bankId,
              packIndex: idx,
              batteryArrayId: array.batteryArrayId,
            };
          });
        } else if (batteryData?.devices && batteryData.devices.length > 0) {
          // Use device data from battery telemetry
          batteries = batteryData.devices.map((dev: any, idx: number) => {
            // Use actual bank ID if available
            const bankId = actualBankIds[idx] || actualBankIds[0] || batteryData.id || primaryBankId;
            return {
              id: bankId, // Use actual bank ID from config
              name: `${batteryBankName} #${idx + 1}`, // Use battery bank name (e.g., "Pylontech Battery Bank #1")
              model: batteryData.info?.model || batteryData?.raw?.model || "Unknown",
              serialNumber: batteryData.info?.serialNumber || `${bankId}-${idx + 1}`,
              status: "online" as const,
              metrics: {
                soc: dev.soc ?? batteryData.soc ?? 0,
                power: (dev.current || 0) * (dev.voltage || batteryData.voltage || 0) / 1000, // Convert to kW
                voltage: dev.voltage ?? batteryData.voltage ?? 0,
                temperature: dev.temperature ?? batteryData.temperature ?? 0,
              },
              // Context fields for API calls
              batteryBankId: bankId,
              packIndex: idx,
              batteryArrayId: array.batteryArrayId,
            };
          });
        } else if (batteryData) {
          // Create a single battery entry from aggregate battery data
          batteries = [{
            id: primaryBankId, // Use actual bank ID
            name: batteryBankName || "Battery Bank",
            model: batteryData.info?.model || "Unknown",
            serialNumber: batteryData.info?.serialNumber || `${primaryBankId}-1`,
            status: "online" as const,
            metrics: {
              soc: batteryData.soc ?? arrayTelemetry?.batterySoc ?? 0,
              power: (batteryData.current || 0) * (batteryData.voltage || 0) / 1000, // Convert to kW
              voltage: batteryData.voltage ?? arrayTelemetry?.batteryVoltage ?? 0,
              temperature: batteryData.temperature ?? arrayTelemetry?.batteryTemperature ?? 0,
            },
            // Context fields for API calls
            batteryBankId: primaryBankId,
            packIndex: 0,
            batteryArrayId: array.batteryArrayId,
          }];
        } else if (arrayTelemetry && (arrayTelemetry.batterySoc !== null || arrayTelemetry.batteryPower !== 0)) {
          // Use battery data from array telemetry if available
          batteries = [{
            id: primaryBankId, // Use actual bank ID
            name: batteryBankName || "Battery Bank",
            model: "Unknown",
            serialNumber: `${primaryBankId}-1`,
            status: "online" as const,
            metrics: {
              soc: arrayTelemetry.batterySoc ?? 0,
              power: arrayTelemetry.batteryPower ?? 0, // Already in kW
              voltage: arrayTelemetry.batteryVoltage ?? 0,
              temperature: arrayTelemetry.batteryTemperature ?? 0,
            },
            // Context fields for API calls
            batteryBankId: primaryBankId,
            packIndex: 0,
            batteryArrayId: array.batteryArrayId,
          }];
        } else {
          // Create placeholder battery entry if no data available yet
          batteries = [{
            id: primaryBankId, // Use actual bank ID even for placeholder
            name: batteryBankName || "Battery Bank",
            model: "Unknown",
            serialNumber: `${primaryBankId}-1`,
            status: "online" as const,
            metrics: {
              soc: 0,
              power: 0,
              voltage: 0,
              temperature: 0,
            },
            // Context fields for API calls
            batteryBankId: primaryBankId,
            packIndex: 0,
            batteryArrayId: array.batteryArrayId,
          }];
        }

        batteryArray = {
          id: array.batteryArrayId,
          name: batteryArrayConfig?.name || "Battery Array",
          batteries,
        };
      }

      return {
        id: array.id,
        name: array.name,
        inverters,
        batteryArrayId: array.batteryArrayId, // Preserve batteryArrayId for use in systems mapping
        // Remove batteryArray from InverterArray - they'll be siblings under System
      };
    });

    // Group Inverter Arrays and Battery Arrays into Systems
    // Each Inverter Array becomes a System, with its attached Battery Array as a sibling
    const systems: System[] = inverterArrays.map(invArray => {
      // Find the battery array attached to this inverter array
      // Try multiple approaches to find the attached battery array:
      // 1. Use batteryArrayId from the inverter array (most direct)
      // 2. Check if any battery array has this inverter array as attachedInverterArrayId
      let attachedBatteryArray: typeof apiHierarchy.batteryArrays[0] | undefined;
      
      // First, try using batteryArrayId from the inverter array
      const batteryArrayId = (invArray as any).batteryArrayId;
      if (batteryArrayId) {
        attachedBatteryArray = apiHierarchy.batteryArrays.find(ba => ba.id === batteryArrayId);
        if (!attachedBatteryArray) {
          console.warn(`[DataProvider] Battery array ${batteryArrayId} not found in apiHierarchy.batteryArrays for inverter array ${invArray.id}`);
        }
      }
      
      // Fallback: check if any battery array has this inverter array as attachedInverterArrayId
      if (!attachedBatteryArray) {
        attachedBatteryArray = apiHierarchy.batteryArrays.find(
          ba => ba.attachedInverterArrayId === invArray.id
        );
      }
      
      // Debug logging
      if (batteryArrayId && !attachedBatteryArray) {
        console.log(`[DataProvider] Inverter array ${invArray.id} has batteryArrayId ${batteryArrayId} but battery array not found. Available battery arrays:`, 
          apiHierarchy.batteryArrays.map(ba => ({ id: ba.id, attachedTo: ba.attachedInverterArrayId }))
        );
      }
      
      // Get the battery array data if it exists
      let batteryArrayData: BatteryArray | undefined;
      const arrayTelemetry = arrayTelemetryMap.get(invArray.id);
      const rawData = arrayTelemetry?.raw as any;
      const packs = rawData?.packs || [];
      const hasBatteryInTelemetry = arrayTelemetry && (
        arrayTelemetry.batterySoc !== null || 
        arrayTelemetry.batteryPower !== 0 || 
        packs.length > 0
      );
      
      // Create battery array if:
      // 1. We found an attached battery array config, OR
      // 2. We have batteryArrayId (even without config), OR
      // 3. We have battery data in array telemetry (even without config)
      if (attachedBatteryArray || batteryArrayId || hasBatteryInTelemetry) {
        const batteryArrayId = attachedBatteryArray?.id || `${invArray.id}-battery-array`;
        // attachedBatteryArray IS already the battery array config from apiHierarchy.batteryArrays
        const batteryArrayConfig = attachedBatteryArray || null;
        
        // Try to find battery data
        let batteryData: any = attachedBatteryArray 
          ? batteryDataMap.get(attachedBatteryArray.id)
          : null;
        
        // Get battery bank IDs from config if available, otherwise try to infer from battery data
        let batteryBankIdsFromConfig = batteryArrayConfig?.batteryBankIds || [];
        
        // If no batteryBankIds from config, try to find them from battery data map
        // by checking which battery IDs match this inverter array's battery data
        if (batteryBankIdsFromConfig.length === 0) {
          // Try to find battery banks that might be associated with this array
          // by checking battery data that exists
          const allBatteryIds = Array.from(batteryDataMap.keys());
          // If we have battery data, use those IDs
          if (allBatteryIds.length > 0) {
            // For now, use all available battery IDs as a fallback
            // In a real scenario, we'd need to match them based on some logic
            batteryBankIdsFromConfig = allBatteryIds;
            console.log(`[DataProvider] No batteryBankIds in config for ${invArray.id}, using available battery IDs:`, batteryBankIdsFromConfig);
          }
        }
        
        if (!batteryData && batteryBankIdsFromConfig.length > 0) {
          for (const bankId of batteryBankIdsFromConfig) {
            const found = batteryDataMap.get(bankId);
            if (found) {
              batteryData = found;
              break;
            }
          }
        }
        
        // Create batteries array
        let batteries: BatteryBank[] = [];
        
        // Get battery bank name from device name map (from database via /api/config)
        // No fallbacks - all configs should be in database
        const deviceNames = (apiHierarchy as any)?._deviceNames;
        
        // DEBUG: Log battery name lookup for system
        console.log(`[DataProvider] System battery name lookup for ${invArray.id}:`, {
          batteryArrayId,
          batteryBankIds: batteryBankIdsFromConfig,
          batteryArrayConfigExists: !!batteryArrayConfig,
          availableBatteryIds: deviceNames?.batteries ? Array.from(deviceNames.batteries.keys()) : [],
        });
        
        // Try all battery bank IDs in the array to find name from multiple sources:
        // 1. Device name map from /api/config (preferred)
        // 2. Configured banks from /api/battery/now response
        // 3. Battery data raw configured_banks
        let batteryBankNameForSystem: string | undefined;
        if (batteryBankIdsFromConfig.length > 0) {
          for (const bankId of batteryBankIdsFromConfig) {
            // First try device name map from /api/config
            if (deviceNames?.batteries) {
              const name = deviceNames.batteries.get(bankId);
              if (name) {
                batteryBankNameForSystem = name;
                console.log(`[DataProvider] Found system battery name from config: ${bankId} -> ${name}`);
                break;
              }
            }
            
            // Second try configured banks map (from /api/battery/now)
            const configuredBank = configuredBanksMap.get(bankId);
            if (configuredBank?.name) {
              batteryBankNameForSystem = configuredBank.name;
              console.log(`[DataProvider] Found system battery name from configured_banks: ${bankId} -> ${batteryBankNameForSystem}`);
              break;
            }
            
            // Third try battery data raw configured_banks
            if (batteryData?.raw?.configured_banks) {
              const rawBank = batteryData.raw.configured_banks.find((b: any) => b.id === bankId);
              if (rawBank?.name) {
                batteryBankNameForSystem = rawBank.name;
                console.log(`[DataProvider] Found system battery name from battery data raw: ${bankId} -> ${batteryBankNameForSystem}`);
                break;
              }
            }
          }
        }
        
        if (!batteryBankNameForSystem) {
          console.warn(`[DataProvider] No battery name found for system ${invArray.id}, batteryBankIds: ${batteryBankIdsFromConfig}`);
          // Only use "Battery Bank" as absolute last resort
          batteryBankNameForSystem = "Battery Bank";
        }
        
        console.log(`[DataProvider] Final system battery bank name for ${invArray.id}: ${batteryBankNameForSystem}`);
        
        // Get actual battery bank IDs from config (or inferred)
        const actualBankIds = batteryBankIdsFromConfig;
        const primaryBankId = actualBankIds[0] || batteryData?.id || `${batteryArrayId}-bank`;
        
        if (packs.length > 0) {
          // Use pack data from array telemetry (preferred - most accurate)
          batteries = packs.map((pack: any, idx: number) => {
            // Use actual bank ID if available, otherwise use pack_id or fallback
            const bankId = actualBankIds[idx] || actualBankIds[0] || pack.pack_id || primaryBankId;
            return {
              id: bankId, // Use actual bank ID from config
              name: `${batteryBankNameForSystem} #${idx + 1}`, // Use battery bank name (e.g., "Pylontech Battery Bank #1")
              model: batteryData?.info?.model || (batteryData?.raw as any)?.model || "Unknown",
              serialNumber: batteryData?.info?.serialNumber || `${bankId}-${idx + 1}`,
              status: "online" as const,
              metrics: {
                soc: pack.soc_pct ?? batteryData?.soc ?? arrayTelemetry?.batterySoc ?? 0,
                power: (pack.power_w || 0) / 1000,
                voltage: pack.voltage_v ?? pack.voltage ?? batteryData?.voltage ?? arrayTelemetry?.batteryVoltage ?? 0,
                temperature: pack.temperature_c ?? pack.temperature ?? batteryData?.temperature ?? arrayTelemetry?.batteryTemperature ?? 0,
              },
              // Context fields for API calls
              batteryBankId: bankId,
              packIndex: idx,
              batteryArrayId: batteryArrayId,
            };
          });
        } else if (batteryData?.devices && batteryData.devices.length > 0) {
          batteries = batteryData.devices.map((dev: any, idx: number) => {
            // Use actual bank ID if available
            const bankId = actualBankIds[idx] || actualBankIds[0] || batteryData.id || primaryBankId;
            return {
              id: bankId, // Use actual bank ID from config
              name: `${batteryBankNameForSystem} #${idx + 1}`, // Use battery bank name (e.g., "Pylontech Battery Bank #1")
              model: batteryData.info?.model || (batteryData?.raw as any)?.model || "Unknown",
              serialNumber: batteryData.info?.serialNumber || `${bankId}-${idx + 1}`,
              status: "online" as const,
              metrics: {
                soc: dev.soc ?? batteryData.soc ?? 0,
                power: (dev.current || 0) * (dev.voltage || batteryData.voltage || 0) / 1000,
                voltage: dev.voltage ?? batteryData.voltage ?? 0,
                temperature: dev.temperature ?? batteryData.temperature ?? 0,
              },
              // Context fields for API calls
              batteryBankId: bankId,
              packIndex: idx,
              batteryArrayId: batteryArrayId,
            };
          });
        } else if (batteryData) {
          batteries = [{
            id: primaryBankId, // Use actual bank ID
            name: batteryBankNameForSystem || "Battery Bank",
            model: batteryData.info?.model || "Unknown",
            serialNumber: batteryData.info?.serialNumber || `${primaryBankId}-1`,
            status: "online" as const,
            metrics: {
              soc: batteryData.soc ?? arrayTelemetry?.batterySoc ?? 0,
              power: (batteryData.current || 0) * (batteryData.voltage || 0) / 1000,
              voltage: batteryData.voltage ?? arrayTelemetry?.batteryVoltage ?? 0,
              temperature: batteryData.temperature ?? arrayTelemetry?.batteryTemperature ?? 0,
            },
            // Context fields for API calls
            batteryBankId: primaryBankId,
            packIndex: 0,
            batteryArrayId: batteryArrayId,
          }];
        } else if (arrayTelemetry && (arrayTelemetry.batterySoc !== null || arrayTelemetry.batteryPower !== 0)) {
          batteries = [{
            id: primaryBankId, // Use actual bank ID
            name: batteryBankNameForSystem || "Battery Bank",
            model: "Unknown",
            serialNumber: `${primaryBankId}-1`,
            status: "online" as const,
            metrics: {
              soc: arrayTelemetry.batterySoc ?? 0,
              power: arrayTelemetry.batteryPower ?? 0,
              voltage: arrayTelemetry.batteryVoltage ?? 0,
              temperature: arrayTelemetry.batteryTemperature ?? 0,
            },
            // Context fields for API calls
            batteryBankId: primaryBankId,
            packIndex: 0,
            batteryArrayId: batteryArrayId,
          }];
        } else {
          // Create placeholder battery entry if no data available yet
          batteries = [{
            id: primaryBankId, // Use actual bank ID even for placeholder
            name: batteryBankNameForSystem || "Battery Bank",
            model: "Unknown",
            serialNumber: `${primaryBankId}-1`,
            status: "online" as const,
            metrics: {
              soc: 0,
              power: 0,
              voltage: 0,
              temperature: 0,
            },
            // Context fields for API calls
            batteryBankId: primaryBankId,
            packIndex: 0,
            batteryArrayId: batteryArrayId,
          }];
        }
        
        batteryArrayData = {
          id: batteryArrayId,
          name: batteryArrayConfig?.name || attachedBatteryArray?.name || `${invArray.name} Battery Array`,
          batteries,
        };
      }
      
      return {
        id: invArray.id,
        name: invArray.name, // System name = Inverter Array name (e.g., "Ground Floor", "First Floor")
        inverterArrays: [invArray], // Each System has one Inverter Array
        batteryArrays: batteryArrayData ? [batteryArrayData] : [], // Battery Array as sibling
      };
    });

    // Transform meters - create from telemetry if available, otherwise from config
    // deviceNames is already declared in the outer scope (line 107)
    const metersFromTelemetry = homeTelemetry?.meters || [];
    const metersFromConfig: string[] = deviceNames?.meters ? Array.from(deviceNames.meters.keys()) as string[] : [];
    
    // DEBUG: Log meter sources
    console.log('[DataProvider] Meter sources:', {
      hasHomeTelemetry: !!homeTelemetry,
      metersFromTelemetry: metersFromTelemetry.map(m => m.id),
      metersFromConfig,
      allMeterIds: [...new Set([...metersFromTelemetry.map(m => m.id), ...metersFromConfig])],
    });
    
    // Combine meters from telemetry and config (avoid duplicates)
    const allMeterIds = new Set<string>([...metersFromTelemetry.map(m => m.id), ...metersFromConfig]);
    const meters: Meter[] = Array.from(allMeterIds).map((meterId: string) => {
      // Try to find meter in telemetry first
      const telemetryMeter = metersFromTelemetry.find(m => m.id === meterId);
      const meterNameFromMap = deviceNames?.meters?.get(meterId);
      
      // DEBUG: Log meter name lookup
      console.log(`[DataProvider] Meter name lookup for ${meterId}:`, {
        meterId,
        meterNameFromMap,
        meterNameFromData: telemetryMeter?.name,
        hasTelemetryData: !!telemetryMeter,
        availableMeterIds: deviceNames?.meters ? Array.from(deviceNames.meters.keys()) : [],
      });
      
      const meterName = meterNameFromMap || 
                       telemetryMeter?.name || 
                       meterId;
      
      console.log(`[DataProvider] Final meter name for ${meterId}: ${meterName}`);
      
      return {
        id: meterId,
        name: meterName,
        model: "Energy Meter",
        serialNumber: meterId,
        status: "online" as const,
        metrics: {
          power: (telemetryMeter?.power || 0) * 1000, // Convert kW to W
          importKwh: telemetryMeter?.importKwh || 0,
          exportKwh: telemetryMeter?.exportKwh || 0,
          frequency: 50.0,
          powerFactor: 0.98,
        },
      };
    });
    
    // DEBUG: Log final meters array
    console.log('[DataProvider] Final meters array:', {
      count: meters.length,
      meters: meters.map(m => ({ id: m.id, name: m.name })),
    });

    return {
      id: apiHierarchy.id,
      name: apiHierarchy.name,
      systems,
      meters,
    };
  }, [apiHierarchy, allBatteryData, homeTelemetry, arrayTelemetryMap]);

  // Transform energy stats
  const energyStats = React.useMemo(() => {
    // If home telemetry is not available, try to aggregate from array telemetry
    let aggregatedTelemetry = homeTelemetry;
    
    if (!homeTelemetry && arrayTelemetryMap.size > 0) {
      // Aggregate data from all arrays
      let totalPvPower = 0;
      let totalBatteryPower = 0;
      let totalBatterySoc = 0;
      let totalLoadPower = 0;
      let totalGridPower = 0;
      let batteryCount = 0;
      
      arrayTelemetryMap.forEach((arrayTel) => {
        totalPvPower += arrayTel.pvPower || 0;
        totalBatteryPower += arrayTel.batteryPower || 0;
        totalLoadPower += arrayTel.loadPower || 0;
        totalGridPower += arrayTel.gridPower || 0;
        if (arrayTel.batterySoc !== null && arrayTel.batterySoc !== undefined) {
          totalBatterySoc += arrayTel.batterySoc;
          batteryCount++;
        }
      });
      
      const avgBatterySoc = batteryCount > 0 ? totalBatterySoc / batteryCount : 0;
      
      // Create aggregated telemetry object
      aggregatedTelemetry = {
        pvPower: totalPvPower,
        batteryPower: totalBatteryPower,
        batterySoc: avgBatterySoc,
        loadPower: totalLoadPower,
        gridPower: totalGridPower,
        batteryVoltage: null,
        batteryCurrent: null,
        batteryTemperature: null,
        inverterTemperature: null,
        isThreePhase: false,
        source: 'home' as const,
        ts: new Date().toISOString(),
        dailyEnergy: undefined,
        financialMetrics: undefined,
        meters: [],
      };
      
      console.log('[DataProvider] Using aggregated telemetry from arrays:', {
        pvPower: aggregatedTelemetry.pvPower,
        batteryPower: aggregatedTelemetry.batteryPower,
        loadPower: aggregatedTelemetry.loadPower,
        gridPower: aggregatedTelemetry.gridPower,
      });
    }
    
    if (!aggregatedTelemetry) {
      return {
        solarPower: 0,
        batteryPower: 0,
        batteryLevel: 0,
        consumption: 0,
        gridPower: 0,
        isGridExporting: false,
        dailyProduction: 0,
        dailyConsumption: 0,
        selfConsumption: 0,
        gridExported: 0,
        batteryChargeEnergy: 0,
        batteryDischargeEnergy: 0,
        loadEnergy: 0,
        gridImportEnergy: 0,
        gridExportEnergy: 0,
        co2Saved: 0,
        moneySaved: 0,
        monthlyBillAmount: 0,
        dailyPrediction: 0,
        avgKwPerKwp: 0,
        installedCapacity: 10,
      };
    }

    // Use daily energy from aggregatedTelemetry if available, otherwise fall back to dailyEnergy hook
    const dailyEnergyData = aggregatedTelemetry.dailyEnergy || dailyEnergy;
    
    // Use financial metrics from aggregatedTelemetry if available (monthly data)
    const financialMetrics = aggregatedTelemetry.financialMetrics;
    
    // DEBUG: Log data availability
    console.log('[DataProvider] Energy stats calculation:', {
      hasHomeTelemetry: !!homeTelemetry,
      hasAggregatedTelemetry: !!aggregatedTelemetry,
      hasDailyEnergy: !!dailyEnergyData,
      hasFinancialMetrics: !!financialMetrics,
      dailyEnergyData,
      financialMetrics,
      telemetryPvPower: aggregatedTelemetry.pvPower,
      telemetryBatteryPower: aggregatedTelemetry.batteryPower,
      telemetryBatterySoc: aggregatedTelemetry.batterySoc,
      telemetryLoadPower: aggregatedTelemetry.loadPower,
      telemetryGridPower: aggregatedTelemetry.gridPower,
    });
    
    // Calculate avg kWh/kWp (daily production / installed capacity)
    const installedCapacity = 10; // Should come from config
    const avgKwPerKwp = installedCapacity > 0 ? (dailyEnergyData?.solar || 0) / installedCapacity : 0;
    
    // Calculate self-consumption percentage: (solar - gridExport) / solar * 100
    // Or use selfSufficiency if available (which is already a percentage)
    const solarProduction = dailyEnergyData?.solar || 0;
    const gridExport = dailyEnergyData?.gridExport || 0;
    const selfConsumptionPct = solarProduction > 0 
      ? (dailyEnergyData?.selfSufficiency || Math.round(((solarProduction - gridExport) / solarProduction) * 100))
      : 0;

    return {
      solarPower: aggregatedTelemetry.pvPower || 0,
      batteryPower: aggregatedTelemetry.batteryPower || 0, // Keep sign: negative = discharging, positive = charging
      batteryLevel: Math.round(aggregatedTelemetry.batterySoc || 0),
      consumption: aggregatedTelemetry.loadPower || 0,
      gridPower: Math.abs(aggregatedTelemetry.gridPower || 0),
      isGridExporting: (aggregatedTelemetry.gridPower || 0) < 0,
      dailyProduction: solarProduction,
      dailyConsumption: dailyEnergyData?.load || 0,
      selfConsumption: selfConsumptionPct,
      gridExported: gridExport,
      batteryChargeEnergy: dailyEnergyData?.batteryCharge || 0,
      batteryDischargeEnergy: dailyEnergyData?.batteryDischarge || 0,
      loadEnergy: dailyEnergyData?.load || 0,
      gridImportEnergy: dailyEnergyData?.gridImport || 0,
      gridExportEnergy: gridExport,
      co2Saved: financialMetrics?.co2PreventedKg || 0,
      moneySaved: financialMetrics?.totalSavedPkr || 0,
      monthlyBillAmount: financialMetrics?.totalBillPkr || 0,
      dailyPrediction: 0, // TODO: Get from forecast API
      avgKwPerKwp: avgKwPerKwp,
      installedCapacity: installedCapacity,
    };
  }, [homeTelemetry, dailyEnergy, arrayTelemetryMap]);

  // Transform chart data
  const chartData = React.useMemo(() => {
    if (!hourlyData || hourlyData.length === 0) {
      return Array.from({ length: 24 }, (_, i) => ({
        time: `${i.toString().padStart(2, "0")}:00`,
        solar: 0,
        consumption: 0,
        battery: 0,
        grid: 0,
      }));
    }

    return hourlyData.map(item => ({
      time: item.time,
      solar: item.solar,
      consumption: item.load,
      battery: item.battery,
      grid: item.grid,
    }));
  }, [hourlyData]);

  // Transform devices list
  const devices = React.useMemo(() => {
    if (!homeHierarchy) return [];
    
    return [
      ...homeHierarchy.systems.flatMap((system) =>
        system.inverterArrays.flatMap((array) =>
          array.inverters.map((inv) => ({
            id: inv.id,
            name: inv.name,
            type: "inverter" as const,
            status: inv.status,
            model: inv.model,
            serialNumber: inv.serialNumber,
            value: inv.metrics.solarPower.toFixed(1),
            unit: "kW",
            metrics: [
              { label: "Solar", value: inv.metrics.solarPower.toFixed(1), unit: "kW" },
              { label: "Grid", value: inv.metrics.gridPower.toFixed(1), unit: "kW" },
              { label: "Load", value: inv.metrics.loadPower.toFixed(1), unit: "kW" },
              { label: "Battery", value: inv.metrics.batteryPower.toFixed(1), unit: "kW" },
            ],
          }))
        )
      ),
      ...homeHierarchy.systems.flatMap((system) =>
        system.batteryArrays.flatMap((batteryArray) =>
          batteryArray.batteries.map((bat) => ({
            id: bat.id,
            name: bat.name,
            type: "battery" as const,
            status: bat.status,
            model: bat.model,
            serialNumber: bat.serialNumber,
            value: bat.metrics.soc.toString(),
            unit: "%",
            metrics: [
              { label: "SOC", value: bat.metrics.soc.toString(), unit: "%" },
              { label: bat.metrics.power >= 0 ? "Charging" : "Discharging", value: Math.abs(bat.metrics.power).toFixed(1), unit: "kW" },
              { label: "Voltage", value: bat.metrics.voltage > 0 ? bat.metrics.voltage.toFixed(1) : "N/A", unit: "V" },
              { label: "Temp", value: bat.metrics.temperature > 0 ? bat.metrics.temperature.toString() : "N/A", unit: "°C" },
            ],
          }))
        )
      ),
      ...homeHierarchy.meters.map((meter) => {
        const netExport = meter.metrics.exportKwh - meter.metrics.importKwh;
        const isExporting = meter.metrics.power < 0;
        return {
          id: meter.id,
          name: meter.name,
          type: "meter" as const,
          status: meter.status,
          model: meter.model,
          serialNumber: meter.serialNumber,
          value: Math.abs(meter.metrics.power / 1000).toFixed(1),
          unit: "kW",
          metrics: [
            { label: "Power", value: Math.abs(meter.metrics.power / 1000).toFixed(1), unit: "kW" },
            { label: "Import", value: meter.metrics.importKwh.toFixed(1), unit: "kWh" },
            { label: "Export", value: meter.metrics.exportKwh.toFixed(1), unit: "kWh" },
            { label: netExport >= 0 ? "Net Export" : "Net Import", value: Math.abs(netExport).toFixed(1), unit: "kWh" },
          ],
        };
      }),
    ];
  }, [homeHierarchy]);

  const value: DataContextValue = {
    homeHierarchy,
    energyStats,
    chartData,
    devices,
  };

  return <DataContext.Provider value={value}>{children}</DataContext.Provider>;
}

export function useDataContext() {
  const context = useContext(DataContext);
  if (!context) {
    throw new Error('useDataContext must be used within DataProvider');
  }
  return context;
}

