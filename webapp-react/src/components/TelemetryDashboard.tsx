import React, { useState, useEffect, useContext } from 'react';
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
import { useTheme } from '../contexts/ThemeContext';
import { ArrayContext } from '../ui/AppLayout';

interface TelemetryDashboardProps {
  inverterId?: string;
  refreshInterval?: number;
}

export const TelemetryDashboard: React.FC<TelemetryDashboardProps> = ({
  inverterId = 'senergy1',
  refreshInterval = 5000
}) => {
  const { theme } = useTheme();
  const { selectedArray } = useContext(ArrayContext);
  const [telemetry, setTelemetry] = useState<TelemetryData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [isDemoMode, setIsDemoMode] = useState(false);

  // Theme-aware colors matching NewDashboardPage
  const textColor = theme === 'dark' ? '#ffffff' : '#1f2937'; // white or gray-800
  const textSecondary = theme === 'dark' ? 'rgba(255, 255, 255, 0.7)' : '#6b7280'; // gray-400
  const cardBg = theme === 'dark' ? '#1f2937' : '#ffffff'; // gray-800 or white
  const borderColor = theme === 'dark' ? '#374151' : '#e5e7eb'; // gray-700 or gray-200
  const shadowColor = theme === 'dark' ? 'rgba(0, 0, 0, 0.3)' : 'rgba(0, 0, 0, 0.1)';

  const fetchTelemetry = async () => {
    try {
      setError(null);
      const inverterParam = inverterId === 'all' ? 'all' : inverterId;
      const url = selectedArray
        ? `/api/now?inverter_id=${inverterParam}&array_id=${selectedArray}`
        : `/api/now?inverter_id=${inverterParam}`;
      const response: TelemetryResponse = await api.get(url);
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
  }, [inverterId, refreshInterval, selectedArray]);

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-lg" style={{ color: textColor }}>Loading telemetry data...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div 
        className="border rounded-lg p-4"
        style={{
          backgroundColor: theme === 'dark' ? '#7f1d1d' : '#fef2f2',
          borderColor: theme === 'dark' ? '#991b1b' : '#fecaca',
        }}
      >
        <div 
          className="font-medium"
          style={{ color: theme === 'dark' ? '#fca5a5' : '#991b1b' }}
        >
          Error loading telemetry
        </div>
        <div 
          className="text-sm mt-1"
          style={{ color: theme === 'dark' ? '#fca5a5' : '#dc2626' }}
        >
          {error}
        </div>
        <button
          onClick={fetchTelemetry}
          className="mt-2 px-3 py-1 rounded text-sm"
          style={{
            backgroundColor: '#dc2626',
            color: '#ffffff',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor = '#b91c1c';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = '#dc2626';
          }}
        >
          Retry
        </button>
      </div>
    );
  }

  if (!telemetry) {
    return (
      <div className="text-center p-8" style={{ color: textSecondary }}>
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
          <h2 className="text-2xl font-bold" style={{ color: textColor }}>
            Solar System Telemetry
          </h2>
          {isDemoMode && (
            <div 
              className="text-sm font-medium mt-1"
              style={{ color: theme === 'dark' ? '#fb923c' : '#ea580c' }}
            >
              🎭 Demo Mode - Using simulated data
            </div>
          )}
        </div>
        <div className="text-sm" style={{ color: textSecondary }}>
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
      <div 
        className="rounded-lg shadow p-6"
        style={{
          backgroundColor: cardBg,
          boxShadow: `0px 4px 6px ${shadowColor}`,
        }}
      >
        <h3 className="text-lg font-semibold mb-4" style={{ color: textColor }}>
          Current Power Flow
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center">
            <div className="text-2xl font-bold" style={{ color: '#3b82f6' }}>
              {formatPower(powerFlow.pv)}
            </div>
            <div className="text-sm" style={{ color: textSecondary }}>
              Solar Generation
            </div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold" style={{ color: '#a855f7' }}>
              {formatPower(powerFlow.load)}
            </div>
            <div className="text-sm" style={{ color: textSecondary }}>
              Load Consumption
            </div>
          </div>
          <div className="text-center">
            <div 
              className="text-2xl font-bold"
              style={{ color: getPowerColor(powerFlow.battery) }}
            >
              {formatPower(powerFlow.battery)}
            </div>
            <div className="text-sm" style={{ color: textSecondary }}>
              Battery ({batteryStatus.status})
            </div>
          </div>
          <div className="text-center">
            <div 
              className="text-2xl font-bold"
              style={{ color: powerFlow.grid > 0 ? '#10b981' : '#ef4444' }}
            >
              {formatPower(powerFlow.grid)}
            </div>
            <div className="text-sm" style={{ color: textSecondary }}>
              Grid {powerFlow.grid > 0 ? 'Export' : 'Import'}
            </div>
          </div>
        </div>
      </div>

      {/* Battery Status section removed as requested */}

      {/* Inverter Status */}
      <div 
        className="rounded-lg shadow p-6"
        style={{
          backgroundColor: cardBg,
          boxShadow: `0px 4px 6px ${shadowColor}`,
        }}
      >
        <h3 className="text-lg font-semibold mb-4" style={{ color: textColor }}>
          Inverter Status
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <div>
            <div className="text-sm" style={{ color: textSecondary }}>Mode</div>
            <div className="text-lg font-medium" style={{ color: textColor }}>
              {inverterStatus.mode}
            </div>
          </div>
          <div>
            <div className="text-sm" style={{ color: textSecondary }}>Temperature</div>
            <div className="text-lg font-medium" style={{ color: textColor }}>
              {formatTemperature(inverterStatus.temperature)}
            </div>
          </div>
          <div>
            <div className="text-sm" style={{ color: textSecondary }}>Error Code</div>
            <div 
              className="text-lg font-medium"
              style={{ 
                color: inverterStatus.errorCode === 0 ? '#10b981' : '#ef4444' 
              }}
            >
              {inverterStatus.errorCode === 0 ? 'No Errors' : `Error ${inverterStatus.errorCode}`}
            </div>
          </div>
        </div>
        <div className="mt-4 grid grid-cols-2 md:grid-cols-3 gap-4">
          <div>
            <div className="text-sm" style={{ color: textSecondary }}>Model</div>
            <div className="text-lg font-medium" style={{ color: textColor }}>
              {inverterStatus.model}
            </div>
          </div>
          <div>
            <div className="text-sm" style={{ color: textSecondary }}>Serial Number</div>
            <div className="text-lg font-medium" style={{ color: textColor }}>
              {inverterStatus.serialNumber}
            </div>
          </div>
          <div>
            <div className="text-sm" style={{ color: textSecondary }}>Rated Power</div>
            <div className="text-lg font-medium" style={{ color: textColor }}>
              {formatPower(inverterStatus.ratedPower)}
            </div>
          </div>
        </div>
      </div>

      {/* Energy Totals */}
      <div 
        className="rounded-lg shadow p-6"
        style={{
          backgroundColor: cardBg,
          boxShadow: `0px 4px 6px ${shadowColor}`,
        }}
      >
        <h3 className="text-lg font-semibold mb-4" style={{ color: textColor }}>
          Energy Totals
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <div className="text-center">
            <div className="text-2xl font-bold" style={{ color: '#3b82f6' }}>
              {formatEnergy(telemetry.today_energy)}
            </div>
            <div className="text-sm" style={{ color: textSecondary }}>Today's Solar</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold" style={{ color: '#a855f7' }}>
              {formatEnergy(telemetry.today_load_energy)}
            </div>
            <div className="text-sm" style={{ color: textSecondary }}>Today's Load</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold" style={{ color: '#10b981' }}>
              {formatEnergy(telemetry.today_export_energy)}
            </div>
            <div className="text-sm" style={{ color: textSecondary }}>Today's Export</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold" style={{ color: '#ef4444' }}>
              {formatEnergy(telemetry.today_import_energy)}
            </div>
            <div className="text-sm" style={{ color: textSecondary }}>Today's Import</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold" style={{ color: textColor }}>
              {formatEnergy(telemetry.total_energy)}
            </div>
            <div className="text-sm" style={{ color: textSecondary }}>Total Energy</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold" style={{ color: '#f97316' }}>
              {formatPower(telemetry.today_peak_power)}
            </div>
            <div className="text-sm" style={{ color: textSecondary }}>Peak Power</div>
          </div>
        </div>
      </div>

      {/* MPPT Details */}
      {(telemetry.mppt1_power || telemetry.mppt2_power) && (
        <div 
          className="rounded-lg shadow p-6"
          style={{
            backgroundColor: cardBg,
            boxShadow: `0px 4px 6px ${shadowColor}`,
          }}
        >
          <h3 className="text-lg font-semibold mb-4" style={{ color: textColor }}>
            MPPT Details
          </h3>
          <div className="grid grid-cols-2 gap-4">
            {telemetry.mppt1_power && (
              <div className="text-center">
                <div className="text-2xl font-bold" style={{ color: '#3b82f6' }}>
                  {formatPower(telemetry.mppt1_power)}
                </div>
                <div className="text-sm" style={{ color: textSecondary }}>MPPT 1</div>
              </div>
            )}
            {telemetry.mppt2_power && (
              <div className="text-center">
                <div className="text-2xl font-bold" style={{ color: '#3b82f6' }}>
                  {formatPower(telemetry.mppt2_power)}
                </div>
                <div className="text-sm" style={{ color: textSecondary }}>MPPT 2</div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Configuration */}
      <div 
        className="rounded-lg shadow p-6"
        style={{
          backgroundColor: cardBg,
          boxShadow: `0px 4px 6px ${shadowColor}`,
        }}
      >
        <h3 className="text-lg font-semibold mb-4" style={{ color: textColor }}>
          Configuration
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <div className="text-sm" style={{ color: textSecondary }}>Grid Charge</div>
            <div className="text-lg font-medium" style={{ color: textColor }}>
              {telemetry.grid_charge ? 'Enabled' : 'Disabled'}
            </div>
          </div>
          <div>
            <div className="text-sm" style={{ color: textSecondary }}>Max Grid Charge</div>
            <div className="text-lg font-medium" style={{ color: textColor }}>
              {formatPower(telemetry.maximum_grid_charger_power)}
            </div>
          </div>
          <div>
            <div className="text-sm" style={{ color: textSecondary }}>Max Charge Power</div>
            <div className="text-lg font-medium" style={{ color: textColor }}>
              {formatPower(telemetry.maximum_charger_power)}
            </div>
          </div>
          <div>
            <div className="text-sm" style={{ color: textSecondary }}>Max Discharge Power</div>
            <div className="text-lg font-medium" style={{ color: textColor }}>
              {formatPower(telemetry.maximum_discharger_power)}
            </div>
          </div>
        </div>
        <div className="mt-4 grid grid-cols-2 md:grid-cols-3 gap-4">
          <div>
            <div className="text-sm" style={{ color: textSecondary }}>Off-Grid Mode</div>
            <div className="text-lg font-medium" style={{ color: textColor }}>
              {telemetry.off_grid_mode ? 'Enabled' : 'Disabled'}
            </div>
          </div>
          <div>
            <div className="text-sm" style={{ color: textSecondary }}>Startup SOC</div>
            <div className="text-lg font-medium" style={{ color: textColor }}>
              {formatPercentage(telemetry.off_grid_start_up_battery_capacity)}
            </div>
          </div>
        </div>
      </div>

      {/* TOU Windows */}
      {(telemetry.charge_start_time_1 || telemetry.discharge_start_time_1) && (
        <div 
          className="rounded-lg shadow p-6"
          style={{
            backgroundColor: cardBg,
            boxShadow: `0px 4px 6px ${shadowColor}`,
          }}
        >
          <h3 className="text-lg font-semibold mb-4" style={{ color: textColor }}>
            Time-of-Use Windows
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {telemetry.charge_start_time_1 && (
              <div>
                <h4 className="font-medium mb-2" style={{ color: textColor }}>
                  Charge Window 1
                </h4>
                <div className="space-y-1 text-sm" style={{ color: textSecondary }}>
                  <div>Time: {telemetry.charge_start_time_1} - {telemetry.charge_end_time_1}</div>
                  <div>Power: {formatPower(telemetry.charge_power_1)}</div>
                  <div>End SOC: {formatPercentage(telemetry.charger_end_soc_1)}</div>
                </div>
              </div>
            )}
            {telemetry.discharge_start_time_1 && (
              <div>
                <h4 className="font-medium mb-2" style={{ color: textColor }}>
                  Discharge Window 1
                </h4>
                <div className="space-y-1 text-sm" style={{ color: textSecondary }}>
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
