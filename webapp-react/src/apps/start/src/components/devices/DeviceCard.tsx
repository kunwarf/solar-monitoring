import { motion } from "framer-motion";
import { Cpu, Gauge, Settings, Activity, Sun, Home, Zap, ArrowDown, ArrowUp, Battery } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

interface DeviceCardProps {
  id: string;
  name: string;
  type: "inverter" | "battery" | "meter";
  status: "online" | "offline" | "warning";
  model: string;
  serialNumber: string;
  metrics: {
    label: string;
    value: string;
    unit: string;
  }[];
  onConfigure?: () => void;
  onViewTelemetry?: () => void;
  delay?: number;
}

const typeColors = {
  inverter: {
    bg: "bg-solar/10",
    border: "border-solar/30",
    icon: "text-solar",
    accent: "text-solar",
  },
  battery: {
    bg: "bg-battery/10",
    border: "border-battery/30",
    icon: "text-battery",
    accent: "text-battery",
  },
  meter: {
    bg: "bg-grid/10",
    border: "border-grid/30",
    icon: "text-grid",
    accent: "text-grid",
  },
};

const statusColors = {
  online: "status-online",
  offline: "status-offline",
  warning: "status-warning",
};

const statusLabels = {
  online: { text: "Online", color: "bg-success/20 text-success" },
  offline: { text: "Offline", color: "bg-destructive/20 text-destructive" },
  warning: { text: "Warning", color: "bg-warning/20 text-warning" },
};

// Dynamic battery icon component
function DynamicBatteryIcon({ className, soc }: { className?: string; soc: number }) {
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
      className={className}
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
    </svg>
  );
}

// Device icon component based on type
function DeviceIcon({ type, className, soc = 78 }: { type: "inverter" | "battery" | "meter"; className?: string; soc?: number }) {
  if (type === "battery") {
    return <DynamicBatteryIcon className={className} soc={soc} />;
  }
  if (type === "inverter") {
    return <Cpu className={className} />;
  }
  return <Gauge className={className} />;
}

// Icon mapping for metric labels
const getMetricIcon = (label: string, type: "inverter" | "battery" | "meter") => {
  const labelLower = label.toLowerCase();
  if (labelLower.includes("solar") || labelLower.includes("production")) return Sun;
  if (labelLower.includes("grid")) return Zap;
  if (labelLower.includes("load") || labelLower.includes("consumption")) return Home;
  if (labelLower.includes("battery") || labelLower.includes("bat")) return Battery;
  if (labelLower.includes("soc") || labelLower.includes("charge")) return Battery;
  if (labelLower.includes("charging") || labelLower.includes("charge")) return ArrowDown;
  if (labelLower.includes("discharging") || labelLower.includes("discharge")) return ArrowUp;
  if (labelLower.includes("import")) return ArrowDown;
  if (labelLower.includes("export")) return ArrowUp;
  if (labelLower.includes("voltage") || labelLower.includes("volt")) return Gauge;
  if (labelLower.includes("temp") || labelLower.includes("temperature")) return Gauge;
  if (labelLower.includes("power")) return type === "meter" ? (labelLower.includes("export") ? ArrowUp : ArrowDown) : Zap;
  return Gauge;
};

const getMetricColor = (label: string, type: "inverter" | "battery" | "meter") => {
  const labelLower = label.toLowerCase();
  if (labelLower.includes("solar") || labelLower.includes("production")) return "text-warning";
  if (labelLower.includes("grid")) return "text-primary";
  if (labelLower.includes("load") || labelLower.includes("consumption")) return "text-success";
  if (labelLower.includes("battery") || labelLower.includes("bat") || labelLower.includes("soc")) return "text-cyan-400";
  if (labelLower.includes("charging") || labelLower.includes("charge")) return "text-success";
  if (labelLower.includes("discharging") || labelLower.includes("discharge")) return "text-warning";
  if (labelLower.includes("import")) return "text-destructive";
  if (labelLower.includes("export")) return "text-success";
  return "text-muted-foreground";
};

export function DeviceCard({
  id,
  name,
  type,
  status,
  model,
  serialNumber,
  metrics,
  onConfigure,
  onViewTelemetry,
  delay = 0,
}: DeviceCardProps) {
  const colors = typeColors[type];
  const statusConfig = statusLabels[status];
  
  // Use actual metrics from props, but ensure we have at least 4 for the grid
  const telemetryMetrics = metrics.length > 0 ? metrics : [];

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.4 }}
      className={cn(
        "glass-card-hover p-3 sm:p-5 border",
        colors.bg,
        colors.border
      )}
    >
      {/* Header */}
      <div className="flex items-center gap-2 sm:gap-4 mb-3 sm:mb-4">
        <div className={cn("w-10 h-10 sm:w-12 sm:h-12 rounded-xl flex items-center justify-center shrink-0", colors.bg)}>
          <DeviceIcon 
            type={type} 
            className={cn("w-5 h-5 sm:w-6 sm:h-6", colors.icon)} 
            soc={type === "battery" && telemetryMetrics.length > 0 
              ? parseFloat(telemetryMetrics.find(m => m.label.toLowerCase().includes("soc"))?.value || "0") 
              : 78} 
          />
        </div>

        <div className="flex-1 min-w-0">
          <h3 className="text-sm sm:text-base font-semibold text-foreground break-words">{name}</h3>
          <p className="text-[10px] sm:text-xs text-muted-foreground capitalize">{type}</p>
        </div>

        <div className="flex items-center gap-1.5 sm:gap-2 shrink-0">
          <span className="text-[10px] sm:text-xs text-muted-foreground capitalize hidden sm:inline">{status}</span>
          <div className={cn("w-2 h-2 sm:w-2.5 sm:h-2.5 rounded-full", statusColors[status])} />
        </div>
      </div>

      {/* Telemetry Metrics Grid - matching dashboard style */}
      <div className="grid grid-cols-2 gap-1.5 sm:gap-2 mb-3 sm:mb-4">
        {telemetryMetrics.map((metric, idx) => {
          const Icon = getMetricIcon(metric.label, type);
          const color = getMetricColor(metric.label, type);
          const isBatteryIcon = metric.label.toLowerCase().includes("soc") || 
                               (metric.label.toLowerCase().includes("battery") && type === "battery");
          const soc = isBatteryIcon && type === "battery" ? parseFloat(metric.value) : undefined;
          
          return (
            <div
              key={idx}
              className="flex items-center gap-1.5 sm:gap-2 p-1.5 sm:p-2 rounded-md bg-background/50"
            >
              {isBatteryIcon && soc !== undefined ? (
                <DynamicBatteryIcon className={cn("w-3.5 h-3.5 sm:w-4 sm:h-4 shrink-0", color)} soc={soc} />
              ) : (
                <Icon className={cn("w-3.5 h-3.5 sm:w-4 sm:h-4 shrink-0", color)} />
              )}
              <div className="min-w-0 flex-1">
                <p className="text-[9px] sm:text-[10px] text-muted-foreground truncate leading-tight">{metric.label}</p>
                <p className={cn("font-mono text-xs sm:text-sm font-medium truncate leading-tight", color)}>
                  {metric.value}
                  <span className="text-[9px] sm:text-[10px] text-muted-foreground ml-0.5">{metric.unit}</span>
                </p>
              </div>
            </div>
          );
        })}
      </div>

      {/* Model & Serial */}
      <div className="mb-3 sm:mb-4 p-1.5 sm:p-2 rounded-lg bg-muted/50">
        <div className="flex justify-between text-[10px] sm:text-xs">
          <span className="text-muted-foreground">Model</span>
          <span className="text-foreground font-medium truncate ml-2">{model}</span>
        </div>
        <div className="flex justify-between text-[10px] sm:text-xs mt-1">
          <span className="text-muted-foreground">Serial</span>
          <span className="font-mono text-foreground truncate ml-2">{serialNumber}</span>
        </div>
      </div>

      {/* Actions */}
      <div className="flex flex-col sm:flex-row gap-2">
        <Button
          variant="outline"
          size="sm"
          className="flex-1 text-xs sm:text-sm"
          onClick={onViewTelemetry}
        >
          <Activity className="w-3.5 h-3.5 sm:w-4 sm:h-4 mr-1.5 sm:mr-2" />
          Telemetry
        </Button>
        <Button
          variant="outline"
          size="sm"
          className="flex-1 text-xs sm:text-sm"
          onClick={onConfigure}
        >
          <Settings className="w-3.5 h-3.5 sm:w-4 sm:h-4 mr-1.5 sm:mr-2" />
          Configure
        </Button>
      </div>
    </motion.div>
  );
}