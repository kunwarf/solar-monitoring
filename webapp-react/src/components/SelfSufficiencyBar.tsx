import React from 'react';
import { TelemetryData } from '../types/telemetry';

interface DailyEnergyData {
  solar_energy_kwh: number;
  load_energy_kwh: number;
  battery_charge_energy_kwh: number;
  battery_discharge_energy_kwh: number;
  grid_import_energy_kwh: number;
  grid_export_energy_kwh: number;
}

interface SelfSufficiencyBarProps {
  telemetry: TelemetryData;
  dailyEnergyData?: DailyEnergyData | null;
}

export const SelfSufficiencyBar: React.FC<SelfSufficiencyBarProps> = ({ telemetry, dailyEnergyData }) => {
  // Helper to convert Wh to kWh if needed
  const toKwh = (value: number | undefined | null): number => {
    if (!value || value === 0) return 0;
    // If value is > 1000, assume it's in Wh, convert to kWh
    // Otherwise assume it's already in kWh
    return value > 1000 ? value / 1000 : value;
  };

  // Use real energy data if available, otherwise fallback to telemetry
  // Convert from Wh to kWh if needed
  const totalLoad = dailyEnergyData?.load_energy_kwh 
    ? (dailyEnergyData.load_energy_kwh > 1000 ? dailyEnergyData.load_energy_kwh / 1000 : dailyEnergyData.load_energy_kwh)
    : toKwh(telemetry.today_load_energy) || toKwh((telemetry as any)?.extra?.today_load_energy) || 0;
  
  const gridImport = dailyEnergyData?.grid_import_energy_kwh
    ? (dailyEnergyData.grid_import_energy_kwh > 1000 ? dailyEnergyData.grid_import_energy_kwh / 1000 : dailyEnergyData.grid_import_energy_kwh)
    : toKwh(telemetry.today_import_energy) || toKwh((telemetry as any)?.extra?.today_import_energy) || 0;
  
  const solarEnergy = dailyEnergyData?.solar_energy_kwh
    ? (dailyEnergyData.solar_energy_kwh > 1000 ? dailyEnergyData.solar_energy_kwh / 1000 : dailyEnergyData.solar_energy_kwh)
    : toKwh(telemetry.today_energy) || toKwh(telemetry.today_solar_energy) || toKwh((telemetry as any)?.extra?.today_energy) || 0;
  
  const gridExport = dailyEnergyData?.grid_export_energy_kwh
    ? (dailyEnergyData.grid_export_energy_kwh > 1000 ? dailyEnergyData.grid_export_energy_kwh / 1000 : dailyEnergyData.grid_export_energy_kwh)
    : toKwh(telemetry.today_export_energy) || toKwh((telemetry as any)?.extra?.today_export_energy) || 0;
  
  const batteryDischarge = dailyEnergyData?.battery_discharge_energy_kwh
    ? (dailyEnergyData.battery_discharge_energy_kwh > 1000 ? dailyEnergyData.battery_discharge_energy_kwh / 1000 : dailyEnergyData.battery_discharge_energy_kwh)
    : toKwh((telemetry as any)?.today_battery_discharge_energy) || toKwh((telemetry as any)?.extra?.today_battery_discharge_energy) || 0;
  
  const batteryCharge = dailyEnergyData?.battery_charge_energy_kwh
    ? (dailyEnergyData.battery_charge_energy_kwh > 1000 ? dailyEnergyData.battery_charge_energy_kwh / 1000 : dailyEnergyData.battery_charge_energy_kwh)
    : toKwh((telemetry as any)?.today_battery_charge_energy) || toKwh((telemetry as any)?.extra?.today_battery_charge_energy) || 0;
  
  // Debug logging
  console.log('SelfSufficiencyBar data:', {
    dailyEnergyData,
    telemetry: {
      today_load_energy: telemetry.today_load_energy,
      today_import_energy: telemetry.today_import_energy,
      today_energy: telemetry.today_energy,
      extra: (telemetry as any)?.extra
    },
    calculated: { totalLoad, gridImport, solarEnergy, gridExport, batteryDischarge }
  });
  
  // Calculate self-sufficiency components
  // Self-served energy = solar + battery discharge that served the load
  // If we have solar and battery, they served the load (minus grid import)
  const selfServedEnergy = Math.max(0, totalLoad - gridImport);
  const gridServedEnergy = Math.min(gridImport, totalLoad);
  
  // Calculate how much of the self-served energy came from solar vs battery
  // Solar served = min(solar available, self-served)
  const solarServedEnergy = Math.min(solarEnergy, selfServedEnergy);
  // Battery served = min(battery discharge, remaining self-served after solar)
  const batteryServedEnergy = Math.min(batteryDischarge, Math.max(0, selfServedEnergy - solarServedEnergy));
  
  // Calculate percentages
  const selfSufficiencyPct = totalLoad > 0 ? (selfServedEnergy / totalLoad) * 100 : 0;
  const gridDependencyPct = totalLoad > 0 ? (gridServedEnergy / totalLoad) * 100 : 0;
  
  // Ensure percentages don't exceed 100%
  const clampedSelfSufficiency = Math.min(100, Math.max(0, selfSufficiencyPct));
  const clampedGridDependency = Math.min(100, Math.max(0, gridDependencyPct));
  
  // Calculate net export (if any)
  const netExport = Math.max(0, gridExport - gridImport);
  const netExportPct = totalLoad > 0 ? (netExport / totalLoad) * 100 : 0;
  
  return (
    <div className="bg-white rounded-lg p-4 sm:p-6 shadow-sm border border-gray-200">
      <div className="mb-4">
        <h3 className="text-base sm:text-lg font-semibold text-gray-900 mb-2">Today's Energy Self-Sufficiency</h3>
        <div className="text-xs sm:text-sm text-gray-600">
          How your load was served: Solar + Battery vs Grid Import
        </div>
      </div>
      
      {/* Self-Sufficiency Percentage */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-700">Self-Sufficiency</span>
          <span className="text-2xl font-bold text-green-600">
            {Math.round(clampedSelfSufficiency)}%
          </span>
        </div>
        
        {/* Progress Bar */}
        <div className="w-full bg-gray-200 rounded-full h-4 sm:h-6 relative overflow-hidden">
          {/* Solar portion (yellow) */}
          <div 
            className="h-full bg-gradient-to-r from-yellow-400 to-yellow-500 absolute top-0 transition-all duration-500"
            style={{ 
              width: `${totalLoad > 0 ? (solarServedEnergy / totalLoad) * 100 : 0}%`
            }}
          />
          {/* Battery portion (green) */}
          <div 
            className="h-full bg-gradient-to-r from-green-500 to-green-600 absolute top-0 transition-all duration-500"
            style={{ 
              left: `${totalLoad > 0 ? (solarServedEnergy / totalLoad) * 100 : 0}%`,
              width: `${totalLoad > 0 ? (batteryServedEnergy / totalLoad) * 100 : 0}%`
            }}
          />
          {/* Grid-served portion (red) */}
          <div 
            className="h-full bg-gradient-to-r from-red-500 to-red-600 absolute top-0 transition-all duration-500"
            style={{ 
              left: `${clampedSelfSufficiency}%`,
              width: `${clampedGridDependency}%`
            }}
          />
        </div>
        
        {/* Legend */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 mt-3 text-[10px] sm:text-xs text-gray-600">
          <div className="flex items-center">
            <div className="w-2 h-2 sm:w-3 sm:h-3 bg-yellow-400 rounded-full mr-1 flex-shrink-0"></div>
            <span className="truncate">Solar: {solarServedEnergy.toFixed(1)} kWh</span>
          </div>
          <div className="flex items-center">
            <div className="w-2 h-2 sm:w-3 sm:h-3 bg-green-500 rounded-full mr-1 flex-shrink-0"></div>
            <span className="truncate">Battery: {batteryServedEnergy.toFixed(1)} kWh</span>
          </div>
          <div className="flex items-center">
            <div className="w-2 h-2 sm:w-3 sm:h-3 bg-red-500 rounded-full mr-1 flex-shrink-0"></div>
            <span className="truncate">Grid: {gridServedEnergy.toFixed(1)} kWh</span>
          </div>
        </div>
      </div>
      
      {/* Energy Breakdown */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs sm:text-sm">
        <div className="bg-yellow-50 rounded-lg p-3">
          <div className="font-medium text-yellow-800 text-xs sm:text-sm">Solar Energy</div>
          <div className="text-base sm:text-lg font-bold text-yellow-600">{solarServedEnergy.toFixed(1)} kWh</div>
          <div className="text-yellow-600 text-xs sm:text-sm">
            {totalLoad > 0 ? ((solarServedEnergy / totalLoad) * 100).toFixed(1) : 0}% of load
          </div>
        </div>
        
        <div className="bg-green-50 rounded-lg p-3">
          <div className="font-medium text-green-800 text-xs sm:text-sm">Battery Energy</div>
          <div className="text-base sm:text-lg font-bold text-green-600">{batteryServedEnergy.toFixed(1)} kWh</div>
          <div className="text-green-600 text-xs sm:text-sm">
            {totalLoad > 0 ? ((batteryServedEnergy / totalLoad) * 100).toFixed(1) : 0}% of load
          </div>
        </div>
        
        <div className="bg-red-50 rounded-lg p-3">
          <div className="font-medium text-red-800 text-xs sm:text-sm">Grid Import</div>
          <div className="text-base sm:text-lg font-bold text-red-600">{gridServedEnergy.toFixed(1)} kWh</div>
          <div className="text-red-600 text-xs sm:text-sm">
            {clampedGridDependency.toFixed(1)}% of total load
          </div>
        </div>
      </div>
      
      {/* Additional Info */}
      {netExport > 0 && (
        <div className="mt-4 p-3 bg-blue-50 rounded-lg">
          <div className="text-sm text-blue-800">
            <strong>Net Export:</strong> {netExport.toFixed(1)} kWh exported to grid
          </div>
        </div>
      )}
      
      {/* Total Load */}
      <div className="mt-4 pt-3 border-t border-gray-200">
        <div className="flex justify-between text-sm">
          <span className="text-gray-600">Total Load Today:</span>
          <span className="font-medium text-gray-900">{totalLoad.toFixed(1)} kWh</span>
        </div>
      </div>
    </div>
  );
};
