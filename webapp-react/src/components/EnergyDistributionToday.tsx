import React, { useState, useEffect } from 'react';

interface TelemetryData {
  ts?: string;
  pv_power_w?: number;
  load_power_w?: number;
  batt_power_w?: number;
  grid_power_w?: number;
  batt_soc_pct?: number;
  today_energy?: number;
  today_load_energy?: number;
  today_import_energy?: number;
  today_export_energy?: number;
}

interface EnergyDistributionTodayProps {
  telemetry: TelemetryData | null;
}

interface EnergyFlow {
  solar: number;
  gridImport: number;
  gridExport: number;
  batteryCharge: number;
  batteryDischarge: number;
  home: number;
}

const EnergyDistributionToday: React.FC<EnergyDistributionTodayProps> = ({ telemetry }) => {
  const [energyFlow, setEnergyFlow] = useState<EnergyFlow>({
    solar: 0,
    gridImport: 0,
    gridExport: 0,
    batteryCharge: 0,
    batteryDischarge: 0,
    home: 0
  });

  // Handle null telemetry
  if (!telemetry) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <div className="text-center">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Energy Distribution Today</h3>
          <div className="text-gray-500 py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
            Loading energy data...
          </div>
        </div>
      </div>
    );
  }

  useEffect(() => {
    // Calculate energy flows from telemetry data
    const calculateEnergyFlow = () => {
      // Get daily energy totals (convert from Wh to kWh)
      const solarGeneration = (telemetry.today_energy || 0) / 1000;
      const homeConsumption = (telemetry.today_load_energy || 0) / 1000;
      const gridImport = (telemetry.today_import_energy || 0) / 1000;
      const gridExport = (telemetry.today_export_energy || 0) / 1000;

      // Calculate battery flows based on current power and SOC
      const currentBatteryPower = (telemetry.batt_power_w || 0) / 1000; // Convert to kW
      const batteryCapacity = 20; // 20kWh battery capacity (from config)
      const currentSOC = telemetry.batt_soc_pct || 0;

      // Estimate daily battery charge/discharge based on current power and time of day
      const now = new Date();
      const hoursElapsed = now.getHours() + now.getMinutes() / 60;
      
      // Rough estimation: if battery is charging now, estimate total daily charge
      let batteryCharge = 0;
      let batteryDischarge = 0;
      
      if (currentBatteryPower > 0) {
        // Battery is charging
        batteryCharge = Math.min(currentBatteryPower * hoursElapsed * 0.1, solarGeneration * 0.3);
      } else if (currentBatteryPower < 0) {
        // Battery is discharging
        batteryDischarge = Math.abs(currentBatteryPower) * hoursElapsed * 0.1;
      }

      return {
        solar: solarGeneration,
        gridImport: gridImport,
        gridExport: gridExport,
        batteryCharge: batteryCharge,
        batteryDischarge: batteryDischarge,
        home: homeConsumption
      };
    };

    const newEnergyFlow = calculateEnergyFlow();
    setEnergyFlow(newEnergyFlow);
  }, [telemetry]);

  const formatEnergy = (value: number): string => {
    return value.toFixed(1);
  };

  const getSelfSufficiency = (): number => {
    if (energyFlow.home === 0) return 0;
    const selfServed = energyFlow.solar + energyFlow.batteryDischarge - energyFlow.gridImport;
    return Math.max(0, Math.min(100, (selfServed / energyFlow.home) * 100));
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <h3 className="text-lg font-semibold text-gray-900">Energy Distribution Today</h3>
        <div className="text-right">
          <div className="text-2xl font-bold text-green-600">{getSelfSufficiency().toFixed(1)}%</div>
          <div className="text-sm text-gray-600">Self-Sufficiency</div>
        </div>
      </div>

      {/* Energy Flow Diagram */}
      <div className="relative">
        {/* Solar Panel */}
        <div className="absolute top-0 left-1/2 transform -translate-x-1/2">
          <div className="bg-gradient-to-br from-yellow-100 to-orange-100 rounded-lg p-4 text-center min-w-[120px]">
            <div className="text-2xl mb-2">☀️</div>
            <div className="text-sm font-medium text-gray-900">Solar</div>
            <div className="text-lg font-bold text-orange-600">{formatEnergy(energyFlow.solar)} kWh</div>
          </div>
        </div>

        {/* Battery */}
        <div className="absolute top-20 left-1/4 transform -translate-x-1/2">
          <div className="bg-gradient-to-br from-green-100 to-emerald-100 rounded-lg p-4 text-center min-w-[120px]">
            <div className="text-2xl mb-2">🔋</div>
            <div className="text-sm font-medium text-gray-900">Battery</div>
            <div className="text-lg font-bold text-green-600">{formatEnergy(energyFlow.batteryDischarge)} kWh</div>
            <div className="text-xs text-gray-600">Discharged</div>
          </div>
        </div>

        {/* Grid */}
        <div className="absolute top-20 right-1/4 transform translate-x-1/2">
          <div className="bg-gradient-to-br from-gray-100 to-slate-100 rounded-lg p-4 text-center min-w-[120px]">
            <div className="text-2xl mb-2">⚡</div>
            <div className="text-sm font-medium text-gray-900">Grid</div>
            <div className="text-lg font-bold text-gray-600">{formatEnergy(energyFlow.gridImport)} kWh</div>
            <div className="text-xs text-gray-600">Imported</div>
          </div>
        </div>

        {/* Home */}
        <div className="absolute top-40 left-1/2 transform -translate-x-1/2">
          <div className="bg-gradient-to-br from-blue-100 to-indigo-100 rounded-lg p-4 text-center min-w-[120px]">
            <div className="text-2xl mb-2">🏠</div>
            <div className="text-sm font-medium text-gray-900">Home</div>
            <div className="text-lg font-bold text-blue-600">{formatEnergy(energyFlow.home)} kWh</div>
            <div className="text-xs text-gray-600">Consumed</div>
          </div>
        </div>

        {/* Energy Flow Arrows */}
        <svg className="absolute inset-0 w-full h-full pointer-events-none" style={{ height: '200px' }}>
          {/* Solar to Home */}
          <defs>
            <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
              <polygon points="0 0, 10 3.5, 0 7" fill="#f59e0b" />
            </marker>
          </defs>
          
          {/* Solar to Home */}
          <line
            x1="50%"
            y1="80"
            x2="50%"
            y2="120"
            stroke="#f59e0b"
            strokeWidth="3"
            markerEnd="url(#arrowhead)"
          />
          
          {/* Battery to Home */}
          <line
            x1="25%"
            y1="140"
            x2="45%"
            y2="160"
            stroke="#10b981"
            strokeWidth="3"
            markerEnd="url(#arrowhead)"
          />
          
          {/* Grid to Home */}
          <line
            x1="75%"
            y1="140"
            x2="55%"
            y2="160"
            stroke="#6b7280"
            strokeWidth="3"
            markerEnd="url(#arrowhead)"
          />
        </svg>
      </div>

      {/* Energy Breakdown */}
      <div className="mt-8 grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-yellow-50 rounded-lg p-3 text-center">
          <div className="text-lg font-bold text-yellow-600">{formatEnergy(energyFlow.solar)} kWh</div>
          <div className="text-sm text-gray-600">Solar Generated</div>
        </div>
        <div className="bg-green-50 rounded-lg p-3 text-center">
          <div className="text-lg font-bold text-green-600">{formatEnergy(energyFlow.batteryDischarge)} kWh</div>
          <div className="text-sm text-gray-600">Battery Used</div>
        </div>
        <div className="bg-gray-50 rounded-lg p-3 text-center">
          <div className="text-lg font-bold text-gray-600">{formatEnergy(energyFlow.gridImport)} kWh</div>
          <div className="text-sm text-gray-600">Grid Import</div>
        </div>
        <div className="bg-blue-50 rounded-lg p-3 text-center">
          <div className="text-lg font-bold text-blue-600">{formatEnergy(energyFlow.home)} kWh</div>
          <div className="text-sm text-gray-600">Total Load</div>
        </div>
      </div>

      {/* Self-Sufficiency Progress Bar */}
      <div className="mt-6">
        <div className="flex justify-between text-sm mb-2">
          <span className="text-gray-600">Self-Sufficiency Progress</span>
          <span className="font-medium">{getSelfSufficiency().toFixed(1)}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-3">
          <div 
            className="bg-gradient-to-r from-green-500 to-green-600 h-3 rounded-full transition-all duration-500"
            style={{ width: `${getSelfSufficiency()}%` }}
          />
        </div>
        <div className="flex justify-between text-xs text-gray-500 mt-1">
          <span>Self-Served: {formatEnergy(energyFlow.solar + energyFlow.batteryDischarge)} kWh</span>
          <span>Grid Import: {formatEnergy(energyFlow.gridImport)} kWh</span>
        </div>
      </div>
    </div>
  );
};

export default EnergyDistributionToday;
