import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { Button } from './ui/button'
import { Badge } from './ui/badge'
import { Bell, AlertTriangle, Info, CheckCircle, X } from 'lucide-react'

const alerts = [
  {
    id: 1,
    type: 'warning',
    title: 'High Temperature Alert',
    message: 'Inverter Array 3 running at 55°C. Consider checking ventilation.',
    time: '10 min ago',
  },
  {
    id: 2,
    type: 'info',
    title: 'Firmware Update Available',
    message: 'New firmware v2.4.1 available for Powerwall units.',
    time: '2 hours ago',
  },
  {
    id: 3,
    type: 'success',
    title: 'Peak Production Reached',
    message: 'System reached peak production of 8.4 kW today at 2:15 PM.',
    time: '4 hours ago',
  },
]

const getAlertConfig = (type: string) => {
  switch (type) {
    case 'warning':
      return {
        icon: AlertTriangle,
        color: 'text-yellow-400',
        bg: 'bg-yellow-400/10',
        border: 'border-yellow-400/20',
      }
    case 'info':
      return {
        icon: Info,
        color: 'text-blue-400',
        bg: 'bg-blue-400/10',
        border: 'border-blue-400/20',
      }
    case 'success':
      return {
        icon: CheckCircle,
        color: 'text-emerald-400',
        bg: 'bg-emerald-400/10',
        border: 'border-emerald-400/20',
      }
    default:
      return {
        icon: Bell,
        color: 'text-muted-foreground',
        bg: 'bg-muted',
        border: 'border-muted',
      }
  }
}

export function AlertsCard() {
  return (
    <Card className="bg-card border-border h-full">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-lg font-medium text-foreground">System Alerts</CardTitle>
        <Badge variant="secondary" className="bg-destructive/20 text-destructive">
          {alerts.length} new
        </Badge>
      </CardHeader>
      <CardContent className="space-y-3">
        {alerts.map((alert) => {
          const config = getAlertConfig(alert.type)
          const Icon = config.icon
          return (
            <div key={alert.id} className={`p-3 rounded-lg ${config.bg} border ${config.border} relative group`}>
              <Button
                variant="ghost"
                size="icon"
                className="absolute top-2 right-2 h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity"
              >
                <X className="h-3 w-3" />
              </Button>
              <div className="flex items-start gap-3">
                <Icon className={`h-5 w-5 ${config.color} shrink-0 mt-0.5`} />
                <div className="flex-1 min-w-0 pr-6">
                  <p className="font-medium text-foreground text-sm">{alert.title}</p>
                  <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{alert.message}</p>
                  <p className="text-xs text-muted-foreground/60 mt-2">{alert.time}</p>
                </div>
              </div>
            </div>
          )
        })}

        <Button variant="ghost" className="w-full text-muted-foreground hover:text-foreground">
          View All Alerts
        </Button>
      </CardContent>
    </Card>
  )
}

