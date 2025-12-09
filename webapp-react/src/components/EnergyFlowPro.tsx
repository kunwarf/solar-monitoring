import React from 'react'
import { Card, CardHeader, CardTitle, CardContent } from './Card'
import { Badge } from './Badge'
import { TelemetryData, ArrayTelemetryData } from '../types/telemetry'

// Simple icon components using emojis/SVG
const SunIcon = () => <span className="text-2xl">☀️</span>
const BatteryIcon = () => <span className="text-2xl">🔋</span>
const ZapIcon = () => <span className="text-2xl">⚡</span>
const HomeIcon = () => <span className="text-2xl">🏠</span>
const PlugIcon = () => <span className="text-2xl">🔌</span>

interface EnergyFlowNodeProps {
  icon: React.ComponentType
  label: string
  value: string
  badge?: string
  colorClass?: string
}

function EnergyFlowNode({ icon: Icon, label, value, badge, colorClass = 'bg-gray-100' }: EnergyFlowNodeProps) {
  return (
    <div className={`flex flex-col items-center p-4 rounded-xl ${colorClass} min-w-[120px]`}>
      <div className="mb-2">
        <Icon />
      </div>
      <div className="text-sm font-medium text-gray-700 mb-1">{label}</div>
      <div className="text-lg font-bold text-gray-900">{value}</div>
      {badge && <Badge variant="outline" className="mt-1">{badge}</Badge>}
    </div>
  )
}

function scaleWidth(w: number, max = 6000) {
  // map power to 2..14 px stroke width
  const pct = Math.min(1, Math.max(0, Math.abs(w) / max))
  return 2 + pct * 12
}

interface EnergyFlowEdgeProps {
  id: string
  from: [number, number]
  to: [number, number]
  powerW: number
  gradientId: string
}

function EnergyFlowEdge({ id, from, to, powerW, gradientId }: EnergyFlowEdgeProps) {
  const [x1, y1] = from
  const [x2, y2] = to
  const width = scaleWidth(powerW)
  const arrow = powerW >= 0 ? 'url(#arrowHead)' : 'url(#arrowHeadRev)'
  
  return (
    <g>
      <path
        id={id}
        d={`M ${x1} ${y1} L ${x2} ${y2}`}
        stroke={`url(#${gradientId})`}
        strokeWidth={width}
        fill="none"
        markerEnd={arrow}
        className="[stroke-dasharray:6_6] animate-[dashMove_2s_linear_infinite]"
      />
    </g>
  )
}

interface EnergyFlowProProps {
  arrayName: string
  solarW: number
  loadW: number
  gridW: number
  battW: number
  todaySolarKwh: number
  todayLoadKwh: number
}

export function EnergyFlowPro({
  arrayName,
  solarW,
  loadW,
  gridW,
  battW,
  todaySolarKwh,
  todayLoadKwh
}: EnergyFlowProProps) {
  const importExport = gridW >= 0 ? `Import ${gridW} W` : `Export ${Math.abs(gridW)} W`
  
  // Calculate inverter power (net entering the inverter)
  const inverterPower = Math.max(0, solarW + gridW + battW)

  return (
    <Card className="border-none">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">{arrayName} • Energy Flow</CardTitle>
          <Badge variant="outline">
            Today: ☀️ {todaySolarKwh.toFixed(1)} kWh • 🏠 {todayLoadKwh.toFixed(1)} kWh
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="relative w-full h-64">
          <svg viewBox="0 0 700 240" className="absolute inset-0 h-full w-full">
            <defs>
              <linearGradient id="gSolar" x1="0" x2="1">
                <stop offset="0%" stopColor="#f59e0b" />
                <stop offset="100%" stopColor="#fbbf24" />
              </linearGradient>
              <linearGradient id="gBattery" x1="0" x2="1">
                <stop offset="0%" stopColor="#059669" />
                <stop offset="100%" stopColor="#10b981" />
              </linearGradient>
              <linearGradient id="gGridIn" x1="0" x2="1">
                <stop offset="0%" stopColor="#8b5cf6" />
                <stop offset="100%" stopColor="#a78bfa" />
              </linearGradient>
              <linearGradient id="gGridOut" x1="0" x2="1">
                <stop offset="0%" stopColor="#ef4444" />
                <stop offset="100%" stopColor="#f97316" />
              </linearGradient>
              <marker
                id="arrowHead"
                viewBox="0 0 10 10"
                refX="10"
                refY="5"
                markerWidth="6"
                markerHeight="6"
                orient="auto-start-reverse"
              >
                <path d="M 0 0 L 10 5 L 0 10 z" fill="currentColor" />
              </marker>
              <marker
                id="arrowHeadRev"
                viewBox="0 0 10 10"
                refX="0"
                refY="5"
                markerWidth="6"
                markerHeight="6"
                orient="auto-start-reverse"
              >
                <path d="M 10 0 L 0 5 L 10 10 z" fill="currentColor" />
              </marker>
              <style>{`@keyframes dashMove { to { stroke-dashoffset: -60; } }`}</style>
            </defs>

            {/* Edges */}
            <EnergyFlowEdge
              id="solar-to-inv"
              from={[200, 60]}
              to={[350, 120]}
              powerW={solarW}
              gradientId="gSolar"
            />
            <EnergyFlowEdge
              id="batt-to-inv"
              from={[200, 180]}
              to={[350, 120]}
              powerW={battW}
              gradientId="gBattery"
            />
            <EnergyFlowEdge
              id="grid-to-inv"
              from={[60, 120]}
              to={[350, 120]}
              powerW={gridW}
              gradientId={gridW >= 0 ? 'gGridIn' : 'gGridOut'}
            />
            <EnergyFlowEdge
              id="inv-to-load"
              from={[350, 120]}
              to={[600, 120]}
              powerW={loadW}
              gradientId="gSolar"
            />
          </svg>

          {/* Nodes overlay */}
          <div className="absolute inset-0 grid grid-cols-3 items-center">
            <div className="flex flex-col items-center">
              <EnergyFlowNode
                icon={PlugIcon}
                label="Grid"
                value={importExport}
                colorClass="bg-violet-100 dark:bg-violet-900/30"
              />
            </div>
            <div className="flex flex-col items-center gap-6">
              <EnergyFlowNode
                icon={SunIcon}
                label="Solar"
                value={`${solarW} W`}
                badge={`Today ${todaySolarKwh.toFixed(1)} kWh`}
                colorClass="bg-amber-100 dark:bg-amber-900/30"
              />
              <EnergyFlowNode
                icon={ZapIcon}
                label="Inverter"
                value={`${inverterPower} W`}
                colorClass="bg-blue-100 dark:bg-blue-900/30"
              />
              <EnergyFlowNode
                icon={BatteryIcon}
                label="Battery"
                value={`${Math.abs(battW)} W`}
                colorClass="bg-emerald-100 dark:bg-emerald-900/30"
              />
            </div>
            <div className="flex flex-col items-center">
              <EnergyFlowNode
                icon={HomeIcon}
                label="Load"
                value={`${loadW} W`}
                badge={`Today ${todayLoadKwh.toFixed(1)} kWh`}
                colorClass="bg-gray-100 dark:bg-gray-800"
              />
            </div>
          </div>
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-gray-500">
          <div className="flex items-center gap-2">
            <span className="h-1.5 w-6 rounded-full bg-amber-400" /> Solar
          </div>
          <div className="flex items-center gap-2">
            <span className="h-1.5 w-6 rounded-full bg-emerald-500" /> Battery (+charge / −discharge)
          </div>
          <div className="flex items-center gap-2">
            <span className="h-1.5 w-6 rounded-full bg-violet-500" /> Grid Import
          </div>
          <div className="flex items-center gap-2">
            <span className="h-1.5 w-6 rounded-full bg-red-500" /> Grid Export
          </div>
          <div className="ml-auto italic">Line thickness ∝ power</div>
        </div>
      </CardContent>
    </Card>
  )
}

