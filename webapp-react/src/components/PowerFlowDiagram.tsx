import React from 'react';
import { TelemetryData } from '../types/telemetry';
import { formatPower, formatEnergy } from '../utils/telemetry';
import { Card, CardHeader, CardTitle, CardContent } from './Card';
import { Badge } from './Badge';
import { useTheme } from '../contexts/ThemeContext';
import GridNormalIcon from '../assets/grid-normal.svg';
import GridFaultIcon from '../assets/grid-fault.svg';
import GridOffIcon from '../assets/grid-off.svg';
import InverterNormalIcon from '../assets/inverter-normal.svg';
import InverterFaultIcon from '../assets/inverter-fault.svg';
import InverterOffIcon from '../assets/inverter-off.svg';

interface PowerFlowDiagramProps {
  telemetry: TelemetryData;
}

const scaleWidth = (w: number, max = 6000) => {
  const pct = Math.min(1, Math.max(0, Math.abs(w) / max));
  // Ensure minimum visible width on mobile (at least 4px for better visibility)
  return Math.max(4, 3 + pct * 12); // 4..15 px
};

function Node({
  x,
  y,
  icon,
  value,
  chip,
  align = 'center',
  textColor,
  textSecondary,
}: {
  x: number;
  y: number;
  icon: string | React.ReactNode;
  value: string;
  chip?: string;
  align?: 'left' | 'center' | 'right';
  textColor: string;
  textSecondary: string;
}) {
  // Convert SVG coordinates to percentage for responsive positioning
  const xPercent = (x / 800) * 100;
  const yPercent = (y / 400) * 100;
  const style: React.CSSProperties = {
    left: `calc(${xPercent}% - 50px)`,
    top: `calc(${yPercent}% - 50px)`,
    width: '100px',
    maxWidth: '25vw', // Prevent overflow on mobile
  };
  const alignClass =
    align === 'left' ? 'items-start text-left' : align === 'right' ? 'items-end text-right' : 'items-center text-center';

  return (
    <div
      className={`absolute ${alignClass} flex flex-col gap-1`}
      style={style}
    >
      {/* Icon */}
      <div className="flex items-center justify-center w-12 h-12 sm:w-14 sm:h-14 md:w-16 md:h-16">
        {typeof icon === 'string' ? (
          <span className="text-3xl sm:text-4xl md:text-5xl">{icon}</span>
        ) : (
          <div className="w-8 h-8 sm:w-10 sm:h-10 md:w-12 md:h-12">{icon}</div>
        )}
      </div>
      {/* Value */}
      <div 
        className="text-xs sm:text-sm md:text-base font-bold text-center leading-tight whitespace-nowrap"
        style={{ color: textColor }}
      >
        {value}
      </div>
      {/* Chip (optional) */}
      {chip && (
        <div 
          className="text-[9px] sm:text-[10px] text-center whitespace-nowrap"
          style={{ color: textSecondary }}
        >
          {chip}
        </div>
      )}
    </div>
  );
}

function LegendSwatch({ className, label }: { className: string; label: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className={`h-1.5 w-6 rounded-full ${className}`} />
      <span>{label}</span>
    </div>
  );
}

export const PowerFlowDiagram: React.FC<PowerFlowDiagramProps> = ({ telemetry }) => {
  const { theme } = useTheme();
  const pvPower = telemetry.pv_power_w || 0;
  const loadPower = telemetry.load_power_w || 0;
  const batteryPower = telemetry.batt_power_w || 0;
  const gridPower = telemetry.grid_power_w || 0;

  // Theme-aware colors
  const textColor = theme === 'dark' ? '#ffffff' : '#1f2937';
  const textSecondary = theme === 'dark' ? 'rgba(255, 255, 255, 0.7)' : '#6b7280';
  const bgGradientFrom = theme === 'dark' ? '#374151' : '#f9fafb';
  const bgGradientTo = theme === 'dark' ? '#1f2937' : '#f3f4f6';
  const labelBg = theme === 'dark' ? '#1f2937' : '#ffffff';
  const labelBorder = theme === 'dark' ? '#4b5563' : 'rgba(0,0,0,0.1)';
  const labelText = theme === 'dark' ? '#ffffff' : '#1f2937';

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

  // Today's energy
  const todaySolarKwh = (telemetry.today_energy || 0) / 1000; // Convert Wh to kWh if needed, or use as-is if already kWh
  const todayLoadKwh = (telemetry.today_load_energy || 0) / 1000;

  // Anchor points (SVG coords in viewBox 0 0 800 400)
  const P = {
    grid: [120, 200],
    solar: [400, 65],
    battery: [400, 335],
    inverter: [400, 200],
    load: [680, 200],
  };

  // Edges with visual params - always show lines with proper direction
  const edges = [
    {
      id: 'solar->inv',
      from: P.solar,
      to: P.inverter,
      w: pvPower,
      grad: 'gSolar',
      label: formatPower(pvPower),
    },
    {
      id: 'grid->inv',
      from: gridPower >= 0 ? P.grid : P.inverter, // Import: grid→inverter, Export: inverter→grid
      to: gridPower >= 0 ? P.inverter : P.grid,
      w: Math.abs(gridPower),
      grad: gridPower >= 0 ? 'gGridIn' : 'gGridOut',
      label: formatPower(Math.abs(gridPower)),
    },
    {
      id: 'batt->inv',
      from: batteryPower >= 0 ? P.inverter : P.battery, // Charge: inverter→battery, Discharge: battery→inverter
      to: batteryPower >= 0 ? P.battery : P.inverter,
      w: Math.abs(batteryPower),
      grad: 'gBattery',
      label: formatPower(Math.abs(batteryPower)),
    },
    {
      id: 'inv->load',
      from: P.inverter,
      to: P.load,
      w: loadPower,
      grad: 'gSolar',
      label: formatPower(loadPower),
    },
  ];

  const invNet = Math.max(0, pvPower + (gridPower >= 0 ? gridPower : 0) + (batteryPower < 0 ? Math.abs(batteryPower) : 0));
  const gridBadge = gridPower >= 0 ? `Import ${formatPower(gridPower)}` : `Export ${formatPower(Math.abs(gridPower))}`;

  return (
    <Card className="border-none">
      <CardHeader className="pb-2">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
          <CardTitle className="text-sm sm:text-base">System • Energy Flow</CardTitle>
          <Badge variant="outline" className="text-[10px] sm:text-xs whitespace-nowrap">
            Today: ☀️ {todaySolarKwh.toFixed(1)} kWh • 🏠 {todayLoadKwh.toFixed(1)} kWh
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="relative">
        {/* Diagram area */}
        <div 
          className="relative w-full overflow-hidden rounded-xl"
          style={{
            background: `linear-gradient(to bottom, ${bgGradientFrom}, ${bgGradientTo})`,
          }}
        >
          <svg viewBox="0 0 800 400" className="h-[280px] sm:h-[350px] md:h-[420px] w-full" preserveAspectRatio="xMidYMid meet">
            <defs>
              <linearGradient id="gSolar" x1="0" x2="1">
                <stop offset="0%" stopColor="hsl(35, 95%, 55%)" />
                <stop offset="100%" stopColor="hsl(217, 91%, 60%)" />
              </linearGradient>
              <linearGradient id="gBattery" x1="0" x2="1">
                <stop offset="0%" stopColor="hsl(152, 70%, 37%)" />
                <stop offset="100%" stopColor="hsl(152, 70%, 47%)" />
              </linearGradient>
              <linearGradient id="gGridIn" x1="0" x2="1">
                <stop offset="0%" stopColor="hsl(258, 90%, 60%)" />
                <stop offset="100%" stopColor="hsl(258, 90%, 70%)" />
              </linearGradient>
              <linearGradient id="gGridOut" x1="0" x2="1">
                <stop offset="0%" stopColor="hsl(4, 85%, 58%)" />
                <stop offset="100%" stopColor="hsl(25, 90%, 55%)" />
              </linearGradient>
              <marker
                id="arrowEnd"
                viewBox="0 0 10 10"
                refX="9"
                refY="5"
                markerWidth="6"
                markerHeight="6"
                orient="auto"
                markerUnits="userSpaceOnUse"
              >
                <path d="M 0 0 L 10 5 L 0 10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </marker>
              <marker
                id="arrowStart"
                viewBox="0 0 10 10"
                refX="1"
                refY="5"
                markerWidth="6"
                markerHeight="6"
                orient="auto"
                markerUnits="userSpaceOnUse"
              >
                <path d="M 10 0 L 0 5 L 10 10" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </marker>
              <style>{`
                @keyframes dashMove { 
                  0% { stroke-dashoffset: 0; }
                  100% { stroke-dashoffset: -22; }
                }
                .flow { 
                  stroke-linecap: round; 
                  stroke-dasharray: 12 10; 
                  animation: dashMove 2s linear infinite; 
                  opacity: 1;
                }
              `}</style>
            </defs>

            {/* Edges - Animated power flow lines */}
            {edges.map((e) => {
              const [x1, y1] = e.from;
              const [x2, y2] = e.to;
              const width = scaleWidth(e.w);
              // Show line if power is significant (> 0.1W for visibility)
              if (e.w < 0.1) return null;
              
              // Calculate midpoint for label
              const midX = (x1 + x2) / 2;
              const midY = (y1 + y2) / 2;
              
              // Always show arrow in direction of flow (from → to)
              return (
                <g key={e.id}>
                  <path
                    d={`M ${x1} ${y1} L ${x2} ${y2}`}
                    stroke={`url(#${e.grad})`}
                    strokeWidth={width}
                    fill="none"
                    className="flow"
                    markerEnd="url(#arrowEnd)"
                    strokeLinecap="round"
                    style={{ 
                      filter: 'drop-shadow(0 1px 2px rgba(0,0,0,0.15))',
                    }}
                  />
                  {/* Power label on line with background for readability */}
                  <g>
                    <rect
                      x={midX - 40}
                      y={midY - 12}
                      width="80"
                      height="24"
                      fill={labelBg}
                      fillOpacity="0.95"
                      rx="6"
                      stroke={labelBorder}
                      strokeWidth="0.5"
                    />
                    <text
                      x={midX}
                      y={midY}
                      textAnchor="middle"
                      dominantBaseline="middle"
                      fill={labelText}
                      fontSize="14"
                      fontWeight="700"
                      pointerEvents="none"
                      style={{ fontFamily: 'system-ui, -apple-system, sans-serif' }}
                    >
                      {e.label}
                    </text>
                  </g>
                </g>
              );
            })}

            {/* Soft dot at inverter */}
            <circle cx={P.inverter[0]} cy={P.inverter[1]} r="6" fill="hsl(217, 91%, 60%)" opacity={0.6} />
        </svg>
        
          {/* Nodes - Icons with data only (no boxes) */}
          <Node
            x={P.grid[0]}
            y={P.grid[1]}
            icon={<img src={gridIcon as unknown as string} alt={`Grid ${gridStatus}`} className="w-full h-full" />}
            value={gridBadge}
            align="left"
            textColor={textColor}
            textSecondary={textSecondary}
          />

          <Node
            x={P.solar[0]}
            y={P.solar[1]}
            icon="☀️"
            value={`${formatPower(pvPower)}`}
            chip={`Today ${todaySolarKwh.toFixed(1)} kWh`}
            textColor={textColor}
            textSecondary={textSecondary}
          />

          <Node
            x={P.inverter[0]}
            y={P.inverter[1]}
            icon={<img src={inverterIcon as unknown as string} alt={`Inverter ${inverterStatus}`} className="w-full h-full" />}
            value={`${formatPower(invNet)}`}
            textColor={textColor}
            textSecondary={textSecondary}
          />

          <Node
            x={P.battery[0]}
            y={P.battery[1]}
            icon="🔋"
            value={`${formatPower(Math.abs(batteryPower))}`}
            textColor={textColor}
            textSecondary={textSecondary}
          />

          <Node
            x={P.load[0]}
            y={P.load[1]}
            icon="🏠"
            value={`${formatPower(loadPower)}`}
            chip={`Today ${todayLoadKwh.toFixed(1)} kWh`}
            align="right"
            textColor={textColor}
            textSecondary={textSecondary}
          />

          {/* Legend - Hidden on very small screens */}
          <div 
            className="absolute bottom-2 right-3 hidden sm:flex items-center gap-2 md:gap-3 text-[10px] sm:text-[12px] flex-wrap max-w-[calc(100%-1rem)]"
            style={{ color: textSecondary }}
          >
            <LegendSwatch className="bg-[hsl(35,95%,55%)]" label="Solar" />
            <LegendSwatch className="bg-[hsl(152,70%,40%)]" label="Battery" />
            <LegendSwatch className="bg-[hsl(258,90%,60%)]" label="Grid In" />
            <LegendSwatch className="bg-[hsl(4,85%,58%)]" label="Grid Out" />
            <span className="italic ml-1 hidden md:inline">line thickness ∝ power</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
