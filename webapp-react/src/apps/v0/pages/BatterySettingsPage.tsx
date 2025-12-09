import React, { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { Switch } from '../components/ui/switch'
import { ArrowLeft, Battery, Zap, Thermometer, Clock, Save, RotateCcw, Activity } from 'lucide-react'

// Mock battery data - in real app this would come from API/database
const batteriesData: Record<
  string,
  {
    id: string
    name: string
    model: string
    capacity: number
    serial: string
    firmwareVersion: string
    installDate: string
    cellCount: number
  }
> = {
  'bat-1': {
    id: 'bat-1',
    name: 'Battery A1',
    model: 'Tesla Powerwall 2',
    capacity: 13.5,
    serial: 'PW2-2024-001',
    firmwareVersion: '23.44.2',
    installDate: '2024-01-15',
    cellCount: 16,
  },
  'bat-2': {
    id: 'bat-2',
    name: 'Battery A2',
    model: 'Tesla Powerwall 2',
    capacity: 13.5,
    serial: 'PW2-2024-002',
    firmwareVersion: '23.44.2',
    installDate: '2024-01-15',
    cellCount: 16,
  },
  'bat-3': {
    id: 'bat-3',
    name: 'Battery B1',
    model: 'LG RESU 10H',
    capacity: 9.8,
    serial: 'LG10H-2024-001',
    firmwareVersion: '1.8.4',
    installDate: '2024-02-20',
    cellCount: 14,
  },
  'bat-4': {
    id: 'bat-4',
    name: 'Garage Battery',
    model: 'BYD Battery-Box',
    capacity: 10.2,
    serial: 'BYD-2024-001',
    firmwareVersion: '2.1.0',
    installDate: '2024-03-10',
    cellCount: 16,
  },
}

interface BatterySettings {
  minReserve: number
  maxChargeRate: number
  maxDischargeRate: number
  cellBalancingEnabled: boolean
  tempProtectionEnabled: boolean
  maxChargeTemp: number
  minChargeTemp: number
  depthOfDischarge: number
  forcedChargeEnabled: boolean
  forcedChargeTime: string
  forcedChargeTarget: number
  gridChargingEnabled: boolean
  peakShavingEnabled: boolean
  peakShavingThreshold: number
}

export const BatterySettingsPage: React.FC = () => {
  const params = useParams<{ id: string }>()
  const navigate = useNavigate()
  const batteryId = params.id as string
  const battery = batteriesData[batteryId]

  const [settings, setSettings] = useState<BatterySettings>({
    minReserve: 20,
    maxChargeRate: 100,
    maxDischargeRate: 100,
    cellBalancingEnabled: true,
    tempProtectionEnabled: true,
    maxChargeTemp: 45,
    minChargeTemp: 5,
    depthOfDischarge: 90,
    forcedChargeEnabled: false,
    forcedChargeTime: '02:00',
    forcedChargeTarget: 100,
    gridChargingEnabled: true,
    peakShavingEnabled: true,
    peakShavingThreshold: 5000,
  })

  const [hasChanges, setHasChanges] = useState(false)

  const updateSetting = <K extends keyof BatterySettings>(key: K, value: BatterySettings[K]) => {
    setSettings((prev) => ({ ...prev, [key]: value }))
    setHasChanges(true)
  }

  if (!battery) {
    return (
      <div className="flex items-center justify-center h-full">
        <Card className="bg-card/50 border-border/50 p-8">
          <p className="text-muted-foreground">Battery not found</p>
          <Button variant="outline" className="mt-4 bg-transparent" onClick={() => navigate(-1)}>
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
            <div className="p-3 rounded-xl bg-blue-500/20">
              <Battery className="h-6 w-6 text-blue-500" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-foreground">{battery.name} Settings</h1>
              <p className="text-muted-foreground">
                {battery.model} | {battery.capacity} kWh
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
                minReserve: 20,
                maxChargeRate: 100,
                maxDischargeRate: 100,
                cellBalancingEnabled: true,
                tempProtectionEnabled: true,
                maxChargeTemp: 45,
                minChargeTemp: 5,
                depthOfDischarge: 90,
                forcedChargeEnabled: false,
                forcedChargeTime: '02:00',
                forcedChargeTarget: 100,
                gridChargingEnabled: true,
                peakShavingEnabled: true,
                peakShavingThreshold: 5000,
              })
              setHasChanges(false)
            }}
          >
            <RotateCcw className="h-4 w-4 mr-2" />
            Reset
          </Button>
          <Button
            className="bg-blue-500 hover:bg-blue-600 text-white"
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
          <div className="grid grid-cols-5 gap-4">
            <div className="p-3 rounded-lg bg-muted/30">
              <p className="text-xs text-muted-foreground">Serial Number</p>
              <p className="text-sm font-medium text-foreground">{battery.serial}</p>
            </div>
            <div className="p-3 rounded-lg bg-muted/30">
              <p className="text-xs text-muted-foreground">Firmware Version</p>
              <p className="text-sm font-medium text-foreground">{battery.firmwareVersion}</p>
            </div>
            <div className="p-3 rounded-lg bg-muted/30">
              <p className="text-xs text-muted-foreground">Install Date</p>
              <p className="text-sm font-medium text-foreground">{battery.installDate}</p>
            </div>
            <div className="p-3 rounded-lg bg-muted/30">
              <p className="text-xs text-muted-foreground">Capacity</p>
              <p className="text-sm font-medium text-foreground">{battery.capacity} kWh</p>
            </div>
            <div className="p-3 rounded-lg bg-muted/30">
              <p className="text-xs text-muted-foreground">Cell Count</p>
              <p className="text-sm font-medium text-foreground">{battery.cellCount} cells</p>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-2 gap-6">
        {/* Charge/Discharge Settings */}
        <Card className="bg-card/50 border-border/50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Zap className="h-4 w-4 text-blue-500" />
              Charge / Discharge Settings
            </CardTitle>
            <CardDescription>Control charging and discharging behavior</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="p-4 rounded-lg bg-muted/30">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <p className="text-sm font-medium text-foreground">Minimum Reserve</p>
                  <p className="text-xs text-muted-foreground">Keep battery above this level</p>
                </div>
                <span className="text-lg font-bold text-blue-500">{settings.minReserve}%</span>
              </div>
              <input
                type="range"
                min="5"
                max="50"
                value={settings.minReserve}
                onChange={(e) => updateSetting('minReserve', Number.parseInt(e.target.value))}
                className="w-full h-2 bg-muted rounded-full appearance-none cursor-pointer accent-blue-500"
              />
              <div className="flex justify-between text-xs text-muted-foreground mt-1">
                <span>5%</span>
                <span>50%</span>
              </div>
            </div>

            <div className="p-4 rounded-lg bg-muted/30">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <p className="text-sm font-medium text-foreground">Depth of Discharge</p>
                  <p className="text-xs text-muted-foreground">Maximum usable capacity</p>
                </div>
                <span className="text-lg font-bold text-green-500">{settings.depthOfDischarge}%</span>
              </div>
              <input
                type="range"
                min="50"
                max="100"
                value={settings.depthOfDischarge}
                onChange={(e) => updateSetting('depthOfDischarge', Number.parseInt(e.target.value))}
                className="w-full h-2 bg-muted rounded-full appearance-none cursor-pointer accent-green-500"
              />
              <div className="flex justify-between text-xs text-muted-foreground mt-1">
                <span>50%</span>
                <span>100%</span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="p-4 rounded-lg bg-muted/30">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-sm font-medium text-foreground">Max Charge</p>
                  <span className="text-sm font-bold text-green-500">{settings.maxChargeRate}%</span>
                </div>
                <input
                  type="range"
                  min="10"
                  max="100"
                  value={settings.maxChargeRate}
                  onChange={(e) => updateSetting('maxChargeRate', Number.parseInt(e.target.value))}
                  className="w-full h-2 bg-muted rounded-full appearance-none cursor-pointer accent-green-500"
                />
              </div>
              <div className="p-4 rounded-lg bg-muted/30">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-sm font-medium text-foreground">Max Discharge</p>
                  <span className="text-sm font-bold text-amber-500">{settings.maxDischargeRate}%</span>
                </div>
                <input
                  type="range"
                  min="10"
                  max="100"
                  value={settings.maxDischargeRate}
                  onChange={(e) => updateSetting('maxDischargeRate', Number.parseInt(e.target.value))}
                  className="w-full h-2 bg-muted rounded-full appearance-none cursor-pointer accent-amber-500"
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Cell Management */}
        <Card className="bg-card/50 border-border/50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Activity className="h-4 w-4 text-purple-500" />
              Cell Management
            </CardTitle>
            <CardDescription>Battery cell balancing and monitoring</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between p-4 rounded-lg bg-muted/30">
              <div>
                <p className="text-sm font-medium text-foreground">Cell Balancing</p>
                <p className="text-xs text-muted-foreground">Automatic cell voltage equalization</p>
              </div>
              <Switch
                checked={settings.cellBalancingEnabled}
                onCheckedChange={(v) => updateSetting('cellBalancingEnabled', v)}
              />
            </div>
            <div className="flex items-center justify-between p-4 rounded-lg bg-muted/30">
              <div>
                <p className="text-sm font-medium text-foreground">Grid Charging</p>
                <p className="text-xs text-muted-foreground">Allow charging from grid during off-peak</p>
              </div>
              <Switch
                checked={settings.gridChargingEnabled}
                onCheckedChange={(v) => updateSetting('gridChargingEnabled', v)}
              />
            </div>
            <div className="flex items-center justify-between p-4 rounded-lg bg-muted/30">
              <div>
                <p className="text-sm font-medium text-foreground">Peak Shaving</p>
                <p className="text-xs text-muted-foreground">Reduce grid demand during peaks</p>
              </div>
              <Switch
                checked={settings.peakShavingEnabled}
                onCheckedChange={(v) => updateSetting('peakShavingEnabled', v)}
              />
            </div>
            {settings.peakShavingEnabled && (
              <div className="p-4 rounded-lg bg-muted/30 ml-4 border-l-2 border-purple-500">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-sm font-medium text-foreground">Threshold</p>
                  <div className="flex items-center gap-2">
                    <input
                      type="number"
                      value={settings.peakShavingThreshold}
                      onChange={(e) => updateSetting('peakShavingThreshold', Number.parseInt(e.target.value))}
                      className="w-24 px-2 py-1 text-right text-sm bg-background border border-border rounded"
                    />
                    <span className="text-sm text-muted-foreground">W</span>
                  </div>
                </div>
                <p className="text-xs text-muted-foreground">Activate when grid demand exceeds</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Temperature Protection */}
        <Card className="bg-card/50 border-border/50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Thermometer className="h-4 w-4 text-red-500" />
              Temperature Protection
            </CardTitle>
            <CardDescription>Temperature limits for safe operation</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between p-4 rounded-lg bg-muted/30">
              <div>
                <p className="text-sm font-medium text-foreground">Temperature Protection</p>
                <p className="text-xs text-muted-foreground">Enable temperature-based charge limiting</p>
              </div>
              <Switch
                checked={settings.tempProtectionEnabled}
                onCheckedChange={(v) => updateSetting('tempProtectionEnabled', v)}
              />
            </div>

            {settings.tempProtectionEnabled && (
              <>
                <div className="p-4 rounded-lg bg-muted/30">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full bg-red-500" />
                      <p className="text-sm font-medium text-foreground">Max Charge Temp</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <input
                        type="number"
                        value={settings.maxChargeTemp}
                        onChange={(e) => updateSetting('maxChargeTemp', Number.parseInt(e.target.value))}
                        className="w-20 px-2 py-1 text-right text-sm bg-background border border-border rounded"
                      />
                      <span className="text-sm text-muted-foreground">°C</span>
                    </div>
                  </div>
                  <p className="text-xs text-muted-foreground">Stop charging above this temperature</p>
                </div>
                <div className="p-4 rounded-lg bg-muted/30">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full bg-blue-500" />
                      <p className="text-sm font-medium text-foreground">Min Charge Temp</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <input
                        type="number"
                        value={settings.minChargeTemp}
                        onChange={(e) => updateSetting('minChargeTemp', Number.parseInt(e.target.value))}
                        className="w-20 px-2 py-1 text-right text-sm bg-background border border-border rounded"
                      />
                      <span className="text-sm text-muted-foreground">°C</span>
                    </div>
                  </div>
                  <p className="text-xs text-muted-foreground">Stop charging below this temperature</p>
                </div>
              </>
            )}
          </CardContent>
        </Card>

        {/* Scheduled Charging */}
        <Card className="bg-card/50 border-border/50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Clock className="h-4 w-4 text-amber-500" />
              Scheduled Charging
            </CardTitle>
            <CardDescription>Automated charging schedules</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between p-4 rounded-lg bg-muted/30">
              <div>
                <p className="text-sm font-medium text-foreground">Forced Charge</p>
                <p className="text-xs text-muted-foreground">Charge to target at scheduled time</p>
              </div>
              <Switch
                checked={settings.forcedChargeEnabled}
                onCheckedChange={(v) => updateSetting('forcedChargeEnabled', v)}
              />
            </div>

            {settings.forcedChargeEnabled && (
              <>
                <div className="p-4 rounded-lg bg-muted/30">
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-sm font-medium text-foreground">Charge Time</p>
                    <input
                      type="time"
                      value={settings.forcedChargeTime}
                      onChange={(e) => updateSetting('forcedChargeTime', e.target.value)}
                      className="px-3 py-1 text-sm bg-background border border-border rounded"
                    />
                  </div>
                  <p className="text-xs text-muted-foreground">Start charging at this time daily</p>
                </div>
                <div className="p-4 rounded-lg bg-muted/30">
                  <div className="flex items-center justify-between mb-3">
                    <div>
                      <p className="text-sm font-medium text-foreground">Target Level</p>
                      <p className="text-xs text-muted-foreground">Charge to this percentage</p>
                    </div>
                    <span className="text-lg font-bold text-green-500">{settings.forcedChargeTarget}%</span>
                  </div>
                  <input
                    type="range"
                    min="50"
                    max="100"
                    value={settings.forcedChargeTarget}
                    onChange={(e) => updateSetting('forcedChargeTarget', Number.parseInt(e.target.value))}
                    className="w-full h-2 bg-muted rounded-full appearance-none cursor-pointer accent-green-500"
                  />
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

