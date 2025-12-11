import React from 'react'
import { Card } from './ui/card'
import { Sun, Battery, Zap, TrendingUp, ArrowUpRight, ArrowDownRight } from 'lucide-react'
import { useV0Data } from '../data/V0DataProvider'

// Icon mapping for stats
const iconMap: Record<string, any> = {
  'Solar Production': Sun,
  'Battery Storage': Battery,
  'Home Consumption': Zap,
  'Grid Export': TrendingUp,
  'Grid Import': TrendingUp,
}

export function StatsCards() {
  const { stats } = useV0Data()

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {stats.map((stat) => {
        const Icon = iconMap[stat.label] || Sun
        return (
          <Card key={stat.label} className="bg-card border-border p-4">
            <div className="flex items-start justify-between">
              <div className={`p-2 rounded-lg ${stat.bgColor}`}>
                <Icon className={`h-5 w-5 ${stat.color}`} />
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
        )
      })}
    </div>
  )
}

