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
  // Fetch hourly energy data for all inverters (aggregated)
  const { data: hourlyData, isLoading: hourlyLoading, error: hourlyError } = useHourlyEnergy({
    inverterId: 'all',
    date: undefined, // Use today's date
  });
  
  // Debug logging for hourly data
  useEffect(() => {
    if (hourlyData) {
      console.log('[DataProvider] Hourly data received:', {
        count: hourlyData.length,
        sample: hourlyData[0],
        isLoading: hourlyLoading,
        error: hourlyError,
      });
    } else {
      console.log('[DataProvider] No hourly data:', {
        isLoading: hourlyLoading,
        error: hourlyError,
      });
    }
  }, [hourlyData, hourlyLoading, hourlyError]);

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

      // Get system-level meters for this system (meters already stored in system.meters)
      const systemMeters: Meter[] = system.meters
        .map(meter => {
          const telemetry = meter.getTelemetry();
          const power = meter.getPower();
          const importKwh = meter.getImportEnergy();
          const exportKwh = meter.getExportEnergy();
          
          return {
            id: meter.id,
            name: meter.name,
            model: meter.model || 'Energy Meter',
            serialNumber: meter.serialNumber || meter.id,
            status: meter.getStatus(),
            metrics: {
              power: power * 1000, // Convert kW to W for display
              importKwh: importKwh,
              exportKwh: exportKwh,
              frequency: 50.0,
              powerFactor: 0.98,
            },
          };
        });

      return {
        id: system.systemId,
        name: system.name,
        inverterArrays,
        batteryArrays,
        meters: systemMeters,
      };
    });

    // Transform home-level meters (meters with systemId="home" or attachmentTarget="home")
    // These are meters not associated with a specific system
    const meters: Meter[] = primarySystem.meters
      .filter(meter => {
        // Home-level meters: systemId is "home" or attachmentTarget is "home"
        return meter.systemId === 'home' || meter.attachmentTarget === 'home';
      })
      .map(meter => {
        const telemetry = meter.getTelemetry();
        // Get latest telemetry values - these are updated by getSystemNow()
        const power = meter.getPower(); // Returns kW (from gridPower)
        const importKwh = meter.getImportEnergy(); // Returns kWh
        const exportKwh = meter.getExportEnergy(); // Returns kWh
        
        console.log(`[DataProvider] Home-level Meter ${meter.id} metrics:`, {
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

    // Calculate today's savings from today's daily energy data
    // Formula: (Load * Import Rate) - (Grid Import * Import Rate) + (Grid Export * Export Rate)
    // This represents: what we would have paid without solar - what we actually paid + what we earned
    let todaySavings = 0;
    if (daily) {
      const todayLoad = daily.load || 0;
      const todayGridImport = daily.gridImport || 0;
      const todayGridExport = daily.gridExport || 0;
      
      // Get rates from financial metrics if available, otherwise use defaults
      // Note: We can't use useBillingConfig here as DataProvider might be outside the provider
      // Instead, we'll use default rates or get them from the API response if available
      const importRate = 50.0; // Default 50 PKR/kWh (should match billing config)
      const exportRate = 22.0; // Default 22 PKR/kWh (should match billing config)
      
      // Calculate today's savings:
      // Without solar: we would have paid (load * importRate)
      // With solar: we paid (gridImport * importRate) and earned (gridExport * exportRate)
      // Savings = (what we would have paid) - (what we actually paid) + (what we earned)
      // Savings = (load * importRate) - (gridImport * importRate) + (gridExport * exportRate)
      // Simplified: (load - gridImport) * importRate + (gridExport * exportRate)
      todaySavings = (todayLoad - todayGridImport) * importRate + (todayGridExport * exportRate);
    }

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
      moneySaved: todaySavings, // Use calculated today's savings instead of monthly total
      monthlyBillAmount: financial?.totalBillPkr || 0,
      dailyPrediction: 0, // Not available in current API
      avgKwPerKwp: 0, // Not available in current API
      installedCapacity: 0, // Could be calculated from inverters
    };
  }, [homeTelemetry]);

  // Transform chart data from hourly data
  const chartData = useMemo(() => {
    console.log('[DataProvider] Transforming chart data, hourlyData:', {
      hasData: !!hourlyData,
      isArray: Array.isArray(hourlyData),
      length: hourlyData?.length,
      sample: hourlyData?.[0],
    });

    // If no hourly data, return 24 hours of empty data points so chart can render
    if (!hourlyData || !Array.isArray(hourlyData) || hourlyData.length === 0) {
      console.log('[DataProvider] No hourly data, returning empty 24-hour array');
      return Array.from({ length: 24 }, (_, i) => ({
        time: `${i.toString().padStart(2, '0')}:00`,
        solar: 0,
        consumption: 0,
        battery: 0,
        grid: 0,
      }));
    }

    // Transform hourly data to chart format
    // Note: Backend returns energy in kWh, but chart displays power in kW
    // For hourly data, we can use the energy values directly as they represent average power over the hour
    const transformed = hourlyData.map(item => {
      // Ensure time format is correct (HH:00)
      let timeStr = item.time || '';
      if (timeStr && !timeStr.includes(':')) {
        // If time is just a number, format it
        const hour = parseInt(timeStr);
        if (!isNaN(hour)) {
          timeStr = `${hour.toString().padStart(2, '0')}:00`;
        }
      }
      
      // Ensure solar is always non-negative and properly mapped
      const solarValue = Math.max(0, item.solar || 0);
      const loadValue = Math.max(0, item.load || 0);
      const batteryValue = item.battery || 0; // Can be negative (discharge) or positive (charge)
      const gridValue = item.grid || 0; // Can be negative (export) or positive (import)
      
      // Debug log for first few items to check data
      if (transformed.length < 3) {
        console.log('[DataProvider] Transforming item:', {
          original: item,
          transformed: {
            time: timeStr,
            solar: solarValue,
            consumption: loadValue,
            battery: batteryValue,
            grid: gridValue,
          },
        });
      }
      
      return {
        time: timeStr,
        solar: solarValue, // kWh (represents average kW over the hour), ensure non-negative
        consumption: loadValue, // Map 'load' to 'consumption' for frontend compatibility
        battery: Math.max(0, batteryValue), // Show only positive battery (charge), discharge will be 0
        grid: gridValue, // Can be negative (export) or positive (import)
      };
    });
    
    // Check if we have any non-zero data
    const hasData = transformed.some(item => 
      item.solar > 0 || item.consumption > 0 || Math.abs(item.battery) > 0 || Math.abs(item.grid) > 0
    );
    
    console.log('[DataProvider] Transformed chart data:', {
      count: transformed.length,
      hasNonZeroData: hasData,
      sample: transformed[0],
      last: transformed[transformed.length - 1],
      maxSolar: Math.max(...transformed.map(d => d.solar)),
      maxConsumption: Math.max(...transformed.map(d => d.consumption)),
    });
    
    return transformed;
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
