import React from 'react'
import { Card, CardHeader, CardTitle, CardContent } from './Card'
import { Badge } from './Badge'

interface HealthStatusCardProps {
  deviceSync?: { status: 'ok' | 'warning' | 'error'; lastUpdate?: string }
  temperature?: { status: 'normal' | 'warning' | 'critical' }
  imbalance?: { status: 'none' | 'detected' }
}

export const HealthStatusCard: React.FC<HealthStatusCardProps> = ({
  deviceSync,
  temperature,
  imbalance
}) => {
  return (
    <Card className="border-none">
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Alerts & Health</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        {deviceSync && (
          <div className="flex items-center justify-between">
            <div className="text-gray-500 dark:text-gray-400">Device Sync</div>
            <Badge variant="outline">
              {deviceSync.status === 'ok' ? 'OK' : deviceSync.status === 'warning' ? 'Warning' : 'Error'}
              {deviceSync.lastUpdate && ` • ${deviceSync.lastUpdate}`}
            </Badge>
          </div>
        )}
        {temperature && (
          <div className="flex items-center justify-between">
            <div className="text-gray-500 dark:text-gray-400">Temperature</div>
            <Badge variant={temperature.status === 'normal' ? 'secondary' : 'default'}>
              {temperature.status === 'normal' ? 'Normal' : temperature.status === 'warning' ? 'Warning' : 'Critical'}
            </Badge>
          </div>
        )}
        {imbalance && (
          <div className="flex items-center justify-between">
            <div className="text-gray-500 dark:text-gray-400">Imbalance</div>
            <Badge variant={imbalance.status === 'none' ? 'default' : 'secondary'}>
              {imbalance.status === 'none' ? 'None' : 'Detected'}
            </Badge>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

