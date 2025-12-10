/**
 * API Adapter Layer
 * 
 * This layer transforms API responses to match the exact structure expected by the frontend.
 * The frontend components remain unchanged - they still import from mockData.ts,
 * but mockData.ts now uses this adapter to fetch real data from the API.
 */

import { useHomeHierarchy, useHomeTelemetry, useArrayTelemetry, useBatteryTelemetry, useDailyEnergy, useHourlyEnergy } from "../../../../api/hooks";
import type {
  BatteryBank,
  BatteryArray,
  Inverter,
  InverterArray,
  Meter,
  HomeHierarchy,
} from "./mockData";

/**
 * Transform API hierarchy to match mockData structure
 */
export function useApiHomeHierarchy(): HomeHierarchy | null {
  const { data: hierarchy } = useHomeHierarchy();
  const { data: homeTelemetry } = useHomeTelemetry();
  const { data: allBatteryData } = useBatteryTelemetry();

  if (!hierarchy) return null;

  // Build battery data map
  const batteryDataMap = new Map<string, any>();
  if (allBatteryData) {
    const batteries = Array.isArray(allBatteryData) ? allBatteryData : [allBatteryData];
    batteries.forEach(bat => {
      batteryDataMap.set(bat.id, bat);
    });
  }

  // Transform to match mockData structure
  const inverterArrays: InverterArray[] = hierarchy.inverterArrays.map(array => {
    // For each inverter ID, we'd need to fetch individual inverter telemetry
    // For now, we'll create placeholder inverters based on IDs
    const inverters: Inverter[] = array.inverterIds.map((invId, idx) => ({
      id: invId,
      name: `Inverter ${idx + 1}`,
      model: "Unknown",
      serialNumber: invId,
      status: "online" as const,
      metrics: {
        solarPower: 0,
        gridPower: 0,
        loadPower: 0,
        batteryPower: 0,
        efficiency: 0,
        dcVoltage: 0,
        temperature: 0,
      },
    }));

    // Get battery array if attached
    let batteryArray: BatteryArray | undefined;
    if (array.batteryArrayId) {
      const batteryArrayConfig = hierarchy.batteryArrays.find(ba => ba.id === array.batteryArrayId);
      const batteryData = batteryDataMap.get(array.batteryArrayId);
      
      if (batteryArrayConfig && batteryData) {
        // Transform battery data
        const batteries: BatteryBank[] = batteryData.devices?.map((dev: any, idx: number) => ({
          id: `${array.batteryArrayId}-${idx + 1}`,
          name: `Battery ${idx + 1}`,
          model: batteryData.info?.model || "Unknown",
          serialNumber: batteryData.info?.serialNumber || `${array.batteryArrayId}-${idx + 1}`,
          status: "online" as const,
          metrics: {
            soc: dev.soc || batteryData.soc || 0,
            power: (dev.current || 0) * (dev.voltage || batteryData.voltage || 0) / 1000, // Convert to kW
            voltage: dev.voltage || batteryData.voltage || 0,
            temperature: dev.temperature || batteryData.temperature || 0,
          },
        })) || [];

        batteryArray = {
          id: array.batteryArrayId,
          name: batteryArrayConfig.name,
          batteries,
        };
      }
    }

    return {
      id: array.id,
      name: array.name,
      inverters,
      batteryArray,
    };
  });

  // Transform meters from home telemetry
  const meters: Meter[] = (homeTelemetry?.meters || []).map(meter => ({
    id: meter.id,
    name: meter.name || meter.id,
    model: "Energy Meter",
    serialNumber: meter.id,
    status: "online" as const,
    metrics: {
      power: meter.power * 1000, // Convert kW to W for consistency (will be converted back in display)
      importKwh: meter.importKwh,
      exportKwh: meter.exportKwh,
      frequency: 50.0,
      powerFactor: 0.98,
    },
  }));

  return {
    id: hierarchy.id,
    name: hierarchy.name,
    inverterArrays,
    meters,
  };
}

/**
 * Transform API data to match energyStats structure
 */
export function useApiEnergyStats() {
  const { data: homeTelemetry } = useHomeTelemetry();
  const { data: dailyEnergy } = useDailyEnergy();
  const { data: hourlyData } = useHourlyEnergy();

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
    co2Saved: 0, // Would need calculation
    moneySaved: 0, // Would need calculation
    monthlyBillAmount: 0, // Would need calculation
    dailyPrediction: 0, // Would need forecast
    avgKwPerKwp: 0, // Would need installed capacity
    installedCapacity: 10,
  };
}

/**
 * Transform API hourly data to match chartData structure
 */
export function useApiChartData() {
  const { data: hourlyData } = useHourlyEnergy();

  if (!hourlyData || hourlyData.length === 0) {
    // Return empty data with 24 hours
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
}

