/**
 * Data Provider Component
 * 
 * This component uses the new hierarchy objects to provide data through context
 * in the exact same structure as mockData. Components can use the data
 * through hooks exported from mockData.ts without any changes.
 */

import React, { createContext, useContext, ReactNode, useMemo, useEffect } from 'react';
import { useHomeTelemetry, useBatteryTelemetry, useDailyEnergy, useHourlyEnergy } from '../../../../api/hooks';
import { useAllSystems, useHierarchyManager } from '../../../../api/hooks/useHierarchyObjects';
import { getDataSyncService } from '../../../../api/services/DataSyncService';
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
  // Load hierarchy manager
  const { manager, isLoading: hierarchyLoading } = useHierarchyManager();
  const systems = useAllSystems();
  
  // Fetch telemetry data
  const { data: homeTelemetry } = useHomeTelemetry();
  const { data: allBatteryData } = useBatteryTelemetry();
  const { data: dailyEnergy } = useDailyEnergy();
  const { data: hourlyData } = useHourlyEnergy();

  // Initialize data sync service on mount
  useEffect(() => {
    if (manager && manager.isLoaded()) {
      const syncService = getDataSyncService({
        pollingInterval: 5000,
        enabled: true,
        updateHierarchy: false, // Hierarchy is loaded separately
      });
      syncService.startPolling();
      
      return () => {
        syncService.stopPolling();
      };
    }
  }, [manager]);

  // Transform hierarchy objects to match mockData structure
  const homeHierarchy: HomeHierarchy | null = useMemo(() => {
    if (!manager || !manager.isLoaded() || systems.length === 0) {
      return null;
    }

    // Get the first system (or default to 'system')
    const primarySystem = systems.find(s => s.systemId === 'system') || systems[0];
    if (!primarySystem) {
      return null;
    }

    // Transform systems
    const transformedSystems: System[] = systems.map(system => {
      // Transform inverter arrays
      const inverterArrays: InverterArray[] = system.inverterArrays.map(invArray => {
        const inverters: Inverter[] = invArray.inverters.map(inverter => {
          const telemetry = inverter.getTelemetry();
          return {
            id: inverter.id,
            name: inverter.name,
            model: inverter.model || 'Unknown',
            serialNumber: inverter.serialNumber || inverter.id,
            status: inverter.getStatus(),
            metrics: {
              solarPower: inverter.getPower(),
              gridPower: inverter.getGridPower(),
              loadPower: inverter.getLoadPower(),
              batteryPower: inverter.getBatteryPower(),
              efficiency: inverter.getEfficiency(),
              dcVoltage: 580, // Default, could be from telemetry
              temperature: inverter.getTemperature() || 0,
            },
          };
        });

        return {
          id: invArray.id,
          name: invArray.name,
          inverters,
          batteryArrayId: invArray.attachedBatteryArrayId,
        };
      });

      // Transform battery arrays
      const batteryArrays: BatteryArray[] = system.batteryArrays.map(batArray => {
        const batteries: BatteryBank[] = batArray.batteryPacks.map(pack => {
          const telemetry = pack.getTelemetry();
          const batteryTelemetry = pack.getBatteryTelemetry();
          return {
            id: pack.id,
            name: pack.name,
            model: pack.chemistry || 'Battery Pack',
            serialNumber: pack.id,
            status: pack.getStatus(),
            metrics: {
              soc: pack.getSOC() || 0,
              power: pack.getPower(),
              voltage: pack.getVoltage() || 0,
              temperature: pack.getTemperature() || 0,
            },
            batteryBankId: pack.id,
            batteryArrayId: batArray.id,
          };
        });

        return {
          id: batArray.id,
          name: batArray.name,
          batteries,
        };
      });

      return {
        id: system.systemId,
        name: system.name,
        inverterArrays,
        batteryArrays,
      };
    });

    // Transform meters - read telemetry directly to ensure we get latest values
    const meters: Meter[] = primarySystem.meters.map(meter => {
      const telemetry = meter.getTelemetry();
      // Get latest telemetry values - these are updated by getSystemNow()
      const power = meter.getPower(); // Returns kW (from gridPower)
      const importKwh = meter.getImportEnergy(); // Returns kWh
      const exportKwh = meter.getExportEnergy(); // Returns kWh
      
      console.log(`[DataProvider] Meter ${meter.id} metrics:`, {
        power,
        importKwh,
        exportKwh,
        hasTelemetry: !!telemetry,
      });
      
      return {
        id: meter.id,
        name: meter.name,
        model: meter.model || 'Energy Meter',
        serialNumber: meter.serialNumber || meter.id,
        status: meter.getStatus(),
        metrics: {
          power: power * 1000, // Convert kW to W for display (MeterCard expects W)
          importKwh: importKwh,
          exportKwh: exportKwh,
          frequency: 50.0, // Default
          powerFactor: 0.98, // Default
        },
      };
    });

    return {
      id: primarySystem.systemId,
      name: primarySystem.name,
      systems: transformedSystems,
      meters,
    };
  }, [manager, systems, homeTelemetry]); // Added homeTelemetry to trigger re-transformation when telemetry updates

  // Transform energy stats from home telemetry
  const energyStats = useMemo(() => {
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
        installedCapacity: 0,
      };
    }

    const daily = homeTelemetry.dailyEnergy;
    const financial = homeTelemetry.financialMetrics;

    return {
      solarPower: homeTelemetry.pvPower,
      batteryPower: homeTelemetry.batteryPower,
      batteryLevel: homeTelemetry.batterySoc || 0,
      consumption: homeTelemetry.loadPower,
      gridPower: homeTelemetry.gridPower,
      isGridExporting: homeTelemetry.gridPower < 0,
      dailyProduction: daily?.solar || 0,
      dailyConsumption: daily?.load || 0,
      selfConsumption: daily?.selfConsumption || 0,
      gridExported: daily?.gridExport || 0,
      batteryChargeEnergy: daily?.batteryCharge || 0,
      batteryDischargeEnergy: daily?.batteryDischarge || 0,
      loadEnergy: daily?.load || 0,
      gridImportEnergy: daily?.gridImport || 0,
      gridExportEnergy: daily?.gridExport || 0,
      co2Saved: financial?.co2PreventedKg || 0,
      moneySaved: financial?.totalSavedPkr || 0,
      monthlyBillAmount: financial?.totalBillPkr || 0,
      dailyPrediction: 0, // Not available in current API
      avgKwPerKwp: 0, // Not available in current API
      installedCapacity: 0, // Could be calculated from inverters
    };
  }, [homeTelemetry]);

  // Transform chart data from hourly data
  const chartData = useMemo(() => {
    if (!hourlyData || !Array.isArray(hourlyData)) {
      return [];
    }

    return hourlyData.map(item => ({
      time: item.time || '',
      solar: item.solar || 0,
      consumption: item.load || 0, // Map 'load' to 'consumption' for frontend compatibility
      battery: item.battery || 0,
      grid: item.grid || 0,
    }));
  }, [hourlyData]);

  // Transform devices list
  const devices = useMemo(() => {
    if (!homeHierarchy) {
      return [];
    }

    const deviceList: DataContextValue['devices'] = [];

    // Add all inverters
    homeHierarchy.systems.forEach(system => {
      system.inverterArrays.forEach(array => {
        array.inverters.forEach(inverter => {
          deviceList.push({
            id: inverter.id,
            name: inverter.name,
            type: 'inverter' as const,
            status: inverter.status,
            model: inverter.model,
            serialNumber: inverter.serialNumber,
            value: `${inverter.metrics.solarPower.toFixed(2)} kW`,
            unit: 'kW',
            metrics: [
              { label: 'Solar Power', value: inverter.metrics.solarPower.toFixed(2), unit: 'kW' },
              { label: 'Grid Power', value: inverter.metrics.gridPower.toFixed(2), unit: 'kW' },
              { label: 'Load Power', value: inverter.metrics.loadPower.toFixed(2), unit: 'kW' },
              { label: 'Battery Power', value: inverter.metrics.batteryPower.toFixed(2), unit: 'kW' },
              { label: 'Efficiency', value: inverter.metrics.efficiency.toFixed(1), unit: '%' },
              { label: 'Temperature', value: inverter.metrics.temperature.toFixed(1), unit: '°C' },
            ],
          });
        });
      });
    });

    // Add all battery packs
    homeHierarchy.systems.forEach(system => {
      system.batteryArrays.forEach(array => {
        array.batteries.forEach(battery => {
          deviceList.push({
            id: battery.id,
            name: battery.name,
            type: 'battery' as const,
            status: battery.status,
            model: battery.model,
            serialNumber: battery.serialNumber,
            value: `${battery.metrics.soc.toFixed(1)}%`,
            unit: '%',
            metrics: [
              { label: 'SOC', value: battery.metrics.soc.toFixed(1), unit: '%' },
              { label: 'Power', value: battery.metrics.power.toFixed(2), unit: 'kW' },
              { label: 'Voltage', value: battery.metrics.voltage.toFixed(1), unit: 'V' },
              { label: 'Temperature', value: battery.metrics.temperature.toFixed(1), unit: '°C' },
            ],
          });
        });
      });
    });

    // Add all meters
    homeHierarchy.meters.forEach(meter => {
      deviceList.push({
        id: meter.id,
        name: meter.name,
        type: 'meter' as const,
        status: meter.status,
        model: meter.model,
        serialNumber: meter.serialNumber,
        value: `${meter.metrics.power.toFixed(2)} kW`,
        unit: 'kW',
        metrics: [
          { label: 'Power', value: meter.metrics.power.toFixed(2), unit: 'kW' },
          { label: 'Import', value: meter.metrics.importKwh.toFixed(2), unit: 'kWh' },
          { label: 'Export', value: meter.metrics.exportKwh.toFixed(2), unit: 'kWh' },
          { label: 'Frequency', value: meter.metrics.frequency.toFixed(1), unit: 'Hz' },
          { label: 'Power Factor', value: meter.metrics.powerFactor.toFixed(2), unit: '' },
        ],
      });
    });

    return deviceList;
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
