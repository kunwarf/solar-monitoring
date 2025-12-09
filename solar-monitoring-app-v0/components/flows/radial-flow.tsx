"use client"

import type React from "react"

import { Sun, Battery, Home, Zap } from "lucide-react"

interface FlowData {
  id: string
  label: string
  value: number
  unit: string
  color: string
  icon: React.ReactNode
  angle: number
  flowDirection: "in" | "out" | "both"
  flowValue: number
}

const flowData: FlowData[] = [
  {
    id: "solar",
    label: "Solar",
    value: 8.4,
    unit: "kW",
    color: "#facc15",
    icon: <Sun className="w-5 h-5" />,
    angle: -90,
    flowDirection: "in",
    flowValue: 8.4,
  },
  {
    id: "battery",
    label: "Battery",
    value: 76,
    unit: "%",
    color: "#3b82f6",
    icon: <Battery className="w-5 h-5" />,
    angle: 0,
    flowDirection: "both",
    flowValue: 2.0,
  },
  {
    id: "grid",
    label: "Grid",
    value: 5.2,
    unit: "kW",
    color: "#10b981",
    icon: <Zap className="w-5 h-5" />,
    angle: 180,
    flowDirection: "out",
    flowValue: 5.2,
  },
]

export function RadialFlowDiagram() {
  const centerX = 200
  const centerY = 150
  const radius = 100

  return (
    <div className="relative h-[350px]">
      <svg className="w-full h-full" viewBox="0 0 400 300">
        <defs>
          {flowData.map((flow) => (
            <linearGradient key={`grad-${flow.id}`} id={`grad-${flow.id}`} x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor={flow.color} stopOpacity="0.1" />
              <stop offset="50%" stopColor={flow.color} stopOpacity="0.8" />
              <stop offset="100%" stopColor={flow.color} stopOpacity="0.1" />
            </linearGradient>
          ))}

          {/* Animated dash pattern */}
          <pattern id="flowPattern" patternUnits="userSpaceOnUse" width="20" height="4">
            <rect width="10" height="4" fill="currentColor">
              <animate attributeName="x" from="0" to="20" dur="0.5s" repeatCount="indefinite" />
            </rect>
          </pattern>
        </defs>

        {/* Flow lines with animation */}
        {flowData.map((flow) => {
          const angleRad = (flow.angle * Math.PI) / 180
          const endX = centerX + Math.cos(angleRad) * radius
          const endY = centerY + Math.sin(angleRad) * radius

          return (
            <g key={flow.id}>
              {/* Glow effect */}
              <line
                x1={centerX}
                y1={centerY}
                x2={endX}
                y2={endY}
                stroke={flow.color}
                strokeWidth="12"
                strokeOpacity="0.1"
                strokeLinecap="round"
              />

              {/* Main line */}
              <line
                x1={centerX}
                y1={centerY}
                x2={endX}
                y2={endY}
                stroke={flow.color}
                strokeWidth="3"
                strokeOpacity="0.3"
                strokeLinecap="round"
              />

              {/* Animated flow */}
              <line
                x1={flow.flowDirection === "out" ? centerX : endX}
                y1={flow.flowDirection === "out" ? centerY : endY}
                x2={flow.flowDirection === "out" ? endX : centerX}
                y2={flow.flowDirection === "out" ? endY : centerY}
                stroke={flow.color}
                strokeWidth="3"
                strokeDasharray="8 12"
                strokeLinecap="round"
              >
                <animate
                  attributeName="stroke-dashoffset"
                  from={flow.flowDirection === "in" ? "0" : "40"}
                  to={flow.flowDirection === "in" ? "40" : "0"}
                  dur="1s"
                  repeatCount="indefinite"
                />
              </line>

              {/* Flow value badge */}
              <g transform={`translate(${(centerX + endX) / 2}, ${(centerY + endY) / 2 - 12})`}>
                <rect x="-20" y="-10" width="40" height="20" rx="10" fill={flow.color} fillOpacity="0.2" />
                <text textAnchor="middle" dominantBaseline="middle" fill={flow.color} fontSize="10" fontWeight="600">
                  {flow.flowValue} kW
                </text>
              </g>
            </g>
          )
        })}

        {/* Center home node */}
        <g transform={`translate(${centerX}, ${centerY})`}>
          <circle r="45" fill="#ec4899" fillOpacity="0.1" className="animate-pulse" />
          <circle r="35" fill="hsl(var(--card))" stroke="#ec4899" strokeWidth="3" />
          <foreignObject x="-12" y="-12" width="24" height="24">
            <Home className="w-6 h-6 text-pink-400" />
          </foreignObject>
        </g>
        <text x={centerX} y={centerY + 55} textAnchor="middle" className="fill-foreground text-sm font-medium">
          Home
        </text>
        <text x={centerX} y={centerY + 72} textAnchor="middle" className="fill-pink-400 text-base font-bold">
          3.2 kW
        </text>

        {/* Outer nodes */}
        {flowData.map((flow) => {
          const angleRad = (flow.angle * Math.PI) / 180
          const nodeX = centerX + Math.cos(angleRad) * (radius + 50)
          const nodeY = centerY + Math.sin(angleRad) * (radius + 50)

          return (
            <g key={`node-${flow.id}`} transform={`translate(${nodeX}, ${nodeY})`}>
              <circle
                r="35"
                fill={flow.color}
                fillOpacity="0.1"
                className="animate-pulse"
                style={{ animationDelay: `${Math.random()}s` }}
              />
              <circle r="28" fill="hsl(var(--card))" stroke={flow.color} strokeWidth="2" />
              <foreignObject x="-10" y="-10" width="20" height="20">
                <div style={{ color: flow.color }}>{flow.icon}</div>
              </foreignObject>
              <text y="45" textAnchor="middle" className="fill-foreground text-xs font-medium">
                {flow.label}
              </text>
              <text y="60" textAnchor="middle" fill={flow.color} fontSize="14" fontWeight="600">
                {flow.value} {flow.unit}
              </text>
            </g>
          )
        })}
      </svg>

      {/* Status indicator */}
      <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20">
        <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
        <span className="text-xs text-emerald-400 font-medium">Exporting to Grid</span>
      </div>
    </div>
  )
}
