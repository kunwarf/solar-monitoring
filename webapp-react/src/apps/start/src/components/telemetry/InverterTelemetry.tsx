import React from "react";
import { motion } from "framer-motion";
import { Sun, Battery, Home, Zap, Activity, Thermometer, Gauge, TrendingUp } from "lucide-react";
import { cn } from "@/lib/utils";
import { useInverterTelemetry, useHourlyEnergy, useArrayTelemetry, useHomeHierarchy } from "@root/api/hooks";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
} from "recharts";

interface InverterTelemetryProps {
  device: {
    id: string;
    name: string;
    metrics: { label: string; value: string; unit: string }[];
  };
}

// Generate historical data for inverter
const generateHistoricalData = () => {
  return Array.from({ length: 24 }, (_, i) => {
    const hour = i;
    const sunIntensity = Math.max(0, Math.sin((hour - 6) * Math.PI / 12));
    return {
      time: `${hour.toString().padStart(2, "0")}:00`,
      solarPower: parseFloat((sunIntensity * 10 + Math.random() * 0.5).toFixed(1)),
      batteryPower: parseFloat((sunIntensity > 0.5 ? 2 + Math.random() * 0.5 : -1.5 - Math.random() * 0.5).toFixed(1)),
      loadPower: parseFloat((3 + Math.random() * 2 + (hour >= 18 && hour <= 22 ? 2 : 0)).toFixed(1)),
      gridPower: parseFloat((Math.random() * 2 - 1).toFixed(1)),
      efficiency: parseFloat((94 + Math.random() * 4).toFixed(1)),
      temperature: parseFloat((35 + sunIntensity * 15 + Math.random() * 5).toFixed(1)),
    };
  });
};

const historicalData = generateHistoricalData();

const PowerFlowCard = ({ 
  icon: Icon, 
  label, 
  value, 
  unit, 
  color, 
  direction,
  delay 
}: { 
  icon: any; 
  label: string; 
  value: string; 
  unit: string; 
  color: string;
  direction?: "in" | "out" | "bidirectional";
  delay: number;
}) => (
  <motion.div
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ delay }}
    className="bg-secondary/30 rounded-xl p-4 border border-border/50"
  >
    <div className="flex items-center justify-between mb-3">
      <div className={cn("p-2 rounded-lg", color)}>
        <Icon className="w-5 h-5" />
      </div>
      {direction && (
        <div className={cn(
          "text-xs px-2 py-0.5 rounded-full",
          direction === "in" && "bg-success/20 text-success",
          direction === "out" && "bg-warning/20 text-warning",
          direction === "bidirectional" && "bg-blue-500/20 text-blue-400"
        )}>
          {direction === "in" ? "↓ Import" : direction === "out" ? "↑ Export" : "↔ Bi-dir"}
        </div>
      )}
    </div>
    <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">{label}</p>
    <p className="text-2xl font-mono font-bold text-foreground">
      {value}<span className="text-sm text-muted-foreground ml-1">{unit}</span>
    </p>
  </motion.div>
);

// Solar array interface matching old app structure
interface SolarArray {
  id: string;
  name: string;
  power: number;
  voltage: number;
  current: number;
  status: "optimal" | "shaded" | "offline" | "low";
  panels?: number;
}

const arrayStatusStyles = {
  optimal: { bg: "bg-success/20", text: "text-success", label: "Optimal" },
  shaded: { bg: "bg-warning/20", text: "text-warning", label: "Partial Shade" },
  offline: { bg: "bg-destructive/20", text: "text-destructive", label: "Offline" },
  low: { bg: "bg-muted/50", text: "text-muted-foreground", label: "Low Output" },
};

const InverterTelemetry = ({ device }: InverterTelemetryProps) => {
  // Fetch real-time telemetry data
  const { data: telemetry, isLoading } = useInverterTelemetry(device.id, {
    refetchInterval: 5000,
  });
  
  // Get hierarchy to find which inverter array this device belongs to and access device name maps
  const { data: hierarchy } = useHomeHierarchy();
  
  // Find the inverter array that contains this device
  const inverterArray = hierarchy?.inverterArrays.find(array =>
    array.inverterIds.includes(device.id)
  );
  
  // Fetch array telemetry if we found the array
  const { data: arrayTelemetry } = useArrayTelemetry(inverterArray?.id || "", {
    enabled: !!inverterArray?.id,
    refetchInterval: 5000,
  });
  
  // Fetch hourly energy data for charts
  const { data: hourlyData } = useHourlyEnergy({ inverterId: device.id });
  
  // Map solar arrays from API data (matching old app structure)
  // IMPORTANT: Only show arrays for the SELECTED device, not all devices in the array
  const solarArrays = React.useMemo<SolarArray[]>(() => {
    if (!arrayTelemetry || !inverterArray) {
      return [];
    }
    
    const rawData = arrayTelemetry.raw as any;
    const invertersData = rawData?.inverters || [];
    
    // Filter to only show arrays for the selected device
    const selectedInverterId = device.id;
    if (!inverterArray.inverterIds.includes(selectedInverterId)) {
      return [];
    }
    
    // Get device name from config (preferred) or fallback to ID
    const deviceName = (hierarchy as any)?._deviceNames?.inverters?.get(selectedInverterId) ||
                      (selectedInverterId.includes('_') 
                        ? selectedInverterId.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase())
                        : selectedInverterId);
    
    // Find inverter data for the selected device
    const inverterData = invertersData.find((inv: any) => inv.inverter_id === selectedInverterId);
    
    // Check for individual MPPT channel data (pv1_power_w, pv2_power_w, mppt1_power_w, mppt2_power_w, etc.)
    const arrays: SolarArray[] = [];
    const extra = inverterData?.extra || telemetry?.raw?.extra || {};
    
    // Try to find MPPT channel data - check for pv1_power_w, pv2_power_w, mppt1_power_w, mppt2_power_w, etc.
    let mpptCount = 0;
    const mpptPowers: number[] = [];
    const mpptVoltages: number[] = [];
    const mpptCurrents: number[] = [];
    
    // Check up to 4 MPPT channels (most inverters have 1-4)
    for (let i = 1; i <= 4; i++) {
      const pvPowerW = extra[`pv${i}_power_w`] || extra[`mppt${i}_power_w`] || extra[`mppt${i}_power`];
      const pvVoltageV = extra[`pv${i}_voltage_v`] || extra[`mppt${i}_voltage_v`] || extra[`mppt${i}_voltage`];
      const pvCurrentA = extra[`pv${i}_current_a`] || extra[`mppt${i}_current_a`] || extra[`mppt${i}_current`];
      
      if (pvPowerW !== undefined && pvPowerW !== null) {
        mpptCount++;
        mpptPowers.push(pvPowerW);
        mpptVoltages.push(pvVoltageV || 380); // Default voltage if not available
        mpptCurrents.push(pvCurrentA || (pvPowerW > 0 && pvVoltageV ? (pvPowerW / pvVoltageV) : 0));
      }
    }
    
    // If we found MPPT channel data, create arrays for each channel
    if (mpptCount > 0) {
      for (let i = 0; i < mpptCount; i++) {
        const power = mpptPowers[i] / 1000; // Convert to kW
        const voltage = mpptVoltages[i];
        const current = mpptCurrents[i];
        
        // Determine status based on power output
        let status: SolarArray["status"] = "optimal";
        if (power === 0) {
          status = "offline";
        } else if (power < 0.5) {
          status = "low";
        } else if (telemetry && power < telemetry.pvPower * 0.7) {
          status = "shaded";
        }
        
        arrays.push({
          id: `array-${selectedInverterId}-${i + 1}`,
          name: `${deviceName} / Array ${i + 1}`, // Format: "Powdrive / Array 1", "Powdrive / Array 2", etc.
          power,
          voltage,
          current,
          status,
        });
      }
    } else {
      // Fallback: single array with total power
      const pvPowerW = inverterData?.pv_power_w || telemetry?.pvPower * 1000 || 0;
      const power = pvPowerW / 1000; // Convert to kW
      
      // Estimate voltage and current from power (if not available)
      const estimatedVoltage = 380; // Default voltage
      const voltage = estimatedVoltage;
      const current = power > 0 ? (power * 1000) / voltage : 0;
      
      // Determine status based on power output
      let status: SolarArray["status"] = "optimal";
      if (power === 0) {
        status = "offline";
      } else if (power < 0.5) {
        status = "low";
      } else if (telemetry && power < telemetry.pvPower * 0.7) {
        status = "shaded";
      }
      
      arrays.push({
        id: `array-${selectedInverterId}`,
        name: `${deviceName} / Array 1`, // Format: "Powdrive / Array 1" or "Senergy / Array 1"
        power,
        voltage,
        current,
        status,
      });
    }
    
    return arrays;
  }, [arrayTelemetry, inverterArray, device.id, telemetry, hierarchy]);
  
  // Use real data or fallback to zeros
  const powerFlowData = telemetry ? {
    solarPower: telemetry.pvPower,
    batteryPower: telemetry.batteryPower,
    batterySoc: telemetry.batterySoc ?? 0,
    loadPower: telemetry.loadPower,
    gridPower: telemetry.gridPower,
    isGridExporting: telemetry.gridPower < 0,
    dcVoltage: 580, // DC voltage not directly available, using placeholder
    acVoltage: 238, // AC voltage not directly available, using placeholder
    frequency: 50.02, // Frequency not directly available, using placeholder
    efficiency: telemetry.pvPower > 0 ? Math.min(99, (telemetry.loadPower / telemetry.pvPower) * 100) : 0,
    temperature: telemetry.inverterTemperature ?? 0,
  } : {
    solarPower: 0,
    batteryPower: 0,
    batterySoc: 0,
    loadPower: 0,
    gridPower: 0,
    isGridExporting: false,
    dcVoltage: 0,
    acVoltage: 0,
    frequency: 50.0,
    efficiency: 0,
    temperature: 0,
  };
  
  // Use hourly data for charts or generate fallback
  const chartData = hourlyData && hourlyData.length > 0 
    ? hourlyData.map(item => ({
        time: item.time,
        solarPower: item.solar,
        batteryPower: item.battery,
        loadPower: item.load,
        gridPower: item.grid,
        efficiency: 97.0,
        temperature: 40,
      }))
    : historicalData;

  return (
    <div className="space-y-6">
      {/* Power Flow Overview */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-card p-5"
      >
        <h3 className="text-lg font-semibold text-foreground mb-4">Power Flow</h3>
        
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <PowerFlowCard
            icon={Sun}
            label="Solar Input"
            value={powerFlowData.solarPower.toFixed(1)}
            unit="kW"
            color="bg-solar/20 text-solar"
            direction="in"
            delay={0}
          />
          <PowerFlowCard
            icon={Battery}
            label="Battery"
            value={powerFlowData.batteryPower.toFixed(1)}
            unit="kW"
            color="bg-battery/20 text-battery"
            direction={powerFlowData.batteryPower > 0 ? "in" : "out"}
            delay={0.1}
          />
          <PowerFlowCard
            icon={Home}
            label="Load"
            value={powerFlowData.loadPower.toFixed(1)}
            unit="kW"
            color="bg-consumption/20 text-consumption"
            direction="out"
            delay={0.2}
          />
          <PowerFlowCard
            icon={Zap}
            label="Grid"
            value={Math.abs(powerFlowData.gridPower).toFixed(1)}
            unit="kW"
            color="bg-grid/20 text-grid"
            direction={powerFlowData.isGridExporting ? "out" : "in"}
            delay={0.3}
          />
        </div>
      </motion.div>

      {/* Solar Array Telemetry */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.25 }}
        className="glass-card p-5"
      >
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-foreground">Solar Array Telemetry</h3>
            <p className="text-sm text-muted-foreground">Individual MPPT channel monitoring</p>
          </div>
          <div className="text-sm text-muted-foreground">
            Total: <span className="font-mono font-bold text-solar">
              {solarArrays.length > 0 
                ? solarArrays.reduce((sum, arr) => sum + arr.power, 0).toFixed(2)
                : telemetry?.pvPower.toFixed(2) || "0.00"
              } kW
            </span>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {solarArrays.length > 0 ? solarArrays.map((array, index) => {
            const statusStyle = arrayStatusStyles[array.status];
            return (
              <motion.div
                key={array.id}
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.3 + index * 0.1 }}
                className="bg-secondary/30 rounded-xl p-4 border border-border/50"
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <div className="p-1.5 rounded-lg bg-solar/20">
                      <Sun className="w-4 h-4 text-solar" />
                    </div>
                    <div>
                      <h4 className="font-medium text-sm text-foreground">
                        {array.name}
                      </h4>
                      {array.panels && (
                        <p className="text-xs text-muted-foreground">{array.panels} panels</p>
                      )}
                    </div>
                  </div>
                  <span className={cn("text-xs px-2 py-0.5 rounded-full", statusStyle.bg, statusStyle.text)}>
                    {statusStyle.label}
                  </span>
                </div>

                <div className="grid grid-cols-3 gap-3">
                  <div className="bg-background/50 rounded-lg p-2.5 text-center">
                    <div className="flex items-center justify-center gap-1 mb-1">
                      <TrendingUp className="w-3 h-3 text-solar" />
                      <span className="text-[10px] uppercase text-muted-foreground">Power</span>
                    </div>
                    <p className="text-lg font-mono font-bold text-solar">{array.power.toFixed(2)}</p>
                    <p className="text-[10px] text-muted-foreground">kW</p>
                  </div>
                  <div className="bg-background/50 rounded-lg p-2.5 text-center">
                    <div className="flex items-center justify-center gap-1 mb-1">
                      <Zap className="w-3 h-3 text-primary" />
                      <span className="text-[10px] uppercase text-muted-foreground">Voltage</span>
                    </div>
                    <p className="text-lg font-mono font-bold text-foreground">{array.voltage.toFixed(1)}</p>
                    <p className="text-[10px] text-muted-foreground">V</p>
                  </div>
                  <div className="bg-background/50 rounded-lg p-2.5 text-center">
                    <div className="flex items-center justify-center gap-1 mb-1">
                      <Activity className="w-3 h-3 text-battery" />
                      <span className="text-[10px] uppercase text-muted-foreground">Current</span>
                    </div>
                    <p className="text-lg font-mono font-bold text-foreground">{array.current.toFixed(2)}</p>
                    <p className="text-[10px] text-muted-foreground">A</p>
                  </div>
                </div>
              </motion.div>
            );
          }) : (
            // Fallback: show single array if no array telemetry
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="bg-secondary/30 rounded-xl p-4 border border-border/50"
            >
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <div className="p-1.5 rounded-lg bg-solar/20">
                    <Sun className="w-4 h-4 text-solar" />
                  </div>
                  <div>
                    <h4 className="font-medium text-sm text-foreground">Solar Array</h4>
                  </div>
                </div>
                <span className={cn(
                  "text-xs px-2 py-0.5 rounded-full",
                  telemetry?.pvPower && telemetry.pvPower > 0.5 ? "bg-success/20 text-success" : "bg-muted/50 text-muted-foreground",
                  telemetry?.pvPower === 0 ? "bg-destructive/20 text-destructive" : ""
                )}>
                  {telemetry?.pvPower && telemetry.pvPower > 0.5 ? "Optimal" : telemetry?.pvPower === 0 ? "Offline" : "Low"}
                </span>
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div className="bg-background/50 rounded-lg p-2.5 text-center">
                  <div className="flex items-center justify-center gap-1 mb-1">
                    <TrendingUp className="w-3 h-3 text-solar" />
                    <span className="text-[10px] uppercase text-muted-foreground">Power</span>
                  </div>
                  <p className="text-lg font-mono font-bold text-solar">{telemetry?.pvPower.toFixed(2) || "0.00"}</p>
                  <p className="text-[10px] text-muted-foreground">kW</p>
                </div>
                <div className="bg-background/50 rounded-lg p-2.5 text-center">
                  <div className="flex items-center justify-center gap-1 mb-1">
                    <Zap className="w-3 h-3 text-primary" />
                    <span className="text-[10px] uppercase text-muted-foreground">Voltage</span>
                  </div>
                  <p className="text-lg font-mono font-bold text-foreground">380.0</p>
                  <p className="text-[10px] text-muted-foreground">V</p>
                </div>
                <div className="bg-background/50 rounded-lg p-2.5 text-center">
                  <div className="flex items-center justify-center gap-1 mb-1">
                    <Activity className="w-3 h-3 text-battery" />
                    <span className="text-[10px] uppercase text-muted-foreground">Current</span>
                  </div>
                  <p className="text-lg font-mono font-bold text-foreground">
                    {telemetry?.pvPower ? ((telemetry.pvPower * 1000) / 380).toFixed(2) : "0.00"}
                  </p>
                  <p className="text-[10px] text-muted-foreground">A</p>
                </div>
              </div>
            </motion.div>
          )}
        </div>
      </motion.div>

      {/* Inverter Metrics */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="glass-card p-5"
      >
        <h3 className="text-lg font-semibold text-foreground mb-4">Inverter Metrics</h3>
        
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
          <div className="bg-secondary/30 rounded-lg p-3">
            <div className="flex items-center gap-2 mb-1">
              <Zap className="w-4 h-4 text-solar" />
              <span className="text-xs text-muted-foreground">DC Voltage</span>
            </div>
            <p className="text-xl font-mono font-bold text-foreground">{powerFlowData.dcVoltage}V</p>
          </div>
          <div className="bg-secondary/30 rounded-lg p-3">
            <div className="flex items-center gap-2 mb-1">
              <Activity className="w-4 h-4 text-grid" />
              <span className="text-xs text-muted-foreground">AC Voltage</span>
            </div>
            <p className="text-xl font-mono font-bold text-foreground">{powerFlowData.acVoltage}V</p>
          </div>
          <div className="bg-secondary/30 rounded-lg p-3">
            <div className="flex items-center gap-2 mb-1">
              <Activity className="w-4 h-4 text-primary" />
              <span className="text-xs text-muted-foreground">Frequency</span>
            </div>
            <p className="text-xl font-mono font-bold text-foreground">{powerFlowData.frequency}Hz</p>
          </div>
          <div className="bg-secondary/30 rounded-lg p-3">
            <div className="flex items-center gap-2 mb-1">
              <Gauge className="w-4 h-4 text-success" />
              <span className="text-xs text-muted-foreground">Efficiency</span>
            </div>
            <p className="text-xl font-mono font-bold text-success">{powerFlowData.efficiency}%</p>
          </div>
          <div className="bg-secondary/30 rounded-lg p-3">
            <div className="flex items-center gap-2 mb-1">
              <Battery className="w-4 h-4 text-battery" />
              <span className="text-xs text-muted-foreground">Battery SOC</span>
            </div>
            <p className="text-xl font-mono font-bold text-battery">{powerFlowData.batterySoc}%</p>
          </div>
          <div className="bg-secondary/30 rounded-lg p-3">
            <div className="flex items-center gap-2 mb-1">
              <Thermometer className="w-4 h-4 text-warning" />
              <span className="text-xs text-muted-foreground">Temperature</span>
            </div>
            <p className={cn(
              "text-xl font-mono font-bold",
              powerFlowData.temperature > 50 ? "text-destructive" : powerFlowData.temperature > 45 ? "text-warning" : "text-foreground"
            )}>{powerFlowData.temperature}°C</p>
          </div>
        </div>
      </motion.div>

      {/* Historical Power Chart */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="glass-card p-5"
      >
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-foreground">Power History</h3>
            <p className="text-sm text-muted-foreground">24-hour power flow trend</p>
          </div>
          <div className="flex items-center gap-4 text-xs">
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-3 rounded-full bg-solar" />
              <span className="text-muted-foreground">Solar</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-3 rounded-full bg-consumption" />
              <span className="text-muted-foreground">Load</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-3 rounded-full bg-battery" />
              <span className="text-muted-foreground">Battery</span>
            </div>
          </div>
        </div>
        
        <div className="h-[250px]">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="solarGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="hsl(var(--solar))" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="hsl(var(--solar))" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="loadGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="hsl(var(--consumption))" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="hsl(var(--consumption))" stopOpacity={0} />
                </linearGradient>
              </defs>
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
              <Area
                type="monotone"
                dataKey="solarPower"
                stroke="hsl(var(--solar))"
                fill="url(#solarGradient)"
                strokeWidth={2}
                name="Solar"
              />
              <Area
                type="monotone"
                dataKey="loadPower"
                stroke="hsl(var(--consumption))"
                fill="url(#loadGradient)"
                strokeWidth={2}
                name="Load"
              />
              <Line
                type="monotone"
                dataKey="batteryPower"
                stroke="hsl(var(--battery))"
                strokeWidth={2}
                dot={false}
                name="Battery"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </motion.div>

      {/* Efficiency & Temperature History */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="glass-card p-5"
      >
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-foreground">Efficiency & Temperature</h3>
            <p className="text-sm text-muted-foreground">24-hour performance metrics</p>
          </div>
        </div>
        
        <div className="h-[200px]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={historicalData}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.3} />
              <XAxis 
                dataKey="time" 
                stroke="hsl(var(--muted-foreground))" 
                fontSize={10}
                tickLine={false}
              />
              <YAxis 
                yAxisId="left"
                stroke="hsl(var(--muted-foreground))" 
                fontSize={10}
                tickLine={false}
                axisLine={false}
                domain={[90, 100]}
                tickFormatter={(v) => `${v}%`}
              />
              <YAxis 
                yAxisId="right"
                orientation="right"
                stroke="hsl(var(--muted-foreground))" 
                fontSize={10}
                tickLine={false}
                axisLine={false}
                domain={[20, 60]}
                tickFormatter={(v) => `${v}°C`}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "hsl(var(--card))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: "8px",
                  fontSize: "12px",
                }}
              />
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="efficiency"
                stroke="hsl(var(--success))"
                strokeWidth={2}
                dot={false}
                name="Efficiency"
              />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="temperature"
                stroke="hsl(var(--warning))"
                strokeWidth={2}
                dot={false}
                name="Temperature"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </motion.div>
    </div>
  );
};

export default InverterTelemetry;
