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
  // Use real energy data if available, otherwise fallback to telemetry
  const totalLoad = dailyEnergyData?.load_energy_kwh || telemetry.today_load_energy || 0;
  const gridImport = dailyEnergyData?.grid_import_energy_kwh || telemetry.today_import_energy || 0;
  const solarEnergy = dailyEnergyData?.solar_energy_kwh || telemetry.today_energy || 0;
  const gridExport = dailyEnergyData?.grid_export_energy_kwh || telemetry.today_export_energy || 0;
  const batteryDischarge = dailyEnergyData?.battery_discharge_energy_kwh || 0;
  
  // Calculate self-sufficiency components
  // Self-served energy = solar + battery discharge that served the load
  const selfServedEnergy = Math.max(0, totalLoad - gridImport);
  const gridServedEnergy = Math.min(gridImport, totalLoad);
  
  // Calculate how much of the self-served energy came from solar vs battery
  const solarServedEnergy = Math.min(solarEnergy, selfServedEnergy);
  const batteryServedEnergy = Math.min(batteryDischarge, selfServedEnergy - solarServedEnergy);
  
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
    <div className="bg-white rounded-lg p-6 shadow-sm border border-gray-200">
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-gray-900 mb-2">Today's Energy Self-Sufficiency</h3>
        <div className="text-sm text-gray-600">
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
        <div className="w-full bg-gray-200 rounded-full h-6 relative overflow-hidden">
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
        <div className="grid grid-cols-3 gap-2 mt-3 text-xs text-gray-600">
          <div className="flex items-center">
            <div className="w-3 h-3 bg-yellow-400 rounded-full mr-1"></div>
            <span>Solar: {solarServedEnergy.toFixed(1)} kWh</span>
          </div>
          <div className="flex items-center">
            <div className="w-3 h-3 bg-green-500 rounded-full mr-1"></div>
            <span>Battery: {batteryServedEnergy.toFixed(1)} kWh</span>
          </div>
          <div className="flex items-center">
            <div className="w-3 h-3 bg-red-500 rounded-full mr-1"></div>
            <span>Grid: {gridServedEnergy.toFixed(1)} kWh</span>
          </div>
        </div>
      </div>
      
      {/* Energy Breakdown */}
      <div className="grid grid-cols-3 gap-3 text-sm">
        <div className="bg-yellow-50 rounded-lg p-3">
          <div className="font-medium text-yellow-800">Solar Energy</div>
          <div className="text-lg font-bold text-yellow-600">{solarServedEnergy.toFixed(1)} kWh</div>
          <div className="text-yellow-600">
            {totalLoad > 0 ? ((solarServedEnergy / totalLoad) * 100).toFixed(1) : 0}% of load
          </div>
        </div>
        
        <div className="bg-green-50 rounded-lg p-3">
          <div className="font-medium text-green-800">Battery Energy</div>
          <div className="text-lg font-bold text-green-600">{batteryServedEnergy.toFixed(1)} kWh</div>
          <div className="text-green-600">
            {totalLoad > 0 ? ((batteryServedEnergy / totalLoad) * 100).toFixed(1) : 0}% of load
          </div>
        </div>
        
        <div className="bg-red-50 rounded-lg p-3">
          <div className="font-medium text-red-800">Grid Import</div>
          <div className="text-lg font-bold text-red-600">{gridServedEnergy.toFixed(1)} kWh</div>
          <div className="text-red-600">
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
