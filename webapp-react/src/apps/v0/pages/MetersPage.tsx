import React from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import { Gauge, Activity, Zap, ArrowDown, ArrowUp, TrendingUp, TrendingDown, Settings, BarChart3 } from 'lucide-react'
import { useV0Data } from '../data/V0DataProvider'

export const MetersPage: React.FC = () => {
  const { meters } = useV0Data()
  
  return (
    <div className="flex-1 p-6 space-y-6 overflow-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Energy Meters</h1>
          <p className="text-muted-foreground">Real-time energy flow measurement</p>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-4 gap-4">
        <Card className="bg-card/50 border-border/50">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-amber-500/20">
                <Zap className="h-5 w-5 text-amber-500" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Solar Production</p>
                <p className="text-2xl font-bold text-foreground">12.8 kW</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-card/50 border-border/50">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-pink-500/20">
                <Activity className="h-5 w-5 text-pink-500" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Consumption</p>
                <p className="text-2xl font-bold text-foreground">4.2 kW</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-card/50 border-border/50">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-green-500/20">
                <TrendingUp className="h-5 w-5 text-green-500" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Grid Export</p>
                <p className="text-2xl font-bold text-green-500">2.4 kW</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-card/50 border-border/50">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-blue-500/20">
                <BarChart3 className="h-5 w-5 text-blue-500" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Self-Consumption</p>
                <p className="text-2xl font-bold text-foreground">81%</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Meter Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {meters.map((meter) => (
          <Card key={meter.id} className="bg-card/50 border-border/50">
            <CardHeader className="pb-3">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div
                    className={`p-2 rounded-lg ${
                      meter.type === 'Production'
                        ? 'bg-amber-500/20'
                        : meter.type === 'Consumption'
                          ? 'bg-pink-500/20'
                          : 'bg-green-500/20'
                    }`}
                  >
                    <Gauge
                      className={`h-5 w-5 ${
                        meter.type === 'Production'
                          ? 'text-amber-500'
                          : meter.type === 'Consumption'
                            ? 'text-pink-500'
                            : 'text-green-500'
                      }`}
                    />
                  </div>
                  <div>
                    <CardTitle className="text-base">{meter.name}</CardTitle>
                    <CardDescription>{meter.type}</CardDescription>
                  </div>
                </div>
                <Badge variant="secondary" className="bg-green-500/20 text-green-500">
                  {meter.status}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Current Power */}
              <div className="flex items-center justify-center p-4 rounded-lg bg-muted/50">
                <div className="text-center">
                  <div className="flex items-center justify-center gap-2">
                    {meter.currentPower < 0 ? (
                      <ArrowUp className="h-5 w-5 text-green-500" />
                    ) : (
                      <ArrowDown className="h-5 w-5 text-amber-500" />
                    )}
                    <span
                      className={`text-3xl font-bold ${meter.currentPower < 0 ? 'text-green-500' : 'text-foreground'}`}
                    >
                      {Math.abs(meter.currentPower).toFixed(1)} kW
                    </span>
                  </div>
                  <p className="text-sm text-muted-foreground mt-1">
                    {meter.currentPower < 0
                      ? 'Exporting to Grid'
                      : meter.type === 'Production'
                        ? 'Generating'
                        : 'Consuming'}
                  </p>
                </div>
              </div>

              {/* Stats Grid */}
              <div className="grid grid-cols-2 gap-3">
                <div className="p-2 rounded-lg bg-muted/50">
                  <p className="text-xs text-muted-foreground">Voltage</p>
                  <p className="text-foreground font-medium">{meter.voltage} V</p>
                </div>
                <div className="p-2 rounded-lg bg-muted/50">
                  <p className="text-xs text-muted-foreground">Current</p>
                  <p className="text-foreground font-medium">{meter.current} A</p>
                </div>
                <div className="p-2 rounded-lg bg-muted/50">
                  <p className="text-xs text-muted-foreground">Frequency</p>
                  <p className="text-foreground font-medium">{meter.frequency} Hz</p>
                </div>
                <div className="p-2 rounded-lg bg-muted/50">
                  <p className="text-xs text-muted-foreground">Power Factor</p>
                  <p className="text-foreground font-medium">{meter.powerFactor}</p>
                </div>
              </div>

              {/* Energy Stats */}
              {meter.type === 'Bidirectional' && (
                <div className="grid grid-cols-2 gap-3 pt-2 border-t border-border/50">
                  <div className="text-center">
                    <div className="flex items-center justify-center gap-1 text-red-400">
                      <TrendingDown className="h-4 w-4" />
                      <span className="font-medium">{meter.importToday} kWh</span>
                    </div>
                    <p className="text-xs text-muted-foreground">Import Today</p>
                  </div>
                  <div className="text-center">
                    <div className="flex items-center justify-center gap-1 text-green-500">
                      <TrendingUp className="h-4 w-4" />
                      <span className="font-medium">{meter.exportToday} kWh</span>
                    </div>
                    <p className="text-xs text-muted-foreground">Export Today</p>
                  </div>
                </div>
              )}
              {meter.type === 'Production' && (
                <div className="pt-2 border-t border-border/50 text-center">
                  <p className="text-2xl font-bold text-amber-500">{meter.productionToday} kWh</p>
                  <p className="text-sm text-muted-foreground">Production Today</p>
                </div>
              )}
              {meter.type === 'Consumption' && (
                <div className="pt-2 border-t border-border/50 text-center">
                  <p className="text-2xl font-bold text-pink-500">{meter.consumptionToday} kWh</p>
                  <p className="text-sm text-muted-foreground">Consumption Today</p>
                </div>
              )}

              {/* Footer */}
              <div className="flex items-center justify-between pt-2 border-t border-border/50">
                <span className="text-xs text-muted-foreground">Updated {meter.lastUpdate}</span>
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

