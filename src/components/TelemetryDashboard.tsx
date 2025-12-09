import React, { useState, useEffect } from 'react';
import { api } from '../lib/api';
import { TelemetryData, TelemetryResponse } from '../types/telemetry';
import {
  formatPower,
  formatEnergy,
  formatTemperature,
  formatVoltage,
  formatCurrent,
  formatPercentage,
  getBatteryStatus,
  getPowerFlow,
  getInverterStatus,
  getPowerColor
} from '../utils/telemetry';
import { PowerFlowChart } from './PowerFlowChart';
import { PowerFlowDiagram } from './PowerFlowDiagram';
import { generateDemoTelemetry } from '../utils/demoData';

interface TelemetryDashboardProps {
  inverterId?: string;
  refreshInterval?: number;
}

export const TelemetryDashboard: React.FC<TelemetryDashboardProps> = ({
  inverterId = 'senergy1',
  refreshInterval = 5000
}) => {
  const [telemetry, setTelemetry] = useState<TelemetryData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [isDemoMode, setIsDemoMode] = useState(false);

  const fetchTelemetry = async () => {
    try {
      setError(null);
      const response: TelemetryResponse = await api.get(`/api/now?inverter_id=${inverterId}`);
      setTelemetry(response.now);
      setLastUpdate(new Date());
    } catch (err) {
      // Use demo data when API is not available
      console.log('API not available, using demo data');
      setTelemetry(generateDemoTelemetry());
      setLastUpdate(new Date());
      setError(null); // Clear error when using demo data
      setIsDemoMode(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTelemetry();
    const interval = setInterval(fetchTelemetry, refreshInterval);
    return () => clearInterval(interval);
  }, [inverterId, refreshInterval]);

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-lg">Loading telemetry data...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <div className="text-red-800 font-medium">Error loading telemetry</div>
        <div className="text-red-600 text-sm mt-1">{error}</div>
        <button
          onClick={fetchTelemetry}
          className="mt-2 px-3 py-1 bg-red-600 text-white rounded text-sm hover:bg-red-700"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!telemetry) {
    return (
      <div className="text-center p-8 text-gray-500">
        No telemetry data available
      </div>
    );
  }

  const batteryStatus = getBatteryStatus(telemetry);
  const powerFlow = getPowerFlow(telemetry);
  const inverterStatus = getInverterStatus(telemetry);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Solar System Telemetry</h2>
          {isDemoMode && (
            <div className="text-sm text-orange-600 font-medium">
              🎭 Demo Mode - Using simulated data
            </div>
          )}
        </div>
        <div className="text-sm text-gray-500">
          Last updated: {lastUpdate?.toLocaleTimeString() || 'Never'}
        </div>
      </div>

      {/* Visual Components Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Power Flow Diagram */}
        <PowerFlowDiagram telemetry={telemetry} />
        
        {/* Battery SOC Chart removed as requested */}
      </div>

      {/* Power Flow Chart */}
      <PowerFlowChart telemetry={telemetry} />

      {/* Power Flow Overview */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">Current Power Flow</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600">{formatPower(powerFlow.pv)}</div>
            <div className="text-sm text-gray-600">Solar Generation</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-purple-600">{formatPower(powerFlow.load)}</div>
            <div className="text-sm text-gray-600">Load Consumption</div>
          </div>
          <div className="text-center">
            <div 
              className="text-2xl font-bold"
              style={{ color: getPowerColor(powerFlow.battery) }}
            >
              {formatPower(powerFlow.battery)}
            </div>
            <div className="text-sm text-gray-600">Battery ({batteryStatus.status})</div>
          </div>
          <div className="text-center">
            <div className={`text-2xl font-bold ${powerFlow.grid > 0 ? 'text-green-600' : 'text-red-600'}`}>
              {formatPower(powerFlow.grid)}
            </div>
            <div className="text-sm text-gray-600">
              Grid {powerFlow.grid > 0 ? 'Export' : 'Import'}
            </div>
          </div>
        </div>
      </div>

      {/* Battery Status section removed as requested */}

      {/* Inverter Status */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">Inverter Status</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <div>
            <div className="text-sm text-gray-600">Mode</div>
            <div className="text-lg font-medium">{inverterStatus.mode}</div>
          </div>
          <div>
            <div className="text-sm text-gray-600">Temperature</div>
            <div className="text-lg font-medium">{formatTemperature(inverterStatus.temperature)}</div>
          </div>
          <div>
            <div className="text-sm text-gray-600">Error Code</div>
            <div className={`text-lg font-medium ${inverterStatus.errorCode === 0 ? 'text-green-600' : 'text-red-600'}`}>
              {inverterStatus.errorCode === 0 ? 'No Errors' : `Error ${inverterStatus.errorCode}`}
            </div>
          </div>
        </div>
        <div className="mt-4 grid grid-cols-2 md:grid-cols-3 gap-4">
          <div>
            <div className="text-sm text-gray-600">Model</div>
            <div className="text-lg font-medium">{inverterStatus.model}</div>
          </div>
          <div>
            <div className="text-sm text-gray-600">Serial Number</div>
            <div className="text-lg font-medium">{inverterStatus.serialNumber}</div>
          </div>
          <div>
            <div className="text-sm text-gray-600">Rated Power</div>
            <div className="text-lg font-medium">{formatPower(inverterStatus.ratedPower)}</div>
          </div>
        </div>
      </div>

      {/* Energy Totals */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">Energy Totals</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600">{formatEnergy(telemetry.today_energy)}</div>
            <div className="text-sm text-gray-600">Today's Solar</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-purple-600">{formatEnergy(telemetry.today_load_energy)}</div>
            <div className="text-sm text-gray-600">Today's Load</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600">{formatEnergy(telemetry.today_export_energy)}</div>
            <div className="text-sm text-gray-600">Today's Export</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-red-600">{formatEnergy(telemetry.today_import_energy)}</div>
            <div className="text-sm text-gray-600">Today's Import</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-gray-700">{formatEnergy(telemetry.total_energy)}</div>
            <div className="text-sm text-gray-600">Total Energy</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-orange-600">{formatPower(telemetry.today_peak_power)}</div>
            <div className="text-sm text-gray-600">Peak Power</div>
          </div>
        </div>
      </div>

      {/* MPPT Details */}
      {(telemetry.mppt1_power || telemetry.mppt2_power) && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">MPPT Details</h3>
          <div className="grid grid-cols-2 gap-4">
            {telemetry.mppt1_power && (
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">{formatPower(telemetry.mppt1_power)}</div>
                <div className="text-sm text-gray-600">MPPT 1</div>
              </div>
            )}
            {telemetry.mppt2_power && (
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">{formatPower(telemetry.mppt2_power)}</div>
                <div className="text-sm text-gray-600">MPPT 2</div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Configuration */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">Configuration</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <div className="text-sm text-gray-600">Grid Charge</div>
            <div className="text-lg font-medium">{telemetry.grid_charge ? 'Enabled' : 'Disabled'}</div>
          </div>
          <div>
            <div className="text-sm text-gray-600">Max Grid Charge</div>
            <div className="text-lg font-medium">{formatPower(telemetry.maximum_grid_charger_power)}</div>
          </div>
          <div>
            <div className="text-sm text-gray-600">Max Charge Power</div>
            <div className="text-lg font-medium">{formatPower(telemetry.maximum_charger_power)}</div>
          </div>
          <div>
            <div className="text-sm text-gray-600">Max Discharge Power</div>
            <div className="text-lg font-medium">{formatPower(telemetry.maximum_discharger_power)}</div>
          </div>
        </div>
        <div className="mt-4 grid grid-cols-2 md:grid-cols-3 gap-4">
          <div>
            <div className="text-sm text-gray-600">Off-Grid Mode</div>
            <div className="text-lg font-medium">{telemetry.off_grid_mode ? 'Enabled' : 'Disabled'}</div>
          </div>
          <div>
            <div className="text-sm text-gray-600">Startup SOC</div>
            <div className="text-lg font-medium">{formatPercentage(telemetry.off_grid_start_up_battery_capacity)}</div>
          </div>
        </div>
      </div>

      {/* TOU Windows */}
      {(telemetry.charge_start_time_1 || telemetry.discharge_start_time_1) && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">Time-of-Use Windows</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {telemetry.charge_start_time_1 && (
              <div>
                <h4 className="font-medium text-gray-900 mb-2">Charge Window 1</h4>
                <div className="space-y-1 text-sm">
                  <div>Time: {telemetry.charge_start_time_1} - {telemetry.charge_end_time_1}</div>
                  <div>Power: {formatPower(telemetry.charge_power_1)}</div>
                  <div>End SOC: {formatPercentage(telemetry.charger_end_soc_1)}</div>
                </div>
              </div>
            )}
            {telemetry.discharge_start_time_1 && (
              <div>
                <h4 className="font-medium text-gray-900 mb-2">Discharge Window 1</h4>
                <div className="space-y-1 text-sm">
                  <div>Time: {telemetry.discharge_start_time_1} - {telemetry.discharge_end_time_1}</div>
                  <div>Power: {formatPower(telemetry.discharge_power_1)}</div>
                  <div>End SOC: {formatPercentage(telemetry.discharge_end_soc_1)}</div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
