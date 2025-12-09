"use client"

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Area, AreaChart, ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid } from "recharts"

const solarData = [
  { time: "06:00", value: 0.2 },
  { time: "08:00", value: 2.1 },
  { time: "10:00", value: 5.4 },
  { time: "12:00", value: 8.2 },
  { time: "14:00", value: 8.4 },
  { time: "16:00", value: 6.1 },
  { time: "18:00", value: 2.8 },
  { time: "20:00", value: 0.1 },
]

const consumptionData = [
  { time: "06:00", value: 1.2 },
  { time: "08:00", value: 2.8 },
  { time: "10:00", value: 2.1 },
  { time: "12:00", value: 3.5 },
  { time: "14:00", value: 2.9 },
  { time: "16:00", value: 3.2 },
  { time: "18:00", value: 4.1 },
  { time: "20:00", value: 3.8 },
]

interface EnergyChartProps {
  title: string
  subtitle: string
  color: "solar" | "consumption"
}

const colorConfig = {
  solar: {
    stroke: "#facc15",
    fill: "#facc15",
  },
  consumption: {
    stroke: "#ec4899",
    fill: "#ec4899",
  },
}

export function EnergyChart({ title, subtitle, color }: EnergyChartProps) {
  const data = color === "solar" ? solarData : consumptionData
  const colors = colorConfig[color]

  return (
    <Card className="bg-card border-border">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-lg font-medium text-foreground">{title}</CardTitle>
            <CardDescription className="text-muted-foreground">{subtitle}</CardDescription>
          </div>
          <div className="text-right">
            <p className="text-2xl font-semibold" style={{ color: colors.stroke }}>
              {color === "solar" ? "42.3" : "28.6"} kWh
            </p>
            <p className="text-xs text-muted-foreground">Today's total</p>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="h-[200px] mt-4">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data}>
              <defs>
                <linearGradient id={`gradient-${color}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={colors.fill} stopOpacity={0.3} />
                  <stop offset="100%" stopColor={colors.fill} stopOpacity={0.05} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#2a2d3e" vertical={false} />
              <XAxis dataKey="time" axisLine={false} tickLine={false} tick={{ fill: "#6b7280", fontSize: 12 }} />
              <YAxis
                axisLine={false}
                tickLine={false}
                tick={{ fill: "#6b7280", fontSize: 12 }}
                tickFormatter={(value) => `${value}kW`}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#1e1e2e",
                  border: "1px solid #2a2d3e",
                  borderRadius: "8px",
                  color: "#fff",
                }}
                labelStyle={{ color: "#9ca3af" }}
              />
              <Area
                type="monotone"
                dataKey="value"
                stroke={colors.stroke}
                strokeWidth={2}
                fill={`url(#gradient-${color})`}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}
