"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Battery,
  BatteryCharging,
  Thermometer,
  Zap,
  Activity,
  Settings,
  ArrowDown,
  ArrowUp,
  ChevronDown,
  ChevronRight,
  X,
  Heart,
  Gauge,
} from "lucide-react"

interface Cell {
  id: string
  voltage: number
  current: number
  soc: number
  temperature: number
  status: "normal" | "warning" | "critical" | "balancing"
}

interface IndividualBattery {
  id: string
  name: string
  model: string
  status: "charging" | "discharging" | "idle" | "balancing"
  soc: number
  voltage: number
  current: number
  temperature: number
  health: number
  cells: Cell[]
}

interface BatteryPack {
  id: string
  name: string
  location: string
  status: "online" | "offline" | "warning"
  totalCapacity: number
  batteries: IndividualBattery[]
}

const batteryPacks: BatteryPack[] = [
  {
    id: "PACK-001",
    name: "Main Battery Pack",
    location: "Garage - East Wall",
    status: "online",
    totalCapacity: 27,
    batteries: [
      {
        id: "BAT-001",
        name: "Battery Unit 1",
        model: "LFP-5000",
        status: "charging",
        soc: 72,
        voltage: 51.2,
        current: 45.5,
        temperature: 28,
        health: 98,
        cells: [
          { id: "C1", voltage: 3.21, current: 3.8, soc: 73, temperature: 27, status: "normal" },
          { id: "C2", voltage: 3.2, current: 3.8, soc: 72, temperature: 28, status: "normal" },
          { id: "C3", voltage: 3.22, current: 3.9, soc: 74, temperature: 27, status: "normal" },
          { id: "C4", voltage: 3.19, current: 3.7, soc: 71, temperature: 29, status: "normal" },
          { id: "C5", voltage: 3.21, current: 3.8, soc: 72, temperature: 28, status: "normal" },
          { id: "C6", voltage: 3.18, current: 3.6, soc: 70, temperature: 30, status: "balancing" },
          { id: "C7", voltage: 3.2, current: 3.8, soc: 72, temperature: 28, status: "normal" },
          { id: "C8", voltage: 3.21, current: 3.8, soc: 73, temperature: 27, status: "normal" },
          { id: "C9", voltage: 3.23, current: 3.9, soc: 75, temperature: 26, status: "normal" },
          { id: "C10", voltage: 3.2, current: 3.8, soc: 72, temperature: 28, status: "normal" },
          { id: "C11", voltage: 3.19, current: 3.7, soc: 71, temperature: 29, status: "normal" },
          { id: "C12", voltage: 3.21, current: 3.8, soc: 72, temperature: 28, status: "normal" },
          { id: "C13", voltage: 3.2, current: 3.8, soc: 72, temperature: 28, status: "normal" },
          { id: "C14", voltage: 3.22, current: 3.9, soc: 74, temperature: 27, status: "normal" },
          { id: "C15", voltage: 3.21, current: 3.8, soc: 73, temperature: 28, status: "normal" },
          { id: "C16", voltage: 3.2, current: 3.8, soc: 72, temperature: 28, status: "normal" },
        ],
      },
      {
        id: "BAT-002",
        name: "Battery Unit 2",
        model: "LFP-5000",
        status: "charging",
        soc: 68,
        voltage: 50.8,
        current: 42.3,
        temperature: 29,
        health: 97,
        cells: [
          { id: "C1", voltage: 3.18, current: 3.5, soc: 69, temperature: 29, status: "normal" },
          { id: "C2", voltage: 3.17, current: 3.5, soc: 68, temperature: 30, status: "normal" },
          { id: "C3", voltage: 3.19, current: 3.6, soc: 70, temperature: 28, status: "normal" },
          { id: "C4", voltage: 3.16, current: 3.4, soc: 67, temperature: 31, status: "warning" },
          { id: "C5", voltage: 3.18, current: 3.5, soc: 69, temperature: 29, status: "normal" },
          { id: "C6", voltage: 3.17, current: 3.5, soc: 68, temperature: 30, status: "normal" },
          { id: "C7", voltage: 3.19, current: 3.6, soc: 70, temperature: 28, status: "normal" },
          { id: "C8", voltage: 3.18, current: 3.5, soc: 69, temperature: 29, status: "normal" },
          { id: "C9", voltage: 3.2, current: 3.7, soc: 71, temperature: 27, status: "normal" },
          { id: "C10", voltage: 3.17, current: 3.5, soc: 68, temperature: 30, status: "normal" },
          { id: "C11", voltage: 3.16, current: 3.4, soc: 67, temperature: 31, status: "normal" },
          { id: "C12", voltage: 3.18, current: 3.5, soc: 69, temperature: 29, status: "normal" },
          { id: "C13", voltage: 3.17, current: 3.5, soc: 68, temperature: 30, status: "normal" },
          { id: "C14", voltage: 3.19, current: 3.6, soc: 70, temperature: 28, status: "normal" },
          { id: "C15", voltage: 3.18, current: 3.5, soc: 69, temperature: 29, status: "normal" },
          { id: "C16", voltage: 3.17, current: 3.5, soc: 68, temperature: 30, status: "normal" },
        ],
      },
      {
        id: "BAT-003",
        name: "Battery Unit 3",
        model: "LFP-5000",
        status: "idle",
        soc: 100,
        voltage: 54.4,
        current: 0,
        temperature: 25,
        health: 99,
        cells: [
          { id: "C1", voltage: 3.4, current: 0, soc: 100, temperature: 25, status: "normal" },
          { id: "C2", voltage: 3.4, current: 0, soc: 100, temperature: 25, status: "normal" },
          { id: "C3", voltage: 3.4, current: 0, soc: 100, temperature: 25, status: "normal" },
          { id: "C4", voltage: 3.4, current: 0, soc: 100, temperature: 25, status: "normal" },
          { id: "C5", voltage: 3.4, current: 0, soc: 100, temperature: 25, status: "normal" },
          { id: "C6", voltage: 3.4, current: 0, soc: 100, temperature: 25, status: "normal" },
          { id: "C7", voltage: 3.4, current: 0, soc: 100, temperature: 25, status: "normal" },
          { id: "C8", voltage: 3.4, current: 0, soc: 100, temperature: 25, status: "normal" },
          { id: "C9", voltage: 3.4, current: 0, soc: 100, temperature: 25, status: "normal" },
          { id: "C10", voltage: 3.4, current: 0, soc: 100, temperature: 25, status: "normal" },
          { id: "C11", voltage: 3.4, current: 0, soc: 100, temperature: 25, status: "normal" },
          { id: "C12", voltage: 3.4, current: 0, soc: 100, temperature: 25, status: "normal" },
          { id: "C13", voltage: 3.4, current: 0, soc: 100, temperature: 25, status: "normal" },
          { id: "C14", voltage: 3.4, current: 0, soc: 100, temperature: 25, status: "normal" },
          { id: "C15", voltage: 3.4, current: 0, soc: 100, temperature: 25, status: "normal" },
          { id: "C16", voltage: 3.4, current: 0, soc: 100, temperature: 25, status: "normal" },
        ],
      },
    ],
  },
  {
    id: "PACK-002",
    name: "Backup Battery Pack",
    location: "Basement - Storage Room",
    status: "online",
    totalCapacity: 13.5,
    batteries: [
      {
        id: "BAT-004",
        name: "Battery Unit 1",
        model: "LFP-5000",
        status: "discharging",
        soc: 45,
        voltage: 48.6,
        current: -32.1,
        temperature: 31,
        health: 96,
        cells: [
          { id: "C1", voltage: 3.04, current: -2.0, soc: 46, temperature: 31, status: "normal" },
          { id: "C2", voltage: 3.03, current: -2.0, soc: 45, temperature: 32, status: "normal" },
          { id: "C3", voltage: 3.05, current: -2.1, soc: 47, temperature: 30, status: "normal" },
          { id: "C4", voltage: 3.02, current: -1.9, soc: 44, temperature: 33, status: "warning" },
          { id: "C5", voltage: 3.04, current: -2.0, soc: 46, temperature: 31, status: "normal" },
          { id: "C6", voltage: 3.03, current: -2.0, soc: 45, temperature: 32, status: "normal" },
          { id: "C7", voltage: 3.05, current: -2.1, soc: 47, temperature: 30, status: "normal" },
          { id: "C8", voltage: 3.04, current: -2.0, soc: 46, temperature: 31, status: "normal" },
          { id: "C9", voltage: 3.06, current: -2.2, soc: 48, temperature: 29, status: "normal" },
          { id: "C10", voltage: 3.03, current: -2.0, soc: 45, temperature: 32, status: "normal" },
          { id: "C11", voltage: 3.02, current: -1.9, soc: 44, temperature: 33, status: "normal" },
          { id: "C12", voltage: 3.04, current: -2.0, soc: 46, temperature: 31, status: "normal" },
          { id: "C13", voltage: 3.03, current: -2.0, soc: 45, temperature: 32, status: "normal" },
          { id: "C14", voltage: 3.05, current: -2.1, soc: 47, temperature: 30, status: "normal" },
          { id: "C15", voltage: 3.04, current: -2.0, soc: 46, temperature: 31, status: "normal" },
          { id: "C16", voltage: 3.03, current: -2.0, soc: 45, temperature: 32, status: "normal" },
        ],
      },
    ],
  },
]

function getCellStatusColor(status: Cell["status"]) {
  switch (status) {
    case "normal":
      return "bg-green-500"
    case "warning":
      return "bg-amber-500"
    case "critical":
      return "bg-red-500"
    case "balancing":
      return "bg-blue-500"
  }
}

function getCellFillColor(status: Cell["status"]) {
  switch (status) {
    case "normal":
      return "#22c55e"
    case "warning":
      return "#f59e0b"
    case "critical":
      return "#ef4444"
    case "balancing":
      return "#3b82f6"
  }
}

function getCellStatusBorder(status: Cell["status"]) {
  switch (status) {
    case "normal":
      return "border-green-500/30"
    case "warning":
      return "border-amber-500/30"
    case "critical":
      return "border-red-500/30"
    case "balancing":
      return "border-blue-500/30"
  }
}

function getBatteryStatusBadge(status: IndividualBattery["status"]) {
  switch (status) {
    case "charging":
      return (
        <Badge className="bg-green-500/20 text-green-500">
          <ArrowDown className="h-3 w-3 mr-1" />
          Charging
        </Badge>
      )
    case "discharging":
      return (
        <Badge className="bg-blue-500/20 text-blue-500">
          <ArrowUp className="h-3 w-3 mr-1" />
          Discharging
        </Badge>
      )
    case "idle":
      return <Badge className="bg-gray-500/20 text-gray-400">Idle</Badge>
    case "balancing":
      return <Badge className="bg-purple-500/20 text-purple-400">Balancing</Badge>
  }
}

function BatteryVisual({
  soc,
  status,
  isCharging,
}: { soc: number; status: IndividualBattery["status"]; isCharging: boolean }) {
  const fillColor = soc > 60 ? "#22c55e" : soc > 30 ? "#f59e0b" : "#ef4444"

  return (
    <div className="relative w-24 h-40">
      <svg viewBox="0 0 60 100" className="w-full h-full">
        {/* Battery terminal */}
        <rect x="20" y="0" width="20" height="6" rx="2" fill="#374151" />

        {/* Battery body - outer shell */}
        <rect x="5" y="6" width="50" height="90" rx="6" fill="#1f2937" stroke="#374151" strokeWidth="2" />

        {/* Inner area */}
        <rect x="9" y="10" width="42" height="82" rx="4" fill="#111827" />

        {/* Fill level with gradient */}
        <defs>
          <linearGradient id={`batteryFill-${soc}`} x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor={fillColor} stopOpacity="0.7" />
            <stop offset="50%" stopColor={fillColor} stopOpacity="1" />
            <stop offset="100%" stopColor={fillColor} stopOpacity="0.7" />
          </linearGradient>
          <filter id="glow">
            <feGaussianBlur stdDeviation="2" result="coloredBlur" />
            <feMerge>
              <feMergeNode in="coloredBlur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* Fill */}
        <rect
          x="11"
          y={12 + (78 * (100 - soc)) / 100}
          width="38"
          height={(78 * soc) / 100}
          rx="3"
          fill={`url(#batteryFill-${soc})`}
          filter="url(#glow)"
        >
          {isCharging && <animate attributeName="opacity" values="0.7;1;0.7" dur="1.5s" repeatCount="indefinite" />}
        </rect>

        {/* Charging bolt */}
        {isCharging && (
          <g filter="url(#glow)">
            <path
              d="M 35 35 L 25 50 L 30 50 L 25 65 L 40 45 L 33 45 L 38 35 Z"
              fill="#fbbf24"
              className="animate-pulse"
            />
          </g>
        )}

        {/* Percentage text */}
        <text x="30" y="58" textAnchor="middle" fill="white" fontSize="14" fontWeight="bold">
          {soc}%
        </text>
      </svg>
    </div>
  )
}

function CellVisual({ cell, onClick }: { cell: Cell; onClick: () => void }) {
  const fillColor = getCellFillColor(cell.status)
  const tempColor = cell.temperature > 35 ? "#ef4444" : cell.temperature > 30 ? "#f59e0b" : "#22c55e"

  return (
    <div
      className="flex flex-col items-center gap-1 cursor-pointer transition-transform hover:scale-105"
      onClick={onClick}
    >
      <div className="relative">
        <svg viewBox="0 0 40 70" className="w-12 h-[70px]">
          {/* Cell terminal (positive) */}
          <ellipse cx="20" cy="5" rx="8" ry="3" fill="#6b7280" />
          <rect x="12" y="5" width="16" height="4" fill="#6b7280" />

          {/* Cell body - 3D cylinder effect */}
          <defs>
            <linearGradient id={`cellBody-${cell.id}`} x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#374151" />
              <stop offset="30%" stopColor="#4b5563" />
              <stop offset="70%" stopColor="#4b5563" />
              <stop offset="100%" stopColor="#374151" />
            </linearGradient>
            <linearGradient id={`cellFill-${cell.id}`} x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor={fillColor} stopOpacity="0.6" />
              <stop offset="30%" stopColor={fillColor} stopOpacity="1" />
              <stop offset="70%" stopColor={fillColor} stopOpacity="1" />
              <stop offset="100%" stopColor={fillColor} stopOpacity="0.6" />
            </linearGradient>
            <linearGradient id={`cellHighlight-${cell.id}`} x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="white" stopOpacity="0" />
              <stop offset="40%" stopColor="white" stopOpacity="0.15" />
              <stop offset="60%" stopColor="white" stopOpacity="0" />
            </linearGradient>
          </defs>

          {/* Outer cylinder */}
          <rect x="4" y="9" width="32" height="54" rx="3" fill={`url(#cellBody-${cell.id})`} />

          {/* Inner fill area */}
          <rect x="6" y="11" width="28" height="50" rx="2" fill="#1f2937" />

          {/* SOC fill level */}
          <rect
            x="7"
            y={12 + (48 * (100 - cell.soc)) / 100}
            width="26"
            height={(48 * cell.soc) / 100}
            rx="1.5"
            fill={`url(#cellFill-${cell.id})`}
          />

          {/* Highlight reflection */}
          <rect x="4" y="9" width="32" height="54" rx="3" fill={`url(#cellHighlight-${cell.id})`} />

          {/* Bottom cap */}
          <ellipse cx="20" cy="63" rx="16" ry="3" fill="#374151" />

          {/* Top cap */}
          <ellipse cx="20" cy="9" rx="16" ry="3" fill="#4b5563" />

          {/* Temperature indicator bar on right side */}
          <rect x="34" y="15" width="3" height="44" rx="1" fill="#1f2937" />
          <rect
            x="34"
            y={15 + 44 * (1 - cell.temperature / 50)}
            width="3"
            height={(44 * cell.temperature) / 50}
            rx="1"
            fill={tempColor}
          />

          {/* Status indicator LED */}
          <circle cx="20" cy="9" r="3" fill={fillColor}>
            {cell.status === "balancing" && (
              <animate attributeName="opacity" values="1;0.3;1" dur="1s" repeatCount="indefinite" />
            )}
          </circle>
        </svg>
      </div>

      {/* Cell ID label */}
      <span className="text-[10px] font-bold text-muted-foreground">{cell.id}</span>

      {/* Quick stats */}
      <div className="text-[9px] text-center space-y-0.5 bg-muted/50 rounded px-1.5 py-1 w-full">
        <div className="flex justify-between gap-2">
          <span className="text-muted-foreground">V</span>
          <span className="text-foreground font-medium">{cell.voltage.toFixed(2)}</span>
        </div>
        <div className="flex justify-between gap-2">
          <span className="text-muted-foreground">T</span>
          <span style={{ color: tempColor }} className="font-medium">
            {cell.temperature}°
          </span>
        </div>
      </div>
    </div>
  )
}

function CellDetailModal({ cell, onClose }: { cell: Cell; onClose: () => void }) {
  const fillColor = getCellFillColor(cell.status)
  const tempColor = cell.temperature > 35 ? "#ef4444" : cell.temperature > 30 ? "#f59e0b" : "#22c55e"

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50" onClick={onClose}>
      <Card className="w-96 bg-card border-border shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <CardHeader className="pb-3 border-b border-border/50">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={`p-2 rounded-lg ${getCellStatusColor(cell.status)}/20`}>
                <Battery className={`h-5 w-5`} style={{ color: fillColor }} />
              </div>
              <div>
                <CardTitle className="text-lg">Cell {cell.id}</CardTitle>
                <CardDescription>Detailed cell telemetry</CardDescription>
              </div>
            </div>
            <Button variant="ghost" size="sm" onClick={onClose}>
              <X className="h-4 w-4" />
            </Button>
          </div>
        </CardHeader>
        <CardContent className="pt-4 space-y-4">
          {/* Large cell visual */}
          <div className="flex justify-center py-2">
            <div className="relative">
              <svg viewBox="0 0 80 140" className="w-32 h-56">
                {/* Cell terminal */}
                <ellipse cx="40" cy="10" rx="16" ry="6" fill="#6b7280" />
                <rect x="24" y="10" width="32" height="8" fill="#6b7280" />

                <defs>
                  <linearGradient id="detailCellBody" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" stopColor="#374151" />
                    <stop offset="30%" stopColor="#4b5563" />
                    <stop offset="70%" stopColor="#4b5563" />
                    <stop offset="100%" stopColor="#374151" />
                  </linearGradient>
                  <linearGradient id="detailCellFill" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" stopColor={fillColor} stopOpacity="0.6" />
                    <stop offset="30%" stopColor={fillColor} stopOpacity="1" />
                    <stop offset="70%" stopColor={fillColor} stopOpacity="1" />
                    <stop offset="100%" stopColor={fillColor} stopOpacity="0.6" />
                  </linearGradient>
                  <linearGradient id="detailCellHighlight" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" stopColor="white" stopOpacity="0" />
                    <stop offset="35%" stopColor="white" stopOpacity="0.2" />
                    <stop offset="65%" stopColor="white" stopOpacity="0" />
                  </linearGradient>
                  <filter id="detailGlow">
                    <feGaussianBlur stdDeviation="2" result="coloredBlur" />
                    <feMerge>
                      <feMergeNode in="coloredBlur" />
                      <feMergeNode in="SourceGraphic" />
                    </feMerge>
                  </filter>
                </defs>

                {/* Outer cylinder */}
                <rect x="8" y="18" width="64" height="108" rx="6" fill="url(#detailCellBody)" />

                {/* Inner area */}
                <rect x="12" y="22" width="56" height="100" rx="4" fill="#1f2937" />

                {/* Fill level */}
                <rect
                  x="14"
                  y={24 + (96 * (100 - cell.soc)) / 100}
                  width="52"
                  height={(96 * cell.soc) / 100}
                  rx="3"
                  fill="url(#detailCellFill)"
                  filter="url(#detailGlow)"
                />

                {/* Highlight */}
                <rect x="8" y="18" width="64" height="108" rx="6" fill="url(#detailCellHighlight)" />

                {/* Bottom cap */}
                <ellipse cx="40" cy="126" rx="32" ry="6" fill="#374151" />

                {/* Top cap */}
                <ellipse cx="40" cy="18" rx="32" ry="6" fill="#4b5563" />

                {/* Status LED */}
                <circle cx="40" cy="18" r="6" fill={fillColor} filter="url(#detailGlow)">
                  {cell.status === "balancing" && (
                    <animate attributeName="opacity" values="1;0.3;1" dur="1s" repeatCount="indefinite" />
                  )}
                </circle>

                {/* SOC text */}
                <text x="40" y="80" textAnchor="middle" fill="white" fontSize="20" fontWeight="bold">
                  {cell.soc}%
                </text>
              </svg>
            </div>
          </div>

          {/* Status badge */}
          <div className="flex justify-center">
            <Badge className={`${getCellStatusColor(cell.status)} text-white px-4 py-1`}>
              {cell.status.charAt(0).toUpperCase() + cell.status.slice(1)}
            </Badge>
          </div>

          {/* Stats grid */}
          <div className="grid grid-cols-2 gap-3">
            <div className="p-4 rounded-xl bg-gradient-to-br from-amber-500/10 to-amber-500/5 border border-amber-500/20">
              <div className="flex items-center gap-2 mb-2">
                <Zap className="h-4 w-4 text-amber-500" />
                <span className="text-xs text-muted-foreground">Voltage</span>
              </div>
              <p className="text-2xl font-bold text-foreground">
                {cell.voltage.toFixed(3)}
                <span className="text-sm font-normal text-muted-foreground ml-1">V</span>
              </p>
              <div className="mt-2 h-1.5 bg-muted rounded-full overflow-hidden">
                <div
                  className="h-full bg-amber-500 rounded-full"
                  style={{ width: `${((cell.voltage - 2.5) / 1) * 100}%` }}
                />
              </div>
              <p className="text-[10px] text-muted-foreground mt-1">Range: 2.5V - 3.5V</p>
            </div>

            <div className="p-4 rounded-xl bg-gradient-to-br from-blue-500/10 to-blue-500/5 border border-blue-500/20">
              <div className="flex items-center gap-2 mb-2">
                <Activity className="h-4 w-4 text-blue-500" />
                <span className="text-xs text-muted-foreground">Current</span>
              </div>
              <p className="text-2xl font-bold text-foreground">
                {cell.current.toFixed(2)}
                <span className="text-sm font-normal text-muted-foreground ml-1">A</span>
              </p>
              <div className="mt-2 h-1.5 bg-muted rounded-full overflow-hidden">
                <div
                  className="h-full bg-blue-500 rounded-full"
                  style={{ width: `${(Math.abs(cell.current) / 5) * 100}%` }}
                />
              </div>
              <p className="text-[10px] text-muted-foreground mt-1">{cell.current >= 0 ? "Charging" : "Discharging"}</p>
            </div>

            <div className="p-4 rounded-xl bg-gradient-to-br from-green-500/10 to-green-500/5 border border-green-500/20">
              <div className="flex items-center gap-2 mb-2">
                <Gauge className="h-4 w-4 text-green-500" />
                <span className="text-xs text-muted-foreground">State of Charge</span>
              </div>
              <p className="text-2xl font-bold text-foreground">
                {cell.soc}
                <span className="text-sm font-normal text-muted-foreground ml-1">%</span>
              </p>
              <div className="mt-2 h-1.5 bg-muted rounded-full overflow-hidden">
                <div className="h-full bg-green-500 rounded-full" style={{ width: `${cell.soc}%` }} />
              </div>
              <p className="text-[10px] text-muted-foreground mt-1">Capacity remaining</p>
            </div>

            <div className="p-4 rounded-xl bg-gradient-to-br from-red-500/10 to-red-500/5 border border-red-500/20">
              <div className="flex items-center gap-2 mb-2">
                <Thermometer className="h-4 w-4" style={{ color: tempColor }} />
                <span className="text-xs text-muted-foreground">Temperature</span>
              </div>
              <p className="text-2xl font-bold text-foreground" style={{ color: tempColor }}>
                {cell.temperature}
                <span className="text-sm font-normal text-muted-foreground ml-1">°C</span>
              </p>
              <div className="mt-2 h-1.5 bg-muted rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full"
                  style={{ width: `${(cell.temperature / 50) * 100}%`, backgroundColor: tempColor }}
                />
              </div>
              <p className="text-[10px] text-muted-foreground mt-1">Optimal: 20-35°C</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export default function BatteriesPage() {
  const [expandedPacks, setExpandedPacks] = useState<string[]>(["PACK-001"])
  const [expandedBatteries, setExpandedBatteries] = useState<string[]>([])
  const [selectedCell, setSelectedCell] = useState<Cell | null>(null)

  const togglePack = (packId: string) => {
    setExpandedPacks((prev) => (prev.includes(packId) ? prev.filter((id) => id !== packId) : [...prev, packId]))
  }

  const toggleBattery = (batteryId: string) => {
    setExpandedBatteries((prev) =>
      prev.includes(batteryId) ? prev.filter((id) => id !== batteryId) : [...prev, batteryId],
    )
  }

  const totalCapacity = batteryPacks.reduce((acc, p) => acc + p.totalCapacity, 0)
  const totalBatteries = batteryPacks.reduce((acc, p) => acc + p.batteries.length, 0)
  const avgSoc = Math.round(
    batteryPacks.flatMap((p) => p.batteries).reduce((acc, b) => acc + b.soc, 0) / totalBatteries,
  )

  return (
    <div className="flex-1 p-6 space-y-6 overflow-auto">
      {/* Summary Cards */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Batteries</h1>
          <p className="text-muted-foreground">Monitor battery packs, individual batteries, and cell-level data</p>
        </div>
        <Button variant="outline" className="bg-transparent">
          <Settings className="h-4 w-4 mr-2" />
          Configure
        </Button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-4 gap-4">
        <Card className="bg-card/50 border-border/50">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-blue-500/20">
                <Battery className="h-5 w-5 text-blue-500" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Battery Packs</p>
                <p className="text-2xl font-bold text-foreground">{batteryPacks.length}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-card/50 border-border/50">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-green-500/20">
                <BatteryCharging className="h-5 w-5 text-green-500" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Total Batteries</p>
                <p className="text-2xl font-bold text-foreground">{totalBatteries}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-card/50 border-border/50">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-amber-500/20">
                <Zap className="h-5 w-5 text-amber-500" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Total Capacity</p>
                <p className="text-2xl font-bold text-foreground">{totalCapacity} kWh</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-card/50 border-border/50">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-purple-500/20">
                <Activity className="h-5 w-5 text-purple-500" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Average SOC</p>
                <p className="text-2xl font-bold text-foreground">{avgSoc}%</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Battery Packs */}
      <div className="space-y-4">
        {batteryPacks.map((pack) => (
          <Card key={pack.id} className="bg-card/50 border-border/50">
            <CardHeader
              className="cursor-pointer hover:bg-muted/30 transition-colors"
              onClick={() => togglePack(pack.id)}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  {expandedPacks.includes(pack.id) ? (
                    <ChevronDown className="h-5 w-5 text-muted-foreground" />
                  ) : (
                    <ChevronRight className="h-5 w-5 text-muted-foreground" />
                  )}
                  <div className="p-2 rounded-lg bg-blue-500/20">
                    <Battery className="h-5 w-5 text-blue-500" />
                  </div>
                  <div>
                    <CardTitle className="text-base">{pack.name}</CardTitle>
                    <CardDescription>
                      {pack.location} | {pack.batteries.length} batteries | {pack.totalCapacity} kWh
                    </CardDescription>
                  </div>
                </div>
                <Badge
                  className={pack.status === "online" ? "bg-green-500/20 text-green-500" : "bg-red-500/20 text-red-500"}
                >
                  {pack.status}
                </Badge>
              </div>
            </CardHeader>

            {expandedPacks.includes(pack.id) && (
              <CardContent className="pt-0 space-y-4">
                {pack.batteries.map((battery) => (
                  <div
                    key={battery.id}
                    className="border border-border/50 rounded-xl overflow-hidden bg-gradient-to-b from-muted/20 to-transparent"
                  >
                    <div
                      className="p-5 cursor-pointer hover:bg-muted/30 transition-colors"
                      onClick={() => toggleBattery(battery.id)}
                    >
                      <div className="flex items-start gap-6">
                        {/* Battery Visual */}
                        <BatteryVisual
                          soc={battery.soc}
                          status={battery.status}
                          isCharging={battery.status === "charging"}
                        />

                        {/* Battery Info */}
                        <div className="flex-1">
                          <div className="flex items-start justify-between mb-4">
                            <div className="flex items-center gap-2">
                              {expandedBatteries.includes(battery.id) ? (
                                <ChevronDown className="h-4 w-4 text-muted-foreground" />
                              ) : (
                                <ChevronRight className="h-4 w-4 text-muted-foreground" />
                              )}
                              <div>
                                <p className="font-semibold text-lg text-foreground">{battery.name}</p>
                                <p className="text-sm text-muted-foreground">
                                  {battery.model} | {battery.cells.length} cells
                                </p>
                              </div>
                            </div>
                            {getBatteryStatusBadge(battery.status)}
                          </div>

                          {/* Stats Row */}
                          <div className="grid grid-cols-5 gap-4">
                            <div className="p-3 rounded-lg bg-muted/50 border border-border/30">
                              <div className="flex items-center gap-1.5 mb-1">
                                <Zap className="h-3.5 w-3.5 text-amber-500" />
                                <span className="text-[10px] text-muted-foreground uppercase tracking-wide">
                                  Voltage
                                </span>
                              </div>
                              <p className="text-lg font-bold text-foreground">
                                {battery.voltage}
                                <span className="text-xs font-normal text-muted-foreground ml-0.5">V</span>
                              </p>
                            </div>
                            <div className="p-3 rounded-lg bg-muted/50 border border-border/30">
                              <div className="flex items-center gap-1.5 mb-1">
                                <Activity className="h-3.5 w-3.5 text-blue-500" />
                                <span className="text-[10px] text-muted-foreground uppercase tracking-wide">
                                  Current
                                </span>
                              </div>
                              <p
                                className={`text-lg font-bold ${battery.current >= 0 ? "text-green-500" : "text-blue-500"}`}
                              >
                                {battery.current > 0 ? "+" : ""}
                                {battery.current}
                                <span className="text-xs font-normal ml-0.5">A</span>
                              </p>
                            </div>
                            <div className="p-3 rounded-lg bg-muted/50 border border-border/30">
                              <div className="flex items-center gap-1.5 mb-1">
                                <Thermometer className="h-3.5 w-3.5 text-red-500" />
                                <span className="text-[10px] text-muted-foreground uppercase tracking-wide">Temp</span>
                              </div>
                              <p className="text-lg font-bold text-foreground">
                                {battery.temperature}
                                <span className="text-xs font-normal text-muted-foreground ml-0.5">°C</span>
                              </p>
                            </div>
                            <div className="p-3 rounded-lg bg-muted/50 border border-border/30">
                              <div className="flex items-center gap-1.5 mb-1">
                                <Heart className="h-3.5 w-3.5 text-pink-500" />
                                <span className="text-[10px] text-muted-foreground uppercase tracking-wide">
                                  Health
                                </span>
                              </div>
                              <p className="text-lg font-bold text-foreground">
                                {battery.health}
                                <span className="text-xs font-normal text-muted-foreground ml-0.5">%</span>
                              </p>
                            </div>
                            <div className="p-3 rounded-lg bg-muted/50 border border-border/30">
                              <div className="flex items-center gap-1.5 mb-1">
                                <Gauge className="h-3.5 w-3.5 text-green-500" />
                                <span className="text-[10px] text-muted-foreground uppercase tracking-wide">SOC</span>
                              </div>
                              <p className="text-lg font-bold text-foreground">
                                {battery.soc}
                                <span className="text-xs font-normal text-muted-foreground ml-0.5">%</span>
                              </p>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>

                    {expandedBatteries.includes(battery.id) && (
                      <div className="p-5 border-t border-border/50 bg-muted/10">
                        <div className="flex items-center justify-between mb-4">
                          <div>
                            <p className="font-medium text-foreground">Cell Bank</p>
                            <p className="text-xs text-muted-foreground">Click any cell for detailed telemetry</p>
                          </div>
                          <div className="flex items-center gap-4 text-xs">
                            <div className="flex items-center gap-1.5">
                              <div className="w-2.5 h-2.5 rounded-full bg-green-500" />
                              <span className="text-muted-foreground">Normal</span>
                            </div>
                            <div className="flex items-center gap-1.5">
                              <div className="w-2.5 h-2.5 rounded-full bg-amber-500" />
                              <span className="text-muted-foreground">Warning</span>
                            </div>
                            <div className="flex items-center gap-1.5">
                              <div className="w-2.5 h-2.5 rounded-full bg-red-500" />
                              <span className="text-muted-foreground">Critical</span>
                            </div>
                            <div className="flex items-center gap-1.5">
                              <div className="w-2.5 h-2.5 rounded-full bg-blue-500 animate-pulse" />
                              <span className="text-muted-foreground">Balancing</span>
                            </div>
                          </div>
                        </div>

                        <div className="flex flex-wrap gap-3 justify-center p-4 bg-gradient-to-b from-muted/30 to-muted/10 rounded-xl border border-border/30">
                          {battery.cells.map((cell) => (
                            <CellVisual key={cell.id} cell={cell} onClick={() => setSelectedCell(cell)} />
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </CardContent>
            )}
          </Card>
        ))}
      </div>

      {selectedCell && <CellDetailModal cell={selectedCell} onClose={() => setSelectedCell(null)} />}
    </div>
  )
}
