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
  const { data: homeTelemetry } = useHomeTelemetry();
  const { data: allBatteryData } = useBatteryTelemetry();
  const { data: dailyEnergy } = useDailyEnergy();
  const { data: hourlyData } = useHourlyEnergy();

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
    if (!apiHierarchy) return null;

    // Build battery data map
    const batteryDataMap = new Map<string, any>();
    if (allBatteryData) {
      const batteries = Array.isArray(allBatteryData) ? allBatteryData : [allBatteryData];
      batteries.forEach(bat => {
        batteryDataMap.set(bat.id, bat);
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
        
        return {
          id: invId,
          name: `Inverter ${idx + 1}`,
          model: "Unknown",
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
        
        if (packs.length > 0) {
          // Use pack data from array telemetry (preferred - most accurate)
          batteries = packs.map((pack: any, idx: number) => ({
            id: pack.pack_id || `${array.batteryArrayId}-pack-${idx + 1}`,
            name: `Battery ${idx + 1}`,
            model: batteryData?.info?.model || "Unknown",
            serialNumber: batteryData?.info?.serialNumber || `${array.batteryArrayId}-${idx + 1}`,
            status: "online" as const,
            metrics: {
              soc: pack.soc_pct ?? batteryData?.soc ?? arrayTelemetry?.batterySoc ?? 0,
              power: (pack.power_w || 0) / 1000, // Convert W to kW (positive = charging, negative = discharging)
              voltage: pack.voltage_v ?? batteryData?.voltage ?? arrayTelemetry?.batteryVoltage ?? 0,
              temperature: pack.temperature ?? batteryData?.temperature ?? arrayTelemetry?.batteryTemperature ?? 0,
            },
          }));
        } else if (batteryData?.devices && batteryData.devices.length > 0) {
          // Use device data from battery telemetry
          batteries = batteryData.devices.map((dev: any, idx: number) => ({
            id: `${array.batteryArrayId}-${idx + 1}`,
            name: `Battery ${idx + 1}`,
            model: batteryData.info?.model || "Unknown",
            serialNumber: batteryData.info?.serialNumber || `${array.batteryArrayId}-${idx + 1}`,
            status: "online" as const,
            metrics: {
              soc: dev.soc ?? batteryData.soc ?? 0,
              power: (dev.current || 0) * (dev.voltage || batteryData.voltage || 0) / 1000, // Convert to kW
              voltage: dev.voltage ?? batteryData.voltage ?? 0,
              temperature: dev.temperature ?? batteryData.temperature ?? 0,
            },
          }));
        } else if (batteryData) {
          // Create a single battery entry from aggregate battery data
          batteries = [{
            id: `${array.batteryArrayId}-1`,
            name: "Battery Bank",
            model: batteryData.info?.model || "Unknown",
            serialNumber: batteryData.info?.serialNumber || `${array.batteryArrayId}-1`,
            status: "online" as const,
            metrics: {
              soc: batteryData.soc ?? arrayTelemetry?.batterySoc ?? 0,
              power: (batteryData.current || 0) * (batteryData.voltage || 0) / 1000, // Convert to kW
              voltage: batteryData.voltage ?? arrayTelemetry?.batteryVoltage ?? 0,
              temperature: batteryData.temperature ?? arrayTelemetry?.batteryTemperature ?? 0,
            },
          }];
        } else if (arrayTelemetry && (arrayTelemetry.batterySoc !== null || arrayTelemetry.batteryPower !== 0)) {
          // Use battery data from array telemetry if available
          batteries = [{
            id: `${array.batteryArrayId}-1`,
            name: "Battery Bank",
            model: "Unknown",
            serialNumber: `${array.batteryArrayId}-1`,
            status: "online" as const,
            metrics: {
              soc: arrayTelemetry.batterySoc ?? 0,
              power: arrayTelemetry.batteryPower ?? 0, // Already in kW
              voltage: arrayTelemetry.batteryVoltage ?? 0,
              temperature: arrayTelemetry.batteryTemperature ?? 0,
            },
          }];
        } else {
          // Create placeholder battery entry if no data available yet
          batteries = [{
            id: `${array.batteryArrayId}-1`,
            name: "Battery Bank",
            model: "Unknown",
            serialNumber: `${array.batteryArrayId}-1`,
            status: "online" as const,
            metrics: {
              soc: 0,
              power: 0,
              voltage: 0,
              temperature: 0,
            },
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
        // Remove batteryArray from InverterArray - they'll be siblings under System
      };
    });

    // Group Inverter Arrays and Battery Arrays into Systems
    // Each Inverter Array becomes a System, with its attached Battery Array as a sibling
    const systems: System[] = inverterArrays.map(invArray => {
      // Find the battery array attached to this inverter array
      const attachedBatteryArray = apiHierarchy.batteryArrays.find(
        ba => ba.attachedInverterArrayId === invArray.id
      );
      
      // Get the battery array data if it exists
      let batteryArrayData: BatteryArray | undefined;
      if (attachedBatteryArray) {
        const batteryArrayConfig = apiHierarchy.batteryArrays.find(ba => ba.id === attachedBatteryArray.id);
        const arrayTelemetry = arrayTelemetryMap.get(invArray.id);
        const rawData = arrayTelemetry?.raw as any;
        const packs = rawData?.packs || [];
        
        // Try to find battery data
        let batteryData: any = batteryDataMap.get(attachedBatteryArray.id);
        if (!batteryData && batteryArrayConfig) {
          for (const bankId of batteryArrayConfig.batteryBankIds) {
            const found = batteryDataMap.get(bankId);
            if (found) {
              batteryData = found;
              break;
            }
          }
        }
        
        // Create batteries array
        let batteries: BatteryBank[] = [];
        
        if (packs.length > 0) {
          batteries = packs.map((pack: any, idx: number) => ({
            id: pack.pack_id || `${attachedBatteryArray.id}-pack-${idx + 1}`,
            name: `Battery ${idx + 1}`,
            model: batteryData?.info?.model || "Unknown",
            serialNumber: batteryData?.info?.serialNumber || `${attachedBatteryArray.id}-${idx + 1}`,
            status: "online" as const,
            metrics: {
              soc: pack.soc_pct ?? batteryData?.soc ?? arrayTelemetry?.batterySoc ?? 0,
              power: (pack.power_w || 0) / 1000,
              voltage: pack.voltage_v ?? batteryData?.voltage ?? arrayTelemetry?.batteryVoltage ?? 0,
              temperature: pack.temperature ?? batteryData?.temperature ?? arrayTelemetry?.batteryTemperature ?? 0,
            },
          }));
        } else if (batteryData?.devices && batteryData.devices.length > 0) {
          batteries = batteryData.devices.map((dev: any, idx: number) => ({
            id: `${attachedBatteryArray.id}-${idx + 1}`,
            name: `Battery ${idx + 1}`,
            model: batteryData.info?.model || "Unknown",
            serialNumber: batteryData.info?.serialNumber || `${attachedBatteryArray.id}-${idx + 1}`,
            status: "online" as const,
            metrics: {
              soc: dev.soc ?? batteryData.soc ?? 0,
              power: (dev.current || 0) * (dev.voltage || batteryData.voltage || 0) / 1000,
              voltage: dev.voltage ?? batteryData.voltage ?? 0,
              temperature: dev.temperature ?? batteryData.temperature ?? 0,
            },
          }));
        } else if (batteryData) {
          batteries = [{
            id: `${attachedBatteryArray.id}-1`,
            name: "Battery Bank",
            model: batteryData.info?.model || "Unknown",
            serialNumber: batteryData.info?.serialNumber || `${attachedBatteryArray.id}-1`,
            status: "online" as const,
            metrics: {
              soc: batteryData.soc ?? arrayTelemetry?.batterySoc ?? 0,
              power: (batteryData.current || 0) * (batteryData.voltage || 0) / 1000,
              voltage: batteryData.voltage ?? arrayTelemetry?.batteryVoltage ?? 0,
              temperature: batteryData.temperature ?? arrayTelemetry?.batteryTemperature ?? 0,
            },
          }];
        } else if (arrayTelemetry && (arrayTelemetry.batterySoc !== null || arrayTelemetry.batteryPower !== 0)) {
          batteries = [{
            id: `${attachedBatteryArray.id}-1`,
            name: "Battery Bank",
            model: "Unknown",
            serialNumber: `${attachedBatteryArray.id}-1`,
            status: "online" as const,
            metrics: {
              soc: arrayTelemetry.batterySoc ?? 0,
              power: arrayTelemetry.batteryPower ?? 0,
              voltage: arrayTelemetry.batteryVoltage ?? 0,
              temperature: arrayTelemetry.batteryTemperature ?? 0,
            },
          }];
        } else {
          batteries = [{
            id: `${attachedBatteryArray.id}-1`,
            name: "Battery Bank",
            model: "Unknown",
            serialNumber: `${attachedBatteryArray.id}-1`,
            status: "online" as const,
            metrics: {
              soc: 0,
              power: 0,
              voltage: 0,
              temperature: 0,
            },
          }];
        }
        
        batteryArrayData = {
          id: attachedBatteryArray.id,
          name: batteryArrayConfig?.name || "Battery Array",
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

    // Transform meters
    const meters: Meter[] = (homeTelemetry?.meters || []).map(meter => ({
      id: meter.id,
      name: meter.name || meter.id,
      model: "Energy Meter",
      serialNumber: meter.id,
      status: "online" as const,
      metrics: {
        power: meter.power * 1000,
        importKwh: meter.importKwh,
        exportKwh: meter.exportKwh,
        frequency: 50.0,
        powerFactor: 0.98,
      },
    }));

    return {
      id: apiHierarchy.id,
      name: apiHierarchy.name,
      systems,
      meters,
    };
  }, [apiHierarchy, allBatteryData, homeTelemetry, arrayTelemetryMap]);

  // Transform energy stats
  const energyStats = React.useMemo(() => {
    if (!homeTelemetry) {
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
        co2Saved: 0,
        moneySaved: 0,
        monthlyBillAmount: 0,
        dailyPrediction: 0,
        avgKwPerKwp: 0,
        installedCapacity: 10,
      };
    }

    return {
      solarPower: homeTelemetry.pvPower,
      batteryPower: Math.abs(homeTelemetry.batteryPower),
      batteryLevel: Math.round(homeTelemetry.batterySoc || 0),
      consumption: homeTelemetry.loadPower,
      gridPower: Math.abs(homeTelemetry.gridPower),
      isGridExporting: homeTelemetry.gridPower < 0,
      dailyProduction: dailyEnergy?.solar || 0,
      dailyConsumption: dailyEnergy?.load || 0,
      selfConsumption: dailyEnergy?.selfSufficiency || 0,
      gridExported: dailyEnergy?.gridExport || 0,
      co2Saved: 0,
      moneySaved: 0,
      monthlyBillAmount: 0,
      dailyPrediction: 0,
      avgKwPerKwp: 0,
      installedCapacity: 10,
    };
  }, [homeTelemetry, dailyEnergy]);

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
              { label: "Power Output", value: inv.metrics.solarPower.toFixed(1), unit: "kW" },
              { label: "Efficiency", value: inv.metrics.efficiency.toFixed(1), unit: "%" },
              { label: "DC Voltage", value: inv.metrics.dcVoltage.toString(), unit: "V" },
              { label: "Temperature", value: inv.metrics.temperature.toString(), unit: "°C" },
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
              { label: "State of Charge", value: bat.metrics.soc.toString(), unit: "%" },
              { label: bat.metrics.power >= 0 ? "Charge Rate" : "Discharge Rate", value: Math.abs(bat.metrics.power).toFixed(1), unit: "kW" },
              { label: "Voltage", value: bat.metrics.voltage.toFixed(1), unit: "V" },
              { label: "Temperature", value: bat.metrics.temperature.toString(), unit: "°C" },
            ],
          }))
        )
      ),
      ...homeHierarchy.meters.map((meter) => ({
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
          { label: meter.metrics.power >= 0 ? "Importing" : "Exporting", value: Math.abs(meter.metrics.power / 1000).toFixed(1), unit: "kW" },
          { label: "Frequency", value: meter.metrics.frequency.toFixed(2), unit: "Hz" },
          { label: "Power Factor", value: meter.metrics.powerFactor.toFixed(2), unit: "" },
        ],
      })),
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

