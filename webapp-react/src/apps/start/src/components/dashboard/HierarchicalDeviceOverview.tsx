import { motion } from "framer-motion";
import { Cpu, Gauge, ChevronRight, ChevronDown, Sun, Zap, Home, ArrowDown, ArrowUp, Layers, Battery } from "lucide-react";
import { cn } from "@/lib/utils";
import { Link } from "react-router-dom";
import { useState } from "react";
import {
  getInverterArrayAggregates,
  getBatteryArrayAggregates,
  InverterArray,
  BatteryArray,
  Inverter,
  BatteryBank,
  Meter,
  System,
} from "@/data/mockData";
import { useHomeHierarchyData } from "@/data/mockDataHooks";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";

const statusColors = {
  online: "status-online",
  offline: "status-offline",
  warning: "status-warning",
};

function DynamicBatteryIcon({ className, soc, isCharging }: { className?: string; soc: number; isCharging?: boolean }) {
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
      className={cn(className, isCharging && "animate-pulse")}
      xmlns="http://www.w3.org/2000/svg"
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

function getArrayStatus(onlineCount: number, warningCount: number, total: number): "online" | "warning" | "offline" {
  if (onlineCount === total) return "online";
  if (onlineCount === 0) return "offline";
  return "warning";
}

// System Card - displays a System summary at the top (like "Main Circuit")
function SystemCard({ system, index }: { system: System; index: number }) {
  // Aggregate data for the system (sum of all inverter arrays)
  const systemAgg = system.inverterArrays.reduce(
    (acc, array) => {
      const agg = getInverterArrayAggregates(array);
      return {
        solarPower: acc.solarPower + agg.solarPower,
        gridPower: acc.gridPower + agg.gridPower,
        loadPower: acc.loadPower + agg.loadPower,
        batteryPower: acc.batteryPower + agg.batteryPower,
        inverterCount: acc.inverterCount + agg.inverterCount,
        onlineCount: acc.onlineCount + agg.onlineCount,
        warningCount: acc.warningCount + agg.warningCount,
      };
    },
    { solarPower: 0, gridPower: 0, loadPower: 0, batteryPower: 0, inverterCount: 0, onlineCount: 0, warningCount: 0 }
  );
  
  // Battery array aggregates
  const batteryAggs = system.batteryArrays.map(ba => getBatteryArrayAggregates(ba));
  const totalBatteryCount = batteryAggs.reduce((sum, agg) => sum + agg.batteryCount, 0);
  const avgBatterySoc = batteryAggs.length > 0 
    ? batteryAggs.reduce((sum, agg) => sum + agg.avgSoc, 0) / batteryAggs.length 
    : 0;
  const totalBatteryPower = batteryAggs.reduce((sum, agg) => sum + agg.totalPower, 0);
  
  const status = getArrayStatus(systemAgg.onlineCount, systemAgg.warningCount, systemAgg.inverterCount);
  const isCharging = totalBatteryPower > 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.1 * index }}
      className="rounded-lg border border-border/50 bg-card/50 overflow-hidden"
    >
      {/* System Header - Always visible (like "Main Circuit") */}
      <div className="p-4">
        <div className="flex items-center gap-4 mb-3">
          <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
            <Layers className="w-5 h-5 text-primary" />
          </div>
          <div className="flex-1 min-w-0 text-left">
            <p className="text-sm font-semibold text-foreground truncate">{system.name}</p>
            <p className="text-xs text-muted-foreground">
              {system.inverterArrays.length} Inverter Array{system.inverterArrays.length > 1 ? "s" : ""}
              {system.batteryArrays.length > 0 && ` • ${system.batteryArrays.length} Battery Array${system.batteryArrays.length > 1 ? "s" : ""}`}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground capitalize">{status}</span>
            <div className={cn("w-2.5 h-2.5 rounded-full", statusColors[status])} />
          </div>
        </div>

        {/* System Aggregated Metrics */}
        <div className="grid grid-cols-5 gap-2">
          <div className="flex items-center gap-2 p-2 rounded-md bg-background/50">
            <Sun className="w-4 h-4 text-warning" />
            <div className="min-w-0 text-left">
              <p className="text-[10px] text-muted-foreground">Solar</p>
              <p className="font-mono text-sm font-medium text-foreground">
                {systemAgg.solarPower.toFixed(1)}<span className="text-xs text-muted-foreground ml-0.5">kW</span>
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 p-2 rounded-md bg-background/50">
            <Home className="w-4 h-4 text-success" />
            <div className="min-w-0 text-left">
              <p className="text-[10px] text-muted-foreground">Load</p>
              <p className="font-mono text-sm font-medium text-foreground">
                {systemAgg.loadPower.toFixed(1)}<span className="text-xs text-muted-foreground ml-0.5">kW</span>
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 p-2 rounded-md bg-background/50">
            <Zap className="w-4 h-4 text-primary" />
            <div className="min-w-0 text-left">
              <p className="text-[10px] text-muted-foreground">Grid</p>
              <p className="font-mono text-sm font-medium text-foreground">
                {systemAgg.gridPower.toFixed(1)}<span className="text-xs text-muted-foreground ml-0.5">kW</span>
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 p-2 rounded-md bg-background/50">
            <Battery className="w-4 h-4 text-cyan-400" />
            <div className="min-w-0 text-left">
              <p className="text-[10px] text-muted-foreground">Avg SOC</p>
              <p className="font-mono text-sm font-medium text-foreground">
                {avgBatterySoc.toFixed(0)}<span className="text-xs text-muted-foreground ml-0.5">%</span>
              </p>
            </div>
          </div>
        </div>
        
        {/* Charging indicator */}
        {totalBatteryPower !== 0 && (
          <div className="mt-2 flex items-center gap-2 p-2 rounded-md bg-background/50">
            {isCharging ? <ArrowDown className="w-4 h-4 text-success" /> : <ArrowUp className="w-4 h-4 text-warning" />}
            <div className="min-w-0 text-left">
              <p className="text-[10px] text-muted-foreground">{isCharging ? "Charging" : "Discharging"}</p>
              <p className="font-mono text-sm font-medium text-foreground">
                {Math.abs(totalBatteryPower).toFixed(1)}<span className="text-xs text-muted-foreground ml-0.5">kW</span>
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Inverter Arrays - Each as separate expandable card */}
      <div className="px-4 pb-4 space-y-3 border-t border-border/50 pt-4">
        {system.inverterArrays.map((array, arrIndex) => (
          <InverterArrayCard key={array.id} array={array} index={arrIndex} />
        ))}

        {/* Battery Arrays - Each as separate expandable card */}
        {system.batteryArrays.map((batteryArray, batIndex) => (
          <BatteryArrayCard key={batteryArray.id} batteryArray={batteryArray} index={batIndex} />
        ))}
      </div>
    </motion.div>
  );
}

// Inverter Array Card with aggregated data (expandable, shows nested inverters)
function InverterArrayCard({ array, index }: { array: InverterArray; index: number }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const agg = getInverterArrayAggregates(array);
  const status = getArrayStatus(agg.onlineCount, agg.warningCount, agg.inverterCount);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.1 * index }}
      className="rounded-lg border border-border/50 bg-card/50 overflow-hidden"
    >
      <Collapsible open={isExpanded} onOpenChange={setIsExpanded}>
        <CollapsibleTrigger asChild>
          <button className="w-full p-4 hover:bg-secondary/30 transition-colors">
            {/* Array Header */}
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                <Layers className="w-5 h-5 text-primary" />
              </div>
              <div className="flex-1 min-w-0 text-left">
                <p className="text-sm font-semibold text-foreground truncate">{array.name}</p>
                <p className="text-xs text-muted-foreground">
                  {agg.inverterCount} Inverter{agg.inverterCount > 1 ? "s" : ""} • {agg.solarPower.toFixed(1)} kW
                </p>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-muted-foreground capitalize">{status}</span>
                <div className={cn("w-2.5 h-2.5 rounded-full", statusColors[status])} />
                {isExpanded ? (
                  <ChevronDown className="w-4 h-4 text-muted-foreground" />
                ) : (
                  <ChevronRight className="w-4 h-4 text-muted-foreground" />
                )}
              </div>
            </div>
          </button>
        </CollapsibleTrigger>

        <CollapsibleContent>
          <div className="px-4 pb-4 space-y-3">
            {/* Individual Inverters */}
            {array.inverters.map((inv) => (
              <InverterCard key={inv.id} inverter={inv} />
            ))}
          </div>
        </CollapsibleContent>
      </Collapsible>
    </motion.div>
  );
}

// Battery Array Card with aggregated data (expandable, shows nested batteries)
function BatteryArrayCard({ batteryArray, index }: { batteryArray: BatteryArray; index: number }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const agg = getBatteryArrayAggregates(batteryArray);
  const status = getArrayStatus(
    batteryArray.batteries.filter(b => b.status === 'online').length,
    batteryArray.batteries.filter(b => b.status === 'warning').length,
    batteryArray.batteries.length
  );

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.1 * index }}
      className="rounded-lg border border-border/50 bg-card/50 overflow-hidden"
    >
      <Collapsible open={isExpanded} onOpenChange={setIsExpanded}>
        <CollapsibleTrigger asChild>
          <button className="w-full p-4 hover:bg-secondary/30 transition-colors">
            {/* Battery Array Header */}
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                <Battery className="w-5 h-5 text-primary" />
              </div>
              <div className="flex-1 min-w-0 text-left">
                <p className="text-sm font-semibold text-foreground truncate">{batteryArray.name}</p>
                <p className="text-xs text-muted-foreground">
                  {agg.batteryCount} Bank{agg.batteryCount > 1 ? "s" : ""} • {agg.avgSoc.toFixed(0)}% SOC
                </p>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-muted-foreground capitalize">{status}</span>
                <div className={cn("w-2.5 h-2.5 rounded-full", statusColors[status])} />
                {isExpanded ? (
                  <ChevronDown className="w-4 h-4 text-muted-foreground" />
                ) : (
                  <ChevronRight className="w-4 h-4 text-muted-foreground" />
                )}
              </div>
            </div>
          </button>
        </CollapsibleTrigger>

        <CollapsibleContent>
          <div className="px-4 pb-4 space-y-3">
            {/* Individual Batteries */}
            {batteryArray.batteries.length > 0 ? (
              batteryArray.batteries.map((bat) => (
                <BatteryCard key={bat.id} battery={bat} />
              ))
            ) : (
              <div className="p-3 rounded-lg border border-border/50 bg-secondary/30">
                <p className="text-xs text-muted-foreground">No battery data available</p>
              </div>
            )}
          </div>
        </CollapsibleContent>
      </Collapsible>
    </motion.div>
  );
}

// Individual Inverter Card
function InverterCard({ inverter }: { inverter: Inverter }) {
  return (
    <Link to={`/start/telemetry?device=${inverter.id}`}>
      <div className="p-3 rounded-lg border border-border/50 bg-secondary/30 hover:bg-secondary/50 transition-colors mb-2">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-8 h-8 rounded-lg bg-muted flex items-center justify-center">
            <Cpu className="w-4 h-4 text-muted-foreground" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-foreground truncate">{inverter.name}</p>
            <p className="text-xs text-muted-foreground">{inverter.model}</p>
          </div>
          <div className="flex items-center gap-2">
            <div className={cn("w-2 h-2 rounded-full", statusColors[inverter.status])} />
            <ChevronRight className="w-4 h-4 text-muted-foreground" />
          </div>
        </div>
        <div className="grid grid-cols-4 gap-2">
          <MetricPill icon={Sun} label="Solar" value={inverter.metrics.solarPower.toFixed(1)} unit="kW" color="text-warning" />
          <MetricPill icon={Zap} label="Grid" value={inverter.metrics.gridPower.toFixed(1)} unit="kW" color="text-primary" />
          <MetricPill icon={Home} label="Load" value={inverter.metrics.loadPower.toFixed(1)} unit="kW" color="text-success" />
          <MetricPill icon={Battery} label="Bat" value={inverter.metrics.batteryPower.toFixed(1)} unit="kW" color="text-cyan-400" />
        </div>
      </div>
    </Link>
  );
}

// Individual Battery Card
function BatteryCard({ battery }: { battery: BatteryBank }) {
  const isCharging = battery.metrics.power >= 0;
  return (
    <Link to={`/start/telemetry?device=${battery.id}`}>
      <div className="p-3 rounded-lg border border-border/50 bg-secondary/30 hover:bg-secondary/50 transition-colors mb-2">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-8 h-8 rounded-lg bg-muted flex items-center justify-center">
            <DynamicBatteryIcon className="w-4 h-4 text-muted-foreground" soc={battery.metrics.soc} isCharging={isCharging} />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-foreground truncate">{battery.name}</p>
            <p className="text-xs text-muted-foreground">{battery.model}</p>
          </div>
          <div className="flex items-center gap-2">
            <div className={cn("w-2 h-2 rounded-full", statusColors[battery.status])} />
            <ChevronRight className="w-4 h-4 text-muted-foreground" />
          </div>
        </div>
        <div className="grid grid-cols-4 gap-2">
          <MetricPill 
            icon={() => <DynamicBatteryIcon className="w-4 h-4" soc={battery.metrics.soc} />} 
            label="SOC" 
            value={battery.metrics.soc.toString()} 
            unit="%" 
            color="text-success" 
          />
          <MetricPill 
            icon={isCharging ? ArrowDown : ArrowUp} 
            label={isCharging ? "Chrg" : "Disch"} 
            value={Math.abs(battery.metrics.power).toFixed(1)} 
            unit="kW" 
            color={isCharging ? "text-success" : "text-warning"} 
          />
          <MetricPill icon={Gauge} label="Volt" value={battery.metrics.voltage > 0 ? battery.metrics.voltage.toFixed(1) : "N/A"} unit="V" color="text-muted-foreground" />
          <MetricPill icon={Gauge} label="Temp" value={battery.metrics.temperature > 0 ? battery.metrics.temperature.toString() : "N/A"} unit="°C" color="text-muted-foreground" />
        </div>
      </div>
    </Link>
  );
}

// Meter Card
function MeterCard({ meter }: { meter: Meter }) {
  const isExporting = meter.metrics.power < 0;
  const netExport = meter.metrics.exportKwh - meter.metrics.importKwh;
  
  return (
    <Link to={`/start/telemetry?device=${meter.id}`}>
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="p-4 rounded-lg bg-secondary/30 hover:bg-secondary/50 transition-colors"
      >
        <div className="flex items-center gap-4 mb-3">
          <div className="w-10 h-10 rounded-lg bg-muted flex items-center justify-center">
            <Gauge className="w-5 h-5 text-muted-foreground" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-foreground truncate">{meter.name}</p>
            <p className="text-xs text-muted-foreground">{meter.model}</p>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground capitalize">{meter.status}</span>
            <div className={cn("w-2.5 h-2.5 rounded-full", statusColors[meter.status])} />
            <ChevronRight className="w-4 h-4 text-muted-foreground" />
          </div>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          <div className="flex items-center gap-2 p-2 rounded-md bg-background/50">
            {isExporting ? <ArrowUp className="w-4 h-4 text-success" /> : <ArrowDown className="w-4 h-4 text-destructive" />}
            <div className="min-w-0">
              <p className="text-[10px] text-muted-foreground">{isExporting ? "Exporting" : "Importing"}</p>
              <p className="font-mono text-sm font-medium text-foreground">
                {Math.abs(meter.metrics.power / 1000).toFixed(1)}<span className="text-xs text-muted-foreground ml-0.5">kW</span>
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 p-2 rounded-md bg-background/50">
            <ArrowDown className="w-4 h-4 text-destructive" />
            <div className="min-w-0">
              <p className="text-[10px] text-muted-foreground">Import</p>
              <p className="font-mono text-sm font-medium text-foreground">
                {meter.metrics.importKwh.toFixed(1)}<span className="text-xs text-muted-foreground ml-0.5">kWh</span>
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 p-2 rounded-md bg-background/50">
            <ArrowUp className="w-4 h-4 text-success" />
            <div className="min-w-0">
              <p className="text-[10px] text-muted-foreground">Export</p>
              <p className="font-mono text-sm font-medium text-foreground">
                {meter.metrics.exportKwh.toFixed(1)}<span className="text-xs text-muted-foreground ml-0.5">kWh</span>
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 p-2 rounded-md bg-background/50">
            {netExport >= 0 ? <ArrowUp className="w-4 h-4 text-success" /> : <ArrowDown className="w-4 h-4 text-destructive" />}
            <div className="min-w-0">
              <p className="text-[10px] text-muted-foreground">{netExport >= 0 ? "Net Export" : "Net Import"}</p>
              <p className="font-mono text-sm font-medium text-foreground">
                {Math.abs(netExport).toFixed(1)}<span className="text-xs text-muted-foreground ml-0.5">kWh</span>
              </p>
            </div>
          </div>
        </div>
      </motion.div>
    </Link>
  );
}

// Metric Pill Component
function MetricPill({ 
  icon: Icon, 
  label, 
  value, 
  unit, 
  color 
}: { 
  icon: React.ComponentType<{ className?: string }> | (() => React.ReactNode); 
  label: string; 
  value: string; 
  unit: string; 
  color: string;
}) {
  return (
    <div className="flex items-center gap-1.5 p-2 rounded bg-background/30">
      {typeof Icon === 'function' && Icon.length === 0 ? (
        <Icon />
      ) : (
        <Icon className={cn("w-4 h-4", color)} />
      )}
      <div className="min-w-0 flex-1">
        <p className="text-[10px] text-muted-foreground truncate">{label}</p>
        <p className={cn("font-mono text-sm font-medium truncate", color)}>
          {value}<span className="text-[10px] ml-0.5">{unit}</span>
        </p>
      </div>
    </div>
  );
}

export function HierarchicalDeviceOverview() {
  // Get data from API (same structure as mockData.homeHierarchy)
  const homeHierarchy = useHomeHierarchyData();
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.4 }}
      className="glass-card p-6"
    >
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold text-foreground">Device Hierarchy</h3>
          <p className="text-sm text-muted-foreground">{homeHierarchy.name}</p>
        </div>
        <Link
          to="/start/devices"
          className="text-sm text-primary hover:text-primary/80 transition-colors flex items-center gap-1"
        >
          View All
          <ChevronRight className="w-4 h-4" />
        </Link>
      </div>

      <div className="space-y-4">
        {/* Systems (each System contains Inverter Arrays and Battery Arrays as siblings) */}
        {homeHierarchy.systems.map((system, index) => (
          <SystemCard key={system.id} system={system} index={index} />
        ))}

        {/* Meters */}
        {homeHierarchy.meters.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide px-1">Energy Meters</p>
            {homeHierarchy.meters.map((meter) => (
              <MeterCard key={meter.id} meter={meter} />
            ))}
          </div>
        )}
      </div>
    </motion.div>
  );
}
