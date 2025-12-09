import React from 'react'
import { Card, CardContent } from './Card'
import { Badge } from './Badge'

interface KPICardProps {
  icon: React.ComponentType<{ className?: string }>
  label: string
  value: string | number
  unit?: string
  trend?: 'up' | 'down' | null
}

export const KPICard: React.FC<KPICardProps> = ({ icon: Icon, label, value, unit, trend }) => {
  return (
    <Card className="border-none bg-gradient-to-b from-white/70 to-white/30 dark:from-gray-900/60 dark:to-gray-900/30 backdrop-blur-md">
      <CardContent className="p-4 sm:p-5">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
            <Icon className="h-5 w-5 text-blue-600 dark:text-blue-400" />
          </div>
          <div className="flex-1">
            <div className="text-xs text-gray-500 dark:text-gray-400">{label}</div>
            <div className="text-xl font-semibold tracking-tight text-gray-900 dark:text-gray-100">
              {value}
              {unit && <span className="ml-1 text-sm text-gray-500 dark:text-gray-400">{unit}</span>}
            </div>
          </div>
          {trend && (
            <Badge variant={trend === 'up' ? 'default' : 'secondary'} className="gap-1">
              {trend === 'up' ? '↑' : '↓'}
              {trend === 'up' ? 'Up' : 'Down'}
            </Badge>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

