import React, { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { Switch } from '../components/ui/switch'
import { ArrowLeft, Sun, Zap, Activity, Clock, Shield, Save, RotateCcw, Thermometer, Gauge } from 'lucide-react'

// Mock inverter data - in real app this would come from API/database
const invertersData: Record<
  string,
  {
    id: string
    name: string
    model: string
    maxPower: number
    serial: string
    firmwareVersion: string
    installDate: string
  }
> = {
  'inv-1': {
    id: 'inv-1',
    name: 'Inverter 1',
    model: 'SolarEdge SE10K',
    maxPower: 10,
    serial: 'SE10K-2024-001',
    firmwareVersion: '4.12.35',
    installDate: '2024-01-15',
  },
  'inv-2': {
    id: 'inv-2',
    name: 'Inverter 2',
    model: 'SolarEdge SE10K',
    maxPower: 10,
    serial: 'SE10K-2024-002',
    firmwareVersion: '4.12.35',
    installDate: '2024-01-15',
  },
  'inv-3': {
    id: 'inv-3',
    name: 'Inverter 3',
    model: 'SolarEdge SE7K',
    maxPower: 7,
    serial: 'SE7K-2024-003',
    firmwareVersion: '4.12.35',
    installDate: '2024-02-20',
  },
  'inv-4': {
    id: 'inv-4',
    name: 'Roof Inverter',
    model: 'Fronius Primo 6.0',
    maxPower: 6,
    serial: 'FP6-2024-001',
    firmwareVersion: '3.24.7',
    installDate: '2024-03-10',
  },
}

interface InverterSettings {
  powerLimit: number
  exportLimit: number
  mpptEnabled: boolean
  gridSupportEnabled: boolean
  antiIslandingEnabled: boolean
  startupDelay: number
  reconnectDelay: number
  overTempThreshold: number
  underVoltageThreshold: number
  overVoltageThreshold: number
  reactiveControl: boolean
  frequencyResponse: boolean
}

export const InverterSettingsPage: React.FC = () => {
  const params = useParams<{ id: string }>()
  const navigate = useNavigate()
  const inverterId = params.id as string
  const inverter = invertersData[inverterId]

  const [settings, setSettings] = useState<InverterSettings>({
    powerLimit: 100,
    exportLimit: 80,
    mpptEnabled: true,
    gridSupportEnabled: true,
    antiIslandingEnabled: true,
    startupDelay: 60,
    reconnectDelay: 300,
    overTempThreshold: 75,
    underVoltageThreshold: 180,
    overVoltageThreshold: 270,
    reactiveControl: false,
    frequencyResponse: true,
  })

  const [hasChanges, setHasChanges] = useState(false)

  const updateSetting = <K extends keyof InverterSettings>(key: K, value: InverterSettings[K]) => {
    setSettings((prev) => ({ ...prev, [key]: value }))
    setHasChanges(true)
  }

  if (!inverter) {
    return (
      <div className="flex items-center justify-center h-full">
        <Card className="bg-card/50 border-border/50 p-8">
          <p className="text-muted-foreground">Inverter not found</p>
          <Button variant="outline" className="mt-4 bg-transparent" onClick={() => navigate('/v0/settings')}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Go Back
          </Button>
        </Card>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate('/v0/settings')}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-xl bg-amber-500/20">
              <Sun className="h-6 w-6 text-amber-500" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-foreground">{inverter.name} Settings</h1>
              <p className="text-muted-foreground">
                {inverter.model} | {inverter.maxPower} kW
              </p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            disabled={!hasChanges}
            onClick={() => {
              setSettings({
                powerLimit: 100,
                exportLimit: 80,
                mpptEnabled: true,
                gridSupportEnabled: true,
                antiIslandingEnabled: true,
                startupDelay: 60,
                reconnectDelay: 300,
                overTempThreshold: 75,
                underVoltageThreshold: 180,
                overVoltageThreshold: 270,
                reactiveControl: false,
                frequencyResponse: true,
              })
              setHasChanges(false)
            }}
          >
            <RotateCcw className="h-4 w-4 mr-2" />
            Reset
          </Button>
          <Button
            className="bg-amber-500 hover:bg-amber-600 text-black"
            disabled={!hasChanges}
            onClick={() => setHasChanges(false)}
          >
            <Save className="h-4 w-4 mr-2" />
            Save Changes
          </Button>
        </div>
      </div>

      {/* Device Info Card */}
      <Card className="bg-card/50 border-border/50">
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Device Information</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-4 gap-4">
            <div className="p-3 rounded-lg bg-muted/30">
              <p className="text-xs text-muted-foreground">Serial Number</p>
              <p className="text-sm font-medium text-foreground">{inverter.serial}</p>
            </div>
            <div className="p-3 rounded-lg bg-muted/30">
              <p className="text-xs text-muted-foreground">Firmware Version</p>
              <p className="text-sm font-medium text-foreground">{inverter.firmwareVersion}</p>
            </div>
            <div className="p-3 rounded-lg bg-muted/30">
              <p className="text-xs text-muted-foreground">Install Date</p>
              <p className="text-sm font-medium text-foreground">{inverter.installDate}</p>
            </div>
            <div className="p-3 rounded-lg bg-muted/30">
              <p className="text-xs text-muted-foreground">Max Power</p>
              <p className="text-sm font-medium text-foreground">{inverter.maxPower} kW</p>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-2 gap-6">
        {/* Power Settings */}
        <Card className="bg-card/50 border-border/50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Zap className="h-4 w-4 text-amber-500" />
              Power Settings
            </CardTitle>
            <CardDescription>Control power output and export limits</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="p-4 rounded-lg bg-muted/30">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <p className="text-sm font-medium text-foreground">Power Output Limit</p>
                  <p className="text-xs text-muted-foreground">Maximum power output percentage</p>
                </div>
                <span className="text-lg font-bold text-amber-500">{settings.powerLimit}%</span>
              </div>
              <input
                type="range"
                min="50"
                max="100"
                value={settings.powerLimit}
                onChange={(e) => updateSetting('powerLimit', Number.parseInt(e.target.value))}
                className="w-full h-2 bg-muted rounded-full appearance-none cursor-pointer accent-amber-500"
              />
              <div className="flex justify-between text-xs text-muted-foreground mt-1">
                <span>50%</span>
                <span>100%</span>
              </div>
            </div>

            <div className="p-4 rounded-lg bg-muted/30">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <p className="text-sm font-medium text-foreground">Grid Export Limit</p>
                  <p className="text-xs text-muted-foreground">Maximum export to grid</p>
                </div>
                <span className="text-lg font-bold text-green-500">{settings.exportLimit}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                value={settings.exportLimit}
                onChange={(e) => updateSetting('exportLimit', Number.parseInt(e.target.value))}
                className="w-full h-2 bg-muted rounded-full appearance-none cursor-pointer accent-green-500"
              />
              <div className="flex justify-between text-xs text-muted-foreground mt-1">
                <span>0%</span>
                <span>100%</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* MPPT & Grid Settings */}
        <Card className="bg-card/50 border-border/50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Activity className="h-4 w-4 text-blue-500" />
              MPPT & Grid Settings
            </CardTitle>
            <CardDescription>Maximum power point tracking and grid interaction</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between p-4 rounded-lg bg-muted/30">
              <div>
                <p className="text-sm font-medium text-foreground">MPPT Optimization</p>
                <p className="text-xs text-muted-foreground">Advanced maximum power point tracking</p>
              </div>
              <Switch checked={settings.mpptEnabled} onCheckedChange={(v) => updateSetting('mpptEnabled', v)} />
            </div>
            <div className="flex items-center justify-between p-4 rounded-lg bg-muted/30">
              <div>
                <p className="text-sm font-medium text-foreground">Grid Support Mode</p>
                <p className="text-xs text-muted-foreground">Provide voltage and frequency support</p>
              </div>
              <Switch
                checked={settings.gridSupportEnabled}
                onCheckedChange={(v) => updateSetting('gridSupportEnabled', v)}
              />
            </div>
            <div className="flex items-center justify-between p-4 rounded-lg bg-muted/30">
              <div>
                <p className="text-sm font-medium text-foreground">Anti-Islanding Protection</p>
                <p className="text-xs text-muted-foreground">Disconnect during grid outages</p>
              </div>
              <Switch
                checked={settings.antiIslandingEnabled}
                onCheckedChange={(v) => updateSetting('antiIslandingEnabled', v)}
              />
            </div>
            <div className="flex items-center justify-between p-4 rounded-lg bg-muted/30">
              <div>
                <p className="text-sm font-medium text-foreground">Reactive Power Control</p>
                <p className="text-xs text-muted-foreground">Enable VAR management</p>
              </div>
              <Switch checked={settings.reactiveControl} onCheckedChange={(v) => updateSetting('reactiveControl', v)} />
            </div>
            <div className="flex items-center justify-between p-4 rounded-lg bg-muted/30">
              <div>
                <p className="text-sm font-medium text-foreground">Frequency Response</p>
                <p className="text-xs text-muted-foreground">Automatic frequency regulation</p>
              </div>
              <Switch
                checked={settings.frequencyResponse}
                onCheckedChange={(v) => updateSetting('frequencyResponse', v)}
              />
            </div>
          </CardContent>
        </Card>

        {/* Timing Settings */}
        <Card className="bg-card/50 border-border/50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Clock className="h-4 w-4 text-purple-500" />
              Timing Settings
            </CardTitle>
            <CardDescription>Startup and reconnection delays</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="p-4 rounded-lg bg-muted/30">
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm font-medium text-foreground">Startup Delay</p>
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    value={settings.startupDelay}
                    onChange={(e) => updateSetting('startupDelay', Number.parseInt(e.target.value))}
                    className="w-20 px-2 py-1 text-right text-sm bg-background border border-border rounded"
                  />
                  <span className="text-sm text-muted-foreground">sec</span>
                </div>
              </div>
              <p className="text-xs text-muted-foreground">Time to wait before starting after power-on</p>
            </div>
            <div className="p-4 rounded-lg bg-muted/30">
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm font-medium text-foreground">Reconnect Delay</p>
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    value={settings.reconnectDelay}
                    onChange={(e) => updateSetting('reconnectDelay', Number.parseInt(e.target.value))}
                    className="w-20 px-2 py-1 text-right text-sm bg-background border border-border rounded"
                  />
                  <span className="text-sm text-muted-foreground">sec</span>
                </div>
              </div>
              <p className="text-xs text-muted-foreground">Time to wait before reconnecting after grid fault</p>
            </div>
          </CardContent>
        </Card>

        {/* Protection Settings */}
        <Card className="bg-card/50 border-border/50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Shield className="h-4 w-4 text-red-500" />
              Protection Thresholds
            </CardTitle>
            <CardDescription>Safety limits and protection settings</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="p-4 rounded-lg bg-muted/30">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <Thermometer className="h-4 w-4 text-red-500" />
                  <p className="text-sm font-medium text-foreground">Over Temperature</p>
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    value={settings.overTempThreshold}
                    onChange={(e) => updateSetting('overTempThreshold', Number.parseInt(e.target.value))}
                    className="w-20 px-2 py-1 text-right text-sm bg-background border border-border rounded"
                  />
                  <span className="text-sm text-muted-foreground">°C</span>
                </div>
              </div>
              <p className="text-xs text-muted-foreground">Shut down when temperature exceeds this value</p>
            </div>
            <div className="p-4 rounded-lg bg-muted/30">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <Gauge className="h-4 w-4 text-amber-500" />
                  <p className="text-sm font-medium text-foreground">Under Voltage</p>
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    value={settings.underVoltageThreshold}
                    onChange={(e) => updateSetting('underVoltageThreshold', Number.parseInt(e.target.value))}
                    className="w-20 px-2 py-1 text-right text-sm bg-background border border-border rounded"
                  />
                  <span className="text-sm text-muted-foreground">V</span>
                </div>
              </div>
              <p className="text-xs text-muted-foreground">Disconnect when grid voltage drops below</p>
            </div>
            <div className="p-4 rounded-lg bg-muted/30">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <Gauge className="h-4 w-4 text-red-500" />
                  <p className="text-sm font-medium text-foreground">Over Voltage</p>
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    value={settings.overVoltageThreshold}
                    onChange={(e) => updateSetting('overVoltageThreshold', Number.parseInt(e.target.value))}
                    className="w-20 px-2 py-1 text-right text-sm bg-background border border-border rounded"
                  />
                  <span className="text-sm text-muted-foreground">V</span>
                </div>
              </div>
              <p className="text-xs text-muted-foreground">Disconnect when grid voltage exceeds</p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

