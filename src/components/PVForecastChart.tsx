import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, ComposedChart } from 'recharts';
import { api } from '../lib/api';
import { formatPower, formatEnergy } from '../utils/telemetry';

interface PVForecastData {
  time: string;
  generated: number;
  predicted: number;
  cloudCover: number;
}

interface SolarHistoryData {
  time: string;
  power: number;
}

interface HourlyEnergyData {
  time: string;
  solar: number;
  load: number;
  battery_charge: number;
  battery_discharge: number;
  grid_import: number;
  grid_export: number;
  avg_solar_power_w: number;
  avg_load_power_w: number;
  avg_battery_power_w: number;
  avg_grid_power_w: number;
  sample_count: number;
}

interface PVForecastChartProps {
  inverterId?: string;
  telemetry?: any; // TelemetryData from parent component
}

export const PVForecastChart: React.FC<PVForecastChartProps> = ({ inverterId = 'senergy1', telemetry }) => {
  const [data, setData] = useState<PVForecastData[]>([]);
  // Historical series removed per requirement; use hourly energy for today's actuals only
  const [hourlyEnergy, setHourlyEnergy] = useState<HourlyEnergyData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dataSource, setDataSource] = useState<string>('mock');
  const [totalDailyGeneration, setTotalDailyGeneration] = useState<number>(0);
  const [yAxisDomain, setYAxisDomain] = useState<[number, number]>([0, 5]);

  const calculateYAxisDomain = (data: any[]): [number, number] => {
    if (data.length === 0) return [0, 5];
    
    // Get all energy values from the data
    const allValues: number[] = [];
    data.forEach(point => {
      if (point.actual !== undefined && point.actual !== null) allValues.push(point.actual);
      if (point.predicted !== undefined && point.predicted !== null) allValues.push(point.predicted);
      if (point.generated !== undefined && point.generated !== null) allValues.push(point.generated);
    });
    
    if (allValues.length === 0) return [0, 5];
    
    const maxValue = Math.max(...allValues);
    
    // Add some padding (20% on top)
    const padding = maxValue * 0.2;
    const paddedMax = maxValue + padding;
    
    // Ensure we have a reasonable range (at least 0.5 kWh difference)
    const range = paddedMax;
    if (range < 0.5) {
      return [0, 1];
    }
    
    return [0, paddedMax];
  };

  // Create 24-hour chart data (00:00 to 23:00)
  const create24HourData = () => {
    const hours = [];
    for (let hour = 0; hour < 24; hour++) {
      const time = `${hour.toString().padStart(2, '0')}:00`;
      hours.push({
        time,
        hour,
        actual: 0,
        predicted: 0,
        cloudCover: 20
      });
    }
    return hours;
  };

  const fetchHourlyEnergyData = async () => {
    try {
      const response = await api.get(`/api/energy/hourly?inverter_id=${inverterId}`) as any;
      if (response && response.hourly_data && Array.isArray(response.hourly_data)) {
        setHourlyEnergy(response.hourly_data);
        console.log('Fetched hourly energy data:', response.hourly_data.length, 'hours');
      } else {
        console.warn('No hourly energy data available');
        setHourlyEnergy([]);
      }
    } catch (error) {
      console.warn('Failed to fetch hourly energy data:', error);
      setHourlyEnergy([]);
    }
  };

  const fetchForecastData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Try to fetch forecast data from API
      try {
        const forecastResponse = await api.get(`/api/forecast?inverter_id=${inverterId}`) as any;
        if (forecastResponse && forecastResponse.forecast && Array.isArray(forecastResponse.forecast)) {
          setData(forecastResponse.forecast);
          setDataSource(forecastResponse.source || 'mock');
          setTotalDailyGeneration(forecastResponse.total_daily_generation_kwh || 0);
          console.log('Using real forecast data from:', forecastResponse.source);
        } else {
          throw new Error('Invalid forecast response format');
        }
      } catch (apiError) {
        console.warn('Forecast API not available, using mock data:', apiError);
        setData(generateMockForecastData());
        setDataSource('mock');
      }

      // Historical fallback removed: use only hourly energy data for today's actuals
      
    } catch (err) {
      setError('Failed to load forecast data');
      console.error('Error fetching forecast data:', err);
      // Fallback to mock data
      setData(generateMockForecastData());
      // No solar-history fallback; rely on hourly energy only
      setDataSource('mock');
    } finally {
      setLoading(false);
    }
  };

  const generateMockForecastData = (): PVForecastData[] => {
    const data: PVForecastData[] = [];
    
    // Generate 24-hour data (00:00 to 23:00)
    for (let hour = 0; hour < 24; hour++) {
      const time = `${hour.toString().padStart(2, '0')}:00`;
      let generated = 0;
      let predicted = 0;
      let cloudCover = 20;
      
      if (hour >= 6 && hour <= 18) {
        // Solar hours: 6 AM to 6 PM
        const hourOfDay = hour - 6;
        const maxEnergy = 2.0; // 2 kWh peak per hour (more realistic)
        
        // Generate realistic solar curve
        const solarFactor = Math.sin((hourOfDay / 12) * Math.PI);
        generated = Math.max(0, solarFactor * maxEnergy * 0.7); // 70% of peak
        predicted = Math.max(0, solarFactor * maxEnergy * 0.85); // 85% of peak
        
        // Add some variation for cloud cover
        cloudCover = Math.random() * 30 + 10; // 10-40% cloud cover
      }
      
      data.push({
        time,
        generated: Math.round(generated * 1000) / 1000, // Round to 3 decimal places
        predicted: Math.round(predicted * 1000) / 1000,
        cloudCover: Math.round(cloudCover)
      });
    }
    
    return data;
  };

  // Removed generateMockSolarHistory: not used anymore

  useEffect(() => {
    fetchForecastData();
    fetchHourlyEnergyData();
    const interval = setInterval(() => {
      fetchForecastData();
      fetchHourlyEnergyData();
    }, 300000); // Refresh every 5 minutes
    return () => clearInterval(interval);
  }, [inverterId]);

  // Calculate Y-axis domain when data changes (actuals + forecast only)
  useEffect(() => {
    const mergedData = create24HourData().map(hourData => {
      const hourlyPoint = hourlyEnergy.find(h => h.time === hourData.time);
      const forecastPoint = data.find(f => f.time === hourData.time);
      return {
        time: hourData.time,
        hour: hourData.hour,
        actual: hourlyPoint ? hourlyPoint.solar : 0, // kWh for the hour
        predicted: forecastPoint ? forecastPoint.predicted / 1000 : 0, // Wh -> kWh
        cloudCover: forecastPoint ? forecastPoint.cloudCover : 20,
        generated: hourlyPoint ? hourlyPoint.solar : 0
      };
    });

    setYAxisDomain(calculateYAxisDomain(mergedData));
  }, [data, hourlyEnergy]);

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">PV Generation & Forecast</h3>
        <div className="h-64 flex items-center justify-center">
          <div className="text-gray-500">Loading forecast data...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">PV Generation & Forecast</h3>
        <div className="h-64 flex items-center justify-center">
          <div className="text-red-500">{error}</div>
        </div>
      </div>
    );
  }

  const currentTime = new Date().toLocaleTimeString('en-US', { 
    hour: '2-digit', 
    minute: '2-digit',
    hour12: false 
  });

  const mergedData = create24HourData().map(hourData => {
    const hourlyPoint = hourlyEnergy.find(h => h.time === hourData.time);
    const forecastPoint = data.find(f => f.time === hourData.time);
    return {
      time: hourData.time,
      hour: hourData.hour,
      actual: hourlyPoint ? hourlyPoint.solar : 0, // kWh
      predicted: forecastPoint ? forecastPoint.predicted / 1000 : 0, // kWh
      cloudCover: forecastPoint ? forecastPoint.cloudCover : 20,
      generated: hourlyPoint ? hourlyPoint.solar : 0
    };
  });

  // Calculate totals
  // Use hourly energy data if available, otherwise use API/telemetry/forecast data
  // Actual/generated relies ONLY on hourly energy data
  const totalGenerated = hourlyEnergy.reduce((sum, point) => sum + point.solar, 0);
  // Predicted and cloud cover come from forecast API
  const totalPredicted = data.reduce((sum, point) => sum + point.predicted, 0) / 1000;

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex justify-between items-center mb-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">PV Energy Generation & Forecast</h3>
          <div className="flex items-center space-x-2 text-sm text-gray-600 mt-1">
            <span className={`px-2 py-1 rounded-full text-xs font-medium ${
              hourlyEnergy.length > 0 
                ? 'bg-green-100 text-green-800' 
                : dataSource === 'smart_scheduler' 
                  ? 'bg-blue-100 text-blue-800' 
                  : 'bg-yellow-100 text-yellow-800'
            }`}>
              {hourlyEnergy.length > 0 ? 'Live Data' : dataSource === 'smart_scheduler' ? 'Real Data' : 'Demo Data'}
            </span>
            {hourlyEnergy.length > 0 && (
              <span className="text-green-600">✓ Hourly Energy</span>
            )}
            {dataSource === 'smart_scheduler' && hourlyEnergy.length === 0 && (
              <span className="text-blue-600">✓ Live Forecast</span>
            )}
          </div>
        </div>
        <div className="text-sm text-gray-500">
          <div>Last updated: {new Date().toLocaleTimeString()}</div>
          <div className="text-xs">
            Data source: {hourlyEnergy.length > 0 ? 'Hourly Energy (today)' : 
                        dataSource === 'smart_scheduler' ? 'Smart Scheduler' : 'Mock Forecast'}
          </div>
        </div>
      </div>

      {/* Summary Bar */}
      <div className="mb-6">
        <div className="flex justify-between text-sm mb-2">
          <span className="text-gray-600">Today's Energy Generation</span>
          <span className="font-medium">{totalGenerated.toFixed(2)} kWh / {totalPredicted.toFixed(2)} kWh</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-3">
          <div 
            className="bg-yellow-500 h-3 rounded-full transition-all duration-500"
            style={{ width: `${totalPredicted > 0 ? Math.min(100, (totalGenerated / totalPredicted) * 100) : 0}%` }}
          ></div>
        </div>
        <div className="flex justify-between text-xs text-gray-500 mt-1">
          <span>{totalGenerated.toFixed(2)} kWh Generated</span>
          <span>{Math.max(0, totalPredicted - totalGenerated).toFixed(2)} kWh Remaining</span>
        </div>
      </div>

      {/* Chart */}
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={mergedData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis 
              dataKey="time" 
              stroke="#666"
              fontSize={12}
              tickLine={false}
              axisLine={false}
            />
            <YAxis 
              yAxisId="power"
              orientation="left"
              stroke="#666"
              fontSize={12}
              tickLine={false}
              axisLine={false}
              domain={yAxisDomain}
              tickFormatter={(value) => {
                return `${value.toFixed(1)} kWh`;
              }}
            />
            <YAxis 
              yAxisId="cloud"
              orientation="right"
              stroke="#666"
              fontSize={12}
              tickLine={false}
              axisLine={false}
              domain={[0, 100]}
              tickFormatter={(value) => `${value}%`}
            />
            <Tooltip
              content={({ active, payload, label }) => {
                if (active && payload && payload.length) {
                  return (
                    <div className="bg-white p-3 border border-gray-200 rounded-lg shadow-lg">
                      <p className="font-medium text-gray-900">{label}</p>
                      {payload.map((entry, index) => (
                        <p key={index} className="text-sm" style={{ color: entry.color }}>
                          {entry.name}: {entry.name === 'Cloud Cover' ? `${entry.value}%` : 
                                       entry.name.includes('Energy') || entry.name.includes('Historical') ? `${(entry.value as number).toFixed(2)} kWh` : 
                                       formatPower(entry.value as number)}
                        </p>
                      ))}
                    </div>
                  );
                }
                return null;
              }}
            />
            
            {/* Historical background removed: using only today's actuals and forecast */}
            
            {/* Predicted Energy Area */}
            <Area
              yAxisId="power"
              type="monotone"
              dataKey="predicted"
              stroke="#f59e0b"
              strokeWidth={2}
              fill="#fef3c7"
              fillOpacity={0.3}
              name="Predicted Energy"
            />
            
            {/* Actual Energy Generated Line (from hourly data) */}
            <Line
              yAxisId="power"
              type="monotone"
              dataKey="actual"
              stroke="#10b981"
              strokeWidth={3}
              dot={{ fill: '#10b981', strokeWidth: 2, r: 4 }}
              name="Actual Energy"
            />
            
            {/* Predicted Energy Line */}
            <Line
              yAxisId="power"
              type="monotone"
              dataKey="predicted"
              stroke="#f59e0b"
              strokeWidth={2}
              strokeDasharray="5 5"
              dot={false}
              name="Predicted Energy"
            />
            
            {/* Cloud Cover Line */}
            <Line
              yAxisId="cloud"
              type="monotone"
              dataKey="cloudCover"
              stroke="#9ca3af"
              strokeWidth={1}
              dot={false}
              name="Cloud Cover"
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* Legend */}
      <div className="flex justify-center space-x-6 mt-4 text-sm">
        <div className="flex items-center">
          <div className="w-4 h-3 bg-gray-200 rounded mr-2"></div>
          <span className="text-gray-600">Historical</span>
        </div>
        <div className="flex items-center">
          <div className="w-4 h-0.5 bg-green-500 border-t-2 mr-2"></div>
          <span className="text-gray-600">Actual Energy</span>
        </div>
        <div className="flex items-center">
          <div className="w-4 h-0.5 bg-yellow-500 border-dashed border-t-2 mr-2"></div>
          <span className="text-gray-600">Predicted Energy</span>
        </div>
        <div className="flex items-center">
          <div className="w-4 h-0.5 bg-gray-400 mr-2"></div>
          <span className="text-gray-600">Cloud Cover</span>
        </div>
      </div>
    </div>
  );
};
