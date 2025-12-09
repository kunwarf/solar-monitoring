import React from 'react'
import { Card } from './ui/card'
import { Sun, Battery, Zap, TrendingUp, ArrowUpRight, ArrowDownRight } from 'lucide-react'

const stats = [
  {
    label: 'Solar Production',
    value: '8.4',
    unit: 'kW',
    change: '+12%',
    trend: 'up',
    icon: Sun,
    color: 'text-yellow-400',
    bgColor: 'bg-yellow-400/10',
  },
  {
    label: 'Battery Storage',
    value: '76',
    unit: '%',
    change: 'Charging',
    trend: 'up',
    icon: Battery,
    color: 'text-blue-400',
    bgColor: 'bg-blue-400/10',
  },
  {
    label: 'Home Consumption',
    value: '3.2',
    unit: 'kW',
    change: '-8%',
    trend: 'down',
    icon: Zap,
    color: 'text-pink-400',
    bgColor: 'bg-pink-400/10',
  },
  {
    label: 'Grid Export',
    value: '5.2',
    unit: 'kW',
    change: '+24%',
    trend: 'up',
    icon: TrendingUp,
    color: 'text-emerald-400',
    bgColor: 'bg-emerald-400/10',
  },
]

export function StatsCards() {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {stats.map((stat) => (
        <Card key={stat.label} className="bg-card border-border p-4">
          <div className="flex items-start justify-between">
            <div className={`p-2 rounded-lg ${stat.bgColor}`}>
              <stat.icon className={`h-5 w-5 ${stat.color}`} />
            </div>
            <div
              className={`flex items-center gap-1 text-xs ${
                stat.trend === 'up' ? 'text-emerald-400' : 'text-pink-400'
              }`}
            >
              {stat.trend === 'up' ? <ArrowUpRight className="h-3 w-3" /> : <ArrowDownRight className="h-3 w-3" />}
              {stat.change}
            </div>
          </div>
          <div className="mt-3">
            <div className="flex items-baseline gap-1">
              <span className="text-3xl font-semibold text-foreground">{stat.value}</span>
              <span className="text-lg text-muted-foreground">{stat.unit}</span>
            </div>
            <p className="text-sm text-muted-foreground mt-1">{stat.label}</p>
          </div>
        </Card>
      ))}
    </div>
  )
}

