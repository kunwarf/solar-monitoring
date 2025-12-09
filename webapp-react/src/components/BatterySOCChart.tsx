import React from 'react';
import { TelemetryData } from '../types/telemetry';
import { formatPercentage, getSOCColor } from '../utils/telemetry';

interface BatterySOCChartProps {
  telemetry: TelemetryData;
  inverterId?: string;
}

export const BatterySOCChart: React.FC<BatterySOCChartProps> = ({ telemetry, inverterId = 'senergy1' }) => {
  const soc = telemetry?.batt_soc_pct || 0;
  const socColor = getSOCColor(soc);
  
  // Determine SOC status
  const getSOCStatus = (soc: number) => {
    if (soc >= 80) return { text: 'Excellent', color: 'text-green-600', bgColor: 'bg-green-50' };
    if (soc >= 50) return { text: 'Good', color: 'text-yellow-600', bgColor: 'bg-yellow-50' };
    if (soc >= 20) return { text: 'Low', color: 'text-orange-600', bgColor: 'bg-orange-50' };
    return { text: 'Critical', color: 'text-red-600', bgColor: 'bg-red-50' };
  };

  const status = getSOCStatus(soc);

  // Get SOC color for the progress bar
  const getSOCBarColor = (soc: number) => {
    if (soc >= 80) return 'bg-green-500';
    if (soc >= 50) return 'bg-yellow-500';
    if (soc >= 20) return 'bg-orange-500';
    return 'bg-red-500';
  };

  const barColor = getSOCBarColor(soc);

  // Calculate estimated runtime
  const getEstimatedRuntime = () => {
    const power = Math.abs(telemetry?.batt_power_w || 0);
    const capacity = (soc / 100) * 18; // Assuming 18kWh battery capacity
    
    if (power === 0) return 'Standby';
    const hours = capacity / (power / 1000);
    
    if (hours > 24) return `${Math.floor(hours / 24)}d ${Math.floor(hours % 24)}h`;
    if (hours >= 1) return `${hours.toFixed(1)}h`;
    return `${(hours * 60).toFixed(0)}m`;
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-gray-900">
          Battery Status {inverterId === 'all' ? '(All Inverters)' : ''}
        </h3>
        <div className={`text-sm px-3 py-1 rounded-full ${status.color} ${status.bgColor}`}>
          {status.text}
        </div>
      </div>
      
      {/* SOC Progress Bar */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-3">
          <h4 className="text-lg font-semibold text-gray-800">Battery State of Charge</h4>
          <div className="text-2xl font-bold text-gray-800">
            {formatPercentage(soc)}
          </div>
        </div>
        
        {/* Progress Bar Container */}
        <div className="relative">
          <div className="w-full bg-gray-200 rounded-full h-8 overflow-hidden">
            <div 
              className={`h-full ${barColor} transition-all duration-500 ease-out rounded-full`}
              style={{ width: `${Math.min(100, Math.max(0, soc))}%` }}
            />
          </div>
          
          {/* SOC Level Markers */}
          <div className="flex justify-between mt-2 text-xs text-gray-500">
            <span>0%</span>
            <span>25%</span>
            <span>50%</span>
            <span>75%</span>
            <span>100%</span>
          </div>
        </div>
      </div>
      
      {/* Detailed Information Below */}
      <div className="space-y-6">
        {/* Primary Battery Metrics */}
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-xl p-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-2xl font-bold text-blue-800">
                  {telemetry?.batt_voltage_v ? `${telemetry.batt_voltage_v.toFixed(1)}V` : 'N/A'}
                </div>
                <div className="text-sm text-blue-600 mt-1">Voltage</div>
              </div>
              <div className="text-2xl">⚡</div>
            </div>
          </div>
          
          <div className="bg-gradient-to-br from-green-50 to-green-100 rounded-xl p-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-2xl font-bold text-green-800">
                  {telemetry?.batt_current_a ? `${Math.abs(telemetry.batt_current_a).toFixed(1)}A` : 'N/A'}
                </div>
                <div className="text-sm text-green-600 mt-1">Current</div>
              </div>
              <div className="text-2xl">🔋</div>
            </div>
          </div>
        </div>

        {/* Secondary Battery Metrics */}
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-xl p-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-2xl font-bold text-purple-800">
                  {telemetry?.batt_power_w ? `${Math.abs(telemetry.batt_power_w).toFixed(0)}W` : 'N/A'}
                </div>
                <div className="text-sm text-purple-600 mt-1">Power</div>
              </div>
              <div className="text-2xl">⚡</div>
            </div>
          </div>
          
          <div className="bg-gradient-to-br from-orange-50 to-orange-100 rounded-xl p-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-2xl font-bold text-orange-800">
                  {telemetry?.batt_temp_c ? `${telemetry.batt_temp_c.toFixed(1)}°C` : 'N/A'}
                </div>
                <div className="text-sm text-orange-600 mt-1">Temperature</div>
              </div>
              <div className="text-2xl">🌡️</div>
            </div>
          </div>
        </div>

        {/* Battery Status and Runtime */}
        <div className="grid grid-cols-2 gap-4">
          <div className={`${status.bgColor} rounded-xl p-4`}>
            <div className="flex items-center justify-between">
              <div>
                <div className={`text-lg font-semibold ${status.color}`}>
                  {status.text}
                </div>
                <div className="text-sm text-gray-600 mt-1">Status</div>
              </div>
              <div className="text-2xl">
                {soc >= 80 && "🔋"}
                {soc >= 50 && soc < 80 && "⚡"}
                {soc >= 20 && soc < 50 && "⚠️"}
                {soc < 20 && "🚨"}
              </div>
            </div>
          </div>
          
          <div className="bg-gradient-to-br from-indigo-50 to-indigo-100 rounded-xl p-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-lg font-bold text-indigo-800">
                  {getEstimatedRuntime()}
                </div>
                <div className="text-sm text-indigo-600 mt-1">Est. Runtime</div>
              </div>
              <div className="text-2xl">⏱️</div>
            </div>
          </div>
        </div>
        
        {/* Status Description */}
        <div className={`${status.bgColor} rounded-xl p-4`}>
          <div className={`text-sm ${status.color} font-medium`}>
            {soc >= 80 && "🔋 Well charged and ready for use - optimal performance"}
            {soc >= 50 && soc < 80 && "⚡ Good charge level, optimal for daily use"}
            {soc >= 20 && soc < 50 && "⚠️ Charge getting low, consider charging soon"}
            {soc < 20 && "🚨 Critically low - immediate charge needed"}
          </div>
        </div>
      </div>
    </div>
  );
};
