import React from 'react';
import { TelemetryData } from '../types/telemetry';
import { formatPower, formatEnergy, formatPercentage, formatVoltage, formatCurrent, formatTemperature } from '../utils/telemetry';
import GridNormalIcon from '../assets/grid-normal.svg';
import GridFaultIcon from '../assets/grid-fault.svg';
import GridOffIcon from '../assets/grid-off.svg';
import InverterNormalIcon from '../assets/inverter-normal.svg';
import InverterFaultIcon from '../assets/inverter-fault.svg';
import InverterOffIcon from '../assets/inverter-off.svg';

interface PowerFlowDiagramProps {
  telemetry: TelemetryData;
}

export const PowerFlowDiagram: React.FC<PowerFlowDiagramProps> = ({ telemetry }) => {
  const pvPower = telemetry.pv_power_w || 0;
  const loadPower = telemetry.load_power_w || 0;
  const batteryPower = telemetry.batt_power_w || 0;
  const gridPower = telemetry.grid_power_w || 0;

  // Determine power flow directions and states
  const isBatteryCharging = batteryPower > 0;
  const isBatteryDischarging = batteryPower < 0;
  const isGridExporting = gridPower < 0;
  const isGridImporting = gridPower > 0;

  // Grid status (normal, fault, off)
  const gridStatus: 'normal' | 'fault' | 'off' = (() => {
    const gridFault = (telemetry as any)?.grid_fault;
    const offGrid = telemetry?.off_grid_mode && telemetry.off_grid_mode !== 0;
    const noActivity = Math.abs(gridPower) < 1 && (telemetry?.today_import_energy ?? 0) === 0 && (telemetry?.today_export_energy ?? 0) === 0;
    if (gridFault || ((telemetry?.error_code ?? 0) !== 0 && !offGrid)) return 'fault';
    if (offGrid || noActivity) return 'off';
    return 'normal';
  })();
  const gridIcon = gridStatus === 'fault' ? GridFaultIcon : gridStatus === 'off' ? GridOffIcon : GridNormalIcon;

  // Inverter status (normal, fault, off)
  const inverterStatus: 'normal' | 'fault' | 'off' = (() => {
    const err = telemetry?.error_code ?? 0;
    const mode = (telemetry?.inverter_mode || '').toLowerCase();
    if (err && err !== 0) return 'fault';
    if (['off', 'offline', 'standby'].includes(mode)) return 'off';
    return 'normal';
  })();
  const inverterIcon = inverterStatus === 'fault' ? InverterFaultIcon : inverterStatus === 'off' ? InverterOffIcon : InverterNormalIcon;

  const getEstimatedRuntime = () => {
    const soc = telemetry?.batt_soc_pct || 0;
    const power = Math.abs(telemetry?.batt_power_w || 0);
    const capacityKwh = (soc / 100) * 18; // assume 18 kWh pack
    if (power === 0) return 'Standby';
    const hours = capacityKwh / (power / 1000);
    if (hours > 24) return `${Math.floor(hours / 24)}d ${Math.floor(hours % 24)}h`;
    if (hours >= 1) return `${hours.toFixed(1)}h`;
    return `${(hours * 60).toFixed(0)}m`;
  };

  // Calculate power flow intensity for visual representation
  const getFlowIntensity = (power: number) => {
    const absPower = Math.abs(power);
    if (absPower === 0) return 'w-0';
    if (absPower < 100) return 'w-1';
    if (absPower < 500) return 'w-2';
    if (absPower < 1000) return 'w-3';
    if (absPower < 2000) return 'w-4';
    return 'w-6';
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold mb-6">System Overview</h3>
      
      {/* Main Power Flow Diagram */}
      <div className="relative bg-gradient-to-br from-gray-50 to-gray-100 rounded-xl p-4 sm:p-6 md:p-10 min-h-[460px] sm:min-h-[560px] md:min-h-[700px] overflow-hidden min-w-0">
        {/* Animated flow lines (SVG overlay) */}
        <style>
          {`
            @keyframes flow-dash { to { stroke-dashoffset: -24; } }
            @keyframes flow-dash-rev { to { stroke-dashoffset: 24; } }
          `}
        </style>
        <svg className="absolute inset-0 w-full h-full z-0 pointer-events-none" preserveAspectRatio="none">
          {(() => {
            const strokeWidthFor = (power: number) => {
              const p = Math.abs(power);
              if (p < 100) return 2;
              if (p < 500) return 3;
              if (p < 1000) return 4;
              if (p < 2000) return 5;
              return 6;
            };
            const line = (
              x1: number,
              y1: number,
              x2: number,
              y2: number,
              color: string,
              width: number,
              reverse = false
            ) => (
              <line
                x1={`${x1}%`}
                y1={`${y1}%`}
                x2={`${x2}%`}
                y2={`${y2}%`}
                stroke={color}
                strokeWidth={width}
                strokeLinecap="round"
                strokeDasharray="8 6"
                style={{ animation: `${reverse ? 'flow-dash-rev' : 'flow-dash'} 1.2s linear infinite` }}
              />
            );
            const staticLine = (
              x1: number,
              y1: number,
              x2: number,
              y2: number,
              color = '#d1d5db',
              width = 2
            ) => (
              <line
                x1={`${x1}%`}
                y1={`${y1}%`}
                x2={`${x2}%`}
                y2={`${y2}%`}
                stroke={color}
                strokeWidth={width}
                strokeLinecap="round"
                strokeDasharray="6 8"
              />
            );

            const elementsY = {
              solar: 12,
              inverter: 45,
              battery: 78,
              load: 45,
              grid: 45,
            };
            const elementsX = {
              center: 50,
              battery: 50,
              load: 90,
              grid: 10,
              solar: 50,
              inverter: 50,
            };

            // Shorten lines so they don't cross icons
            const gridLineX = 16; // stop before grid icon center (12%)
            const inverterLineXForGrid = 46; // stop before inverter icon center (50%)
            const invToBattStartY = 50; // a bit below inverter center (45%)
            const invToBattEndY = 72;   // a bit above battery center (78%)

            const paths: JSX.Element[] = [];
            const addLabel = (
              x1: number,
              y1: number,
              x2: number,
              y2: number,
              text: string,
              color: string,
              yOffset: number = -2
            ) => {
              const mx = (x1 + x2) / 2;
              const my = (y1 + y2) / 2 + yOffset; // adjustable vertical offset from the line
              paths.push(
                <text
                  x={`${mx}%`}
                  y={`${my}%`}
                  textAnchor="middle"
                  alignmentBaseline="middle"
                  fill={color}
                  fontSize="13"
                  fontWeight={600}
                  stroke="#ffffff"
                  strokeWidth={3}
                  paintOrder="stroke"
                >
                  {text}
                </text>
              );
            };

            // Shortened endpoints for Solar ↔ Inverter to avoid icon overlap
            const solarLineStartY = 18; // slightly lower to avoid overlapping solar icon
            const inverterLineEndYSolar = 40; // keep proportion by moving a bit lower
            paths.push(staticLine(elementsX.solar, solarLineStartY, elementsX.inverter, inverterLineEndYSolar));
            if (pvPower > 1) {
              paths.push(line(
                elementsX.solar,
                solarLineStartY,
                elementsX.inverter,
                inverterLineEndYSolar,
                '#f59e0b',
                strokeWidthFor(pvPower)
              ));
              addLabel(
                elementsX.solar,
                solarLineStartY,
                elementsX.inverter,
                inverterLineEndYSolar,
                formatPower(pvPower),
                '#b45309',
                -6
              );
            }

            // Inverter ↔ Battery (shortened to avoid icons)
            paths.push(staticLine(elementsX.inverter, invToBattStartY, elementsX.battery, invToBattEndY));
            if (Math.abs(batteryPower) > 1) {
              const isDischarge = isBatteryDischarging;
              paths.push(line(
                elementsX.inverter,
                invToBattStartY,
                elementsX.battery,
                invToBattEndY,
                isDischarge ? '#ef4444' : '#10b981',
                strokeWidthFor(batteryPower),
                isDischarge
              ));
              addLabel(
                elementsX.inverter,
                invToBattStartY,
                elementsX.battery,
                invToBattEndY,
                formatPower(Math.abs(batteryPower)),
                isDischarge ? '#b91c1c' : '#047857',
                -12 // lift label above the line between icons
              );
            }

            // Shortened endpoints for Inverter → Load to avoid icon overlap
            const inverterLineXForLoad = 54; // right of inverter icon center
            const loadLineX = 84; // left of load icon center
            paths.push(staticLine(inverterLineXForLoad, elementsY.inverter, loadLineX, elementsY.load));
            if (loadPower > 1) {
              paths.push(line(
                inverterLineXForLoad,
                elementsY.inverter,
                loadLineX,
                elementsY.load,
                '#3b82f6',
                strokeWidthFor(loadPower)
              ));
              addLabel(
                inverterLineXForLoad,
                elementsY.inverter,
                loadLineX,
                elementsY.load,
                formatPower(loadPower),
                '#1d4ed8',
                4
              );
            }

            // Grid ↔ Inverter (always base line), shortened to avoid crossing icons
            paths.push(staticLine(gridLineX, elementsY.grid, inverterLineXForGrid, elementsY.inverter));
            if (Math.abs(gridPower) > 1) {
              const importing = isGridImporting; // grid -> inverter
              paths.push(line(
                inverterLineXForGrid,
                elementsY.inverter,
                gridLineX,
                elementsY.grid,
                importing ? '#8b5cf6' : '#f97316',
                strokeWidthFor(gridPower),
                importing
              ));
              addLabel(
                inverterLineXForGrid,
                elementsY.inverter,
                gridLineX,
                elementsY.grid,
                formatPower(Math.abs(gridPower)),
                importing ? '#6d28d9' : '#c2410c',
                8 // place label a bit below the line
              );
            }

            return <g>{paths}</g>;
          })()}
        </svg>
        
        {/* Solar (icon centered; today's energy moved to the right of icon) */}
        <div className="absolute" style={{ left: '50%', top: '12%', transform: 'translate(-50%, -50%)' }}>
          <div className="relative">
            <div className="text-center">
              <div className="text-[11px] font-semibold text-yellow-800 mb-1">Solar</div>
              <div className="text-5xl sm:text-6xl md:text-7xl leading-none mb-1">☀️</div>
            </div>
            <div className="absolute text-[12px] sm:text-sm text-yellow-700 whitespace-nowrap" style={{ left: '76px', top: '50%', transform: 'translateY(-50%)' }}>
              Today: {formatEnergy(telemetry.today_energy)}
            </div>
          </div>
        </div>

        {/* Legacy arrows removed (lines handled by SVG) */}

        {/* Inverter (status image centered; mode below) */}
        <div className="absolute" style={{ left: '50%', top: '45%', transform: 'translate(-50%, -50%)' }}>
          <div className="text-center">
            <div className="text-[11px] font-semibold text-gray-800 mb-1" style={{ transform: 'translateX(22px)' }}>Inverter</div>
            <div className="mb-1">
              <img src={inverterIcon as unknown as string} alt={`Inverter ${inverterStatus}`} className="w-24 h-24 sm:w-28 sm:h-28 md:w-28 md:h-28 inline-block" />
            </div>
            <div className="text-[12px] sm:text-sm text-gray-600 font-medium" style={{ transform: 'translateX(22px)' }}>{telemetry.inverter_mode || 'Unknown'}</div>
          </div>
        </div>

        {/* Battery (center icon aligned to flow line; details to the right) */}
        <div className="absolute" style={{ top: '78%', left: 0, right: 0 }}>
          <div className="relative">
            {/* Icon column centered exactly at x=50% to align with SVG line */}
            <div className="absolute text-center" style={{ left: '50%', transform: 'translate(-50%, -50%)' }}>
              <div className={`text-[11px] font-semibold mb-1 ${
                isBatteryCharging ? 'text-green-700' : isBatteryDischarging ? 'text-red-700' : 'text-gray-700'
              }`}>Battery</div>
              <div className="text-7xl sm:text-8xl md:text-9xl leading-none">🔋</div>
            </div>

            {/* Left stats column (align to the left of the icon) */}
            <div className="absolute text-right" style={{ left: 'calc(50% - 110px)', transform: 'translate(-100%, -50%)' }}>
              <div className="space-y-[2px] text-[11px] sm:text-[12px] text-gray-700">
                <div><span className="font-semibold">Volt:</span> {formatVoltage(telemetry.batt_voltage_v)}</div>
                <div><span className="font-semibold">Current:</span> {formatCurrent(telemetry.batt_current_a)}</div>
                <div><span className="font-semibold">Temp:</span> {formatTemperature(telemetry.batt_temp_c)}</div>
              </div>
            </div>

            {/* Details column shifted to the right of the centered icon */}
            <div className="absolute text-left" style={{ left: 'calc(50% + 110px)', transform: 'translateY(-50%)' }}>
              <div className="flex flex-col gap-1 text-[12px] sm:text-sm text-gray-700">
                <div><span className="font-semibold">SOC:</span> {formatPercentage(telemetry.batt_soc_pct)}</div>
                <div><span className="font-semibold">Est. Runtime:</span> {getEstimatedRuntime()}</div>
                <div><span className="font-semibold">Charge:</span> {formatEnergy((telemetry as any)?.today_battery_charge_energy)}</div>
                <div><span className="font-semibold">Discharge:</span> {formatEnergy((telemetry as any)?.today_battery_discharge_energy)}</div>
              </div>
            </div>
          </div>
        </div>

        {/* Legacy arrows removed */}

        {/* Load (icon with small labels + today load energy) */}
        <div className="absolute" style={{ left: '88%', top: '45%', transform: 'translate(-50%, -50%)' }}>
          <div className="text-center">
            <div className="text-[11px] font-semibold text-blue-800 mb-1">Load</div>
            <div className="text-5xl sm:text-6xl md:text-7xl leading-none mb-1">🏠</div>
            <div className="text-[12px] sm:text-sm text-blue-700">Today: {formatEnergy(telemetry.today_load_energy)}</div>
          </div>
        </div>

        {/* Legacy arrows removed */}

        {/* Grid (status image centered on flow line; labels above/below) */}
        <div className="absolute" style={{ left: '12%', top: '45%', transform: 'translate(-50%, -50%)' }}>
          <div className="relative text-center" style={{ width: '200px', height: '220px' }}>
            {/* Title above */}
            <div className={`absolute left-1/2 -translate-x-1/2 top-1 text-[11px] font-semibold ${
              isGridExporting ? 'text-orange-700' : isGridImporting ? 'text-purple-700' : 'text-gray-700'
            }`}>Grid</div>

            {/* Icon perfectly centered to intersect the animated line (y=45%) */}
            <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2">
              <img src={gridIcon as unknown as string} alt={`Grid ${gridStatus}`} className="w-20 h-20 sm:w-24 sm:h-24 md:w-24 md:h-24 inline-block" />
            </div>

            {/* Labels below (positioned under icon to avoid overlap) */}
            <div className="absolute left-1/2 -translate-x-1/2" style={{ top: 'calc(50% + 52px)' }}>
              <div className={`text-[10px] font-semibold ${
                isGridExporting ? 'text-orange-600' : isGridImporting ? 'text-purple-600' : 'text-gray-500'
              }`}>{isGridExporting ? 'Exporting' : isGridImporting ? 'Importing' : 'No Flow'}</div>
            </div>
            <div className="absolute left-1/2 -translate-x-1/2 text-[12px] sm:text-sm" style={{ top: 'calc(50% + 76px)' }}>
              <div className="text-purple-700">Import: {formatEnergy(telemetry.today_import_energy)}</div>
              <div className="text-orange-700">Export: {formatEnergy(telemetry.today_export_energy)}</div>
            </div>
          </div>
        </div>
        </div>
    </div>
  );
};
