"use client"
import { useEffect, useRef, useState } from "react"
import { Sun, Battery, Home, Zap } from "lucide-react"

interface EnergyFlow {
  id: string
  from: string
  to: string
  value: number
  color: string
}

interface EnergyState {
  solarProduction: number
  batteryPercent: number
  batteryFlow: number
  homeConsumption: number
  gridFlow: number
}

const CANVAS_WIDTH = 700
const CANVAS_HEIGHT = 450
const NODE_RADIUS = 42

const nodes = [
  { id: "solar", label: "Solar", color: "#facc15", x: CANVAS_WIDTH * 0.5, y: 55, icon: <Sun className="w-7 h-7" /> },
  {
    id: "battery",
    label: "Battery",
    color: "#3b82f6",
    x: CANVAS_WIDTH * 0.12,
    y: CANVAS_HEIGHT * 0.5,
    icon: <Battery className="w-7 h-7" />,
  },
  {
    id: "home",
    label: "Home",
    color: "#ec4899",
    x: CANVAS_WIDTH * 0.5,
    y: CANVAS_HEIGHT - 55,
    icon: <Home className="w-7 h-7" />,
  },
  {
    id: "grid",
    label: "Grid",
    color: "#10b981",
    x: CANVAS_WIDTH * 0.88,
    y: CANVAS_HEIGHT * 0.5,
    icon: <Zap className="w-7 h-7" />,
  },
]

const scenarios: { name: string; state: EnergyState }[] = [
  {
    name: "Sunny Day - Exporting",
    state: { solarProduction: 8.4, batteryPercent: 76, batteryFlow: 2.0, homeConsumption: 3.2, gridFlow: 3.2 },
  },
  {
    name: "Evening - Battery Powering Home",
    state: { solarProduction: 0.5, batteryPercent: 65, batteryFlow: -2.8, homeConsumption: 3.2, gridFlow: 0 },
  },
  {
    name: "Night - Grid Import",
    state: { solarProduction: 0, batteryPercent: 20, batteryFlow: 0, homeConsumption: 1.8, gridFlow: -1.8 },
  },
  {
    name: "Overnight Charging",
    state: { solarProduction: 0, batteryPercent: 25, batteryFlow: 3.5, homeConsumption: 0.8, gridFlow: -4.3 },
  },
  {
    name: "Peak Solar",
    state: { solarProduction: 12.5, batteryPercent: 90, batteryFlow: 1.5, homeConsumption: 4.2, gridFlow: 6.8 },
  },
]

function calculateFlows(state: EnergyState): EnergyFlow[] {
  const flows: EnergyFlow[] = []

  if (state.solarProduction > 0) {
    const solarToHome = Math.min(state.solarProduction, state.homeConsumption)
    if (solarToHome > 0) {
      flows.push({ id: "solar-home", from: "solar", to: "home", value: solarToHome, color: "#facc15" })
    }

    const solarRemaining = state.solarProduction - solarToHome

    if (state.batteryFlow > 0 && solarRemaining > 0) {
      const solarToBattery = Math.min(solarRemaining, state.batteryFlow)
      flows.push({ id: "solar-battery", from: "solar", to: "battery", value: solarToBattery, color: "#facc15" })
    }

    if (state.gridFlow > 0) {
      flows.push({ id: "solar-grid", from: "solar", to: "grid", value: state.gridFlow, color: "#facc15" })
    }
  }

  if (state.batteryFlow < 0) {
    const batteryToHome = Math.min(Math.abs(state.batteryFlow), state.homeConsumption)
    if (batteryToHome > 0) {
      flows.push({ id: "battery-home", from: "battery", to: "home", value: batteryToHome, color: "#3b82f6" })
    }

    const batteryToGrid = Math.abs(state.batteryFlow) - batteryToHome
    if (batteryToGrid > 0 && state.gridFlow > 0) {
      flows.push({ id: "battery-grid", from: "battery", to: "grid", value: batteryToGrid, color: "#3b82f6" })
    }
  }

  if (state.gridFlow < 0) {
    const gridToHome = Math.min(Math.abs(state.gridFlow), state.homeConsumption)
    if (gridToHome > 0) {
      flows.push({ id: "grid-home", from: "grid", to: "home", value: gridToHome, color: "#10b981" })
    }

    if (state.batteryFlow > 0) {
      const gridToBattery = Math.abs(state.gridFlow) - gridToHome
      if (gridToBattery > 0) {
        flows.push({ id: "grid-battery", from: "grid", to: "battery", value: gridToBattery, color: "#10b981" })
      }
    }
  }

  return flows
}

export function ParticleFlowDiagram() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const particlesRef = useRef<
    Array<{ x: number; y: number; progress: number; flow: EnergyFlow; speed: number; size: number }>
  >([])
  const animationRef = useRef<number>()

  const [scenarioIndex, setScenarioIndex] = useState(0)
  const currentScenario = scenarios[scenarioIndex]
  const flows = calculateFlows(currentScenario.state)

  useEffect(() => {
    const canvas = canvasRef.current
    if (canvas) {
      const dpr = window.devicePixelRatio || 1
      canvas.width = CANVAS_WIDTH * dpr
      canvas.height = CANVAS_HEIGHT * dpr
      const ctx = canvas.getContext("2d")
      if (ctx) {
        ctx.scale(dpr, dpr)
      }
    }
  }, [])

  useEffect(() => {
    particlesRef.current = []

    flows.forEach((flow) => {
      if (flow.value > 0) {
        const particleCount = Math.ceil(flow.value * 3) + 5
        for (let i = 0; i < particleCount; i++) {
          particlesRef.current.push({
            x: 0,
            y: 0,
            progress: Math.random(),
            flow,
            speed: 0.003 + Math.random() * 0.004,
            size: 4 + Math.random() * 4,
          })
        }
      }
    })
  }, [scenarioIndex])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext("2d")
    if (!ctx) return

    const getNodePos = (id: string) => {
      const node = nodes.find((n) => n.id === id)
      return node ? { x: node.x, y: node.y } : { x: 0, y: 0 }
    }

    const getPathPoints = (flowId: string, fromId: string, toId: string) => {
      const fromPos = getNodePos(fromId)
      const toPos = getNodePos(toId)

      const paths: Record<string, { cp1: { x: number; y: number }; cp2: { x: number; y: number } }> = {
        "solar-battery": {
          cp1: { x: CANVAS_WIDTH * 0.25, y: 70 },
          cp2: { x: CANVAS_WIDTH * 0.12, y: CANVAS_HEIGHT * 0.25 },
        },
        "solar-home": {
          cp1: { x: CANVAS_WIDTH * 0.35, y: CANVAS_HEIGHT * 0.4 },
          cp2: { x: CANVAS_WIDTH * 0.35, y: CANVAS_HEIGHT * 0.6 },
        },
        "solar-grid": {
          cp1: { x: CANVAS_WIDTH * 0.75, y: 70 },
          cp2: { x: CANVAS_WIDTH * 0.88, y: CANVAS_HEIGHT * 0.25 },
        },
        "battery-home": {
          cp1: { x: CANVAS_WIDTH * 0.12, y: CANVAS_HEIGHT * 0.75 },
          cp2: { x: CANVAS_WIDTH * 0.25, y: CANVAS_HEIGHT - 70 },
        },
        "battery-grid": {
          cp1: { x: CANVAS_WIDTH * 0.35, y: CANVAS_HEIGHT * 0.32 },
          cp2: { x: CANVAS_WIDTH * 0.65, y: CANVAS_HEIGHT * 0.32 },
        },
        "grid-home": {
          cp1: { x: CANVAS_WIDTH * 0.88, y: CANVAS_HEIGHT * 0.75 },
          cp2: { x: CANVAS_WIDTH * 0.75, y: CANVAS_HEIGHT - 70 },
        },
        "grid-battery": {
          cp1: { x: CANVAS_WIDTH * 0.65, y: CANVAS_HEIGHT * 0.68 },
          cp2: { x: CANVAS_WIDTH * 0.35, y: CANVAS_HEIGHT * 0.68 },
        },
      }

      const pathKey = `${fromId}-${toId}`
      const reverseKey = `${toId}-${fromId}`

      let cp1, cp2
      if (paths[pathKey]) {
        cp1 = paths[pathKey].cp1
        cp2 = paths[pathKey].cp2
      } else if (paths[reverseKey]) {
        cp1 = paths[reverseKey].cp2
        cp2 = paths[reverseKey].cp1
      } else {
        const midX = (fromPos.x + toPos.x) / 2
        const midY = (fromPos.y + toPos.y) / 2
        cp1 = { x: midX, y: midY }
        cp2 = { x: midX, y: midY }
      }

      const startAngle = Math.atan2(cp1.y - fromPos.y, cp1.x - fromPos.x)
      const endAngle = Math.atan2(cp2.y - toPos.y, cp2.x - toPos.x)

      const start = {
        x: fromPos.x + Math.cos(startAngle) * (NODE_RADIUS + 8),
        y: fromPos.y + Math.sin(startAngle) * (NODE_RADIUS + 8),
      }

      const end = {
        x: toPos.x + Math.cos(endAngle) * (NODE_RADIUS + 8),
        y: toPos.y + Math.sin(endAngle) * (NODE_RADIUS + 8),
      }

      return { start, end, cp1, cp2 }
    }

    const drawPath = (
      ctx: CanvasRenderingContext2D,
      start: { x: number; y: number },
      end: { x: number; y: number },
      cp1: { x: number; y: number },
      cp2: { x: number; y: number },
    ) => {
      ctx.moveTo(start.x, start.y)
      ctx.bezierCurveTo(cp1.x, cp1.y, cp2.x, cp2.y, end.x, end.y)
    }

    const getCubicBezierPoint = (
      t: number,
      start: { x: number; y: number },
      cp1: { x: number; y: number },
      cp2: { x: number; y: number },
      end: { x: number; y: number },
    ) => {
      const t2 = t * t
      const t3 = t2 * t
      const mt = 1 - t
      const mt2 = mt * mt
      const mt3 = mt2 * mt

      return {
        x: mt3 * start.x + 3 * mt2 * t * cp1.x + 3 * mt * t2 * cp2.x + t3 * end.x,
        y: mt3 * start.y + 3 * mt2 * t * cp1.y + 3 * mt * t2 * cp2.y + t3 * end.y,
      }
    }

    const animate = () => {
      ctx.clearRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT)

      // Draw flow paths
      flows.forEach((flow) => {
        if (flow.value > 0) {
          const { start, end, cp1, cp2 } = getPathPoints(flow.id, flow.from, flow.to)

          const gradient = ctx.createLinearGradient(start.x, start.y, end.x, end.y)
          gradient.addColorStop(0, flow.color + "60")
          gradient.addColorStop(0.5, flow.color + "30")
          gradient.addColorStop(1, flow.color + "60")

          // Outer glow
          ctx.beginPath()
          ctx.strokeStyle = flow.color + "15"
          ctx.lineWidth = Math.min(flow.value * 2, 12) + 10
          ctx.lineCap = "round"
          drawPath(ctx, start, end, cp1, cp2)
          ctx.stroke()

          // Middle glow
          ctx.beginPath()
          ctx.strokeStyle = flow.color + "25"
          ctx.lineWidth = Math.min(flow.value * 2, 10) + 5
          ctx.lineCap = "round"
          drawPath(ctx, start, end, cp1, cp2)
          ctx.stroke()

          // Core path
          ctx.beginPath()
          ctx.strokeStyle = gradient
          ctx.lineWidth = Math.min(flow.value * 1.5, 6) + 3
          ctx.lineCap = "round"
          drawPath(ctx, start, end, cp1, cp2)
          ctx.stroke()
        }
      })

      // Draw particles
      particlesRef.current.forEach((particle) => {
        particle.progress += particle.speed
        if (particle.progress > 1) particle.progress = 0

        const { start, end, cp1, cp2 } = getPathPoints(particle.flow.id, particle.flow.from, particle.flow.to)

        const t = particle.progress
        const pos = getCubicBezierPoint(t, start, cp1, cp2, end)
        particle.x = pos.x
        particle.y = pos.y

        // Particle trail
        for (let i = 3; i >= 0; i--) {
          const trailT = Math.max(0, t - i * 0.02)
          const trailPos = getCubicBezierPoint(trailT, start, cp1, cp2, end)

          ctx.beginPath()
          ctx.fillStyle = particle.flow.color + (30 - i * 8).toString(16).padStart(2, "0")
          ctx.arc(trailPos.x, trailPos.y, particle.size * (1 - i * 0.2), 0, Math.PI * 2)
          ctx.fill()
        }

        // Particle glow
        ctx.beginPath()
        const glowGradient = ctx.createRadialGradient(
          particle.x,
          particle.y,
          0,
          particle.x,
          particle.y,
          particle.size * 3,
        )
        glowGradient.addColorStop(0, particle.flow.color + "80")
        glowGradient.addColorStop(0.5, particle.flow.color + "30")
        glowGradient.addColorStop(1, particle.flow.color + "00")
        ctx.fillStyle = glowGradient
        ctx.arc(particle.x, particle.y, particle.size * 3, 0, Math.PI * 2)
        ctx.fill()

        // Particle core
        ctx.beginPath()
        ctx.fillStyle = particle.flow.color
        ctx.shadowColor = particle.flow.color
        ctx.shadowBlur = 15
        ctx.arc(particle.x, particle.y, particle.size, 0, Math.PI * 2)
        ctx.fill()

        // White center
        ctx.beginPath()
        ctx.fillStyle = "#ffffff"
        ctx.arc(particle.x, particle.y, particle.size * 0.4, 0, Math.PI * 2)
        ctx.fill()
        ctx.shadowBlur = 0
      })

      animationRef.current = requestAnimationFrame(animate)
    }

    animate()

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
      }
    }
  }, [flows])

  const getNodeValue = (nodeId: string): { value: string; subtext?: string } => {
    const state = currentScenario.state
    switch (nodeId) {
      case "solar":
        return {
          value: `${state.solarProduction.toFixed(1)} kW`,
          subtext: state.solarProduction > 0 ? "Producing" : "Idle",
        }
      case "battery":
        const batteryStatus = state.batteryFlow > 0 ? "Charging" : state.batteryFlow < 0 ? "Discharging" : "Idle"
        return { value: `${state.batteryPercent}%`, subtext: batteryStatus }
      case "home":
        return { value: `${state.homeConsumption.toFixed(1)} kW`, subtext: "Consuming" }
      case "grid":
        const gridStatus = state.gridFlow > 0 ? "Exporting" : state.gridFlow < 0 ? "Importing" : "Idle"
        return { value: `${Math.abs(state.gridFlow).toFixed(1)} kW`, subtext: gridStatus }
      default:
        return { value: "0" }
    }
  }

  return (
    <div className="relative">
      {/* Header */}
      <div className="flex items-center justify-between gap-4 mb-6">
        <div className="flex flex-col gap-0.5">
          <span className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">
            Live Energy Flow
          </span>
          <span className="text-base font-semibold text-foreground">{currentScenario.name}</span>
        </div>
        <div className="flex gap-2">
          {scenarios.map((scenario, idx) => (
            <button
              key={idx}
              onClick={() => setScenarioIndex(idx)}
              className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
                idx === scenarioIndex
                  ? "bg-primary text-primary-foreground shadow-lg shadow-primary/25"
                  : "bg-muted/50 text-muted-foreground hover:bg-muted hover:text-foreground"
              }`}
            >
              {idx + 1}
            </button>
          ))}
        </div>
      </div>

      {/* Canvas Container - Fixed size */}
      <div className="relative rounded-2xl bg-gradient-to-br from-muted/30 via-background to-muted/20 p-6 border border-border/50 overflow-hidden">
        <canvas ref={canvasRef} style={{ width: CANVAS_WIDTH, height: CANVAS_HEIGHT }} className="block mx-auto" />

        {/* Node overlays */}
        {nodes.map((node) => {
          const nodeValue = getNodeValue(node.id)
          const isActive = flows.some((f) => f.from === node.id || f.to === node.id)

          return (
            <div
              key={node.id}
              className="absolute flex flex-col items-center transform -translate-x-1/2 -translate-y-1/2 pointer-events-none"
              style={{
                left: node.x + 24, // Account for padding
                top: node.y + 24,
              }}
            >
              {/* Pulsing ring for active nodes */}
              {isActive && (
                <div
                  className="absolute w-28 h-28 rounded-full animate-ping opacity-20"
                  style={{ backgroundColor: node.color }}
                />
              )}

              {/* Glow backdrop */}
              <div
                className="absolute w-28 h-28 rounded-full opacity-30 blur-lg"
                style={{ backgroundColor: node.color }}
              />

              {/* Main node circle */}
              <div
                className="relative w-[84px] h-[84px] rounded-full flex items-center justify-center border-2 bg-background/95 backdrop-blur-sm shadow-2xl transition-transform hover:scale-105"
                style={{
                  borderColor: node.color,
                  boxShadow: `0 0 30px ${node.color}50, 0 0 60px ${node.color}20, inset 0 0 20px ${node.color}10`,
                }}
              >
                <div style={{ color: node.color }}>{node.icon}</div>
              </div>

              {/* Label badge */}
              <div
                className="mt-2 px-3 py-1 rounded-full text-[11px] font-semibold uppercase tracking-wider"
                style={{ backgroundColor: node.color + "20", color: node.color }}
              >
                {node.label}
              </div>

              {/* Value */}
              <span className="text-xl font-bold mt-1" style={{ color: node.color }}>
                {nodeValue.value}
              </span>

              {/* Status subtext */}
              {nodeValue.subtext && (
                <span className="text-xs px-2 py-0.5 rounded-full bg-muted/80" style={{ color: node.color }}>
                  {nodeValue.subtext}
                </span>
              )}
            </div>
          )
        })}
      </div>

      {/* Flow legend */}
      <div className="flex flex-wrap items-center justify-center gap-3 mt-6">
        {flows.map((flow) => (
          <div
            key={flow.id}
            className="flex items-center gap-2 px-4 py-2 rounded-full border transition-all hover:scale-105"
            style={{
              backgroundColor: flow.color + "10",
              borderColor: flow.color + "30",
            }}
          >
            <div
              className="w-2.5 h-2.5 rounded-full animate-pulse"
              style={{ backgroundColor: flow.color, boxShadow: `0 0 8px ${flow.color}` }}
            />
            <span className="text-sm text-muted-foreground capitalize">{flow.from}</span>
            <svg width="16" height="8" viewBox="0 0 16 8" className="text-muted-foreground">
              <path
                d="M0 4h12M9 1l3 3-3 3"
                stroke="currentColor"
                strokeWidth="1.5"
                fill="none"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            <span className="text-sm text-muted-foreground capitalize">{flow.to}</span>
            <span className="text-sm font-bold" style={{ color: flow.color }}>
              {flow.value.toFixed(1)} kW
            </span>
          </div>
        ))}
        {flows.length === 0 && <span className="text-sm text-muted-foreground italic">No active flows</span>}
      </div>
    </div>
  )
}
