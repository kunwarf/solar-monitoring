import React from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import { Cpu, Activity, Thermometer, Zap, AlertTriangle, CheckCircle, Settings, RefreshCw } from 'lucide-react'
import { useV0Data } from '../data/V0DataProvider'

export const InvertersPage: React.FC = () => {
  const { inverters } = useV0Data()
  
  const totalInverters = inverters.length
  const onlineCount = inverters.filter(inv => inv.status === 'online').length
  const warningCount = inverters.filter(inv => inv.status === 'warning').length
  const totalOutput = inverters.reduce((sum, inv) => sum + inv.power, 0)

  return (
    <div className="flex-1 p-6 space-y-6 overflow-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Inverters</h1>
          <p className="text-muted-foreground">Monitor and manage your solar inverters</p>
        </div>
        <Button variant="outline" size="sm">
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh All
        </Button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-4 gap-4">
        <Card className="bg-card/50 border-border/50">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-primary/20">
                <Cpu className="h-5 w-5 text-primary" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Total Inverters</p>
                <p className="text-2xl font-bold text-foreground">{totalInverters}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-card/50 border-border/50">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-green-500/20">
                <CheckCircle className="h-5 w-5 text-green-500" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Online</p>
                <p className="text-2xl font-bold text-foreground">{onlineCount}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-card/50 border-border/50">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-yellow-500/20">
                <AlertTriangle className="h-5 w-5 text-yellow-500" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Warnings</p>
                <p className="text-2xl font-bold text-foreground">{warningCount}</p>
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
                <p className="text-sm text-muted-foreground">Total Output</p>
                <p className="text-2xl font-bold text-foreground">{totalOutput.toFixed(1)} kW</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Inverter Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
        {inverters.map((inverter) => (
          <Card key={inverter.id} className="bg-card/50 border-border/50">
            <CardHeader className="pb-3">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div
                    className={`p-2 rounded-lg ${inverter.status === 'online' ? 'bg-green-500/20' : 'bg-yellow-500/20'}`}
                  >
                    <Cpu className={`h-5 w-5 ${inverter.status === 'online' ? 'text-green-500' : 'text-yellow-500'}`} />
                  </div>
                  <div>
                    <CardTitle className="text-base">{inverter.name}</CardTitle>
                    <CardDescription>{inverter.model}</CardDescription>
                  </div>
                </div>
                <Badge
                  variant={inverter.status === 'online' ? 'default' : 'secondary'}
                  className={
                    inverter.status === 'online' ? 'bg-green-500/20 text-green-500' : 'bg-yellow-500/20 text-yellow-500'
                  }
                >
                  {inverter.status}
                </Badge>
              </div>
              {inverter.alert && (
                <div className="flex items-center gap-2 mt-2 p-2 rounded-lg bg-yellow-500/10 text-yellow-500 text-sm">
                  <AlertTriangle className="h-4 w-4" />
                  {inverter.alert}
                </div>
              )}
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Power Output Bar */}
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-muted-foreground">Power Output</span>
                  <span className="text-foreground font-medium">
                    {inverter.power} / {inverter.maxPower} kW
                  </span>
                </div>
                <div className="h-2 bg-muted rounded-full overflow-hidden">
                  <div
                    className="h-full bg-primary rounded-full transition-all"
                    style={{ width: `${(inverter.power / inverter.maxPower) * 100}%` }}
                  />
                </div>
              </div>

              {/* Stats Grid */}
              <div className="grid grid-cols-2 gap-3">
                <div className="p-2 rounded-lg bg-muted/50">
                  <div className="flex items-center gap-2 text-muted-foreground text-xs mb-1">
                    <Activity className="h-3 w-3" />
                    Efficiency
                  </div>
                  <p className="text-foreground font-medium">{inverter.efficiency}%</p>
                </div>
                <div className="p-2 rounded-lg bg-muted/50">
                  <div className="flex items-center gap-2 text-muted-foreground text-xs mb-1">
                    <Thermometer className="h-3 w-3" />
                    Temperature
                  </div>
                  <p className={`font-medium ${inverter.temperature > 50 ? 'text-yellow-500' : 'text-foreground'}`}>
                    {inverter.temperature}°C
                  </p>
                </div>
                <div className="p-2 rounded-lg bg-muted/50">
                  <div className="flex items-center gap-2 text-muted-foreground text-xs mb-1">
                    <Zap className="h-3 w-3" />
                    Voltage
                  </div>
                  <p className="text-foreground font-medium">{inverter.voltage}V</p>
                </div>
                <div className="p-2 rounded-lg bg-muted/50">
                  <div className="flex items-center gap-2 text-muted-foreground text-xs mb-1">
                    <Activity className="h-3 w-3" />
                    Frequency
                  </div>
                  <p className="text-foreground font-medium">{inverter.frequency} Hz</p>
                </div>
              </div>

              {/* Energy Stats */}
              <div className="flex justify-between pt-2 border-t border-border/50 text-sm">
                <div>
                  <p className="text-muted-foreground">Today</p>
                  <p className="text-foreground font-medium">{inverter.energyToday} kWh</p>
                </div>
                <div className="text-right">
                  <p className="text-muted-foreground">Lifetime</p>
                  <p className="text-foreground font-medium">{inverter.energyTotal.toLocaleString()} kWh</p>
                </div>
              </div>

              {/* Footer */}
              <div className="flex items-center justify-between pt-2 border-t border-border/50">
                <span className="text-xs text-muted-foreground">Updated {inverter.lastUpdate}</span>
                <Button variant="ghost" size="sm">
                  <Settings className="h-4 w-4" />
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}

