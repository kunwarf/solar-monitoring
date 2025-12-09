import React, { useState, useEffect } from 'react';
import { TelemetryData } from '../types/telemetry';
import { SelfSufficiencyBar } from './SelfSufficiencyBar';
import { formatEnergy } from '../utils/telemetry';
import { api } from '../lib/api';

interface EnergyStatsTilesProps {
  telemetry: TelemetryData | null;
  inverterId?: string;
}

interface DailyEnergyData {
  solar_energy_kwh: number;
  load_energy_kwh: number;
  battery_charge_energy_kwh: number;
  battery_discharge_energy_kwh: number;
  grid_import_energy_kwh: number;
  grid_export_energy_kwh: number;
}

interface EnergyStat {
  title: string;
  value: string;
  icon: React.ReactNode;
  color: string;
  bgColor: string;
  description: string;
}

export const EnergyStatsTiles: React.FC<EnergyStatsTilesProps> = ({ telemetry, inverterId = 'senergy1' }) => {
  const [dailyEnergyData, setDailyEnergyData] = useState<DailyEnergyData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const [isUpdating, setIsUpdating] = useState(false);

  // Manual refresh function
  const refreshData = async () => {
    try {
      setIsUpdating(true);
      const response = await api.get(`/api/now?inverter_id=${inverterId}`);
      const data = response as any;
      if (data && data.now) {
        const nowData = data.now;
        setDailyEnergyData({
          solar_energy_kwh: nowData.today_energy || 0,
          load_energy_kwh: nowData.today_load_energy || 0,
          battery_charge_energy_kwh: nowData.today_battery_charge_energy || 0,
          battery_discharge_energy_kwh: nowData.today_battery_discharge_energy || 0,
          grid_import_energy_kwh: nowData.today_import_energy || 0,
          grid_export_energy_kwh: nowData.today_export_energy || 0,
        });
        setLastUpdate(new Date());
      }
    } catch (err) {
      console.warn('Failed to refresh daily energy data:', err);
    } finally {
      setIsUpdating(false);
    }
  };

  // Fetch real daily energy data from API
  useEffect(() => {
    const fetchDailyEnergyData = async () => {
      try {
        setLoading(true);
        setError(null);
        
        const response = await api.get(`/api/now?inverter_id=${inverterId}`);
        const data = response as any;
        if (data && data.now) {
          const nowData = data.now;
          setDailyEnergyData({
            solar_energy_kwh: nowData.today_energy || 0,
            load_energy_kwh: nowData.today_load_energy || 0,
            battery_charge_energy_kwh: nowData.today_battery_charge_energy || 0,
            battery_discharge_energy_kwh: nowData.today_battery_discharge_energy || 0,
            grid_import_energy_kwh: nowData.today_import_energy || 0,
            grid_export_energy_kwh: nowData.today_export_energy || 0,
          });
          setLastUpdate(new Date());
        }
      } catch (err) {
        console.warn('Failed to fetch daily energy data:', err);
        setError('Failed to load energy data');
        // Fallback to telemetry data if available
        if (telemetry) {
          setDailyEnergyData({
            solar_energy_kwh: telemetry.today_energy || 0,
            load_energy_kwh: telemetry.today_load_energy || 0,
            battery_charge_energy_kwh: (telemetry as any)?.today_battery_charge_energy || 0,
            battery_discharge_energy_kwh: (telemetry as any)?.today_battery_discharge_energy || 0,
            grid_import_energy_kwh: telemetry.today_import_energy || 0,
            grid_export_energy_kwh: telemetry.today_export_energy || 0,
          });
        }
      } finally {
        setLoading(false);
      }
    };

    fetchDailyEnergyData();
  }, []); // Remove telemetry dependency to prevent flickering

  // Add periodic refresh every 5 seconds for near real-time updates without flickering
  useEffect(() => {
    const interval = setInterval(() => {
      const fetchDailyEnergyData = async () => {
        try {
          setIsUpdating(true);
          const response = await api.get(`/api/now?inverter_id=${inverterId}`);
          const data = response as any;
          if (data && data.now) {
            const nowData = data.now;
            setDailyEnergyData(prevData => {
              // Only update if data has actually changed to prevent unnecessary re-renders
              const newData = {
                solar_energy_kwh: nowData.today_energy || 0,
                load_energy_kwh: nowData.today_load_energy || 0,
                battery_charge_energy_kwh: nowData.today_battery_charge_energy || 0,
                battery_discharge_energy_kwh: nowData.today_battery_discharge_energy || 0,
                grid_import_energy_kwh: nowData.today_import_energy || 0,
                grid_export_energy_kwh: nowData.today_export_energy || 0,
              };
              
              // Check if data has changed
              if (!prevData || 
                  prevData.solar_energy_kwh !== newData.solar_energy_kwh ||
                  prevData.load_energy_kwh !== newData.load_energy_kwh ||
                  prevData.battery_charge_energy_kwh !== newData.battery_charge_energy_kwh ||
                  prevData.battery_discharge_energy_kwh !== newData.battery_discharge_energy_kwh ||
                  prevData.grid_import_energy_kwh !== newData.grid_import_energy_kwh ||
                  prevData.grid_export_energy_kwh !== newData.grid_export_energy_kwh) {
                setLastUpdate(new Date());
                return newData;
              }
              
              return prevData; // No change, don't update
            });
          }
        } catch (err) {
          console.warn('Failed to refresh daily energy data:', err);
        } finally {
          setIsUpdating(false);
        }
      };
      fetchDailyEnergyData();
    }, 5 * 1000); // 5 seconds for near real-time updates

    return () => clearInterval(interval);
  }, []);

  // Calculate energy statistics from real data
  const getEnergyStats = (): EnergyStat[] => {
    if (!dailyEnergyData && !telemetry) {
      return [];
    }

    const energyData = dailyEnergyData || {
      solar_energy_kwh: telemetry?.today_energy || 0,
      load_energy_kwh: telemetry?.today_load_energy || 0,
      battery_charge_energy_kwh: (telemetry as any)?.today_battery_charge_energy || 0,
      battery_discharge_energy_kwh: (telemetry as any)?.today_battery_discharge_energy || 0,
      grid_import_energy_kwh: telemetry?.today_import_energy || 0,
      grid_export_energy_kwh: telemetry?.today_export_energy || 0,
    };

    // Calculate total load energy: today_load_energy + daily_energy_to_eps (if available)
    const totalLoadEnergy = energyData.load_energy_kwh + ((telemetry as any)?.daily_energy_to_eps || 0);

    const stats: EnergyStat[] = [
      {
        title: "Total Load Energy",
        value: formatEnergy(totalLoadEnergy),
        icon: (
          <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center">
            <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
        ),
        color: "text-blue-600",
        bgColor: "bg-blue-50",
        description: "Energy consumed today"
      },
      {
        title: "Solar Generation",
        value: formatEnergy(energyData.solar_energy_kwh),
        icon: (
          <div className="w-12 h-12 bg-yellow-100 rounded-xl flex items-center justify-center">
            <svg className="w-6 h-6 text-yellow-600" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
            </svg>
          </div>
        ),
        color: "text-yellow-600",
        bgColor: "bg-yellow-50",
        description: "Total solar energy generated"
      },
      {
        title: "Battery Charge",
        value: formatEnergy(energyData.battery_charge_energy_kwh),
        icon: (
          <div className="w-12 h-12 bg-green-100 rounded-xl flex items-center justify-center">
            <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
            </svg>
          </div>
        ),
        color: "text-green-600",
        bgColor: "bg-green-50",
        description: "Energy charged to battery"
      },
      {
        title: "Battery Discharge",
        value: formatEnergy(energyData.battery_discharge_energy_kwh),
        icon: (
          <div className="w-12 h-12 bg-red-100 rounded-xl flex items-center justify-center">
            <svg className="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
            </svg>
          </div>
        ),
        color: "text-red-600",
        bgColor: "bg-red-50",
        description: "Energy discharged from battery"
      },
      {
        title: "Grid Import",
        value: formatEnergy(energyData.grid_import_energy_kwh),
        icon: (
          <div className="w-12 h-12 bg-orange-100 rounded-xl flex items-center justify-center">
            <svg className="w-6 h-6 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16l-4-4m0 0l4-4m-4 4h18" />
            </svg>
          </div>
        ),
        color: "text-orange-600",
        bgColor: "bg-orange-50",
        description: "Energy imported from grid"
      },
      {
        title: "Grid Export",
        value: formatEnergy(energyData.grid_export_energy_kwh),
        icon: (
          <div className="w-12 h-12 bg-purple-100 rounded-xl flex items-center justify-center">
            <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
            </svg>
          </div>
        ),
        color: "text-purple-600",
        bgColor: "bg-purple-50",
        description: "Energy exported to grid"
      }
    ];

    return stats;
  };


  const energyStats = getEnergyStats();

  if (loading) {
    return (
      <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
        <h3 className="text-xl font-semibold text-gray-900 mb-6">Today's Energy Statistics</h3>
        <div className="text-center text-gray-500 py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
          Loading energy statistics...
        </div>
      </div>
    );
  }

  if (error && !dailyEnergyData) {
    return (
      <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
        <h3 className="text-xl font-semibold text-gray-900 mb-6">Today's Energy Statistics</h3>
        <div className="text-center text-red-500 py-8">
          <div className="text-red-500 mb-2">⚠️</div>
          {error}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
      <div className="flex justify-between items-center mb-6">
        <h3 className="text-xl font-semibold text-gray-900">Today's Energy Statistics</h3>
        <div className="flex items-center space-x-3 text-sm text-gray-500">
          <button
            onClick={refreshData}
            disabled={isUpdating}
            className="flex items-center space-x-1 px-2 py-1 rounded-md hover:bg-gray-100 transition-colors disabled:opacity-50"
            title="Refresh data"
          >
            <svg 
              className={`w-4 h-4 ${isUpdating ? 'animate-spin' : ''}`} 
              fill="none" 
              stroke="currentColor" 
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            <span>Refresh</span>
          </button>
          {isUpdating && (
            <div className="flex items-center space-x-1">
              <div className="animate-spin rounded-full h-3 w-3 border-b border-blue-600"></div>
              <span>Updating...</span>
            </div>
          )}
          <span>Last updated: {lastUpdate.toLocaleTimeString()}</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {energyStats.map((stat, index) => (
          <div
            key={index}
            className={`${stat.bgColor} rounded-xl p-6 border border-gray-100 hover:shadow-md transition-shadow duration-200`}
          >
            <div className="flex items-start justify-between mb-4">
              <div className="flex-1">
                <h4 className="text-sm font-medium text-gray-600 mb-1">{stat.title}</h4>
                <p className={`text-2xl font-bold ${stat.color} mb-2`}>
                  {stat.value}
                </p>
                <p className="text-xs text-gray-500">{stat.description}</p>
              </div>
              <div className="ml-4">
                {stat.icon}
              </div>
            </div>
            
            {/* Progress bar for visual representation */}
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div 
                className={`h-2 rounded-full transition-all duration-1000 ease-out ${
                  stat.color.includes('blue') ? 'bg-blue-500' :
                  stat.color.includes('yellow') ? 'bg-yellow-500' :
                  stat.color.includes('green') ? 'bg-green-500' :
                  stat.color.includes('red') ? 'bg-red-500' :
                  stat.color.includes('orange') ? 'bg-orange-500' :
                  'bg-purple-500'
                }`}
                style={{ 
                  width: `${Math.min(100, Math.max(2, (parseFloat(stat.value.replace(/[^\d.-]/g, '')) / 30) * 100))}%` 
                }}
              ></div>
            </div>
          </div>
        ))}
      </div>

      {/* Summary Section */}
      <div className="mt-8 pt-6 border-t border-gray-100">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="text-center">
            <div className="text-lg font-semibold text-gray-900">
              {formatEnergy((telemetry?.today_energy || 0) - (telemetry?.today_load_energy || 0))}
            </div>
            <div className="text-sm text-gray-500">Net Energy Balance</div>
          </div>
          <div className="text-center">
            <div className="text-lg font-semibold text-gray-900">
              {formatEnergy((telemetry?.today_export_energy || 0) - (telemetry?.today_import_energy || 0))}
            </div>
            <div className="text-sm text-gray-500">Grid Net Export</div>
          </div>
        </div>
        
        {/* Self-Sufficiency Bar */}
        <div className="mt-6">
          {telemetry && <SelfSufficiencyBar telemetry={telemetry} dailyEnergyData={dailyEnergyData} />}
        </div>
      </div>
    </div>
  );
};
