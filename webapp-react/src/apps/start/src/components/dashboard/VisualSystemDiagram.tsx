import { motion } from "framer-motion";
import { Sun, Home, Grid3X3, Cpu, Gauge, ArrowRight, Thermometer, Zap, Activity, ArrowDown, ArrowUp, Battery as BatteryIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { Link } from "react-router-dom";
import { useHomeHierarchyData } from "@/data/mockDataHooks";
import type { Inverter, BatteryBank, Meter } from "@/data/mockData";
import { HoverCard, HoverCardContent, HoverCardTrigger } from "@/components/ui/hover-card";

const statusColors = {
  online: "bg-success",
  offline: "bg-destructive",
  warning: "bg-warning",
};

function DynamicBatteryIcon({ className, soc, isCharging, size = 24 }: { className?: string; soc: number; isCharging?: boolean; size?: number }) {
  const fillHeight = Math.max(0, Math.min(100, soc));
  const getFillColor = () => {
    if (soc >= 60) return "hsl(var(--success))";
    if (soc >= 30) return "hsl(var(--warning))";
    return "hsl(var(--destructive))";
  };

  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      width={size}
      height={size}
      className={cn(className, isCharging && "animate-pulse")}
    >
      <rect x="10" y="2" width="4" height="2" rx="0.5" fill="currentColor" opacity="0.6" />
      <rect x="6" y="4" width="12" height="18" rx="2" stroke="currentColor" strokeWidth="1.5" fill="none" />
      <rect
        x="7.5"
        y={4 + 16 * (1 - fillHeight / 100) + 1}
        width="9"
        height={16 * (fillHeight / 100)}
        rx="1"
        fill={getFillColor()}
      />
      {isCharging && (
        <path
          d="M13 8L10 13H12L11 16L14 11H12L13 8Z"
          fill="hsl(var(--background))"
          stroke="hsl(var(--background))"
          strokeWidth="0.5"
        />
      )}
    </svg>
  );
}

// Device node component with HoverCard for detailed metrics
function DeviceNode({ 
  device, 
  type, 
  index,
  total 
}: { 
  device: Inverter | BatteryBank | Meter; 
  type: "inverter" | "battery" | "meter";
  index: number;
  total: number;
}) {
  const getIcon = () => {
    if (type === "inverter") return <Cpu className="w-5 h-5" />;
    if (type === "battery") {
      const bat = device as BatteryBank;
      return <DynamicBatteryIcon soc={bat.metrics?.soc || 0} isCharging={(bat.metrics?.power || 0) >= 0} size={18} />;
    }
    return <Gauge className="w-5 h-5" />;
  };

  const getValue = () => {
    if (type === "inverter") {
      const inv = device as Inverter;
      return `${inv.metrics?.solarPower?.toFixed(1) || "0.0"} kW`;
    }
    if (type === "battery") {
      const bat = device as BatteryBank;
      return `${bat.metrics?.soc?.toFixed(0) || "0"}%`;
    }
    const meter = device as Meter;
    return `${Math.abs(meter.metrics?.power || 0).toFixed(1)} kW`;
  };

  const getColor = () => {
    if (type === "inverter") return "bg-warning/20 border-warning/40 text-warning";
    if (type === "battery") return "bg-cyan-400/20 border-cyan-400/40 text-cyan-400";
    return "bg-primary/20 border-primary/40 text-primary";
  };

  const renderHoverContent = () => {
    if (type === "inverter") {
      const inv = device as Inverter;
      return (
        <div className="space-y-3">
          <div className="flex items-center gap-2 pb-2 border-b border-border">
            <Cpu className="w-4 h-4 text-warning" />
            <div>
              <p className="font-semibold text-sm">{inv.name}</p>
              <p className="text-xs text-muted-foreground">{inv.model}</p>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="flex items-center gap-1.5">
              <Sun className="w-3 h-3 text-warning" />
              <span className="text-muted-foreground">Solar</span>
              <span className="ml-auto font-mono font-medium">{(inv.metrics?.solarPower || 0).toFixed(1)} kW</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Grid3X3 className="w-3 h-3 text-primary" />
              <span className="text-muted-foreground">Grid</span>
              <span className="ml-auto font-mono font-medium">{(inv.metrics?.gridPower || 0).toFixed(1)} kW</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Activity className="w-3 h-3 text-success" />
              <span className="text-muted-foreground">Load</span>
              <span className="ml-auto font-mono font-medium">{(inv.metrics?.loadPower || 0).toFixed(1)} kW</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Zap className="w-3 h-3 text-cyan-400" />
              <span className="text-muted-foreground">Battery</span>
              <span className="ml-auto font-mono font-medium">{(inv.metrics?.batteryPower || 0).toFixed(1)} kW</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Zap className="w-3 h-3 text-muted-foreground" />
              <span className="text-muted-foreground">DC Volt</span>
              <span className="ml-auto font-mono font-medium">{inv.metrics?.dcVoltage || 0} V</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Thermometer className="w-3 h-3 text-orange-400" />
              <span className="text-muted-foreground">Temp</span>
              <span className="ml-auto font-mono font-medium">{inv.metrics?.temperature || 0}°C</span>
            </div>
          </div>
          <div className="pt-2 border-t border-border">
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Efficiency</span>
              <span className="font-mono font-medium text-success">{(inv.metrics?.efficiency || 0).toFixed(1)}%</span>
            </div>
          </div>
        </div>
      );
    }

    if (type === "battery") {
      const bat = device as BatteryBank;
      const isCharging = (bat.metrics?.power || 0) >= 0;
      return (
        <div className="space-y-3">
          <div className="flex items-center gap-2 pb-2 border-b border-border">
            <DynamicBatteryIcon soc={bat.metrics?.soc || 0} isCharging={isCharging} size={18} className="text-cyan-400" />
            <div>
              <p className="font-semibold text-sm">{bat.name}</p>
              <p className="text-xs text-muted-foreground">{bat.model}</p>
            </div>
          </div>
          <div className="space-y-2 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">State of Charge</span>
              <div className="flex items-center gap-1">
                <div className="w-16 h-2 bg-secondary rounded-full overflow-hidden">
                  <div 
                    className={cn("h-full rounded-full", (bat.metrics?.soc || 0) >= 60 ? "bg-success" : (bat.metrics?.soc || 0) >= 30 ? "bg-warning" : "bg-destructive")}
                    style={{ width: `${bat.metrics?.soc || 0}%` }}
                  />
                </div>
                <span className="font-mono font-medium w-8 text-right">{bat.metrics?.soc || 0}%</span>
              </div>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                {isCharging ? <ArrowDown className="w-3 h-3 text-success" /> : <ArrowUp className="w-3 h-3 text-orange-400" />}
                <span className="text-muted-foreground">{isCharging ? "Charging" : "Discharging"}</span>
              </div>
              <span className="font-mono font-medium">{Math.abs(bat.metrics?.power || 0).toFixed(1)} kW</span>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <Zap className="w-3 h-3 text-muted-foreground" />
                <span className="text-muted-foreground">Voltage</span>
              </div>
              <span className="font-mono font-medium">{(bat.metrics?.voltage || 0).toFixed(1)} V</span>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <Thermometer className="w-3 h-3 text-orange-400" />
                <span className="text-muted-foreground">Temperature</span>
              </div>
              <span className="font-mono font-medium">{bat.metrics?.temperature || 0}°C</span>
            </div>
          </div>
        </div>
      );
    }

    // Meter type
    const meter = device as Meter;
    const isExporting = (meter.metrics?.power || 0) < 0;
    const netImportExport = (meter.metrics?.exportKwh || 0) - (meter.metrics?.importKwh || 0);
    return (
      <div className="space-y-3">
        <div className="flex items-center gap-2 pb-2 border-b border-border">
          <Gauge className="w-4 h-4 text-primary" />
          <div>
            <p className="font-semibold text-sm">{meter.name}</p>
            <p className="text-xs text-muted-foreground">{meter.model}</p>
          </div>
        </div>
        <div className="space-y-2 text-xs">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              {isExporting ? <ArrowUp className="w-3 h-3 text-success" /> : <ArrowDown className="w-3 h-3 text-orange-400" />}
              <span className="text-muted-foreground">Current Power</span>
            </div>
            <span className={cn("font-mono font-medium", isExporting ? "text-success" : "text-orange-400")}>
              {isExporting ? "-" : "+"}{Math.abs(meter.metrics?.power || 0).toFixed(2)} kW
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Import Today</span>
            <span className="font-mono font-medium">{(meter.metrics?.importKwh || 0).toFixed(2)} kWh</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Export Today</span>
            <span className="font-mono font-medium">{(meter.metrics?.exportKwh || 0).toFixed(2)} kWh</span>
          </div>
          <div className="flex items-center justify-between pt-1 border-t border-border/50">
            <span className="text-muted-foreground">Net Import/Export</span>
            <span className={cn("font-mono font-medium", netImportExport >= 0 ? "text-success" : "text-orange-400")}>
              {netImportExport >= 0 ? "+" : ""}{netImportExport.toFixed(2)} kWh
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Frequency</span>
            <span className="font-mono font-medium">{(meter.metrics?.frequency || 0).toFixed(2)} Hz</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Power Factor</span>
            <span className="font-mono font-medium">{(meter.metrics?.powerFactor || 0).toFixed(2)}</span>
          </div>
        </div>
      </div>
    );
  };

  return (
    <HoverCard openDelay={100} closeDelay={100}>
      <HoverCardTrigger asChild>
        <Link to={`/telemetry?device=${device.id}`}>
          <motion.div
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ delay: 0.1 + index * 0.05, type: "spring", stiffness: 300 }}
            className={cn(
              "relative w-14 h-14 sm:w-16 sm:h-16 rounded-xl border-2 flex flex-col items-center justify-center cursor-pointer",
              "hover:scale-110 transition-transform",
              getColor()
            )}
          >
            {getIcon()}
            <span className="text-[10px] sm:text-xs font-mono font-medium mt-0.5">{getValue()}</span>
            <div className={cn(
              "absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full border border-background",
              statusColors[device.status]
            )} />
          </motion.div>
        </Link>
      </HoverCardTrigger>
      <HoverCardContent side="top" className="w-64 p-3">
        {renderHoverContent()}
      </HoverCardContent>
    </HoverCard>
  );
}

// Section containing devices of one type - with extra stats (horizontal layout)
function DeviceSection({ 
  title, 
  icon: Icon, 
  devices, 
  type, 
  aggregate,
  extraStats,
  color 
}: { 
  title: string;
  icon: React.ElementType;
  devices: (Inverter | BatteryBank | Meter)[];
  type: "inverter" | "battery" | "meter";
  aggregate: string;
  extraStats?: { label: string; value: string; highlight?: boolean }[];
  color: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        "rounded-xl border bg-card/30 p-3",
        color
      )}
    >
      {/* Horizontal layout: Left (header + devices) | Right (stats) */}
      <div className="flex items-stretch gap-3">
        {/* Left side: Header and device nodes */}
        <div className="flex flex-col min-w-0">
          {/* Header with icon and title */}
          <div className="flex items-center gap-2 mb-2">
            <div className={cn("w-8 h-8 rounded-lg flex items-center justify-center shrink-0", color.replace("border-", "bg-").replace("/30", "/20"))}>
              <Icon className="w-4 h-4" />
            </div>
            <div className="min-w-0">
              <p className="text-sm font-semibold text-foreground leading-tight">{title}</p>
              <p className="text-xs text-muted-foreground font-mono">{aggregate}</p>
            </div>
          </div>
          
          {/* Device nodes */}
          {devices.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {devices.map((device, i) => (
                <DeviceNode key={device.id} device={device} type={type} index={i} total={devices.length} />
              ))}
            </div>
          )}
        </div>

        {/* Right side: Stats - vertical layout with divider */}
        {extraStats && extraStats.length > 0 && (
          <div className="flex items-center gap-3 ml-auto">
            <div className="w-px h-full bg-border/40 self-stretch" />
            <div className="grid grid-cols-2 gap-x-4 gap-y-1.5">
              {extraStats.map((stat, i) => (
                <div key={i} className="flex items-center gap-1.5 whitespace-nowrap">
                  <span className="text-xs text-muted-foreground">{stat.label}:</span>
                  <span className={cn(
                    "text-xs font-mono font-bold",
                    stat.highlight ? "text-success" : "text-foreground"
                  )}>{stat.value}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </motion.div>
  );
}

// System visual block - compact horizontal layout
function SystemVisualBlock({ system, index }: { system: any; index: number }) {
  const allInverters = system.inverterArrays?.flatMap((arr: any) => arr.inverters || []) || [];
  const allBatteries = system.batteryArrays?.flatMap((arr: any) => arr.batteries || []) || [];
  
  // Calculate aggregates
  const totalInverterPower = allInverters.reduce((sum: number, inv: Inverter) => sum + (inv.metrics?.solarPower || 0), 0);
  const totalBatteryPower = allBatteries.reduce((sum: number, bat: BatteryBank) => sum + Math.abs(bat.metrics?.power || 0), 0);
  const avgBatterySoc = allBatteries.length > 0 
    ? allBatteries.reduce((sum: number, bat: BatteryBank) => sum + (bat.metrics?.soc || 0), 0) / allBatteries.length
    : 0;
  
  // Calculate daily stats (mock - in real app would come from data)
  const dailyGeneration = (totalInverterPower * 4.2).toFixed(1);
  const peakGeneration = (totalInverterPower * 1.2).toFixed(1);
  
  // Load stats
  const totalLoad = allInverters.reduce((sum: number, inv: Inverter) => sum + (inv.metrics?.loadPower || 0), 0);
  const peakLoad = Math.max(...allInverters.map((inv: Inverter) => inv.metrics?.loadPower || 0), 0);
  const avgLoad = allInverters.length > 0 ? totalLoad / allInverters.length : 0;
  
  // Battery stats
  const batteryCharging = totalBatteryPower >= 0;
  const batteryTodayCharge = (Math.abs(totalBatteryPower) * 3.5).toFixed(1);
  const batteryTodayDischarge = (Math.abs(totalBatteryPower) * 2.8).toFixed(1);
  const maxCharge = Math.max(...allBatteries.map((bat: BatteryBank) => Math.abs(bat.metrics?.power || 0)), 0);
  const maxDischarge = maxCharge;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1 }}
      className="rounded-xl border border-border/50 bg-card/50 p-3"
    >
      {/* System Header - compact */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
            <Home className="w-4 h-4 text-primary" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-foreground">{system.name}</h3>
            <p className="text-[10px] text-muted-foreground">
              {allInverters.length} inverters • {allBatteries.length} batteries • {system.meters?.length || 0} meters
            </p>
          </div>
        </div>
        <Link 
          to={`/devices?system=${system.id}`}
          className="text-xs text-primary hover:underline flex items-center gap-1"
        >
          Details <ArrowRight className="w-3 h-3" />
        </Link>
      </div>

      {/* Visual Flow Diagram - compact side-by-side layout */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 items-start">
        {/* Inverters Section */}
        {allInverters.length > 0 && (
          <DeviceSection
            title="Inverter"
            icon={Cpu}
            devices={allInverters}
            type="inverter"
            aggregate={`${totalInverterPower.toFixed(1)} kW`}
            extraStats={[
              { label: "Today", value: `${dailyGeneration} kWh`, highlight: true },
              { label: "Peak", value: `${peakGeneration} kW` },
              { label: "Peak Load", value: `${(peakLoad * 1.3).toFixed(1)} kW` },
              { label: "Avg Load", value: `${(avgLoad * 0.85).toFixed(1)} kW` },
            ]}
            color="border-warning/30 text-warning"
          />
        )}

        {/* Battery Section */}
        {allBatteries.length > 0 && (
          <DeviceSection
            title="Battery"
            icon={() => <DynamicBatteryIcon soc={avgBatterySoc} size={16} className="text-cyan-400" />}
            devices={allBatteries}
            type="battery"
            aggregate={`${avgBatterySoc.toFixed(0)}% • ${Math.abs(totalBatteryPower).toFixed(1)} kW`}
            extraStats={[
              { label: "Charged", value: `${batteryTodayCharge} kWh`, highlight: batteryCharging },
              { label: "Discharged", value: `${batteryTodayDischarge} kWh` },
              { label: "Max Charge", value: `${(maxCharge * 1.5).toFixed(1)} kW` },
              { label: "Max Discharge", value: `${(maxDischarge * 1.2).toFixed(1)} kW` },
            ]}
            color="border-cyan-400/30 text-cyan-400"
          />
        )}
      </div>
    </motion.div>
  );
}

export function VisualSystemDiagram() {
  const homeHierarchy = useHomeHierarchyData();
  
  if (!homeHierarchy) {
    return null;
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="rounded-xl border border-border/50 bg-card p-4"
    >
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-base font-semibold text-foreground">System Overview</h2>
          <p className="text-xs text-muted-foreground">{homeHierarchy.name}</p>
        </div>
        <Link
          to="/devices"
          className="text-xs text-primary hover:underline flex items-center gap-1"
        >
          View All <ArrowRight className="w-3 h-3" />
        </Link>
      </div>

      {/* Home-level meters - compact inline view */}
      {homeHierarchy.meters.length > 0 && (
        <div className="mb-3 p-3 rounded-xl border border-border/30 bg-secondary/20">
          <div className="flex items-center gap-2 mb-2">
            <Gauge className="w-5 h-5 text-primary" />
            <span className="text-sm font-medium text-foreground">Home Meters</span>
          </div>
          <div className="grid gap-2">
            {homeHierarchy.meters.map((meter, i) => {
              // Convert power from W to kW (meter.metrics.power is stored in W in DataProvider)
              const powerKw = (meter.metrics?.power || 0) / 1000;
              const isExporting = powerKw < 0;
              const netImportExport = (meter.metrics?.exportKwh || 0) - (meter.metrics?.importKwh || 0);
              return (
                <Link key={meter.id} to={`/telemetry?device=${meter.id}`}>
                  <motion.div
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.1 + i * 0.05 }}
                    className="flex items-center gap-3 p-2.5 rounded-lg border border-primary/20 bg-primary/5 hover:bg-primary/10 transition-colors cursor-pointer"
                  >
                    {/* Meter name & status */}
                    <div className="flex items-center gap-2.5 min-w-[140px]">
                      <div className="relative w-10 h-10 rounded-lg bg-primary/20 flex items-center justify-center shrink-0">
                        <Gauge className="w-5 h-5 text-primary" />
                        <div className={cn(
                          "absolute -top-0.5 -right-0.5 w-2.5 h-2.5 rounded-full border border-background",
                          statusColors[meter.status]
                        )} />
                      </div>
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-foreground truncate">{meter.name}</p>
                        <p className="text-xs text-muted-foreground truncate">{meter.model}</p>
                      </div>
                    </div>

                    {/* Current Power */}
                    <div className="flex items-center gap-1.5 min-w-[100px]">
                      {isExporting ? <ArrowUp className="w-4 h-4 text-success" /> : <ArrowDown className="w-4 h-4 text-orange-400" />}
                      <div>
                        <p className={cn("text-sm font-mono font-semibold", isExporting ? "text-success" : "text-orange-400")}>
                          {Math.abs(powerKw).toFixed(2)} kW {isExporting ? "Exporting" : "Importing"}
                        </p>
                      </div>
                    </div>

                    {/* Import */}
                    <div className="min-w-[80px] hidden sm:block">
                      <p className="text-sm font-mono font-medium text-foreground">{(meter.metrics?.importKwh || 0).toFixed(1)} kWh</p>
                      <p className="text-xs text-muted-foreground">Import</p>
                    </div>

                    {/* Export */}
                    <div className="min-w-[80px] hidden sm:block">
                      <p className="text-sm font-mono font-medium text-foreground">{(meter.metrics?.exportKwh || 0).toFixed(1)} kWh</p>
                      <p className="text-xs text-muted-foreground">Export</p>
                    </div>

                    {/* Net */}
                    <div className="min-w-[90px] hidden md:block">
                      <p className={cn("text-sm font-mono font-semibold", netImportExport >= 0 ? "text-success" : "text-orange-400")}>
                        {netImportExport >= 0 ? "+" : ""}{netImportExport.toFixed(1)} kWh
                      </p>
                      <p className="text-xs text-muted-foreground">Net Balance</p>
                    </div>

                    {/* Frequency */}
                    <div className="min-w-[70px] hidden lg:block">
                      <p className="text-sm font-mono font-medium text-foreground">{(meter.metrics?.frequency || 0).toFixed(2)} Hz</p>
                      <p className="text-xs text-muted-foreground">Freq</p>
                    </div>

                    {/* Power Factor */}
                    <div className="min-w-[50px] hidden lg:block">
                      <p className="text-sm font-mono font-medium text-foreground">{(meter.metrics?.powerFactor || 0).toFixed(2)}</p>
                      <p className="text-xs text-muted-foreground">PF</p>
                    </div>

                    <ArrowRight className="w-4 h-4 text-muted-foreground ml-auto shrink-0" />
                  </motion.div>
                </Link>
              );
            })}
          </div>
        </div>
      )}

      {/* Systems */}
      <div className="space-y-3">
        {homeHierarchy.systems.map((system, index) => (
          <SystemVisualBlock key={system.id} system={system} index={index} />
        ))}
      </div>
    </motion.div>
  );
}
