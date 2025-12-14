import React from "react";
import { motion } from "framer-motion";
import { Zap, ArrowUpRight, ArrowDownLeft, Activity, Gauge, TrendingUp, TrendingDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { useHomeTelemetry, useHourlyEnergy, useMeterTelemetry } from "@root/api/hooks";
import { useDevicesData } from "@/data/mockDataHooks";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";

interface MeterTelemetryProps {
  device: {
    id: string;
    name: string;
    metrics: { label: string; value: string; unit: string }[];
  };
}

// Phase data is now calculated from telemetry in the component

// Historical import/export data
const generateHistoricalData = () => {
  return Array.from({ length: 24 }, (_, i) => {
    const hour = i;
    const sunIntensity = Math.max(0, Math.sin((hour - 6) * Math.PI / 12));
    const baseConsumption = 3 + (hour >= 18 && hour <= 22 ? 3 : 0) + (hour >= 7 && hour <= 9 ? 1.5 : 0);
    const solarProduction = sunIntensity * 12;
    const netPower = baseConsumption - solarProduction;
    
    return {
      time: `${hour.toString().padStart(2, "0")}:00`,
      import: Math.max(0, netPower + Math.random() * 0.5),
      export: Math.max(0, -netPower + Math.random() * 0.5),
      consumption: baseConsumption + Math.random() * 0.5,
    };
  });
};

const historicalData = generateHistoricalData();

// This is now calculated from hourly data in the component

interface PhaseData {
  phase: string;
  voltage: number;
  current: number;
  power: number;
  powerFactor: number;
  direction: "import" | "export";
  frequency: number;
}

const PhaseCard = ({ data, index }: { data: PhaseData; index: number }) => (
  <motion.div
    initial={{ opacity: 0, x: -20 }}
    animate={{ opacity: 1, x: 0 }}
    transition={{ delay: index * 0.1 }}
    className="bg-secondary/30 rounded-xl p-4 border border-border/50"
  >
    <div className="flex items-center justify-between mb-4">
      <div className="flex items-center gap-2">
        <div className={cn(
          "w-10 h-10 rounded-lg flex items-center justify-center font-bold text-lg",
          index === 0 && "bg-red-500/20 text-red-400",
          index === 1 && "bg-yellow-500/20 text-yellow-400",
          index === 2 && "bg-blue-500/20 text-blue-400"
        )}>
          {data.phase}
        </div>
        <span className="text-sm text-muted-foreground">Phase {index + 1}</span>
      </div>
      <div className={cn(
        "flex items-center gap-1 text-xs px-2 py-1 rounded-full",
        data.direction === "import" 
          ? "bg-warning/20 text-warning" 
          : "bg-success/20 text-success"
      )}>
        {data.direction === "import" 
          ? <ArrowDownLeft className="w-3 h-3" /> 
          : <ArrowUpRight className="w-3 h-3" />
        }
        {data.direction === "import" ? "Import" : "Export"}
      </div>
    </div>
    
    <div className="grid grid-cols-2 gap-3">
      <div>
        <p className="text-xs text-muted-foreground mb-0.5">Voltage</p>
        <p className="text-lg font-mono font-bold text-foreground">{data.voltage.toFixed(3)}V</p>
      </div>
      <div>
        <p className="text-xs text-muted-foreground mb-0.5">Current</p>
        <p className="text-lg font-mono font-bold text-foreground">{data.current.toFixed(2)}A</p>
      </div>
      <div>
        <p className="text-xs text-muted-foreground mb-0.5">Power</p>
        <p className={cn(
          "text-lg font-mono font-bold",
          data.direction === "export" ? "text-success" : "text-warning"
        )}>{data.power.toFixed(2)}kW</p>
      </div>
      <div>
        <p className="text-xs text-muted-foreground mb-0.5">Power Factor</p>
        <p className={cn(
          "text-lg font-mono font-bold",
          data.powerFactor >= 0.95 ? "text-success" : data.powerFactor >= 0.9 ? "text-warning" : "text-destructive"
        )}>{data.powerFactor.toFixed(2)}</p>
      </div>
    </div>
    
    {/* Power bar visualization */}
    <div className="mt-3 pt-3 border-t border-border/30">
      <div className="flex items-center justify-between text-xs text-muted-foreground mb-1">
        <span>Power Load</span>
        <span>{((data.power / 5) * 100).toFixed(0)}%</span>
      </div>
      <div className="h-2 bg-secondary rounded-full overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${(data.power / 5) * 100}%` }}
          transition={{ delay: index * 0.1 + 0.3, duration: 0.5 }}
          className={cn(
            "h-full rounded-full",
            data.direction === "export" ? "bg-success" : "bg-warning"
          )}
        />
      </div>
    </div>
  </motion.div>
);

const MeterTelemetry = ({ device }: MeterTelemetryProps) => {
  // Fetch dedicated meter telemetry from /api/meter/now
  const { data: meterTelemetry, isLoading: meterLoading, error: meterError } = useMeterTelemetry(device.id, { refetchInterval: 5000 });
  
  // Fetch hourly energy for charts
  const { data: hourlyData } = useHourlyEnergy({ inverterId: undefined });
  
  // Get devices to find meter info (fallback)
  const devices = useDevicesData();
  const meterDevice = devices.find(d => d.id === device.id && d.type === "meter");
  
  // Show loading or error state
  if (meterLoading) {
    return <div className="text-center py-8 text-muted-foreground">Loading meter telemetry...</div>;
  }
  
  if (meterError) {
    return <div className="text-center py-8 text-destructive">Error loading meter telemetry: {String(meterError)}</div>;
  }
  
  if (!meterTelemetry) {
    return <div className="text-center py-8 text-muted-foreground">No meter telemetry data available. Meter may not be connected or polling.</div>;
  }
  
  // Calculate today's stats from hourly data
  const todayStats = React.useMemo(() => {
    if (!hourlyData || hourlyData.length === 0) {
      return {
        totalImport: 0,
        totalExport: 0,
        peakImport: 0,
        peakExport: 0,
        netEnergy: 0,
      };
    }
    
    let totalImport = 0;
    let totalExport = 0;
    let peakImport = 0;
    let peakExport = 0;
    
    hourlyData.forEach(item => {
      if (item.grid > 0) {
        totalImport += item.grid;
        peakImport = Math.max(peakImport, item.grid);
      } else {
        totalExport += Math.abs(item.grid);
        peakExport = Math.max(peakExport, Math.abs(item.grid));
      }
    });
    
    return {
      totalImport,
      totalExport,
      peakImport,
      peakExport,
      netEnergy: totalExport - totalImport,
    };
  }, [hourlyData]);
  
  // Extract meter data from telemetry
  // Backend returns: grid_power_w (positive = import, negative = export)
  const currentPower = meterTelemetry?.grid_power_w ? meterTelemetry.grid_power_w / 1000 : 0; // Convert W to kW
  const importKwh = meterTelemetry?.grid_import_wh ? meterTelemetry.grid_import_wh / 1000 : 0; // Convert Wh to kWh
  const exportKwh = meterTelemetry?.grid_export_wh ? meterTelemetry.grid_export_wh / 1000 : 0; // Convert Wh to kWh
  const gridVoltage = meterTelemetry?.grid_voltage_v || null;
  const gridCurrent = meterTelemetry?.grid_current_a || null;
  const gridFrequency = meterTelemetry?.grid_frequency_hz || null;
  const powerFactor = meterTelemetry?.power_factor || null;
  
  // Check if three-phase meter (has phase-specific data)
  const isThreePhase = !!(meterTelemetry?.voltage_phase_a || meterTelemetry?.voltage_phase_b || meterTelemetry?.voltage_phase_c);
  
  // Generate phase data from real meter telemetry
  const phaseData = isThreePhase && meterTelemetry ? [
    {
      phase: "L1",
      voltage: meterTelemetry.voltage_phase_a || meterTelemetry.grid_voltage_v || 0,
      current: meterTelemetry.current_phase_a || 0,
      power: meterTelemetry.power_phase_a ? meterTelemetry.power_phase_a / 1000 : 0, // Convert W to kW
      powerFactor: powerFactor || 0.97,
      direction: (meterTelemetry.power_phase_a ?? 0) < 0 ? "export" as const : "import" as const,
      frequency: gridFrequency || 50.0,
    },
    {
      phase: "L2",
      voltage: meterTelemetry.voltage_phase_b || meterTelemetry.grid_voltage_v || 0,
      current: meterTelemetry.current_phase_b || 0,
      power: meterTelemetry.power_phase_b ? meterTelemetry.power_phase_b / 1000 : 0,
      powerFactor: powerFactor || 0.95,
      direction: (meterTelemetry.power_phase_b ?? 0) < 0 ? "export" as const : "import" as const,
      frequency: gridFrequency || 50.0,
    },
    {
      phase: "L3",
      voltage: meterTelemetry.voltage_phase_c || meterTelemetry.grid_voltage_v || 0,
      current: meterTelemetry.current_phase_c || 0,
      power: meterTelemetry.power_phase_c ? meterTelemetry.power_phase_c / 1000 : 0,
      powerFactor: powerFactor || 0.96,
      direction: (meterTelemetry.power_phase_c ?? 0) < 0 ? "export" as const : "import" as const,
      frequency: gridFrequency || 50.0,
    },
  ] : [
    {
      phase: "L1",
      voltage: gridVoltage || 0,
      current: gridCurrent || 0,
      power: Math.abs(currentPower),
      powerFactor: powerFactor || 0.97,
      direction: currentPower < 0 ? "export" as const : "import" as const,
      frequency: gridFrequency || 50.0,
    },
  ];
  
  // Use hourly data for charts
  const chartData = hourlyData && hourlyData.length > 0
    ? hourlyData.map(item => ({
        time: item.time,
        import: item.grid > 0 ? item.grid : 0,
        export: item.grid < 0 ? Math.abs(item.grid) : 0,
        consumption: item.load,
      }))
    : historicalData;
  const totalPower = phaseData.reduce((sum, p) => sum + (p.direction === "import" ? p.power : -p.power), 0);
  const avgPowerFactor = phaseData.reduce((sum, p) => sum + p.powerFactor, 0) / phaseData.length;
  const avgVoltage = phaseData.reduce((sum, p) => sum + p.voltage, 0) / phaseData.length;
  
  return (
    <div className="space-y-6">
      {/* Summary Stats */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-card p-5"
      >
        <h3 className="text-lg font-semibold text-foreground mb-4">Today's Summary</h3>
        
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div className="bg-secondary/30 rounded-lg p-3 text-center">
            <div className="flex items-center justify-center gap-1 mb-1">
              <ArrowDownLeft className="w-4 h-4 text-warning" />
              <span className="text-xs text-muted-foreground">Total Import</span>
            </div>
            <p className="text-2xl font-mono font-bold text-warning">{todayStats.totalImport}</p>
            <p className="text-xs text-muted-foreground">kWh</p>
          </div>
          <div className="bg-secondary/30 rounded-lg p-3 text-center">
            <div className="flex items-center justify-center gap-1 mb-1">
              <ArrowUpRight className="w-4 h-4 text-success" />
              <span className="text-xs text-muted-foreground">Total Export</span>
            </div>
            <p className="text-2xl font-mono font-bold text-success">{todayStats.totalExport}</p>
            <p className="text-xs text-muted-foreground">kWh</p>
          </div>
          <div className="bg-secondary/30 rounded-lg p-3 text-center">
            <div className="flex items-center justify-center gap-1 mb-1">
              <TrendingDown className="w-4 h-4 text-warning" />
              <span className="text-xs text-muted-foreground">Peak Import</span>
            </div>
            <p className="text-2xl font-mono font-bold text-foreground">{todayStats.peakImport}</p>
            <p className="text-xs text-muted-foreground">kW</p>
          </div>
          <div className="bg-secondary/30 rounded-lg p-3 text-center">
            <div className="flex items-center justify-center gap-1 mb-1">
              <TrendingUp className="w-4 h-4 text-success" />
              <span className="text-xs text-muted-foreground">Peak Export</span>
            </div>
            <p className="text-2xl font-mono font-bold text-foreground">{todayStats.peakExport}</p>
            <p className="text-xs text-muted-foreground">kW</p>
          </div>
          <div className="bg-secondary/30 rounded-lg p-3 text-center">
            <div className="flex items-center justify-center gap-1 mb-1">
              <Activity className="w-4 h-4 text-primary" />
              <span className="text-xs text-muted-foreground">Net Energy</span>
            </div>
            <p className={cn(
              "text-2xl font-mono font-bold",
              todayStats.netEnergy < 0 ? "text-success" : "text-warning"
            )}>
              {todayStats.netEnergy > 0 ? "+" : ""}{todayStats.netEnergy}
            </p>
            <p className="text-xs text-muted-foreground">kWh</p>
          </div>
        </div>
      </motion.div>

      {/* Phase Data */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="glass-card p-5"
      >
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-foreground">Three-Phase Data</h3>
            <p className="text-sm text-muted-foreground">Real-time per-phase measurements</p>
          </div>
          <div className="text-right">
            <p className="text-xs text-muted-foreground">Total Power</p>
            <p className={cn(
              "text-xl font-mono font-bold",
              totalPower > 0 ? "text-warning" : "text-success"
            )}>
              {totalPower > 0 ? "+" : ""}{totalPower.toFixed(2)} kW
            </p>
          </div>
        </div>
        
        <div className="grid md:grid-cols-3 gap-4">
          {phaseData.map((phase, index) => (
            <PhaseCard key={phase.phase} data={phase} index={index} />
          ))}
        </div>
        
        {/* Grid Stats */}
        <div className="grid grid-cols-3 gap-4 mt-4 pt-4 border-t border-border/30">
          <div className="text-center">
            <p className="text-xs text-muted-foreground mb-1">Avg Voltage</p>
            <p className="text-lg font-mono font-bold text-foreground">{avgVoltage.toFixed(3)}V</p>
          </div>
          <div className="text-center">
            <p className="text-xs text-muted-foreground mb-1">Frequency</p>
            <p className="text-lg font-mono font-bold text-foreground">50.01Hz</p>
          </div>
          <div className="text-center">
            <p className="text-xs text-muted-foreground mb-1">Avg Power Factor</p>
            <p className={cn(
              "text-lg font-mono font-bold",
              avgPowerFactor >= 0.95 ? "text-success" : "text-warning"
            )}>{avgPowerFactor.toFixed(2)}</p>
          </div>
        </div>
      </motion.div>

      {/* Import/Export History */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="glass-card p-5"
      >
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-foreground">Import/Export History</h3>
            <p className="text-sm text-muted-foreground">24-hour grid energy flow</p>
          </div>
          <div className="flex items-center gap-4 text-xs">
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-3 rounded bg-warning" />
              <span className="text-muted-foreground">Import</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-3 rounded bg-success" />
              <span className="text-muted-foreground">Export</span>
            </div>
          </div>
        </div>
        
        <div className="h-[250px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.3} />
              <XAxis 
                dataKey="time" 
                stroke="hsl(var(--muted-foreground))" 
                fontSize={10}
                tickLine={false}
              />
              <YAxis 
                stroke="hsl(var(--muted-foreground))" 
                fontSize={10}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v) => `${v}kW`}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "hsl(var(--card))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: "8px",
                  fontSize: "12px",
                }}
              />
              <Bar dataKey="import" fill="hsl(var(--warning))" name="Import" radius={[2, 2, 0, 0]} />
              <Bar dataKey="export" fill="hsl(var(--success))" name="Export" radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </motion.div>
    </div>
  );
};

export default MeterTelemetry;
