import React from 'react';
import { useNavigate } from 'react-router-dom';
import { TelemetryData } from '../types/telemetry';
import { formatEnergy } from '../utils/telemetry';

interface EnergyDistributionDiagramProps {
  telemetry: TelemetryData;
}

export const EnergyDistributionDiagram: React.FC<EnergyDistributionDiagramProps> = ({ telemetry }) => {
  const navigate = useNavigate();
  const pvPower = telemetry.pv_power_w || 0;
  const loadPower = telemetry.load_power_w || 0;
  const batteryPower = telemetry.batt_power_w || 0;
  const gridPower = telemetry.grid_power_w || 0;

  // Calculate daily energy values (using today's energy data from API)
  const solarEnergy = telemetry.today_energy || 0; // kWh
  const loadEnergy = telemetry.today_load_energy || 0; // kWh
  const gridImportEnergy = telemetry.today_import_energy || 0; // kWh
  const gridExportEnergy = telemetry.today_export_energy || 0; // kWh
  
  // Estimate battery energy (simplified calculation)
  const batteryChargeEnergy = batteryPower > 0 ? (batteryPower * 0.1) / 1000 : 0; // Rough estimate
  const batteryDischargeEnergy = batteryPower < 0 ? (Math.abs(batteryPower) * 0.1) / 1000 : 0; // Rough estimate

  return (
    <div className="bg-gray-800 rounded-xl p-8 min-h-[500px] relative overflow-hidden">
      {/* Title */}
      <div className="text-white text-xl font-semibold mb-8">Energy distribution today</div>
      
      {/* Flow Lines - SVG Background (rendered first so it's behind clickable elements) */}
      <svg className="absolute inset-0 w-full h-full pointer-events-none z-0">
        {/* Solar to Center */}
        <path
          d="M 50% 80 L 50% 50%"
          stroke="#f97316"
          strokeWidth="3"
          fill="none"
          className="drop-shadow-sm"
        />
        
        {/* Solar to Grid (Purple) */}
        <path
          d="M 50% 80 Q 30% 60% 80 50%"
          stroke="#a855f7"
          strokeWidth="3"
          fill="none"
          className="drop-shadow-sm"
        />
        
        {/* Solar to Battery (Pink) */}
        <path
          d="M 50% 80 Q 70% 60% 50% 420"
          stroke="#ec4899"
          strokeWidth="3"
          fill="none"
          className="drop-shadow-sm"
        />
        
        {/* Center to Home (Light Blue) */}
        <path
          d="M 50% 50% Q 70% 50% 420 50%"
          stroke="#60a5fa"
          strokeWidth="3"
          fill="none"
          className="drop-shadow-sm"
        />
        <circle cx="calc(50% + 50px)" cy="50%" r="3" fill="#60a5fa" className="drop-shadow-sm" />
        
        {/* Center to Grid (Light Blue) */}
        <path
          d="M 50% 50% Q 30% 50% 80 50%"
          stroke="#60a5fa"
          strokeWidth="3"
          fill="none"
          className="drop-shadow-sm"
        />
        <circle cx="calc(50% - 50px)" cy="50%" r="3" fill="#a855f7" className="drop-shadow-sm" />
        
        {/* Center to Battery (Pink) */}
        <path
          d="M 50% 50% Q 50% 70% 50% 420"
          stroke="#ec4899"
          strokeWidth="3"
          fill="none"
          className="drop-shadow-sm"
        />
        <circle cx="50%" cy="calc(50% + 50px)" r="3" fill="#ec4899" className="drop-shadow-sm" />
        
        {/* Grid to Center (White) */}
        <path
          d="M 80 50% Q 30% 50% 50% 50%"
          stroke="#ffffff"
          strokeWidth="2"
          fill="none"
          className="drop-shadow-sm"
        />
        
        {/* Battery to Center (White) */}
        <path
          d="M 50% 420 Q 50% 70% 50% 50%"
          stroke="#ffffff"
          strokeWidth="2"
          fill="none"
          className="drop-shadow-sm"
        />
      </svg>
      
      {/* Central Hub (Inverter) - Clickable */}
      <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 z-10">
        <div 
          className="w-20 h-20 bg-blue-600 rounded-full border-4 border-blue-400 flex items-center justify-center shadow-lg cursor-pointer hover:bg-blue-700 transition-colors"
          onClick={() => navigate('/telemetry')}
          title="Click to view inverter telemetry"
        >
          <div className="text-white text-2xl">⚡</div>
        </div>
        <div className="text-white text-sm mt-2 text-center">Inverter</div>
      </div>

      {/* Solar Node (Top) */}
      <div className="absolute top-8 left-1/2 transform -translate-x-1/2 z-10">
        <div className="text-center">
          <div className="text-white text-sm mb-2">Solar</div>
          <div className="w-20 h-20 bg-orange-500 rounded-full border-4 border-orange-400 flex items-center justify-center shadow-lg">
            <div className="text-white text-2xl">⚡</div>
          </div>
          <div className="text-white text-lg font-bold mt-2">{formatEnergy(solarEnergy)}</div>
        </div>
      </div>

      {/* Grid Node (Left) */}
      <div className="absolute top-1/2 left-8 transform -translate-y-1/2 z-10">
        <div className="text-center">
          <div 
            className="w-20 h-20 bg-blue-500 rounded-full border-4 border-blue-400 flex items-center justify-center shadow-lg cursor-pointer hover:bg-blue-600 transition-colors"
            onClick={() => navigate('/grid-detail')}
            title="Click to view grid details"
          >
            <div className="text-white text-2xl">🏭</div>
          </div>
          <div className="text-white text-lg font-bold mt-2">
            <div className="text-sm">← {formatEnergy(gridImportEnergy)}</div>
            <div className="text-sm">→ {formatEnergy(gridExportEnergy)}</div>
          </div>
          <div className="text-white text-sm mt-2">Grid</div>
        </div>
      </div>

      {/* Home Node (Right) */}
      <div className="absolute top-1/2 right-8 transform -translate-y-1/2 z-10">
        <div className="text-center">
          <div className="w-20 h-20 bg-orange-500 rounded-full border-4 border-orange-400 flex items-center justify-center shadow-lg relative">
            <div className="text-white text-2xl">🏠</div>
            {/* Partial fill indicator */}
            <div className="absolute inset-0 rounded-full border-4 border-blue-400 border-r-0 border-b-0 transform rotate-45"></div>
          </div>
          <div className="text-white text-lg font-bold mt-2">{formatEnergy(loadEnergy)}</div>
          <div className="text-white text-sm mt-2">Home</div>
        </div>
      </div>

      {/* Battery Node (Bottom) */}
      <div className="absolute bottom-8 left-1/2 transform -translate-x-1/2 z-10">
        <div className="text-center">
          <div className="text-white text-sm mb-2">Battery</div>
          <div className="w-20 h-20 bg-pink-500 rounded-full border-4 border-pink-400 flex items-center justify-center shadow-lg">
            <div className="text-white text-2xl">🔋</div>
          </div>
          <div className="text-white text-lg font-bold mt-2">
            <div className="text-sm">↓ {formatEnergy(batteryDischargeEnergy)}</div>
            <div className="text-sm">↑ {formatEnergy(batteryChargeEnergy)}</div>
          </div>
        </div>
      </div>

      {/* Flow Lines */}
      
      {/* Solar to Center (Orange) */}
      <svg className="absolute inset-0 w-full h-full pointer-events-none">
        {/* Solar to Center */}
        <path
          d="M 50% 80 L 50% 50%"
          stroke="#f97316"
          strokeWidth="3"
          fill="none"
          className="drop-shadow-sm"
        />
        
        {/* Solar to Grid (Purple) */}
        <path
          d="M 50% 80 Q 30% 60% 80 50%"
          stroke="#a855f7"
          strokeWidth="3"
          fill="none"
          className="drop-shadow-sm"
        />
        
        {/* Solar to Battery (Pink) */}
        <path
          d="M 50% 80 Q 70% 60% 50% 420"
          stroke="#ec4899"
          strokeWidth="3"
          fill="none"
          className="drop-shadow-sm"
        />
        
        {/* Center to Home (Light Blue) */}
        <path
          d="M 50% 50% Q 70% 50% 420 50%"
          stroke="#60a5fa"
          strokeWidth="3"
          fill="none"
          className="drop-shadow-sm"
        />
        <circle cx="calc(50% + 50px)" cy="50%" r="3" fill="#60a5fa" className="drop-shadow-sm" />
        
        {/* Center to Grid (Light Blue) */}
        <path
          d="M 50% 50% Q 30% 50% 80 50%"
          stroke="#60a5fa"
          strokeWidth="3"
          fill="none"
          className="drop-shadow-sm"
        />
        <circle cx="calc(50% - 50px)" cy="50%" r="3" fill="#a855f7" className="drop-shadow-sm" />
        
        {/* Center to Battery (Pink) */}
        <path
          d="M 50% 50% Q 50% 70% 50% 420"
          stroke="#ec4899"
          strokeWidth="3"
          fill="none"
          className="drop-shadow-sm"
        />
        <circle cx="50%" cy="calc(50% + 50px)" r="3" fill="#ec4899" className="drop-shadow-sm" />
        
        {/* Grid to Center (White) */}
        <path
          d="M 80 50% Q 30% 50% 50% 50%"
          stroke="#ffffff"
          strokeWidth="2"
          fill="none"
          className="drop-shadow-sm"
        />
        
        {/* Battery to Center (White) */}
        <path
          d="M 50% 420 Q 50% 70% 50% 50%"
          stroke="#ffffff"
          strokeWidth="2"
          fill="none"
          className="drop-shadow-sm"
        />
      </svg>

      {/* Energy Flow Labels */}
      <div className="absolute top-32 left-1/2 transform -translate-x-1/2">
        <div className="text-orange-400 text-xs font-semibold">Solar Generation</div>
      </div>
      
      <div className="absolute top-1/2 left-32 transform -translate-y-1/2">
        <div className="text-blue-400 text-xs font-semibold">Grid Exchange</div>
      </div>
      
      <div className="absolute top-1/2 right-32 transform -translate-y-1/2">
        <div className="text-blue-400 text-xs font-semibold">Home Consumption</div>
      </div>
      
      <div className="absolute bottom-32 left-1/2 transform -translate-x-1/2">
        <div className="text-pink-400 text-xs font-semibold">Battery Storage</div>
      </div>

      {/* Summary Stats */}
      <div className="absolute bottom-4 left-4 right-4">
        <div className="bg-gray-700 rounded-lg p-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
            <div>
              <div className="text-orange-400 text-sm font-semibold">Solar</div>
              <div className="text-white text-lg font-bold">{formatEnergy(solarEnergy)}</div>
            </div>
            <div>
              <div className="text-blue-400 text-sm font-semibold">Grid Net</div>
              <div className="text-white text-lg font-bold">{formatEnergy(gridExportEnergy - gridImportEnergy)}</div>
            </div>
            <div>
              <div className="text-pink-400 text-sm font-semibold">Battery Net</div>
              <div className="text-white text-lg font-bold">{formatEnergy(batteryDischargeEnergy - batteryChargeEnergy)}</div>
            </div>
            <div>
              <div className="text-green-400 text-sm font-semibold">Self-Sufficiency</div>
              <div className="text-white text-lg font-bold">
                {(() => {
                  if (loadEnergy === 0) return 0;
                  const selfSufficiency = Math.max(0, Math.min(100, ((loadEnergy - gridImportEnergy) / loadEnergy) * 100));
                  return Math.round(selfSufficiency);
                })()}%
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
