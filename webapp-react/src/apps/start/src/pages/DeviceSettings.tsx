import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { AppHeader } from "@/components/layout/AppHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Slider } from "@/components/ui/slider";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { 
  Cpu, Battery, Gauge, Save, RotateCcw, ArrowLeft,
  Zap, Thermometer, Bell, Shield, Activity 
} from "lucide-react";
import { cn } from "@/lib/utils";
import { toast } from "@/hooks/use-toast";
import { devices } from "@/data/mockData";
import { InverterSettingsPage } from "@/components/settings/InverterSettingsPage";
// Battery Settings Component
const BatterySettings = () => {
  const [settings, setSettings] = useState({
    minSoc: 10,
    maxSoc: 95,
    chargePriority: "solar-first",
    dischargePriority: "peak-shaving",
    maxChargeRate: 50,
    maxDischargeRate: 50,
    balancingEnabled: true,
    tempProtection: true,
    lowTempThreshold: 5,
    highTempThreshold: 45,
  });

  return (
    <Tabs defaultValue="soc" className="w-full">
      <TabsList className="grid w-full grid-cols-3 mb-4">
        <TabsTrigger value="soc">SOC Limits</TabsTrigger>
        <TabsTrigger value="charging">Charging</TabsTrigger>
        <TabsTrigger value="protection">Protection</TabsTrigger>
      </TabsList>

      <TabsContent value="soc" className="space-y-4">
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <Label className="flex items-center gap-2">
              <Battery className="w-4 h-4 text-destructive" />
              Minimum SOC
            </Label>
            <span className="text-sm font-mono text-foreground">{settings.minSoc}%</span>
          </div>
          <Slider
            value={[settings.minSoc]}
            onValueChange={([v]) => setSettings({ ...settings, minSoc: v })}
            max={50}
            min={5}
            step={5}
          />
          <p className="text-xs text-muted-foreground">Battery will stop discharging at this level</p>
        </div>

        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <Label className="flex items-center gap-2">
              <Battery className="w-4 h-4 text-battery" />
              Maximum SOC
            </Label>
            <span className="text-sm font-mono text-foreground">{settings.maxSoc}%</span>
          </div>
          <Slider
            value={[settings.maxSoc]}
            onValueChange={([v]) => setSettings({ ...settings, maxSoc: v })}
            max={100}
            min={60}
            step={5}
          />
          <p className="text-xs text-muted-foreground">Battery will stop charging at this level</p>
        </div>
      </TabsContent>

      <TabsContent value="charging" className="space-y-4">
        <div className="space-y-3">
          <Label>Charge Priority</Label>
          <Select
            value={settings.chargePriority}
            onValueChange={(v) => setSettings({ ...settings, chargePriority: v })}
          >
            <SelectTrigger className="bg-secondary/50">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="solar-first">Solar First</SelectItem>
              <SelectItem value="grid-first">Grid First</SelectItem>
              <SelectItem value="time-based">Time Based</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-3">
          <Label>Discharge Priority</Label>
          <Select
            value={settings.dischargePriority}
            onValueChange={(v) => setSettings({ ...settings, dischargePriority: v })}
          >
            <SelectTrigger className="bg-secondary/50">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="peak-shaving">Peak Shaving</SelectItem>
              <SelectItem value="self-consumption">Self Consumption</SelectItem>
              <SelectItem value="backup-only">Backup Only</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label>Max Charge Rate</Label>
              <span className="text-sm font-mono">{settings.maxChargeRate}%</span>
            </div>
            <Slider
              value={[settings.maxChargeRate]}
              onValueChange={([v]) => setSettings({ ...settings, maxChargeRate: v })}
              max={100}
              min={10}
              step={10}
            />
          </div>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label>Max Discharge Rate</Label>
              <span className="text-sm font-mono">{settings.maxDischargeRate}%</span>
            </div>
            <Slider
              value={[settings.maxDischargeRate]}
              onValueChange={([v]) => setSettings({ ...settings, maxDischargeRate: v })}
              max={100}
              min={10}
              step={10}
            />
          </div>
        </div>
      </TabsContent>

      <TabsContent value="protection" className="space-y-4">
        <div className="flex items-center justify-between p-3 rounded-lg bg-secondary/30">
          <div>
            <Label className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-battery" />
              Cell Balancing
            </Label>
            <p className="text-xs text-muted-foreground mt-1">Automatically balance cell voltages</p>
          </div>
          <Switch
            checked={settings.balancingEnabled}
            onCheckedChange={(v) => setSettings({ ...settings, balancingEnabled: v })}
          />
        </div>

        <div className="flex items-center justify-between p-3 rounded-lg bg-secondary/30">
          <div>
            <Label className="flex items-center gap-2">
              <Thermometer className="w-4 h-4 text-warning" />
              Temperature Protection
            </Label>
            <p className="text-xs text-muted-foreground mt-1">Stop charging/discharging at extreme temps</p>
          </div>
          <Switch
            checked={settings.tempProtection}
            onCheckedChange={(v) => setSettings({ ...settings, tempProtection: v })}
          />
        </div>

        {settings.tempProtection && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            className="grid grid-cols-1 sm:grid-cols-2 gap-4"
          >
            <div className="space-y-2">
              <Label>Low Temp Limit (°C)</Label>
              <Input
                type="number"
                value={settings.lowTempThreshold}
                onChange={(e) => setSettings({ ...settings, lowTempThreshold: Number(e.target.value) })}
                className="bg-secondary/50"
              />
            </div>
            <div className="space-y-2">
              <Label>High Temp Limit (°C)</Label>
              <Input
                type="number"
                value={settings.highTempThreshold}
                onChange={(e) => setSettings({ ...settings, highTempThreshold: Number(e.target.value) })}
                className="bg-secondary/50"
              />
            </div>
          </motion.div>
        )}
      </TabsContent>
    </Tabs>
  );
};

// Meter Settings Component
const MeterSettings = () => {
  const [settings, setSettings] = useState({
    ctRatio: 100,
    vtRatio: 1,
    phaseMode: "three-phase",
    exportDirection: "reverse",
    importDirection: "forward",
    demandPeriod: 15,
    peakDemandReset: "monthly",
    alertsEnabled: true,
    powerQualityMonitoring: true,
  });

  return (
    <Tabs defaultValue="metering" className="w-full">
      <TabsList className="grid w-full grid-cols-3 mb-4">
        <TabsTrigger value="metering">Metering</TabsTrigger>
        <TabsTrigger value="direction">Direction</TabsTrigger>
        <TabsTrigger value="demand">Demand</TabsTrigger>
      </TabsList>

      <TabsContent value="metering" className="space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label>CT Ratio</Label>
            <Input
              type="number"
              value={settings.ctRatio}
              onChange={(e) => setSettings({ ...settings, ctRatio: Number(e.target.value) })}
              className="bg-secondary/50"
            />
            <p className="text-xs text-muted-foreground">Current transformer ratio</p>
          </div>
          <div className="space-y-2">
            <Label>VT Ratio</Label>
            <Input
              type="number"
              value={settings.vtRatio}
              onChange={(e) => setSettings({ ...settings, vtRatio: Number(e.target.value) })}
              className="bg-secondary/50"
            />
            <p className="text-xs text-muted-foreground">Voltage transformer ratio</p>
          </div>
        </div>

        <div className="space-y-3">
          <Label>Phase Configuration</Label>
          <Select
            value={settings.phaseMode}
            onValueChange={(v) => setSettings({ ...settings, phaseMode: v })}
          >
            <SelectTrigger className="bg-secondary/50">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="single-phase">Single Phase</SelectItem>
              <SelectItem value="three-phase">Three Phase (3P4W)</SelectItem>
              <SelectItem value="three-phase-3w">Three Phase (3P3W)</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center justify-between p-3 rounded-lg bg-secondary/30">
          <div>
            <Label className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-grid" />
              Power Quality Monitoring
            </Label>
            <p className="text-xs text-muted-foreground mt-1">Monitor THD, voltage sags/swells</p>
          </div>
          <Switch
            checked={settings.powerQualityMonitoring}
            onCheckedChange={(v) => setSettings({ ...settings, powerQualityMonitoring: v })}
          />
        </div>
      </TabsContent>

      <TabsContent value="direction" className="space-y-4">
        <div className="space-y-3">
          <Label>Import Direction</Label>
          <Select
            value={settings.importDirection}
            onValueChange={(v) => setSettings({ ...settings, importDirection: v })}
          >
            <SelectTrigger className="bg-secondary/50">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="forward">Forward (Grid → Load)</SelectItem>
              <SelectItem value="reverse">Reverse (Load → Grid)</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-3">
          <Label>Export Direction</Label>
          <Select
            value={settings.exportDirection}
            onValueChange={(v) => setSettings({ ...settings, exportDirection: v })}
          >
            <SelectTrigger className="bg-secondary/50">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="forward">Forward (Grid → Load)</SelectItem>
              <SelectItem value="reverse">Reverse (Load → Grid)</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </TabsContent>

      <TabsContent value="demand" className="space-y-4">
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <Label>Demand Period</Label>
            <span className="text-sm font-mono text-foreground">{settings.demandPeriod} min</span>
          </div>
          <Slider
            value={[settings.demandPeriod]}
            onValueChange={([v]) => setSettings({ ...settings, demandPeriod: v })}
            max={60}
            min={5}
            step={5}
          />
          <p className="text-xs text-muted-foreground">Averaging period for demand calculation</p>
        </div>

        <div className="space-y-3">
          <Label>Peak Demand Reset</Label>
          <Select
            value={settings.peakDemandReset}
            onValueChange={(v) => setSettings({ ...settings, peakDemandReset: v })}
          >
            <SelectTrigger className="bg-secondary/50">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="daily">Daily</SelectItem>
              <SelectItem value="weekly">Weekly</SelectItem>
              <SelectItem value="monthly">Monthly</SelectItem>
              <SelectItem value="manual">Manual Only</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center justify-between p-3 rounded-lg bg-secondary/30">
          <div>
            <Label className="flex items-center gap-2">
              <Bell className="w-4 h-4 text-primary" />
              Demand Alerts
            </Label>
            <p className="text-xs text-muted-foreground mt-1">Alert when demand exceeds threshold</p>
          </div>
          <Switch
            checked={settings.alertsEnabled}
            onCheckedChange={(v) => setSettings({ ...settings, alertsEnabled: v })}
          />
        </div>
      </TabsContent>
    </Tabs>
  );
};

const deviceIcons = {
  inverter: Cpu,
  battery: Battery,
  meter: Gauge,
};

const typeColors = {
  inverter: "text-solar",
  battery: "text-battery",
  meter: "text-grid",
};

const DeviceSettingsPage = () => {
  const { deviceId } = useParams<{ deviceId: string }>();
  const navigate = useNavigate();
  
  const device = devices.find(d => d.id === deviceId);

  const handleSave = () => {
    toast({
      title: "Settings Saved",
      description: `Configuration for ${device?.name} has been updated.`,
    });
    navigate("/start/devices");
  };

  const handleReset = () => {
    toast({
      title: "Settings Reset",
      description: "Device settings have been reset to defaults.",
    });
  };

  if (!device) {
    return (
      <>
        <AppHeader title="Device Not Found" subtitle="The requested device could not be found" />
        <div className="p-6">
          <Button variant="outline" onClick={() => navigate("/start/devices")}>
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Devices
          </Button>
        </div>
      </>
    );
  }

  const Icon = deviceIcons[device.type];

  return (
    <>
      <AppHeader 
        title={`${device.name} Settings`}
        subtitle={`${device.model} • ${device.serialNumber}`}
      />
      
      <div className="p-6 space-y-6">
        {/* Back Button */}
        <Button variant="ghost" onClick={() => navigate("/devices")} className="gap-2">
          <ArrowLeft className="w-4 h-4" />
          Back to Devices
        </Button>

        {/* Device Header Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-card p-4"
        >
          <div className="flex items-center gap-4">
            <div className={cn(
              "w-12 h-12 rounded-xl flex items-center justify-center",
              device.type === "inverter" && "bg-solar/20",
              device.type === "battery" && "bg-battery/20",
              device.type === "meter" && "bg-grid/20"
            )}>
              <Icon className={cn("w-6 h-6", typeColors[device.type])} />
            </div>
            <div className="flex-1">
              <h2 className="text-lg font-semibold text-foreground">{device.name}</h2>
              <p className="text-sm text-muted-foreground">{device.model} • {device.serialNumber}</p>
            </div>
            <div className={cn(
              "px-3 py-1 rounded-full text-xs font-medium capitalize",
              device.status === "online" && "bg-success/20 text-success",
              device.status === "warning" && "bg-warning/20 text-warning"
            )}>
              {device.status}
            </div>
          </div>
        </motion.div>

        {/* Settings Content */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className={cn(device.type !== "inverter" && "glass-card p-6")}
        >
          {device.type === "inverter" && <InverterSettingsPage />}
          {device.type === "battery" && <BatterySettings />}
          {device.type === "meter" && <MeterSettings />}
        </motion.div>

        {/* Action Buttons */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="flex flex-col sm:flex-row justify-between gap-4"
        >
          <Button variant="outline" onClick={handleReset}>
            <RotateCcw className="w-4 h-4 mr-2" />
            Reset to Defaults
          </Button>
          <div className="flex flex-col sm:flex-row gap-2">
            <Button variant="outline" onClick={() => navigate("/start/devices")}>
              Cancel
            </Button>
            <Button onClick={handleSave}>
              <Save className="w-4 h-4 mr-2" />
              Save Settings
            </Button>
          </div>
        </motion.div>
      </div>
    </>
  );
};

export default DeviceSettingsPage;