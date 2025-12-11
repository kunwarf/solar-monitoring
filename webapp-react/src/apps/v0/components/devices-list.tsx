import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { Badge } from './ui/badge'
import { Button } from './ui/button'
import { Cpu, Battery, Gauge, MoreVertical, CheckCircle, AlertTriangle, ChevronRight } from 'lucide-react'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from './ui/dropdown-menu'
import { useV0Data } from '../data/V0DataProvider'

const getIcon = (type: string) => {
  switch (type) {
    case 'inverter':
      return Cpu
    case 'battery':
      return Battery
    case 'meter':
      return Gauge
    default:
      return Cpu
  }
}

const getStatusColor = (status: string) => {
  switch (status) {
    case 'online':
      return 'bg-emerald-400/20 text-emerald-400'
    case 'warning':
      return 'bg-yellow-400/20 text-yellow-400'
    case 'offline':
      return 'bg-red-400/20 text-red-400'
    default:
      return 'bg-muted text-muted-foreground'
  }
}

export function DevicesList() {
  const { devices } = useV0Data()

  return (
    <Card className="bg-card border-border">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-lg font-medium text-foreground">Connected Devices</CardTitle>
        <Button variant="ghost" size="sm" className="text-muted-foreground">
          View all
          <ChevronRight className="h-4 w-4 ml-1" />
        </Button>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {devices.map((device) => {
            const Icon = getIcon(device.type)
            return (
              <div
                key={device.id}
                className="flex items-center gap-4 p-3 rounded-lg bg-secondary/50 hover:bg-secondary transition-colors"
              >
                <div className="p-2 rounded-lg bg-card">
                  <Icon className="h-5 w-5 text-muted-foreground" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-foreground truncate">{device.name}</span>
                    <Badge variant="secondary" className={getStatusColor(device.status)}>
                      {device.status === 'online' && <CheckCircle className="h-3 w-3 mr-1" />}
                      {device.status === 'warning' && <AlertTriangle className="h-3 w-3 mr-1" />}
                      {device.status}
                    </Badge>
                  </div>
                  <p className="text-sm text-muted-foreground truncate">{device.model}</p>
                </div>
                <div className="hidden sm:flex items-center gap-6 text-sm">
                  {device.type === 'inverter' && (
                    <>
                      <div className="text-right">
                        <p className="text-muted-foreground">Output</p>
                        <p className="font-medium text-foreground">{device.output}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-muted-foreground">Efficiency</p>
                        <p className="font-medium text-foreground">{device.efficiency}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-muted-foreground">Temp</p>
                        <p
                          className={`font-medium ${device.temperature === '55°C' ? 'text-yellow-400' : 'text-foreground'}`}
                        >
                          {device.temperature}
                        </p>
                      </div>
                    </>
                  )}
                  {device.type === 'battery' && (
                    <>
                      <div className="text-right">
                        <p className="text-muted-foreground">Charge</p>
                        <p className="font-medium text-blue-400">{device.charge}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-muted-foreground">Power</p>
                        <p className="font-medium text-emerald-400">{device.power}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-muted-foreground">Cycles</p>
                        <p className="font-medium text-foreground">{device.cycles}</p>
                      </div>
                    </>
                  )}
                  {device.type === 'meter' && (
                    <>
                      <div className="text-right">
                        <p className="text-muted-foreground">Usage</p>
                        <p className="font-medium text-pink-400">{device.consumption}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-muted-foreground">Export</p>
                        <p className="font-medium text-emerald-400">{device.export}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-muted-foreground">Voltage</p>
                        <p className="font-medium text-foreground">{device.voltage}</p>
                      </div>
                    </>
                  )}
                </div>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" size="icon" className="h-8 w-8">
                      <MoreVertical className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem>View Details</DropdownMenuItem>
                    <DropdownMenuItem>View Telemetry</DropdownMenuItem>
                    <DropdownMenuItem>Settings</DropdownMenuItem>
                    <DropdownMenuItem>Restart Device</DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}

