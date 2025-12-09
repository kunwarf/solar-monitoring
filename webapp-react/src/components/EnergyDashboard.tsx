import React, { useState, useEffect } from 'react';
import { api } from '../lib/api';
import { TelemetryData, TelemetryResponse } from '../types/telemetry';
import { StatusCard } from './StatusCard';
import { SemiCircularGauge } from './SemiCircularGauge';
import { generateDemoTelemetry } from '../utils/demoData';

interface EnergyDashboardProps {
  inverterId?: string;
  refreshInterval?: number;
}

export const EnergyDashboard: React.FC<EnergyDashboardProps> = ({
  inverterId = 'senergy1',
  refreshInterval = 5000
}) => {
  const [telemetry, setTelemetry] = useState<TelemetryData | null>(null);
  const [loading, setLoading] = useState(true);
  const [isDemoMode, setIsDemoMode] = useState(false);

  const fetchTelemetry = async () => {
    try {
      const response: TelemetryResponse = await api.get(`/api/now?inverter_id=${inverterId}`);
      setTelemetry(response.now);
      setIsDemoMode(false);
    } catch (err) {
      // Use demo data when API is not available
      setTelemetry(generateDemoTelemetry());
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
        <div className="text-lg">Loading dashboard...</div>
      </div>
    );
  }

  if (!telemetry) {
    return (
      <div className="text-center p-8 text-gray-500">
        No data available
      </div>
    );
  }

  // Icons (using simple Unicode/Emoji for now)
  const InverterIcon = () => (
    <div className="w-12 h-12 bg-gray-300 rounded-lg flex items-center justify-center">
      <div className="w-8 h-6 bg-gray-400 rounded flex items-center justify-center">
        <div className="w-2 h-2 bg-green-500 rounded-sm"></div>
      </div>
    </div>
  );

  const SolarIcon = () => (
    <div className="text-4xl">☀️</div>
  );

  const GridIcon = () => (
    <div className="w-12 h-12 bg-gray-300 rounded-lg flex items-center justify-center relative">
      <div className="w-6 h-6 bg-gray-400 rounded"></div>
      <div className="absolute -bottom-1 -right-1 w-4 h-4 bg-green-500 rounded-full flex items-center justify-center">
        <div className="w-2 h-2 bg-white rounded-full"></div>
      </div>
    </div>
  );

  const BatteryIcon = () => (
    <div className="w-12 h-12 bg-green-100 border-2 border-green-300 rounded-lg flex items-center justify-center">
      <div className="w-8 h-6 bg-green-200 rounded flex items-center justify-center">
        <div className="w-6 h-4 bg-green-300 rounded-sm flex items-center justify-center">
          <div className="w-1 h-2 bg-green-500 rounded-sm"></div>
        </div>
      </div>
    </div>
  );

  // Format values
  const formatPower = (watts?: number) => {
    if (watts === undefined || watts === null) return '0 W';
    if (watts >= 1000) return `${(watts / 1000).toFixed(1)} kW`;
    return `${watts.toFixed(0)} W`;
  };

  const formatEnergy = (kwh?: number) => {
    if (kwh === undefined || kwh === null) return '0 kWh';
    return `${kwh.toFixed(1)} kWh`;
  };

  const formatVoltage = (volts?: number) => {
    if (volts === undefined || volts === null) return '0 V';
    return `${volts.toFixed(0)} V`;
  };

  const formatPercentage = (percent?: number) => {
    if (percent === undefined || percent === null) return '0%';
    return `${percent.toFixed(0)}%`;
  };

  // Get current day name
  const getCurrentDay = () => {
    const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    return days[new Date().getDay()];
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Energy Dashboard</h1>
        {isDemoMode && (
          <div className="text-sm text-orange-600 font-medium">
            🎭 Demo Mode - Using simulated data
          </div>
        )}
      </div>

      {/* Status Cards Section */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {/* Inverter Card */}
        <StatusCard
          icon={<InverterIcon />}
          title="Inverter"
          status={telemetry.inverter_mode || 'Unknown'}
        />

        {/* Solar PV Card */}
        <StatusCard
          icon={<SolarIcon />}
          title="Solar PV"
          value={`${getCurrentDay()}: ${formatEnergy(telemetry.today_energy)}`}
          subtitle={`Peak: ${formatPower(telemetry.today_peak_power)}`}
        />

        {/* Grid Card */}
        <StatusCard
          icon={<GridIcon />}
          title="Grid"
          value={formatVoltage(telemetry.batt_voltage_v)}
        />

        {/* Battery Card */}
        <StatusCard
          icon={<BatteryIcon />}
          title="Battery"
          value={formatPower(Math.abs(telemetry.batt_power_w || 0))}
          subtitle={(telemetry.batt_power_w || 0) >= 0 ? 'Charging' : 'Discharging'}
        />
      </div>

      {/* Semi-Circular Gauges Section */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Load Gauge */}
        <SemiCircularGauge
          value={telemetry.load_power_w || 0}
          maxValue={5000}
          label="Load"
          color="#3b82f6"
          unit="kW"
        />

        {/* Grid Gauge */}
        <SemiCircularGauge
          value={telemetry.grid_power_w || 0}
          maxValue={5000}
          label="Grid"
          color="#ef4444"
          unit="kW"
        />

        {/* Solar PV Gauge */}
        <SemiCircularGauge
          value={telemetry.pv_power_w || 0}
          maxValue={6000}
          label="Solar PV"
          color="#f59e0b"
          unit="kW"
        />

        {/* Battery Gauge */}
        <SemiCircularGauge
          value={telemetry.batt_power_w || 0}
          maxValue={5000}
          label="Battery"
          color="#10b981"
          unit="kW"
        />
      </div>

      {/* Additional Info */}
      <div className="mt-8 text-center text-sm text-gray-500">
        Last updated: {new Date().toLocaleTimeString()}
      </div>
    </div>
  );
};
