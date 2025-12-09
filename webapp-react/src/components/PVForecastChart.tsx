import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, ComposedChart, Legend, ReferenceLine } from 'recharts';
import { api } from '../lib/api';
import { formatPower, formatEnergy } from '../utils/telemetry';
import { Card, CardHeader, CardTitle, CardContent } from './Card';
import { Badge } from './Badge';

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
  arrayId?: string | null;
  telemetry?: any; // TelemetryData from parent component
  date?: string; // Date filter in YYYY-MM-DD format
}

export const PVForecastChart: React.FC<PVForecastChartProps> = ({ inverterId, arrayId, telemetry, date }) => {
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
      if (!arrayId && !inverterId) {
        console.warn('PVForecastChart: No arrayId or inverterId provided, skipping fetch');
        setHourlyEnergy([]);
        return;
      }
      // Support 'all' for aggregated data
      const dateParam = date ? `&date=${date}` : '';
      const url = arrayId 
        ? `/api/arrays/${arrayId}/energy/hourly${date ? `?date=${date}` : ''}`
        : `/api/energy/hourly?inverter_id=${inverterId || 'all'}${dateParam}`;
      const response = await api.get(url) as any;
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
      
      if (!arrayId && !inverterId) {
        console.warn('PVForecastChart: No arrayId or inverterId provided, using mock data');
        setData(generateMockForecastData());
        setDataSource('mock');
        setLoading(false);
        return;
      }
      
      // Try to fetch forecast data from API
      try {
        // Support 'all' for aggregated data
        const dateParam = date ? `&date=${date}` : '';
        const url = arrayId
          ? `/api/arrays/${arrayId}/forecast${date ? `?date=${date}` : ''}`
          : `/api/forecast?inverter_id=${inverterId || 'all'}${dateParam}`;
        const forecastResponse = await api.get(url) as any;
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
  }, [inverterId, arrayId, date]);

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
      <Card className="border-none">
        <CardHeader className="pb-2">
          <CardTitle className="text-base">PV Energy Generation & Forecast</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-64 flex items-center justify-center">
            <div className="text-gray-500">Loading forecast data...</div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="border-none">
        <CardHeader className="pb-2">
          <CardTitle className="text-base">PV Energy Generation & Forecast</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-64 flex items-center justify-center">
            <div className="text-red-500">{error}</div>
          </div>
        </CardContent>
      </Card>
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
    <Card className="border-none">
      <CardHeader className="pb-2">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
          <CardTitle className="text-sm sm:text-base">PV Energy Generation & Forecast</CardTitle>
          <Badge variant="outline" className="gap-1 text-[10px] sm:text-xs">
            <span className="text-base sm:text-lg">☁️</span>
            <span className="hidden sm:inline">Live / Hourly</span>
            <span className="sm:hidden">Live</span>
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="pt-2">
        {/* Chart */}
        <div className="h-48 sm:h-64 w-full overflow-x-auto">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={mergedData} margin={{ left: 8, right: 8, top: 8, bottom: 0 }}>
              <defs>
                <linearGradient id="gActual" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="currentColor" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="currentColor" stopOpacity={0.05} />
                </linearGradient>
                <linearGradient id="gPred" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="currentColor" stopOpacity={0.25} />
                  <stop offset="95%" stopColor="currentColor" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis 
                dataKey="time" 
                tick={{ fontSize: 12 }}
                stroke="#666"
              />
              <YAxis 
                yAxisId="power"
                tick={{ fontSize: 12 }}
                domain={yAxisDomain}
              />
              <YAxis 
                yAxisId="cloud"
                orientation="right"
                tick={{ fontSize: 12 }}
                domain={[0, 100]}
              />
              <Tooltip
                contentStyle={{ 
                  background: 'hsl(var(--card))', 
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '0.5rem'
                }}
              />
              <Legend />
              <ReferenceLine y={0} stroke="#9ca3af" strokeDasharray="3 3" />
              <Area
                yAxisId="power"
                type="monotone"
                dataKey="actual"
                name="Actual kW"
                strokeWidth={2}
                stroke="hsl(var(--primary))"
                fill="url(#gActual)"
              />
              <Area
                yAxisId="power"
                type="monotone"
                dataKey="predicted"
                name="Predicted kW"
                strokeWidth={2}
                stroke="hsl(var(--secondary-foreground))"
                fill="url(#gPred)"
              />
              <Line
                yAxisId="cloud"
                type="monotone"
                dataKey="cloudCover"
                name="Cloud %"
                stroke="hsl(var(--muted-foreground))"
                dot={false}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>

      </CardContent>
    </Card>
  );
};
