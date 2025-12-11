/**
 * V0 App Data Provider
 * 
 * Provides data from hierarchy objects to v0 app components
 * Transforms hierarchy objects to match the expected structure for each component
 * Only mapping layer - no frontend design changes
 */

import React, { createContext, useContext, ReactNode, useMemo, useEffect } from 'react';
import { useHomeTelemetry } from '../../../api/hooks';
import { useAllSystems, useAllInverters, useAllBatteryPacks, useAllMeters, useHierarchyManager } from '../../../api/hooks/useHierarchyObjects';
import { getDataSyncService } from '../../../api/services/DataSyncService';

// Types matching v0 app component expectations
export interface V0Stats {
  label: string;
  value: string;
  unit: string;
  change: string;
  trend: 'up' | 'down';
  icon: any;
  color: string;
  bgColor: string;
}

export interface V0Device {
  id: number | string;
  name: string;
  type: 'inverter' | 'battery' | 'meter';
  model: string;
  status: 'online' | 'offline' | 'warning';
  output?: string;
  efficiency?: string;
  temperature?: string;
  charge?: string;
  power?: string;
  cycles?: string;
  consumption?: string;
  export?: string;
  voltage?: string;
}

export interface V0BatteryCell {
  id: string;
  voltage: number;
  current: number;
  soc: number;
  temperature: number;
  status: 'normal' | 'warning' | 'critical' | 'balancing';
}

export interface V0IndividualBattery {
  id: string;
  name: string;
  model: string;
  status: 'charging' | 'discharging' | 'idle' | 'balancing';
  soc: number;
  voltage: number;
  current: number;
  temperature: number;
  health: number;
  cells: V0BatteryCell[];
}

export interface V0BatteryPack {
  id: string;
  name: string;
  location: string;
  status: 'online' | 'offline' | 'warning';
  totalCapacity: number;
  batteries: V0IndividualBattery[];
}

export interface V0Inverter {
  id: string;
  name: string;
  model: string;
  status: 'online' | 'offline' | 'warning';
  power: number;
  maxPower: number;
  efficiency: number;
  temperature: number;
  voltage: number;
  current: number;
  frequency: number;
  energyToday: number;
  energyTotal: number;
  lastUpdate: string;
  alert?: string;
}

interface V0DataContextValue {
  stats: V0Stats[];
  devices: V0Device[];
  batteryPacks: V0BatteryPack[];
  inverters: V0Inverter[];
  meters: Array<{
    id: string;
    name: string;
    type: string;
    status: string;
    currentPower: number;
    voltage: number;
    current: number;
    frequency: number;
    powerFactor: number;
    importToday: number;
    exportToday: number;
    importTotal: number;
    exportTotal: number;
    lastUpdate: string;
  }>;
}

const V0DataContext = createContext<V0DataContextValue | null>(null);

export function V0DataProvider({ children }: { children: ReactNode }) {
  // Load hierarchy manager
  const { manager, isLoading: hierarchyLoading } = useHierarchyManager();
  const systems = useAllSystems();
  const inverters = useAllInverters();
  const batteryPacks = useAllBatteryPacks();
  const meters = useAllMeters();
  const { data: homeTelemetry } = useHomeTelemetry();

  // Initialize data sync service on mount
  useEffect(() => {
    if (manager && manager.isLoaded()) {
      const syncService = getDataSyncService({
        pollingInterval: 5000,
        enabled: true,
        updateHierarchy: false,
      });
      syncService.startPolling();
      
      return () => {
        syncService.stopPolling();
      };
    }
  }, [manager]);

  // Transform stats from home telemetry
  const stats: V0Stats[] = useMemo(() => {
    if (!homeTelemetry) {
      // Return default stats if no telemetry
      return [
        {
          label: 'Solar Production',
          value: '0',
          unit: 'kW',
          change: '0%',
          trend: 'up',
          icon: null,
          color: 'text-yellow-400',
          bgColor: 'bg-yellow-400/10',
        },
        {
          label: 'Battery Storage',
          value: '0',
          unit: '%',
          change: 'N/A',
          trend: 'up',
          icon: null,
          color: 'text-blue-400',
          bgColor: 'bg-blue-400/10',
        },
        {
          label: 'Home Consumption',
          value: '0',
          unit: 'kW',
          change: '0%',
          trend: 'down',
          icon: null,
          color: 'text-pink-400',
          bgColor: 'bg-pink-400/10',
        },
        {
          label: 'Grid Export',
          value: '0',
          unit: 'kW',
          change: '0%',
          trend: 'up',
          icon: null,
          color: 'text-emerald-400',
          bgColor: 'bg-emerald-400/10',
        },
      ];
    }

    const solarPower = homeTelemetry.pvPower || 0;
    const batterySOC = homeTelemetry.batterySoc || 0;
    const loadPower = homeTelemetry.loadPower || 0;
    const gridPower = Math.abs(homeTelemetry.gridPower || 0);
    const isGridExporting = (homeTelemetry.gridPower || 0) < 0;

    return [
      {
        label: 'Solar Production',
        value: solarPower.toFixed(1),
        unit: 'kW',
        change: '+12%', // TODO: Calculate from historical data
        trend: 'up',
        icon: null,
        color: 'text-yellow-400',
        bgColor: 'bg-yellow-400/10',
      },
      {
        label: 'Battery Storage',
        value: Math.round(batterySOC).toString(),
        unit: '%',
        change: homeTelemetry.batteryPower && homeTelemetry.batteryPower > 0 ? 'Charging' : 'Discharging',
        trend: homeTelemetry.batteryPower && homeTelemetry.batteryPower > 0 ? 'up' : 'down',
        icon: null,
        color: 'text-blue-400',
        bgColor: 'bg-blue-400/10',
      },
      {
        label: 'Home Consumption',
        value: loadPower.toFixed(1),
        unit: 'kW',
        change: '-8%', // TODO: Calculate from historical data
        trend: 'down',
        icon: null,
        color: 'text-pink-400',
        bgColor: 'bg-pink-400/10',
      },
      {
        label: isGridExporting ? 'Grid Export' : 'Grid Import',
        value: gridPower.toFixed(1),
        unit: 'kW',
        change: '+24%', // TODO: Calculate from historical data
        trend: 'up',
        icon: null,
        color: 'text-emerald-400',
        bgColor: 'bg-emerald-400/10',
      },
    ];
  }, [homeTelemetry]);

  // Transform devices list
  const devices: V0Device[] = useMemo(() => {
    const deviceList: V0Device[] = [];

    // Add inverter arrays as devices
    systems.forEach(system => {
      system.inverterArrays.forEach((array, idx) => {
        const totalPower = array.getTotalPower() || 0;
        const avgEfficiency = array.getAverageEfficiency() || 0;
        const temp = array.inverters.length > 0 
          ? (array.inverters[0]?.getTemperature() || 0)
          : 0;

        deviceList.push({
          id: `array-${array.id}`,
          name: array.name || `Inverter Array ${idx + 1}`,
          type: 'inverter',
          model: 'Solar Array',
          status: array.hasRecentTelemetry(10) ? 'online' : 'offline',
          output: `${totalPower.toFixed(1)} kW`,
          efficiency: `${avgEfficiency.toFixed(1)}%`,
          temperature: `${Math.round(temp)}°C`,
        });
      });
    });

    // Add battery packs as devices
    batteryPacks.forEach((pack, idx) => {
      const soc = pack.getSOC() || 0;
      const power = pack.getPower();
      const isCharging = power > 0;

      deviceList.push({
        id: `pack-${pack.id}`,
        name: pack.name || `Battery Pack ${idx + 1}`,
        type: 'battery',
        model: pack.chemistry || 'Battery Pack',
        status: pack.getStatus(),
        charge: `${Math.round(soc)}%`,
        power: `${isCharging ? '+' : ''}${Math.abs(power).toFixed(1)} kW`,
        cycles: '0', // TODO: Get from telemetry if available
      });
    });

    // Add meters as devices
    meters.forEach((meter, idx) => {
      const power = meter.getPower();
      deviceList.push({
        id: `meter-${meter.id}`,
        name: meter.name || `Energy Meter ${idx + 1}`,
        type: 'meter',
        model: meter.model || 'Energy Meter',
        status: meter.getStatus(),
        consumption: `${Math.abs(power).toFixed(1)} kW`,
        export: '0 kW', // TODO: Get from telemetry
        voltage: '240V', // TODO: Get from telemetry
      });
    });

    return deviceList;
  }, [systems, batteryPacks, meters]);

  // Transform battery packs for BatteriesPage
  const batteryPacksData: V0BatteryPack[] = useMemo(() => {
    if (!manager || !manager.isLoaded()) {
      return [];
    }

    const packs: V0BatteryPack[] = [];

    systems.forEach(system => {
      system.batteryArrays.forEach((batteryArray, arrayIdx) => {
        batteryArray.batteryPacks.forEach((pack, packIdx) => {
          const batteryTelemetry = pack.getBatteryTelemetry();
          const devices = batteryTelemetry?.devices || [];
          const cells = batteryTelemetry?.cells || [];

          // Transform individual batteries from battery telemetry
          const individualBatteries: V0IndividualBattery[] = devices.map((device, deviceIdx) => {
            // Map cells for this battery
            const batteryCells: V0BatteryCell[] = cells
              .filter(cell => cell.batteryIndex === deviceIdx)
              .map((cell, cellIdx) => ({
                id: `C${cellIdx + 1}`,
                voltage: cell.voltage || 3.2,
                current: 0, // Not available in cell data
                soc: cell.soc || 0,
                temperature: cell.temperature || 0,
                status: 'normal' as const, // Determine from voltage/temp if needed
              }));

            // Determine status from power
            let status: 'charging' | 'discharging' | 'idle' | 'balancing' = 'idle';
            const packPower = pack.getPower();
            if (packPower > 0) {
              status = 'charging';
            } else if (packPower < 0) {
              status = 'discharging';
            }

            return {
              id: `BAT-${pack.id}-${deviceIdx + 1}`,
              name: `Battery Unit ${deviceIdx + 1}`,
              model: pack.chemistry || 'LFP Battery',
              status,
              soc: device.soc || pack.getSOC() || 0,
              voltage: device.voltage || pack.getVoltage() || 0,
              current: device.current || pack.getCurrent() || 0,
              temperature: device.temperature || pack.getTemperature() || 0,
              health: device.soh || 100, // State of Health, default to 100
              cells: batteryCells.length > 0 ? batteryCells : Array.from({ length: 16 }, (_, i) => ({
                id: `C${i + 1}`,
                voltage: 3.2,
                current: 0,
                soc: device.soc || 0,
                temperature: device.temperature || 0,
                status: 'normal' as const,
              })),
            };
          });

          // If no devices in telemetry, create a default battery
          if (individualBatteries.length === 0) {
            const soc = pack.getSOC() || 0;
            const power = pack.getPower();
            individualBatteries.push({
              id: `BAT-${pack.id}-1`,
              name: 'Battery Unit 1',
              model: pack.chemistry || 'LFP Battery',
              status: power > 0 ? 'charging' : power < 0 ? 'discharging' : 'idle',
              soc,
              voltage: pack.getVoltage() || 0,
              current: pack.getCurrent() || 0,
              temperature: pack.getTemperature() || 0,
              health: 100,
              cells: Array.from({ length: 16 }, (_, i) => ({
                id: `C${i + 1}`,
                voltage: 3.2,
                current: 0,
                soc,
                temperature: pack.getTemperature() || 0,
                status: 'normal' as const,
              })),
            });
          }

          packs.push({
            id: `PACK-${pack.id}`,
            name: pack.name || `Battery Pack ${packIdx + 1}`,
            location: `${batteryArray.name} - Pack ${packIdx + 1}`, // Default location
            status: pack.getStatus(),
            totalCapacity: pack.nominalKwh,
            batteries: individualBatteries,
          });
        });
      });
    });

    return packs;
  }, [manager, systems]);

  // Transform inverters for InvertersPage
  const invertersData: V0Inverter[] = useMemo(() => {
    return inverters.map((inverter, idx) => {
      const telemetry = inverter.getTelemetry();
      const power = inverter.getPower() || 0;
      const temperature = inverter.getTemperature() || 0;
      const efficiency = inverter.getEfficiency() || 0;
      
      // Estimate max power (could be from config or telemetry)
      const maxPower = 10; // Default, should come from config

      return {
        id: inverter.id,
        name: inverter.name,
        model: inverter.model || 'Solar Inverter',
        status: inverter.getStatus(),
        power,
        maxPower,
        efficiency,
        temperature,
        voltage: telemetry?.gridVoltage || 240, // Default, should come from telemetry
        current: power > 0 ? (power * 1000) / 240 : 0, // Estimated
        frequency: telemetry?.gridFrequency || 50.0, // Default
        energyToday: 0, // TODO: Get from daily energy
        energyTotal: 0, // TODO: Get from historical data
        lastUpdate: 'just now',
        alert: temperature > 50 ? 'High temperature warning' : undefined,
      };
    });
  }, [inverters]);

  // Transform meters for MetersPage
  const metersData = useMemo(() => {
    return meters.map((meter, idx) => {
      const telemetry = meter.getTelemetry();
      const power = meter.getPower() || 0;
      const isExporting = power < 0;

      return {
        id: meter.id,
        name: meter.name,
        type: meter.meterType || 'Bidirectional',
        status: meter.getStatus(),
        currentPower: Math.abs(power),
        voltage: telemetry?.gridVoltage || 240, // Default
        current: Math.abs(power) > 0 ? (Math.abs(power) * 1000) / 240 : 0,
        frequency: telemetry?.gridFrequency || 50.0, // Default
        powerFactor: 0.98, // Default
        importToday: isExporting ? 0 : meter.getImportEnergy() || 0,
        exportToday: isExporting ? meter.getExportEnergy() || 0 : 0,
        importTotal: 0, // TODO: Get from historical data
        exportTotal: 0, // TODO: Get from historical data
        lastUpdate: 'just now',
      };
    });
  }, [meters]);

  const value: V0DataContextValue = {
    stats,
    devices,
    batteryPacks: batteryPacksData,
    inverters: invertersData,
    meters: metersData,
  };

  return <V0DataContext.Provider value={value}>{children}</V0DataContext.Provider>;
}

export function useV0Data() {
  const context = useContext(V0DataContext);
  if (!context) {
    throw new Error('useV0Data must be used within V0DataProvider');
  }
  return context;
}

