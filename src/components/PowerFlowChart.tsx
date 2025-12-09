import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar } from 'recharts';
import { TelemetryData } from '../types/telemetry';
import { formatPower } from '../utils/telemetry';

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
  const [dataPoints, setDataPoints] = useState<PowerDataPoint[]>([]);
  const maxDataPoints = 60; // 5 minutes at 5-second intervals

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
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">Power Flow Over Time</h3>
        <div className="bg-gray-50 rounded p-8 text-center">
          <div className="text-gray-500">Loading power data...</div>
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
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold mb-4">Power Flow Over Time</h3>
      
      {/* Recharts Line Chart */}
      <div className="h-80 mb-4">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis 
              dataKey="time" 
              stroke="#666"
              fontSize={12}
            />
            <YAxis 
              stroke="#666"
              fontSize={12}
              tickFormatter={(value) => `${(value / 1000).toFixed(1)}kW`}
            />
            <Tooltip 
              formatter={(value: any, name: any) => [
                formatPower(typeof value === 'number' ? value : Number(value)),
                String(name)
              ]}
              labelFormatter={(label) => `Time: ${label}`}
              contentStyle={{
                backgroundColor: '#fff',
                border: '1px solid #ccc',
                borderRadius: '4px'
              }}
            />
            <Legend />
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
        <div className="bg-blue-50 rounded-lg p-3 text-center">
          <div className="text-sm text-gray-600 mb-1">Solar Generation</div>
          <div className="text-xl font-bold text-blue-600">{formatPower(telemetry?.pv_power_w)}</div>
        </div>
        <div className="bg-purple-50 rounded-lg p-3 text-center">
          <div className="text-sm text-gray-600 mb-1">Load Consumption</div>
          <div className="text-xl font-bold text-purple-600">{formatPower(telemetry?.load_power_w)}</div>
        </div>
        <div className={`rounded-lg p-3 text-center ${(telemetry?.batt_power_w || 0) >= 0 ? 'bg-green-50' : 'bg-red-50'}`}>
          <div className="text-sm text-gray-600 mb-1">Battery {(telemetry?.batt_power_w || 0) >= 0 ? 'Charging' : 'Discharging'}</div>
          <div className={`text-xl font-bold ${(telemetry?.batt_power_w || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            {formatPower(Math.abs(telemetry?.batt_power_w || 0))}
          </div>
        </div>
        <div className={`rounded-lg p-3 text-center ${(telemetry?.grid_power_w || 0) >= 0 ? 'bg-orange-50' : 'bg-yellow-50'}`}>
          <div className="text-sm text-gray-600 mb-1">Grid {(telemetry?.grid_power_w || 0) >= 0 ? 'Import' : 'Export'}</div>
          <div className={`text-xl font-bold ${(telemetry?.grid_power_w || 0) >= 0 ? 'text-orange-600' : 'text-yellow-600'}`}>
            {formatPower(Math.abs(telemetry?.grid_power_w || 0))}
          </div>
        </div>
      </div>

      {/* Debug Info - Remove this in production */}
      <div className="mt-4 p-2 bg-gray-100 rounded text-xs">
        <div>Data Points: {dataPoints.length}</div>
        <div>Max Power: {formatPower(maxPower)}</div>
        <div>Latest: PV={telemetry?.pv_power_w}, Load={telemetry?.load_power_w}, Batt={telemetry?.batt_power_w}, Grid={telemetry?.grid_power_w}</div>
      </div>
    </div>
  );
};
