import React from 'react';
import { TelemetryData } from '../types/telemetry';
import { formatPower, formatEnergy, formatVoltage, formatCurrent } from '../utils/telemetry';

interface SolarSystemDiagramProps {
  telemetry: TelemetryData;
}

export const SolarSystemDiagram: React.FC<SolarSystemDiagramProps> = ({ telemetry }) => {
  const pvPower = telemetry.pv_power_w || 0;
  const loadPower = telemetry.load_power_w || 0;
  const batteryPower = telemetry.batt_power_w || 0;
  const gridPower = telemetry.grid_power_w || 0;
  const batterySOC = telemetry.batt_soc_pct || 0;
  const batteryVoltage = telemetry.batt_voltage_v || 0;
  const batteryCurrent = telemetry.batt_current_a || 0;

  // Calculate daily energy values
  const dailySolar = telemetry.today_energy || 0;
  const totalSolar = telemetry.total_energy || 0;
  const dailyLoad = telemetry.today_load_energy || 0;
  const dailyImport = telemetry.today_import_energy || 0;
  const dailyExport = telemetry.today_export_energy || 0;

  // Calculate battery runtime (simplified)
  const batteryCapacity = 20; // kWh (from config)
  const currentLoad = loadPower / 1000; // Convert to kW
  const runtimeHours = currentLoad > 0 ? (batteryCapacity * batterySOC / 100) / currentLoad : 0;
  const runtimeMinutes = Math.round((runtimeHours % 1) * 60);

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
      {/* Title */}
      <div className="text-gray-900 text-xl font-bold text-center mb-6">Solar System Overview</div>

      {/* Main System Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Solar Generation Section */}
        <div className="bg-gradient-to-br from-yellow-50 to-orange-50 rounded-lg p-6">
          <div className="flex items-center mb-4">
            <div className="text-3xl mr-3">☀️</div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900">Solar Generation</h3>
              <p className="text-sm text-gray-600">PV Array Output</p>
            </div>
          </div>
          
          {/* Current Power */}
          <div className="text-center mb-4">
            <div className="text-3xl font-bold text-orange-600">
              {formatPower(pvPower)}
            </div>
            <div className="text-sm text-gray-600">Current Output</div>
          </div>

          {/* Daily/Total Energy */}
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div className="bg-white rounded-lg p-3 text-center">
              <div className="font-semibold text-gray-900">{formatEnergy(dailySolar)}</div>
              <div className="text-gray-600">Today</div>
            </div>
            <div className="bg-white rounded-lg p-3 text-center">
              <div className="font-semibold text-gray-900">{formatEnergy(totalSolar / 1000)}</div>
              <div className="text-gray-600">Total</div>
            </div>
          </div>

          {/* PV Strings */}
          <div className="mt-4 space-y-2">
            <div className="text-sm font-medium text-gray-700 mb-2">PV Strings</div>
            <div className="bg-white rounded px-3 py-2 text-sm">
              <div className="flex justify-between">
                <span className="font-medium text-gray-900">String 1</span>
                <span className="text-orange-600 font-semibold">{Math.round(pvPower * 0.5)}W</span>
              </div>
            </div>
            <div className="bg-white rounded px-3 py-2 text-sm">
              <div className="flex justify-between">
                <span className="font-medium text-gray-900">String 2</span>
                <span className="text-orange-600 font-semibold">{Math.round(pvPower * 0.5)}W</span>
              </div>
            </div>
          </div>
        </div>

        {/* Inverter Section */}
        <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-lg p-6">
          <div className="flex items-center mb-4">
            <div className="text-3xl mr-3">🔄</div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900">Inverter</h3>
              <p className="text-sm text-gray-600">Power Conversion</p>
            </div>
          </div>
          
          {/* Inverter Status */}
          <div className="text-center mb-4">
            <div className="text-2xl font-bold text-blue-600">
              {formatPower(pvPower + Math.abs(batteryPower))}
            </div>
            <div className="text-sm text-gray-600">Total Throughput</div>
          </div>

          {/* Inverter Details */}
          <div className="space-y-3">
            <div className="bg-white rounded-lg p-3">
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Temperature</span>
                <span className="font-semibold text-gray-900">
                  {telemetry.inverter_temp_c || 0}°C
                </span>
              </div>
            </div>
            <div className="bg-white rounded-lg p-3">
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Efficiency</span>
                <span className="font-semibold text-green-600">96.5%</span>
              </div>
            </div>
            <div className="bg-white rounded-lg p-3">
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Mode</span>
                <span className="font-semibold text-blue-600">
                  {telemetry.inverter_mode || 'Hybrid'}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Battery Section */}
        <div className="bg-gradient-to-br from-green-50 to-emerald-50 rounded-lg p-6">
          <div className="flex items-center mb-4">
            <div className="text-3xl mr-3">🔋</div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900">Battery Storage</h3>
              <p className="text-sm text-gray-600">Energy Storage System</p>
            </div>
          </div>
          
          {/* Battery SOC */}
          <div className="text-center mb-4">
            <div className="text-3xl font-bold text-green-600">
              {batterySOC}%
            </div>
            <div className="text-sm text-gray-600">State of Charge</div>
          </div>

          {/* Battery Details */}
          <div className="space-y-3">
            <div className="bg-white rounded-lg p-3">
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Power</span>
                <span className="font-semibold text-gray-900">
                  {formatPower(Math.abs(batteryPower))}
                </span>
              </div>
            </div>
            <div className="bg-white rounded-lg p-3">
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Voltage</span>
                <span className="font-semibold text-gray-900">
                  {formatVoltage(batteryVoltage)}
                </span>
              </div>
            </div>
            <div className="bg-white rounded-lg p-3">
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Current</span>
                <span className="font-semibold text-gray-900">
                  {formatCurrent(batteryCurrent)}
                </span>
              </div>
            </div>
            <div className="bg-white rounded-lg p-3">
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Runtime</span>
                <span className="font-semibold text-gray-900">
                  {Math.floor(runtimeHours)}h {runtimeMinutes}m
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* System Summary */}
      <div className="mt-6 bg-gray-50 rounded-lg p-4">
        <h4 className="text-lg font-semibold text-gray-900 mb-4 text-center">System Summary</h4>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-orange-600">{formatPower(pvPower)}</div>
            <div className="text-sm text-gray-600">Solar Generation</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600">{formatPower(Math.abs(batteryPower))}</div>
            <div className="text-sm text-gray-600">Battery Power</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600">{formatPower(loadPower)}</div>
            <div className="text-sm text-gray-600">Load Consumption</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-red-600">{formatPower(Math.abs(gridPower))}</div>
            <div className="text-sm text-gray-600">Grid Power</div>
          </div>
        </div>
      </div>
    </div>
  );
};
