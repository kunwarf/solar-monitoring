import React from 'react'
import { Card, CardHeader, CardTitle, CardContent } from './Card'
import { Badge } from './Badge'
import { SOCRing } from './SOCRing'

interface BatteryPackCardProps {
  name: string
  soc: number
  powerW: number
  voltage?: number
  temperature?: number
}

export const BatteryPackCard: React.FC<BatteryPackCardProps> = ({
  name,
  soc,
  powerW,
  voltage,
  temperature
}) => {
  return (
    <Card className="border-none">
      <CardHeader className="pb-0">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <span className="text-xl">🔋</span>
            {name}
          </CardTitle>
          <Badge variant={powerW >= 0 ? 'secondary' : 'default'}>
            {powerW >= 0 ? 'Charging' : 'Discharging'}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="pt-3">
        <div className="flex items-center gap-4">
          <SOCRing soc={soc * 100} size={80} strokeWidth={8} />
          <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
            <div className="text-gray-500 dark:text-gray-400">Power</div>
            <div className="font-medium text-gray-900 dark:text-gray-100">{Math.abs(powerW)} W</div>
            {voltage !== undefined && (
              <>
                <div className="text-gray-500 dark:text-gray-400">Voltage</div>
                <div className="font-medium text-gray-900 dark:text-gray-100">{voltage.toFixed(2)} V</div>
              </>
            )}
            {temperature !== undefined && (
              <>
                <div className="text-gray-500 dark:text-gray-400">Temp</div>
                <div className="font-medium text-gray-900 dark:text-gray-100">{temperature.toFixed(1)} °C</div>
              </>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

