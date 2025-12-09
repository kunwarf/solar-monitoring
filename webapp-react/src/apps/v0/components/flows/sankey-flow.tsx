import React from 'react'
import { Sun, Battery, Home, Zap, TrendingUp } from 'lucide-react'

interface SankeyNode {
  id: string
  label: string
  value: number
  unit: string
  color: string
  icon: React.ReactNode
  side: 'left' | 'right'
}

interface SankeyFlow {
  from: string
  to: string
  value: number
}

const leftNodes: SankeyNode[] = [
  {
    id: 'solar',
    label: 'Solar Panels',
    value: 8.4,
    unit: 'kW',
    color: '#facc15',
    icon: <Sun className="w-5 h-5" />,
    side: 'left',
  },
  {
    id: 'grid-import',
    label: 'Grid Import',
    value: 0,
    unit: 'kW',
    color: '#6b7280',
    icon: <Zap className="w-5 h-5" />,
    side: 'left',
  },
]

const rightNodes: SankeyNode[] = [
  {
    id: 'home',
    label: 'Home Usage',
    value: 3.2,
    unit: 'kW',
    color: '#ec4899',
    icon: <Home className="w-5 h-5" />,
    side: 'right',
  },
  {
    id: 'battery',
    label: 'Battery Charge',
    value: 2.0,
    unit: 'kW',
    color: '#3b82f6',
    icon: <Battery className="w-5 h-5" />,
    side: 'right',
  },
  {
    id: 'grid-export',
    label: 'Grid Export',
    value: 3.2,
    unit: 'kW',
    color: '#10b981',
    icon: <TrendingUp className="w-5 h-5" />,
    side: 'right',
  },
]

const flows: SankeyFlow[] = [
  { from: 'solar', to: 'home', value: 3.2 },
  { from: 'solar', to: 'battery', value: 2.0 },
  { from: 'solar', to: 'grid-export', value: 3.2 },
]

export function SankeyFlowDiagram() {
  const totalInput = leftNodes.reduce((sum, n) => sum + n.value, 0)
  const height = 280
  const flowAreaWidth = 200

  // Calculate vertical positions based on values
  const getNodePositions = (nodes: SankeyNode[], startY: number, totalHeight: number) => {
    const total = nodes.reduce((sum, n) => sum + Math.max(n.value, 0.5), 0)
    let currentY = startY
    return nodes.map((node) => {
      const nodeHeight = Math.max((Math.max(node.value, 0.5) / total) * totalHeight, 30)
      const pos = { ...node, y: currentY, height: nodeHeight }
      currentY += nodeHeight + 8
      return pos
    })
  }

  const leftPositions = getNodePositions(leftNodes, 20, height - 60)
  const rightPositions = getNodePositions(rightNodes, 20, height - 60)

  return (
    <div className="relative">
      <div className="flex items-stretch justify-between gap-4">
        {/* Left side - Sources */}
        <div className="flex flex-col gap-2 w-[140px]">
          <span className="text-xs text-muted-foreground font-medium uppercase tracking-wider mb-2">Sources</span>
          {leftPositions.map((node) => (
            <div
              key={node.id}
              className="flex items-center gap-3 p-3 rounded-lg border transition-all hover:scale-[1.02]"
              style={{
                borderColor: node.color + '40',
                backgroundColor: node.color + '10',
                minHeight: Math.max(node.height, 60),
              }}
            >
              <div
                className="w-10 h-10 rounded-lg flex items-center justify-center"
                style={{ backgroundColor: node.color + '20' }}
              >
                <div style={{ color: node.color }}>{node.icon}</div>
              </div>
              <div className="flex flex-col">
                <span className="text-xs text-muted-foreground">{node.label}</span>
                <span className="text-lg font-bold" style={{ color: node.color }}>
                  {node.value} {node.unit}
                </span>
              </div>
            </div>
          ))}
        </div>

        {/* Flow visualization */}
        <div className="flex-1 relative min-h-[280px]">
          <svg className="w-full h-full" viewBox={`0 0 ${flowAreaWidth} ${height}`} preserveAspectRatio="none">
            <defs>
              {flows.map((flow, i) => (
                <linearGradient key={`flow-grad-${i}`} id={`flow-grad-${i}`} x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor={leftNodes.find((n) => n.id === flow.from)?.color} stopOpacity="0.6" />
                  <stop offset="100%" stopColor={rightNodes.find((n) => n.id === flow.to)?.color} stopOpacity="0.6" />
                </linearGradient>
              ))}
            </defs>

            {/* Animated flow paths */}
            {flows.map((flow, i) => {
              const fromNode = leftPositions.find((n) => n.id === flow.from)
              const toNode = rightPositions.find((n) => n.id === flow.to)
              if (!fromNode || !toNode || flow.value === 0) return null

              const flowHeight = Math.max((flow.value / totalInput) * 60, 8)
              const fromY = fromNode.y + fromNode.height / 2
              const toY = toNode.y + toNode.height / 2

              return (
                <g key={`flow-${i}`}>
                  {/* Flow band */}
                  <path
                    d={`
                      M 0 ${fromY - flowHeight / 2}
                      C ${flowAreaWidth * 0.4} ${fromY - flowHeight / 2},
                        ${flowAreaWidth * 0.6} ${toY - flowHeight / 2},
                        ${flowAreaWidth} ${toY - flowHeight / 2}
                      L ${flowAreaWidth} ${toY + flowHeight / 2}
                      C ${flowAreaWidth * 0.6} ${toY + flowHeight / 2},
                        ${flowAreaWidth * 0.4} ${fromY + flowHeight / 2},
                        0 ${fromY + flowHeight / 2}
                      Z
                    `}
                    fill={`url(#flow-grad-${i})`}
                  />

                  {/* Animated particles on flow */}
                  {[0, 0.25, 0.5, 0.75].map((offset, j) => (
                    <circle key={`particle-${i}-${j}`} r="4" fill="white" fillOpacity="0.8">
                      <animateMotion
                        dur="2s"
                        repeatCount="indefinite"
                        begin={`${offset * 2}s`}
                        path={`
                          M 0 ${fromY}
                          C ${flowAreaWidth * 0.4} ${fromY},
                            ${flowAreaWidth * 0.6} ${toY},
                            ${flowAreaWidth} ${toY}
                        `}
                      />
                    </circle>
                  ))}

                  {/* Flow value label */}
                  <text
                    x={flowAreaWidth / 2}
                    y={(fromY + toY) / 2 - 8}
                    textAnchor="middle"
                    className="fill-foreground text-xs font-semibold"
                  >
                    {flow.value} kW
                  </text>
                </g>
              )
            })}
          </svg>
        </div>

        {/* Right side - Destinations */}
        <div className="flex flex-col gap-2 w-[140px]">
          <span className="text-xs text-muted-foreground font-medium uppercase tracking-wider mb-2">Destinations</span>
          {rightPositions.map((node) => (
            <div
              key={node.id}
              className="flex items-center gap-3 p-3 rounded-lg border transition-all hover:scale-[1.02]"
              style={{
                borderColor: node.color + '40',
                backgroundColor: node.color + '10',
                minHeight: Math.max(node.height, 60),
              }}
            >
              <div
                className="w-10 h-10 rounded-lg flex items-center justify-center"
                style={{ backgroundColor: node.color + '20' }}
              >
                <div style={{ color: node.color }}>{node.icon}</div>
              </div>
              <div className="flex flex-col">
                <span className="text-xs text-muted-foreground">{node.label}</span>
                <span className="text-lg font-bold" style={{ color: node.color }}>
                  {node.value} {node.unit}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Summary bar */}
      <div className="mt-4 pt-4 border-t border-border">
        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-emerald-400" />
            <span className="text-muted-foreground">Self-sufficiency:</span>
            <span className="font-semibold text-emerald-400">100%</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground">Net export:</span>
            <span className="font-semibold text-emerald-400">+5.2 kW</span>
          </div>
        </div>
      </div>
    </div>
  )
}

