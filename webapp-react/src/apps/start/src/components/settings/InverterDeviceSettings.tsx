import { useState, useEffect, useImperativeHandle, forwardRef } from "react";
import { motion } from "framer-motion";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
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
import {
  Info,
  Zap,
  Battery,
  Settings2,
  Shield,
  Sun,
  Cpu,
  Plug,
  Power,
  Clock,
  Edit3,
  Check,
  X,
  Plus,
  Trash2,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { toast } from "@/hooks/use-toast";
import { useQuery } from "@tanstack/react-query";

interface SettingRowProps {
  label: string;
  value: string | number;
  unit?: string;
  description?: string;
  editable?: boolean;
  onEdit?: (value: string) => void;
}

const SettingRow = ({ label, value, unit, description, editable, onEdit }: SettingRowProps) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState(String(value));

  const handleSave = () => {
    onEdit?.(editValue);
    setIsEditing(false);
  };

  return (
    <div className="flex items-center justify-between py-3 border-b border-border/50 last:border-0">
      <div className="flex-1">
        <p className="text-sm text-foreground">{label}</p>
        {description && <p className="text-xs text-muted-foreground mt-0.5">{description}</p>}
      </div>
      <div className="flex items-center gap-2">
        {isEditing ? (
          <>
            <Input
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              className="w-24 h-8 text-right bg-secondary/50"
            />
            <Button size="icon" variant="ghost" className="h-7 w-7" onClick={handleSave}>
              <Check className="h-4 w-4 text-success" />
            </Button>
            <Button size="icon" variant="ghost" className="h-7 w-7" onClick={() => setIsEditing(false)}>
              <X className="h-4 w-4 text-destructive" />
            </Button>
          </>
        ) : (
          <>
            <span className="font-mono text-sm text-foreground">
              {value}{unit && <span className="text-muted-foreground ml-1">{unit}</span>}
            </span>
            {editable && (
              <Button size="icon" variant="ghost" className="h-7 w-7" onClick={() => setIsEditing(true)}>
                <Edit3 className="h-3 w-3 text-primary" />
              </Button>
            )}
          </>
        )}
      </div>
    </div>
  );
};

interface ToggleRowProps {
  label: string;
  description?: string;
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
}

const ToggleRow = ({ label, description, checked, onCheckedChange }: ToggleRowProps) => {
  return (
    <div className="flex items-center justify-between py-3 border-b border-border/50 last:border-0">
      <div className="flex-1">
        <p className="text-sm text-foreground">{label}</p>
        {description && <p className="text-xs text-muted-foreground mt-0.5">{description}</p>}
      </div>
      <Switch checked={checked} onCheckedChange={onCheckedChange} />
    </div>
  );
};

interface SliderRowProps {
  label: string;
  value: number;
  min: number;
  max: number;
  step?: number;
  unit?: string;
  description?: string;
  onChange: (value: number) => void;
}

const SliderRow = ({ label, value, min, max, step = 1, unit = "%", description, onChange }: SliderRowProps) => {
  return (
    <div className="py-3 border-b border-border/50 last:border-0">
      <div className="flex items-center justify-between mb-2">
        <div className="flex-1">
          <p className="text-sm text-foreground">{label}</p>
          {description && <p className="text-xs text-muted-foreground mt-0.5">{description}</p>}
        </div>
        <span className="font-mono text-sm text-foreground">{value}{unit}</span>
      </div>
      <Slider
        value={[value]}
        onValueChange={([v]) => onChange(v)}
        min={min}
        max={max}
        step={step}
        className="mt-2"
      />
    </div>
  );
};

// ============== TOU Window Components ==============

interface TOUWindowData {
  mode: string;
  startTime: string;
  endTime: string;
  power: number;
  targetSoc: number;
  enabled: boolean;
}

const TOUWindowRow = ({ windowNum, data, onUpdate, onDelete }: {
  windowNum: number;
  data: TOUWindowData;
  onUpdate: (data: TOUWindowData) => void;
  onDelete: () => void;
}) => {
  const modeColors = {
    auto: "bg-primary/20 text-primary border-primary/30",
    charge: "bg-success/20 text-success border-success/30",
    discharge: "bg-warning/20 text-warning border-warning/30",
  };

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        "glass-card p-4 border transition-all",
        data.enabled ? "opacity-100" : "opacity-50"
      )}
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className={cn(
            "px-2.5 py-1 rounded-full text-xs font-medium border",
            modeColors[data.mode as keyof typeof modeColors] || modeColors.auto
          )}>
            Window {windowNum}
          </div>
          <Switch
            checked={data.enabled}
            onCheckedChange={(v) => onUpdate({ ...data, enabled: v })}
          />
        </div>
        <Button
          size="icon"
          variant="ghost"
          className="h-8 w-8 text-muted-foreground hover:text-destructive"
          onClick={onDelete}
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3">
        <div className="col-span-2 sm:col-span-1">
          <Label className="text-xs text-muted-foreground mb-1.5 block">Mode</Label>
          <Select value={data.mode} onValueChange={(v) => onUpdate({ ...data, mode: v })} disabled={!data.enabled}>
            <SelectTrigger className="h-9 bg-secondary/50 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="auto">Auto</SelectItem>
              <SelectItem value="charge">Charge</SelectItem>
              <SelectItem value="discharge">Discharge</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div>
          <Label className="text-xs text-muted-foreground mb-1.5 block">Start</Label>
          <Input
            type="time"
            value={data.startTime}
            onChange={(e) => onUpdate({ ...data, startTime: e.target.value })}
            className="h-9 bg-secondary/50 text-xs"
            disabled={!data.enabled}
          />
        </div>
        <div>
          <Label className="text-xs text-muted-foreground mb-1.5 block">End</Label>
          <Input
            type="time"
            value={data.endTime}
            onChange={(e) => onUpdate({ ...data, endTime: e.target.value })}
            className="h-9 bg-secondary/50 text-xs"
            disabled={!data.enabled}
          />
        </div>
        <div>
          <Label className="text-xs text-muted-foreground mb-1.5 block">Power (W)</Label>
          <Input
            type="number"
            value={data.power}
            onChange={(e) => onUpdate({ ...data, power: parseInt(e.target.value) })}
            className="h-9 bg-secondary/50 text-xs"
            disabled={!data.enabled}
          />
        </div>
        <div>
          <Label className="text-xs text-muted-foreground mb-1.5 block">Target SOC (%)</Label>
          <Input
            type="number"
            value={data.targetSoc}
            onChange={(e) => onUpdate({ ...data, targetSoc: parseInt(e.target.value) })}
            className="h-9 bg-secondary/50 text-xs"
            min={0}
            max={100}
            disabled={!data.enabled}
          />
        </div>
      </div>
    </motion.div>
  );
};

const TOUTimeline = ({ windows }: { windows: TOUWindowData[] }) => {
  const modeColors = {
    auto: "bg-primary",
    charge: "bg-success",
    discharge: "bg-warning",
  };

  const timeToPercent = (time: string) => {
    const [h, m] = time.split(":").map(Number);
    return ((h * 60 + m) / (24 * 60)) * 100;
  };

  return (
    <div className="space-y-2 mb-6">
      <div className="flex justify-between text-xs text-muted-foreground">
        <span>00:00</span>
        <span>06:00</span>
        <span>12:00</span>
        <span>18:00</span>
        <span>24:00</span>
      </div>
      <div className="relative h-8 bg-secondary/30 rounded-lg overflow-hidden">
        {windows.filter(w => w.enabled).map((w, i) => {
          const start = timeToPercent(w.startTime);
          const end = timeToPercent(w.endTime);
          const width = end > start ? end - start : 100 - start + end;
          return (
            <div
              key={i}
              className={cn(
                "absolute h-full flex items-center justify-center text-xs font-medium text-white",
                modeColors[w.mode as keyof typeof modeColors] || modeColors.auto
              )}
              style={{ left: `${start}%`, width: `${width}%` }}
            >
              W{i + 1}
            </div>
          );
        })}
      </div>
      <div className="flex gap-4 text-xs">
        <div className="flex items-center gap-1.5">
          <div className="w-3 h-3 rounded bg-primary" />
          <span>Auto</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-3 h-3 rounded bg-success" />
          <span>Charge</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-3 h-3 rounded bg-warning" />
          <span>Discharge</span>
        </div>
      </div>
    </div>
  );
};

interface InverterDeviceSettingsProps {
  deviceId: string;
  onSave?: (settings: any) => Promise<void>;
}

export interface InverterDeviceSettingsRef {
  save: () => Promise<void>;
}

export const InverterDeviceSettings = forwardRef<InverterDeviceSettingsRef, InverterDeviceSettingsProps>(
  ({ deviceId, onSave }, ref) => {
  // Fetch device settings from backend
  const { data: deviceSettings, isLoading } = useQuery({
    queryKey: ['device-settings', deviceId],
    queryFn: async () => {
      const { deviceService } = await import('@root/api/services/device');
      return await deviceService.getDeviceSettings(deviceId);
    },
    enabled: !!deviceId,
  });

  // System Tab - Device Identity
  const [deviceIdentity, setDeviceIdentity] = useState({
    id: deviceId,
    name: '',
    array_id: '',
  });

  // System Tab - Specification
  const [specification, setSpecification] = useState({
    driver: '',
    serialNumber: '',
    protocolVersion: 0,
    maxAcOutputPower: 0,
    mpptConnections: 0,
    parallelMode: false,
    modbusNumber: 0,
  });

  // System Tab - Grid Settings
  const [gridSettings, setGridSettings] = useState({
    voltageHigh: 265,
    voltageLow: 195,
    frequency: 50.0,
    frequencyHigh: 52.0,
    frequencyLow: 48.0,
    peakShavingEnabled: false,
    peakShavingPower: 0,
  });

  // System Tab - Adapter Settings
  const [adapterSettings, setAdapterSettings] = useState({
    adapterType: '',
    transport: 'rtu',
    serialPort: '',
    baudrate: 115200,
    parity: 'N',
    stopbits: 1,
    bytesize: 8,
    host: '',
    port: 502,
    unitId: 1,
    registerMapFile: '',
  });

  // System Tab - Safety Settings
  const [safetySettings, setSafetySettings] = useState({
    maxBattVoltage: 52,
    maxChargeA: 100,
    maxDischargeA: 100,
  });

  // System Tab - Solar Arrays
  const [solarArrays, setSolarArrays] = useState<Array<{
    pv_dc_kw: number;
    tilt_deg: number;
    azimuth_deg: number;
    perf_ratio: number;
    albedo: number;
  }>>([]);

  // Power Tab - Battery Configuration
  const [batteryConfig, setBatteryConfig] = useState({
    type: 'Lithium Battery',
    capacity: 450,
    operation: 'State of Charge',
    maxDischargeCurrent: 100,
    maxChargeCurrent: 100,
    maxGridChargeCurrent: 0,
    maxGeneratorChargeCurrent: 0,
    maxGridChargerPower: 0,
    maxChargerPower: 0,
    maxDischargerPower: 0,
  });

  // Power Tab - Work Mode
  const [workMode, setWorkMode] = useState({
    remoteSwitch: true,
    gridCharge: false,
    generatorCharge: false,
    forceGeneratorOn: false,
    outputShutdownCapacity: 10,
    stopBatteryDischargeCapacity: 35,
    startBatteryDischargeCapacity: 40,
    startGridChargeCapacity: 50,
    offGridMode: false,
    offGridStartupBatteryCapacity: 40,
  });

  // Power Tab - Work Mode Detail
  const [workModeDetail, setWorkModeDetail] = useState({
    workMode: 'zero-export',
    solarExportWhenFull: true,
    energyPattern: 'load-first',
    maxSellPower: 0,
    maxSolarPower: 0,
    gridTrickleFeed: 20,
    maxFeedInPower: 0,
  });

  // Power Tab - Auxiliary Settings
  const [auxiliarySettings, setAuxiliarySettings] = useState({
    auxiliaryPort: 'Generator Input',
    generatorConnectedToGrid: false,
    generatorPeakShaving: false,
    generatorPeakShavingPower: 0,
    generatorStopCapacity: 0,
    generatorStartCapacity: 30,
    generatorMaxRunTime: 24,
    generatorDownTime: 0,
  });

  // Scheduling Tab - TOU Windows
  const [touWindows, setTouWindows] = useState<TOUWindowData[]>([]);

  // Load device settings when available
  useEffect(() => {
    if (deviceSettings) {
      console.log('[InverterDeviceSettings] Loading device settings:', deviceSettings);
      
      // Device Identity
      setDeviceIdentity({
        id: deviceId,
        name: deviceSettings.general?.name || deviceId,
        array_id: deviceSettings.general?.array_id || '',
      });

      // Specification
      if (deviceSettings.general?.specification) {
        setSpecification({
          driver: deviceSettings.general.specification.driver || '',
          serialNumber: deviceSettings.general.specification.serialNumber || '',
          protocolVersion: deviceSettings.general.specification.protocolVersion || 0,
          maxAcOutputPower: deviceSettings.general.specification.maxAcOutputPower || 0,
          mpptConnections: deviceSettings.general.specification.mpptConnections || 0,
          parallelMode: deviceSettings.general.specification.parallelMode || false,
          modbusNumber: deviceSettings.general.specification.modbusNumber || 0,
        });
      }

      // Grid Settings
      if (deviceSettings.safety?.grid) {
        setGridSettings(prev => ({
          ...prev,
          ...deviceSettings.safety.grid,
        }));
      }

      // Adapter Settings
      if (deviceSettings.adapter) {
        setAdapterSettings({
          adapterType: deviceSettings.adapter.adapter_type || '',
          transport: deviceSettings.adapter.transport || 'rtu',
          serialPort: deviceSettings.adapter.serial_port || '',
          baudrate: deviceSettings.adapter.baudrate || 115200,
          parity: deviceSettings.adapter.parity || 'N',
          stopbits: deviceSettings.adapter.stopbits || 1,
          bytesize: deviceSettings.adapter.bytesize || 8,
          host: deviceSettings.adapter.host || '',
          port: deviceSettings.adapter.port || 502,
          unitId: deviceSettings.adapter.unit_id || 1,
          registerMapFile: deviceSettings.adapter.register_map_file || '',
        });
      }

      // Safety Settings
      if (deviceSettings.safety) {
        setSafetySettings(prev => ({
          ...prev,
          maxBattVoltage: deviceSettings.safety.max_batt_voltage_v || prev.maxBattVoltage,
          maxChargeA: deviceSettings.safety.max_charge_a || prev.maxChargeA,
          maxDischargeA: deviceSettings.safety.max_discharge_a || prev.maxDischargeA,
        }));
      }

      // Solar Arrays
      if (deviceSettings.solar?.arrays) {
        setSolarArrays(deviceSettings.solar.arrays);
      }

      // Battery Config
      if (deviceSettings.solar?.battery) {
        setBatteryConfig(prev => ({
          ...prev,
          ...deviceSettings.solar.battery,
        }));
      }

      // Work Mode
      if (deviceSettings.solar?.workMode) {
        setWorkMode(prev => ({
          ...prev,
          ...deviceSettings.solar.workMode,
        }));
      }

      // Work Mode Detail
      if (deviceSettings.solar?.workModeDetail) {
        setWorkModeDetail(prev => ({
          ...prev,
          ...deviceSettings.solar.workModeDetail,
        }));
      }

      // Auxiliary Settings
      if (deviceSettings.solar?.auxiliary) {
        setAuxiliarySettings(prev => ({
          ...prev,
          ...deviceSettings.solar.auxiliary,
        }));
      }

      // TOU Windows
      if (deviceSettings.scheduling?.touWindows) {
        console.log('[InverterDeviceSettings] Loading TOU windows:', deviceSettings.scheduling.touWindows);
        setTouWindows(deviceSettings.scheduling.touWindows);
      } else {
        console.log('[InverterDeviceSettings] No TOU windows found in settings');
      }
    }
  }, [deviceSettings, deviceId]);

  const handleSave = async () => {
    try {
      const { deviceService } = await import('@root/api/services/device');
      
      const settingsToSave = {
        general: {
          ...deviceIdentity,
          specification,
        },
        adapter: adapterSettings,
        safety: {
          ...safetySettings,
          grid: gridSettings,
        },
        solar: {
          arrays: solarArrays,
          battery: batteryConfig,
          workMode,
          workModeDetail,
          auxiliary: auxiliarySettings,
        },
        scheduling: {
          touWindows,
        },
      };
      
      console.log('[InverterDeviceSettings] Saving settings:', settingsToSave);
      console.log('[InverterDeviceSettings] TOU Windows being saved:', touWindows);
      
      const response = await deviceService.saveDeviceSettings(deviceId, settingsToSave);

      if (response.status === 'success') {
        if (onSave) {
          await onSave(settingsToSave);
        } else {
          toast({
            title: "Settings Saved",
            description: response.message || `Configuration for ${deviceId} has been updated.`,
          });
        }
      } else {
        throw new Error(response.message || 'Failed to save settings');
      }
    } catch (error: any) {
      console.error('[InverterDeviceSettings] Error saving settings:', error);
      toast({
        title: "Error",
        description: error?.message || "Failed to save settings",
        variant: "destructive",
      });
      throw error;
    }
  };

  // Expose save function to parent via ref
  useImperativeHandle(ref, () => ({
    save: handleSave,
  }));

  const addSolarArray = () => {
    setSolarArrays(prev => [...prev, { pv_dc_kw: 5.0, tilt_deg: 25, azimuth_deg: 180, perf_ratio: 0.80, albedo: 0.2 }]);
  };

  const removeSolarArray = (index: number) => {
    setSolarArrays(prev => prev.filter((_, i) => i !== index));
  };

  const updateSolarArray = (index: number, key: string, value: number) => {
    setSolarArrays(prev => prev.map((arr, i) => i === index ? { ...arr, [key]: value } : arr));
  };

  const addTouWindow = () => {
    if (touWindows.length >= 6) return;
    setTouWindows(prev => [...prev, { mode: "auto", startTime: "00:00", endTime: "06:00", power: 1000, targetSoc: 50, enabled: true }]);
  };

  const updateTouWindow = (index: number, data: TOUWindowData) => {
    setTouWindows(prev => prev.map((w, i) => i === index ? data : w));
  };

  const deleteTouWindow = (index: number) => {
    setTouWindows(prev => prev.filter((_, i) => i !== index));
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <Tabs defaultValue="system" className="w-full">
      <TabsList className="grid w-full grid-cols-3 mb-4">
        <TabsTrigger value="system" className="gap-2">
          <Settings2 className="w-4 h-4 hidden sm:inline" />
          System
        </TabsTrigger>
        <TabsTrigger value="power" className="gap-2">
          <Power className="w-4 h-4 hidden sm:inline" />
          Power
        </TabsTrigger>
        <TabsTrigger value="scheduling" className="gap-2">
          <Clock className="w-4 h-4 hidden sm:inline" />
          Scheduling
        </TabsTrigger>
      </TabsList>

      {/* ============== SYSTEM TAB ============== */}
      <TabsContent value="system" className="space-y-4">
        <Accordion type="multiple" defaultValue={["general", "specification", "grid", "adapter", "safety", "solar"]} className="space-y-2">
          
          {/* Device Identity */}
          <AccordionItem value="general" className="glass-card border-none">
            <AccordionTrigger className="px-4 hover:no-underline">
              <div className="flex items-center gap-2">
                <Cpu className="w-4 h-4 text-solar" />
                <span>Device Identity</span>
              </div>
            </AccordionTrigger>
            <AccordionContent className="px-4 pb-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Device ID</Label>
                  <Input value={deviceIdentity.id} onChange={(e) => setDeviceIdentity({ ...deviceIdentity, id: e.target.value })} className="bg-secondary/50 font-mono" />
                </div>
                <div className="space-y-2">
                  <Label>Device Name</Label>
                  <Input value={deviceIdentity.name} onChange={(e) => setDeviceIdentity({ ...deviceIdentity, name: e.target.value })} className="bg-secondary/50" />
                </div>
              </div>
              <div className="space-y-2 mt-4">
                <Label>Array Assignment</Label>
                <Select value={deviceIdentity.array_id} onValueChange={(v) => setDeviceIdentity({ ...deviceIdentity, array_id: v })}>
                  <SelectTrigger className="bg-secondary/50">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="array1">Array 1</SelectItem>
                    <SelectItem value="array2">Array 2</SelectItem>
                    <SelectItem value="array3">Array 3</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </AccordionContent>
          </AccordionItem>

          {/* Specification */}
          <AccordionItem value="specification" className="glass-card border-none">
            <AccordionTrigger className="px-4 hover:no-underline">
              <div className="flex items-center gap-2">
                <Info className="w-4 h-4 text-primary" />
                <span>Specification</span>
              </div>
            </AccordionTrigger>
            <AccordionContent className="px-4 pb-4">
              <SettingRow label="Driver" value={specification.driver} />
              <SettingRow label="Serial Number" value={specification.serialNumber} />
              <SettingRow label="Protocol Version" value={specification.protocolVersion} />
              <SettingRow label="Max AC Output Power" value={specification.maxAcOutputPower} unit="kW" editable onEdit={(v) => setSpecification({ ...specification, maxAcOutputPower: parseFloat(v) })} />
              <SettingRow label="MPPT Connections" value={specification.mpptConnections} />
              <ToggleRow label="Parallel Mode" checked={specification.parallelMode} onCheckedChange={(v) => setSpecification({ ...specification, parallelMode: v })} />
              <SettingRow label="Modbus Number" value={specification.modbusNumber} />
            </AccordionContent>
          </AccordionItem>

          {/* Grid Settings */}
          <AccordionItem value="grid" className="glass-card border-none">
            <AccordionTrigger className="px-4 hover:no-underline">
              <div className="flex items-center gap-2">
                <Zap className="w-4 h-4 text-grid" />
                <span>Grid Settings</span>
              </div>
            </AccordionTrigger>
            <AccordionContent className="px-4 pb-4">
              <SettingRow label="Grid Voltage High" value={gridSettings.voltageHigh} unit="V" editable onEdit={(v) => setGridSettings({ ...gridSettings, voltageHigh: parseFloat(v) })} />
              <SettingRow label="Grid Voltage Low" value={gridSettings.voltageLow || "—"} unit="V" editable onEdit={(v) => setGridSettings({ ...gridSettings, voltageLow: parseFloat(v) })} />
              <SettingRow label="Grid Frequency" value={gridSettings.frequency} unit="Hz" editable onEdit={(v) => setGridSettings({ ...gridSettings, frequency: parseFloat(v) })} />
              <SettingRow label="Grid Frequency High" value={gridSettings.frequencyHigh} unit="Hz" editable onEdit={(v) => setGridSettings({ ...gridSettings, frequencyHigh: parseFloat(v) })} />
              <SettingRow label="Grid Frequency Low" value={gridSettings.frequencyLow} unit="Hz" editable onEdit={(v) => setGridSettings({ ...gridSettings, frequencyLow: parseFloat(v) })} />
              <ToggleRow 
                label="Grid Peak Shaving" 
                description="Limit power drawn from grid during peak times"
                checked={gridSettings.peakShavingEnabled} 
                onCheckedChange={(v) => setGridSettings({ ...gridSettings, peakShavingEnabled: v })} 
              />
              {gridSettings.peakShavingEnabled && (
                <SettingRow label="Grid Peak Shaving Power" value={gridSettings.peakShavingPower} unit="kW" editable onEdit={(v) => setGridSettings({ ...gridSettings, peakShavingPower: parseFloat(v) })} />
              )}
            </AccordionContent>
          </AccordionItem>

          {/* Adapter Settings */}
          <AccordionItem value="adapter" className="glass-card border-none">
            <AccordionTrigger className="px-4 hover:no-underline">
              <div className="flex items-center gap-2">
                <Plug className="w-4 h-4 text-primary" />
                <span>Adapter / Communication</span>
              </div>
            </AccordionTrigger>
            <AccordionContent className="px-4 pb-4 space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Adapter Type</Label>
                  <Select value={adapterSettings.adapterType} onValueChange={(v) => setAdapterSettings({ ...adapterSettings, adapterType: v })}>
                    <SelectTrigger className="bg-secondary/50">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="powdrive">Powdrive</SelectItem>
                      <SelectItem value="sunsynk">Sunsynk</SelectItem>
                      <SelectItem value="growatt">Growatt</SelectItem>
                      <SelectItem value="deye">Deye</SelectItem>
                      <SelectItem value="solis">Solis</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Transport</Label>
                  <Select value={adapterSettings.transport} onValueChange={(v) => setAdapterSettings({ ...adapterSettings, transport: v as 'rtu' | 'tcp' })}>
                    <SelectTrigger className="bg-secondary/50">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="rtu">RTU (Serial)</SelectItem>
                      <SelectItem value="tcp">TCP (Network)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {adapterSettings.transport === "rtu" ? (
                <>
                  <div className="space-y-2">
                    <Label>Serial Port</Label>
                    <Input value={adapterSettings.serialPort} onChange={(e) => setAdapterSettings({ ...adapterSettings, serialPort: e.target.value })} className="bg-secondary/50 font-mono text-xs" placeholder="/dev/ttyUSB0" />
                  </div>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                    <div className="space-y-2">
                      <Label>Unit ID</Label>
                      <Input type="number" value={adapterSettings.unitId} onChange={(e) => setAdapterSettings({ ...adapterSettings, unitId: parseInt(e.target.value) })} className="bg-secondary/50" min={1} max={247} />
                    </div>
                    <div className="space-y-2">
                      <Label>Baudrate</Label>
                      <Select value={adapterSettings.baudrate.toString()} onValueChange={(v) => setAdapterSettings({ ...adapterSettings, baudrate: parseInt(v) })}>
                        <SelectTrigger className="bg-secondary/50"><SelectValue /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="4800">4800</SelectItem>
                          <SelectItem value="9600">9600</SelectItem>
                          <SelectItem value="19200">19200</SelectItem>
                          <SelectItem value="38400">38400</SelectItem>
                          <SelectItem value="57600">57600</SelectItem>
                          <SelectItem value="115200">115200</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label>Parity</Label>
                      <Select value={adapterSettings.parity} onValueChange={(v) => setAdapterSettings({ ...adapterSettings, parity: v })}>
                        <SelectTrigger className="bg-secondary/50"><SelectValue /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="N">None (N)</SelectItem>
                          <SelectItem value="E">Even (E)</SelectItem>
                          <SelectItem value="O">Odd (O)</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label>Stop Bits</Label>
                      <Select value={adapterSettings.stopbits.toString()} onValueChange={(v) => setAdapterSettings({ ...adapterSettings, stopbits: parseInt(v) })}>
                        <SelectTrigger className="bg-secondary/50"><SelectValue /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="1">1</SelectItem>
                          <SelectItem value="2">2</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Byte Size</Label>
                      <Select value={adapterSettings.bytesize.toString()} onValueChange={(v) => setAdapterSettings({ ...adapterSettings, bytesize: parseInt(v) })}>
                        <SelectTrigger className="bg-secondary/50"><SelectValue /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="7">7</SelectItem>
                          <SelectItem value="8">8</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label>Register Map File</Label>
                      <Input value={adapterSettings.registerMapFile} onChange={(e) => setAdapterSettings({ ...adapterSettings, registerMapFile: e.target.value })} className="bg-secondary/50 font-mono text-xs" />
                    </div>
                  </div>
                </>
              ) : (
                <>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>IP Address</Label>
                      <Input value={adapterSettings.host} onChange={(e) => setAdapterSettings({ ...adapterSettings, host: e.target.value })} className="bg-secondary/50 font-mono" placeholder="192.168.1.100" />
                    </div>
                    <div className="space-y-2">
                      <Label>Port</Label>
                      <Input type="number" value={adapterSettings.port} onChange={(e) => setAdapterSettings({ ...adapterSettings, port: parseInt(e.target.value) })} className="bg-secondary/50" min={1} max={65535} />
                    </div>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Unit ID</Label>
                      <Input type="number" value={adapterSettings.unitId} onChange={(e) => setAdapterSettings({ ...adapterSettings, unitId: parseInt(e.target.value) })} className="bg-secondary/50" min={1} max={247} />
                    </div>
                    <div className="space-y-2">
                      <Label>Register Map File</Label>
                      <Input value={adapterSettings.registerMapFile} onChange={(e) => setAdapterSettings({ ...adapterSettings, registerMapFile: e.target.value })} className="bg-secondary/50 font-mono text-xs" />
                    </div>
                  </div>
                </>
              )}
            </AccordionContent>
          </AccordionItem>

          {/* Safety Limits */}
          <AccordionItem value="safety" className="glass-card border-none">
            <AccordionTrigger className="px-4 hover:no-underline">
              <div className="flex items-center gap-2">
                <Shield className="w-4 h-4 text-warning" />
                <span>Safety Limits</span>
              </div>
            </AccordionTrigger>
            <AccordionContent className="px-4 pb-4 space-y-4">
              <SliderRow label="Max Battery Voltage" value={safetySettings.maxBattVoltage} min={40} max={60} step={0.5} unit=" V" onChange={(v) => setSafetySettings({ ...safetySettings, maxBattVoltage: v })} />
              <SliderRow label="Max Charge Current" value={safetySettings.maxChargeA} min={10} max={200} step={5} unit=" A" onChange={(v) => setSafetySettings({ ...safetySettings, maxChargeA: v })} />
              <SliderRow label="Max Discharge Current" value={safetySettings.maxDischargeA} min={10} max={200} step={5} unit=" A" onChange={(v) => setSafetySettings({ ...safetySettings, maxDischargeA: v })} />
            </AccordionContent>
          </AccordionItem>

          {/* Solar Arrays */}
          <AccordionItem value="solar" className="glass-card border-none">
            <AccordionTrigger className="px-4 hover:no-underline">
              <div className="flex items-center gap-2">
                <Sun className="w-4 h-4 text-solar" />
                <span>Solar Arrays</span>
              </div>
            </AccordionTrigger>
            <AccordionContent className="px-4 pb-4 space-y-4">
              <div className="flex justify-end">
                <Button size="sm" variant="outline" onClick={addSolarArray} className="gap-2">
                  <Plus className="w-4 h-4" />
                  Add Array
                </Button>
              </div>
              {solarArrays.map((arr, index) => (
                <div key={index} className="bg-secondary/20 rounded-lg p-4 space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">Solar Array {index + 1}</span>
                    {solarArrays.length > 1 && (
                      <Button variant="ghost" size="sm" onClick={() => removeSolarArray(index)} className="text-destructive hover:text-destructive">
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    )}
                  </div>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                    <div className="space-y-2">
                      <Label className="text-xs">PV DC Power (kW)</Label>
                      <Input type="number" value={arr.pv_dc_kw} onChange={(e) => updateSolarArray(index, "pv_dc_kw", parseFloat(e.target.value))} className="bg-secondary/50" step={0.1} />
                    </div>
                    <div className="space-y-2">
                      <Label className="text-xs">Tilt Angle (°)</Label>
                      <Input type="number" value={arr.tilt_deg} onChange={(e) => updateSolarArray(index, "tilt_deg", parseInt(e.target.value))} className="bg-secondary/50" min={0} max={90} />
                    </div>
                    <div className="space-y-2">
                      <Label className="text-xs">Azimuth (°)</Label>
                      <Input type="number" value={arr.azimuth_deg} onChange={(e) => updateSolarArray(index, "azimuth_deg", parseInt(e.target.value))} className="bg-secondary/50" min={0} max={360} />
                    </div>
                    <div className="space-y-2">
                      <Label className="text-xs">Performance Ratio</Label>
                      <Input type="number" value={arr.perf_ratio} onChange={(e) => updateSolarArray(index, "perf_ratio", parseFloat(e.target.value))} className="bg-secondary/50" step={0.01} min={0.5} max={1} />
                    </div>
                    <div className="space-y-2">
                      <Label className="text-xs">Albedo</Label>
                      <Input type="number" value={arr.albedo} onChange={(e) => updateSolarArray(index, "albedo", parseFloat(e.target.value))} className="bg-secondary/50" step={0.05} min={0} max={1} />
                    </div>
                  </div>
                </div>
              ))}
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      </TabsContent>

      {/* ============== POWER TAB ============== */}
      <TabsContent value="power" className="space-y-4">
        <Accordion type="multiple" defaultValue={["battery-config", "work-mode", "work-mode-detail", "auxiliary"]} className="space-y-2">
          
          {/* Battery Configuration */}
          <AccordionItem value="battery-config" className="glass-card border-none">
            <AccordionTrigger className="px-4 hover:no-underline">
              <div className="flex items-center gap-2">
                <Battery className="w-4 h-4 text-battery" />
                <span>Battery Configuration</span>
              </div>
            </AccordionTrigger>
            <AccordionContent className="px-4 pb-4">
              <SettingRow label="Battery Type" value={batteryConfig.type} editable onEdit={(v) => setBatteryConfig({ ...batteryConfig, type: v })} />
              <SettingRow label="Battery Capacity" value={batteryConfig.capacity} unit="Ah" editable onEdit={(v) => setBatteryConfig({ ...batteryConfig, capacity: parseInt(v) })} />
              <SettingRow label="Battery Operation" value={batteryConfig.operation} editable onEdit={(v) => setBatteryConfig({ ...batteryConfig, operation: v })} />
              <div className="border-t border-border/50 my-3" />
              <SettingRow label="Max Discharge Current" value={batteryConfig.maxDischargeCurrent} unit="A" editable onEdit={(v) => setBatteryConfig({ ...batteryConfig, maxDischargeCurrent: parseInt(v) })} />
              <SettingRow label="Max Charge Current" value={batteryConfig.maxChargeCurrent} unit="A" editable onEdit={(v) => setBatteryConfig({ ...batteryConfig, maxChargeCurrent: parseInt(v) })} />
              <SettingRow label="Max Grid Charge Current" value={batteryConfig.maxGridChargeCurrent} unit="A" editable onEdit={(v) => setBatteryConfig({ ...batteryConfig, maxGridChargeCurrent: parseInt(v) })} />
              <SettingRow label="Max Generator Charge Current" value={batteryConfig.maxGeneratorChargeCurrent} unit="A" editable onEdit={(v) => setBatteryConfig({ ...batteryConfig, maxGeneratorChargeCurrent: parseInt(v) })} />
              <SettingRow label="Max Grid Charger Power" value={batteryConfig.maxGridChargerPower} unit="W" editable onEdit={(v) => setBatteryConfig({ ...batteryConfig, maxGridChargerPower: parseInt(v) })} />
              <SettingRow label="Max Charger Power" value={batteryConfig.maxChargerPower} unit="W" description="Maximum total charging power" editable onEdit={(v) => setBatteryConfig({ ...batteryConfig, maxChargerPower: parseInt(v) })} />
              <SettingRow label="Max Discharger Power" value={batteryConfig.maxDischargerPower} unit="W" description="Maximum discharging power" editable onEdit={(v) => setBatteryConfig({ ...batteryConfig, maxDischargerPower: parseInt(v) })} />
            </AccordionContent>
          </AccordionItem>

          {/* Work Mode */}
          <AccordionItem value="work-mode" className="glass-card border-none">
            <AccordionTrigger className="px-4 hover:no-underline">
              <div className="flex items-center gap-2">
                <Settings2 className="w-4 h-4 text-warning" />
                <span>Work Mode</span>
              </div>
            </AccordionTrigger>
            <AccordionContent className="px-4 pb-4 space-y-1">
              <ToggleRow label="Remote Switch" checked={workMode.remoteSwitch} onCheckedChange={(v) => setWorkMode({ ...workMode, remoteSwitch: v })} />
              <ToggleRow label="Grid Charge" checked={workMode.gridCharge} onCheckedChange={(v) => setWorkMode({ ...workMode, gridCharge: v })} />
              <ToggleRow label="Generator Charge" checked={workMode.generatorCharge} onCheckedChange={(v) => setWorkMode({ ...workMode, generatorCharge: v })} />
              <ToggleRow label="Force Generator On" checked={workMode.forceGeneratorOn} onCheckedChange={(v) => setWorkMode({ ...workMode, forceGeneratorOn: v })} />
              
              <div className="space-y-3 pt-4">
                <div>
                  <div className="flex justify-between mb-2">
                    <Label className="text-sm">Output Shutdown Capacity</Label>
                    <span className="text-sm font-mono">{workMode.outputShutdownCapacity}%</span>
                  </div>
                  <Slider
                    value={[workMode.outputShutdownCapacity]}
                    onValueChange={([v]) => setWorkMode({ ...workMode, outputShutdownCapacity: v })}
                    max={50}
                    min={5}
                    step={5}
                  />
                </div>
                <div>
                  <div className="flex justify-between mb-2">
                    <Label className="text-sm">Stop Battery Discharge Capacity</Label>
                    <span className="text-sm font-mono">{workMode.stopBatteryDischargeCapacity}%</span>
                  </div>
                  <Slider
                    value={[workMode.stopBatteryDischargeCapacity]}
                    onValueChange={([v]) => setWorkMode({ ...workMode, stopBatteryDischargeCapacity: v })}
                    max={80}
                    min={10}
                    step={5}
                  />
                </div>
                <div>
                  <div className="flex justify-between mb-2">
                    <Label className="text-sm">Start Battery Discharge Capacity</Label>
                    <span className="text-sm font-mono">{workMode.startBatteryDischargeCapacity}%</span>
                  </div>
                  <Slider
                    value={[workMode.startBatteryDischargeCapacity]}
                    onValueChange={([v]) => setWorkMode({ ...workMode, startBatteryDischargeCapacity: v })}
                    max={90}
                    min={20}
                    step={5}
                  />
                </div>
                <div>
                  <div className="flex justify-between mb-2">
                    <Label className="text-sm">Start Grid Charge Capacity</Label>
                    <span className="text-sm font-mono">{workMode.startGridChargeCapacity}%</span>
                  </div>
                  <Slider
                    value={[workMode.startGridChargeCapacity]}
                    onValueChange={([v]) => setWorkMode({ ...workMode, startGridChargeCapacity: v })}
                    max={50}
                    min={10}
                    step={5}
                  />
                </div>
              </div>

              <div className="border-t border-border/50 pt-4 mt-4 space-y-1">
                <ToggleRow 
                  label="Off-Grid Mode" 
                  description="Enable inverter operation without grid connection"
                  checked={workMode.offGridMode} 
                  onCheckedChange={(v) => setWorkMode({ ...workMode, offGridMode: v })} 
                />
                {workMode.offGridMode && (
                  <div className="pt-2">
                    <div className="flex justify-between mb-2">
                      <Label className="text-sm">Off-Grid Startup Battery Capacity</Label>
                      <span className="text-sm font-mono">{workMode.offGridStartupBatteryCapacity}%</span>
                    </div>
                    <Slider
                      value={[workMode.offGridStartupBatteryCapacity]}
                      onValueChange={([v]) => setWorkMode({ ...workMode, offGridStartupBatteryCapacity: v })}
                      max={80}
                      min={20}
                      step={5}
                    />
                    <p className="text-xs text-muted-foreground mt-1">Minimum battery capacity to start in off-grid mode</p>
                  </div>
                )}
              </div>
            </AccordionContent>
          </AccordionItem>

          {/* Work Mode Detail */}
          <AccordionItem value="work-mode-detail" className="glass-card border-none">
            <AccordionTrigger className="px-4 hover:no-underline">
              <div className="flex items-center gap-2">
                <Settings2 className="w-4 h-4 text-primary" />
                <span>Work Mode Detail</span>
              </div>
            </AccordionTrigger>
            <AccordionContent className="px-4 pb-4 space-y-4">
              <div className="space-y-2">
                <Label>Work Mode</Label>
                <Select value={workModeDetail.workMode} onValueChange={(v) => setWorkModeDetail({ ...workModeDetail, workMode: v })}>
                  <SelectTrigger className="bg-secondary/50">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="zero-export">Zero Export to Load</SelectItem>
                    <SelectItem value="feed-in">Feed-in Priority</SelectItem>
                    <SelectItem value="self-use">Self-Use Priority</SelectItem>
                    <SelectItem value="backup">Backup Mode</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <ToggleRow 
                label="Solar Export When Battery Full" 
                checked={workModeDetail.solarExportWhenFull} 
                onCheckedChange={(v) => setWorkModeDetail({ ...workModeDetail, solarExportWhenFull: v })} 
              />

              <div className="space-y-2">
                <Label>Energy Pattern</Label>
                <Select value={workModeDetail.energyPattern} onValueChange={(v) => setWorkModeDetail({ ...workModeDetail, energyPattern: v })}>
                  <SelectTrigger className="bg-secondary/50">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="load-first">Load First</SelectItem>
                    <SelectItem value="battery-first">Battery First</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
                <div className="space-y-2">
                  <Label>Max Sell Power (kW)</Label>
                  <Input
                    type="number"
                    value={workModeDetail.maxSellPower}
                    onChange={(e) => setWorkModeDetail({ ...workModeDetail, maxSellPower: Number(e.target.value) })}
                    className="bg-secondary/50"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Max Solar Power (kW)</Label>
                  <Input
                    type="number"
                    value={workModeDetail.maxSolarPower}
                    onChange={(e) => setWorkModeDetail({ ...workModeDetail, maxSolarPower: Number(e.target.value) })}
                    className="bg-secondary/50"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Grid Trickle Feed (W)</Label>
                  <Input
                    type="number"
                    value={workModeDetail.gridTrickleFeed}
                    onChange={(e) => setWorkModeDetail({ ...workModeDetail, gridTrickleFeed: Number(e.target.value) })}
                    className="bg-secondary/50"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Max Feed-in Grid Power (W)</Label>
                  <Input
                    type="number"
                    value={workModeDetail.maxFeedInPower}
                    onChange={(e) => setWorkModeDetail({ ...workModeDetail, maxFeedInPower: Number(e.target.value) })}
                    className="bg-secondary/50"
                  />
                  <p className="text-xs text-muted-foreground">Maximum power that can be fed into the grid</p>
                </div>
              </div>
            </AccordionContent>
          </AccordionItem>

          {/* Auxiliary / Generator */}
          <AccordionItem value="auxiliary" className="glass-card border-none">
            <AccordionTrigger className="px-4 hover:no-underline">
              <div className="flex items-center gap-2">
                <Power className="w-4 h-4 text-muted-foreground" />
                <span>Auxiliary / Generator</span>
              </div>
            </AccordionTrigger>
            <AccordionContent className="px-4 pb-4">
              <SettingRow label="Auxiliary Port" value={auxiliarySettings.auxiliaryPort} editable onEdit={(v) => setAuxiliarySettings({ ...auxiliarySettings, auxiliaryPort: v })} />
              <ToggleRow 
                label="Generator Connected to Grid Input" 
                checked={auxiliarySettings.generatorConnectedToGrid}
                onCheckedChange={(v) => setAuxiliarySettings({ ...auxiliarySettings, generatorConnectedToGrid: v })}
              />
              <ToggleRow 
                label="Generator Peak Shaving" 
                checked={auxiliarySettings.generatorPeakShaving}
                onCheckedChange={(v) => setAuxiliarySettings({ ...auxiliarySettings, generatorPeakShaving: v })}
              />
              {auxiliarySettings.generatorPeakShaving && (
                <SettingRow label="Generator Peak Shaving Power" value={auxiliarySettings.generatorPeakShavingPower} unit="kW" editable onEdit={(v) => setAuxiliarySettings({ ...auxiliarySettings, generatorPeakShavingPower: parseFloat(v) })} />
              )}
              <SettingRow label="Generator Stop Capacity" value={auxiliarySettings.generatorStopCapacity || "—"} unit="%" editable onEdit={(v) => setAuxiliarySettings({ ...auxiliarySettings, generatorStopCapacity: parseFloat(v) })} />
              <SettingRow label="Generator Start Capacity" value={auxiliarySettings.generatorStartCapacity} unit="%" editable onEdit={(v) => setAuxiliarySettings({ ...auxiliarySettings, generatorStartCapacity: parseFloat(v) })} />
              <SettingRow label="Generator Max Run Time" value={auxiliarySettings.generatorMaxRunTime} unit="h" editable onEdit={(v) => setAuxiliarySettings({ ...auxiliarySettings, generatorMaxRunTime: parseInt(v) })} />
              <SettingRow label="Generator Down Time" value={auxiliarySettings.generatorDownTime} unit="h" editable onEdit={(v) => setAuxiliarySettings({ ...auxiliarySettings, generatorDownTime: parseInt(v) })} />
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      </TabsContent>

      {/* ============== SCHEDULING TAB ============== */}
      <TabsContent value="scheduling" className="space-y-4">
        <div className="glass-card p-4 sm:p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <Clock className="w-5 h-5 text-primary" />
              <div>
                <h3 className="font-semibold">Time of Use (TOU) Windows</h3>
                <p className="text-sm text-muted-foreground">Configure up to 6 bidirectional windows</p>
              </div>
            </div>
            {touWindows.length < 6 && (
              <Button
                size="sm"
                variant="outline"
                onClick={addTouWindow}
                className="gap-1.5"
              >
                <Plus className="h-4 w-4" />
                Add Window
              </Button>
            )}
          </div>

          {/* Visual Timeline */}
          <TOUTimeline windows={touWindows} />

          {/* Window Rows */}
          <div className="space-y-3">
            {touWindows.map((window, idx) => (
              <TOUWindowRow
                key={idx}
                windowNum={idx + 1}
                data={window}
                onUpdate={(data) => updateTouWindow(idx, data)}
                onDelete={() => deleteTouWindow(idx)}
              />
            ))}
          </div>

          {touWindows.length === 0 && (
            <div className="text-center py-8 text-muted-foreground">
              <Clock className="h-12 w-12 mx-auto mb-3 opacity-30" />
              <p>No TOU windows configured</p>
              <Button
                size="sm"
                variant="outline"
                onClick={addTouWindow}
                className="mt-3 gap-1.5"
              >
                <Plus className="h-4 w-4" />
                Add First Window
              </Button>
            </div>
          )}
        </div>
      </TabsContent>
    </Tabs>
  );
  }
);
InverterDeviceSettings.displayName = 'InverterDeviceSettings';
