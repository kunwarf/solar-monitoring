import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar } from 'recharts';
import { TelemetryData } from '../types/telemetry';
import { formatPower } from '../utils/telemetry';
import { useTheme } from '../contexts/ThemeContext';

interface PowerFlowChartProps {
  telemetry: TelemetryData;
}

interface PowerDataPoint {
  timestamp: Date;
  pv: number;
  load: number;
  battery: number;
  grid: number;
}

export const PowerFlowChart: React.FC<PowerFlowChartProps> = ({ telemetry }) => {
  const { theme } = useTheme();
  const [dataPoints, setDataPoints] = useState<PowerDataPoint[]>([]);
  const maxDataPoints = 60; // 5 minutes at 5-second intervals

  // Theme-aware colors
  const cardBg = theme === 'dark' ? '#1f2937' : '#ffffff';
  const textColor = theme === 'dark' ? '#ffffff' : '#1f2937';
  const textSecondary = theme === 'dark' ? 'rgba(255, 255, 255, 0.7)' : '#6b7280';
  const borderColor = theme === 'dark' ? '#374151' : '#e5e7eb';
  const gridColor = theme === 'dark' ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)';
  const axisColor = theme === 'dark' ? 'rgba(255, 255, 255, 0.7)' : '#666';
  const tooltipBg = theme === 'dark' ? '#1f2937' : '#ffffff';
  const tooltipBorder = theme === 'dark' ? '#374151' : '#ccc';
  const tooltipText = theme === 'dark' ? '#ffffff' : '#1f2937';
  const shadowColor = theme === 'dark' ? 'rgba(0, 0, 0, 0.3)' : 'rgba(0, 0, 0, 0.1)';

  useEffect(() => {
    // Only add data point if we have valid telemetry data
    if (telemetry && (telemetry.pv_power_w !== undefined || telemetry.load_power_w !== undefined)) {
      const newPoint: PowerDataPoint = {
        timestamp: new Date(),
        pv: telemetry.pv_power_w || 0,
        load: telemetry.load_power_w || 0,
        battery: telemetry.batt_power_w || 0,
        grid: telemetry.grid_power_w || 0,
      };

      setDataPoints(prev => {
        const updated = [...prev, newPoint];
        return updated.length > maxDataPoints ? updated.slice(-maxDataPoints) : updated;
      });
    }
  }, [telemetry]);

  const getMaxPower = () => {
    const allValues = dataPoints.flatMap(d => [d.pv, d.load, Math.abs(d.battery), Math.abs(d.grid)]);
    return Math.max(...allValues, 1000); // Minimum 1kW for scale
  };

  const maxPower = getMaxPower();

  // Show loading state if no data points yet
  if (dataPoints.length === 0) {
    return (
      <div 
        className="rounded-lg shadow p-6"
        style={{
          backgroundColor: cardBg,
          boxShadow: `0px 4px 6px ${shadowColor}`,
        }}
      >
        <h3 
          className="text-lg font-semibold mb-4"
          style={{ color: textColor }}
        >
          Power Flow Over Time
        </h3>
        <div 
          className="rounded p-8 text-center"
          style={{
            backgroundColor: theme === 'dark' ? '#374151' : '#f3f4f6',
          }}
        >
          <div style={{ color: textSecondary }}>Loading power data...</div>
        </div>
      </div>
    );
  }

  // Format data for Recharts
  const chartData = dataPoints.slice(-15).map(point => ({
    time: point.timestamp.toLocaleTimeString().slice(-5),
    pv: point.pv,
    load: point.load,
    battery: point.battery,
    grid: point.grid,
    batteryAbs: Math.abs(point.battery),
    gridAbs: Math.abs(point.grid)
  }));

  return (
    <div 
      className="rounded-lg shadow p-6"
      style={{
        backgroundColor: cardBg,
        boxShadow: `0px 4px 6px ${shadowColor}`,
      }}
    >
      <h3 
        className="text-lg font-semibold mb-4"
        style={{ color: textColor }}
      >
        Power Flow Over Time
      </h3>
      
      {/* Recharts Line Chart */}
      <div className="h-80 mb-4">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
            <XAxis 
              dataKey="time" 
              stroke={axisColor}
              fontSize={12}
              tick={{ fill: axisColor }}
            />
            <YAxis 
              stroke={axisColor}
              fontSize={12}
              tick={{ fill: axisColor }}
              tickFormatter={(value) => `${(value / 1000).toFixed(1)}kW`}
            />
            <Tooltip 
              formatter={(value: any, name: any) => [
                formatPower(typeof value === 'number' ? value : Number(value)),
                String(name)
              ]}
              labelFormatter={(label) => `Time: ${label}`}
              contentStyle={{
                backgroundColor: tooltipBg,
                border: `1px solid ${tooltipBorder}`,
                borderRadius: '4px',
                color: tooltipText
              }}
              labelStyle={{ color: tooltipText }}
            />
            <Legend 
              wrapperStyle={{ color: textColor }}
            />
            <Line 
              type="monotone" 
              dataKey="pv" 
              stroke="#3b82f6" 
              strokeWidth={2}
              name="Solar PV"
              dot={{ fill: '#3b82f6', strokeWidth: 2, r: 4 }}
            />
            <Line 
              type="monotone" 
              dataKey="load" 
              stroke="#8b5cf6" 
              strokeWidth={2}
              name="Load"
              dot={{ fill: '#8b5cf6', strokeWidth: 2, r: 4 }}
            />
            <Line 
              type="monotone" 
              dataKey="battery" 
              stroke="#10b981" 
              strokeWidth={2}
              name="Battery"
              dot={{ fill: '#10b981', strokeWidth: 2, r: 4 }}
            />
            <Line 
              type="monotone" 
              dataKey="grid" 
              stroke="#f59e0b" 
              strokeWidth={2}
              name="Grid"
              dot={{ fill: '#f59e0b', strokeWidth: 2, r: 4 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Current Values Summary */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div 
          className="rounded-lg p-3 text-center"
          style={{
            backgroundColor: theme === 'dark' ? '#1e3a8a' : '#dbeafe',
          }}
        >
          <div className="text-sm mb-1" style={{ color: textSecondary }}>Solar Generation</div>
          <div className="text-xl font-bold" style={{ color: '#3b82f6' }}>
            {formatPower(telemetry?.pv_power_w)}
          </div>
        </div>
        <div 
          className="rounded-lg p-3 text-center"
          style={{
            backgroundColor: theme === 'dark' ? '#581c87' : '#f3e8ff',
          }}
        >
          <div className="text-sm mb-1" style={{ color: textSecondary }}>Load Consumption</div>
          <div className="text-xl font-bold" style={{ color: '#a855f7' }}>
            {formatPower(telemetry?.load_power_w)}
          </div>
        </div>
        <div 
          className="rounded-lg p-3 text-center"
          style={{
            backgroundColor: (telemetry?.batt_power_w || 0) >= 0 
              ? (theme === 'dark' ? '#14532d' : '#dcfce7')
              : (theme === 'dark' ? '#7f1d1d' : '#fee2e2'),
          }}
        >
          <div className="text-sm mb-1" style={{ color: textSecondary }}>
            Battery {(telemetry?.batt_power_w || 0) >= 0 ? 'Charging' : 'Discharging'}
          </div>
          <div 
            className="text-xl font-bold"
            style={{ 
              color: (telemetry?.batt_power_w || 0) >= 0 ? '#10b981' : '#ef4444' 
            }}
          >
            {formatPower(Math.abs(telemetry?.batt_power_w || 0))}
          </div>
        </div>
        <div 
          className="rounded-lg p-3 text-center"
          style={{
            backgroundColor: (telemetry?.grid_power_w || 0) >= 0 
              ? (theme === 'dark' ? '#7c2d12' : '#ffedd5')
              : (theme === 'dark' ? '#78350f' : '#fef3c7'),
          }}
        >
          <div className="text-sm mb-1" style={{ color: textSecondary }}>
            Grid {(telemetry?.grid_power_w || 0) >= 0 ? 'Import' : 'Export'}
          </div>
          <div 
            className="text-xl font-bold"
            style={{ 
              color: (telemetry?.grid_power_w || 0) >= 0 ? '#f97316' : '#eab308' 
            }}
          >
            {formatPower(Math.abs(telemetry?.grid_power_w || 0))}
          </div>
        </div>
      </div>

      {/* Debug Info - Remove this in production */}
      <div 
        className="mt-4 p-2 rounded text-xs"
        style={{
          backgroundColor: theme === 'dark' ? '#374151' : '#f3f4f6',
          color: textSecondary,
        }}
      >
        <div>Data Points: {dataPoints.length}</div>
        <div>Max Power: {formatPower(maxPower)}</div>
        <div>Latest: PV={telemetry?.pv_power_w}, Load={telemetry?.load_power_w}, Batt={telemetry?.batt_power_w}, Grid={telemetry?.grid_power_w}</div>
      </div>
    </div>
  );
};
