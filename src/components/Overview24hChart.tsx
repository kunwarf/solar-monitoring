import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { api } from '../lib/api';
import { formatPower } from '../utils/telemetry';

interface OverviewData {
  time: string;
  solar: number; // kWh
  load: number; // kWh
  battery: number; // kWh (positive=charge, negative=discharge)
  grid: number; // kWh (positive=import, negative=export)
}

interface Overview24hChartProps {
  inverterId?: string;
}

export const Overview24hChart: React.FC<Overview24hChartProps> = ({ inverterId = 'senergy1' }) => {
  const [data, setData] = useState<OverviewData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dataSource, setDataSource] = useState<string>('mock');
  const [yAxisDomain, setYAxisDomain] = useState<[number, number]>([-1000, 1000]);

  const calculateYAxisDomain = (data: OverviewData[]): [number, number] => {
    if (data.length === 0) return [-1, 5];
    
    // Get all values from all data series
    const allValues: number[] = [];
    data.forEach(point => {
      allValues.push(point.solar, point.load, point.battery, point.grid);
    });
    
    const minValue = Math.min(...allValues);
    const maxValue = Math.max(...allValues);
    
    // Add some padding (20%) on both sides
    const padAbs = Math.max(Math.abs(minValue), Math.abs(maxValue)) * 0.2;
    const paddedMin = Math.min(0, minValue - padAbs);
    const paddedMax = Math.max(0, maxValue + padAbs);
    
    // Ensure we have a reasonable range
    if (paddedMax - paddedMin < 1) {
      return [Math.min(0, paddedMin, -0.5), Math.max(0, paddedMax, 0.5)];
    }
    
    return [paddedMin, paddedMax];
  };

  const fetchOverviewData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Fetch from /api/energy/hourly
      try {
        const response = await api.get(`/api/energy/hourly?inverter_id=${inverterId}`) as any;
        if (response && response.hourly_data && Array.isArray(response.hourly_data)) {
          const normalized: OverviewData[] = response.hourly_data.map((p: any) => {
            // Support both net and split fields from API
            const battery = (p.battery !== undefined)
              ? Number(p.battery)
              : (Number(p.battery_charge || 0) - Number(p.battery_discharge || 0));
            const grid = (p.grid !== undefined)
              ? Number(p.grid)
              : (Number(p.grid_import || 0) - Number(p.grid_export || 0));
            return {
              time: p.time,
              solar: Number(p.solar || 0),
              load: Number(p.load || 0),
              battery,
              grid,
            };
          });
          setData(normalized);
          setYAxisDomain(calculateYAxisDomain(normalized));
          setDataSource('hourly_energy');
          return;
        } else {
          throw new Error('Invalid response format');
        }
      } catch (apiError) {
        console.warn('Hourly energy API not available, using mock data:', apiError);
        setDataSource('mock');
      }
      
      // Fallback to mock data
      const mockData = generateMockOverviewData();
      setData(mockData);
      setYAxisDomain(calculateYAxisDomain(mockData));
    } catch (err) {
      setError('Failed to load overview data');
      console.error('Error fetching overview data:', err);
    } finally {
      setLoading(false);
    }
  };

  const generateMockOverviewData = (): OverviewData[] => {
    const data: OverviewData[] = [];
    
    for (let hour = 0; hour < 24; hour++) {
      const timeStr = `${hour.toString().padStart(2, '0')}:00`;
      
      // Solar generation (only during daylight hours) - in kWh
      let solar = 0;
      if (hour >= 6 && hour <= 18) {
        const hourOfDay = hour - 6;
        const maxEnergy = 2.0; // 2kWh peak per hour
        const solarFactor = Math.sin((hourOfDay / 12) * Math.PI);
        solar = Math.max(0, solarFactor * maxEnergy);
      }
      
      // Load consumption (higher during day, lower at night) - in kWh
      let load = 0.5; // Base load
      if (hour >= 6 && hour <= 22) {
        load += Math.random() * 1.5 + 0.5; // 0.5-2kWh additional during active hours
      } else {
        load += Math.random() * 0.2; // 0-0.2kWh additional at night
      }
      
      // Battery net (positive=charge, negative=discharge) - in kWh
      let battery = 0;
      if (solar > load) {
        battery = Math.min(solar - load, 1.5); // charge
      } else if (solar < load) {
        battery = -Math.min(load - solar, 2.0); // discharge
      }
      
      // Grid net (positive=import, negative=export) - in kWh
      const netNeed = load - solar - battery; // battery already applied
      let grid = 0;
      if (netNeed > 0) {
        grid = netNeed; // import
      } else if (netNeed < 0) {
        grid = netNeed; // negative = export
      }
      
      data.push({
        time: timeStr,
        solar: Math.round(solar * 100) / 100,
        load: Math.round(load * 100) / 100,
        battery: Math.round(battery * 100) / 100,
        grid: Math.round(grid * 100) / 100,
      });
    }
    
    return data;
  };

  useEffect(() => {
    fetchOverviewData();
    const interval = setInterval(fetchOverviewData, 300000); // Refresh every 5 minutes
    return () => clearInterval(interval);
  }, [inverterId]);

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">Overview</h3>
        <div className="h-64 flex items-center justify-center">
          <div className="text-gray-500">Loading overview data...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">Overview</h3>
        <div className="h-64 flex items-center justify-center">
          <div className="text-red-500">{error}</div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold">24-Hour Overview</h3>
        <div className="text-sm text-gray-500">
          <div>Last 24 hours (kWh)</div>
          <div className="text-xs">
            Data source: {dataSource === 'hourly_energy' ? 'Hourly Energy API' : 'Mock Data'}
          </div>
        </div>
      </div>

      {/* Chart */}
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis 
              dataKey="time" 
              stroke="#666"
              fontSize={12}
              tickLine={false}
              axisLine={false}
              interval={0}
              tickFormatter={(value) => {
                // Show every 3rd hour (00:00, 03:00, 06:00, 09:00, 12:00, 15:00, 18:00, 21:00)
                const hour = parseInt(value.split(':')[0]);
                return hour % 3 === 0 ? value : '';
              }}
            />
            <YAxis 
              stroke="#666"
              fontSize={12}
              tickLine={false}
              axisLine={false}
              domain={yAxisDomain}
              tickFormatter={(value) => {
                return `${value.toFixed(1)}`;
              }}
            />
            <Tooltip
              content={({ active, payload, label }) => {
                if (active && payload && payload.length) {
                  return (
                    <div className="bg-white p-3 border border-gray-200 rounded-lg shadow-lg">
                      <p className="font-medium text-gray-900">{label}</p>
                      {payload.map((entry, index) => (
                        <p key={index} className="text-sm" style={{ color: entry.color }}>
                          {entry.name}: {(entry.value as number).toFixed(2)} kWh
                        </p>
                      ))}
                    </div>
                  );
                }
                return null;
              }}
            />
            <Legend />
            
            {/* Zero Reference Line */}
            <Line
              type="monotone"
              dataKey={() => 0}
              stroke="#374151"
              strokeWidth={2}
              dot={false}
              name="Zero"
            />
            
            {/* Solar PV Line */}
            <Line
              type="monotone"
              dataKey="solar"
              stroke="#f59e0b"
              strokeWidth={2}
              dot={false}
              name="Solar"
            />
            
            {/* Load Line */}
            <Line
              type="monotone"
              dataKey="load"
              stroke="#3b82f6"
              strokeWidth={2}
              dot={false}
              name="Load"
            />
            
            {/* Battery Net Line (pos=charge, neg=discharge) */}
            <Line
              type="monotone"
              dataKey="battery"
              stroke="#10b981"
              strokeWidth={2}
              dot={false}
              name="Battery (net)"
            />
            
            {/* Grid Net Line (pos=import, neg=export) */}
            <Line
              type="monotone"
              dataKey="grid"
              stroke="#ef4444"
              strokeWidth={2}
              dot={false}
              name="Grid (net)"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4 pt-4 border-t border-gray-100">
        <div className="text-center">
          <div className="text-lg font-bold text-yellow-600">
            {data.reduce((sum, point) => sum + point.solar, 0).toFixed(1)} kWh
          </div>
          <div className="text-xs text-gray-500">Total Solar</div>
        </div>
        <div className="text-center">
          <div className="text-lg font-bold text-blue-600">
            {data.reduce((sum, point) => sum + point.load, 0).toFixed(1)} kWh
          </div>
          <div className="text-xs text-gray-500">Total Load</div>
        </div>
        <div className="text-center">
          <div className="text-lg font-bold text-green-600">
            {data.reduce((sum, point) => sum + Math.max(point.battery, 0), 0).toFixed(1)} kWh
          </div>
          <div className="text-xs text-gray-500">Battery Charge</div>
        </div>
        <div className="text-center">
          <div className="text-lg font-bold text-red-600">
            {data.reduce((sum, point) => sum + Math.max(point.grid, 0), 0).toFixed(1)} kWh
          </div>
          <div className="text-xs text-gray-500">Grid Import</div>
        </div>
      </div>
    </div>
  );
};
