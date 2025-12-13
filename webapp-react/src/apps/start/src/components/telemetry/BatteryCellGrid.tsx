import React from "react";
import { motion } from "framer-motion";
import { Thermometer, Zap, Battery, Activity } from "lucide-react";
import { cn } from "@/lib/utils";
import { useBatteryTelemetry, useHourlyEnergy, useHomeHierarchy } from "@root/api/hooks";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
} from "recharts";

interface CellData {
  id: number;
  voltage: number;
  temperature: number;
  soc: number;
  health: number;
  status: "normal" | "warning" | "critical" | "balancing";
}

// Generate mock cell data for a battery pack
const generateCellData = (packId: number, cellCount: number = 16): CellData[] => {
  return Array.from({ length: cellCount }, (_, i) => {
    const baseVoltage = 3.2 + Math.random() * 0.5;
    const baseTemp = 25 + Math.random() * 20;
    const baseSoc = 70 + Math.random() * 25;
    const health = 90 + Math.random() * 10;
    
    // Add some variation for visual interest
    const isWarning = Math.random() > 0.9;
    const isCritical = Math.random() > 0.97;
    const isBalancing = Math.random() > 0.85 && !isWarning && !isCritical;
    
    return {
      id: packId * 100 + i + 1,
      voltage: Number((isWarning ? baseVoltage - 0.3 : baseVoltage).toFixed(3)),
      temperature: Number((isCritical ? baseTemp + 15 : baseTemp).toFixed(1)),
      soc: Number(baseSoc.toFixed(1)),
      health: Number(health.toFixed(1)),
      status: isCritical ? "critical" : isWarning ? "warning" : isBalancing ? "balancing" : "normal",
    };
  });
};

interface BatteryCellGridProps {
  device?: {
    id: string;
    name: string;
  };
}

const batteryPacks = [
  { id: 1, name: "Battery Pack A", cells: generateCellData(1, 16) },
  { id: 2, name: "Battery Pack B", cells: generateCellData(2, 16) },
];

// Historical battery data
const generateHistoricalData = () => {
  return Array.from({ length: 24 }, (_, i) => {
    const hour = i;
    const sunIntensity = Math.max(0, Math.sin((hour - 6) * Math.PI / 12));
    const baseSOC = 50;
    const charging = sunIntensity > 0.3;
    
    return {
      time: `${hour.toString().padStart(2, "0")}:00`,
      soc: Math.min(95, Math.max(15, baseSOC + (charging ? sunIntensity * 40 : -hour * 2) + Math.random() * 5)),
      voltage: 51.2 + Math.random() * 2,
      current: charging ? 20 + Math.random() * 10 : -(10 + Math.random() * 5),
      temperature: 25 + sunIntensity * 10 + Math.random() * 3,
      power: charging ? 2 + Math.random() : -(1 + Math.random()),
    };
  });
};

const historicalData = generateHistoricalData();

const getStatusColor = (status: CellData["status"]) => {
  switch (status) {
    case "critical":
      return "text-destructive";
    case "warning":
      return "text-warning";
    case "balancing":
      return "text-blue-400";
    default:
      return "text-battery";
  }
};

const getStatusBorderColor = (status: CellData["status"]) => {
  switch (status) {
    case "critical":
      return "#ef4444";
    case "warning":
      return "#f59e0b";
    case "balancing":
      return "#60a5fa";
    default:
      return "#22c55e";
  }
};

const getFillColor = (status: CellData["status"]) => {
  switch (status) {
    case "critical":
      return "#ef4444";
    case "warning":
      return "#f59e0b";
    case "balancing":
      return "#60a5fa";
    default:
      return "#22c55e";
  }
};

const getVoltageColor = (voltage: number) => {
  if (voltage < 3.0) return "text-destructive";
  if (voltage < 3.2) return "text-warning";
  return "text-battery";
};

const getTempColor = (temp: number) => {
  if (temp > 45) return "text-destructive";
  if (temp > 38) return "text-warning";
  return "text-muted-foreground";
};

const CellVisual = ({ cell, index }: { cell: CellData; index: number }) => {
  const fillPercent = cell.soc;
  const borderColor = getStatusBorderColor(cell.status);
  const fillColor = getFillColor(cell.status);
  
  return (
    <TooltipProvider>
      <Tooltip delayDuration={100}>
        <TooltipTrigger asChild>
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: index * 0.015, duration: 0.2 }}
            className={cn(
              "relative cursor-pointer transition-all hover:scale-110 hover:z-10",
              cell.status === "balancing" && "animate-pulse"
            )}
          >
            <svg
              viewBox="0 0 24 40"
              className="w-full h-10"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              {/* Battery terminal (top cap) */}
              <rect
                x="8"
                y="0"
                width="8"
                height="3"
                rx="1"
                fill={borderColor}
                opacity="0.8"
              />
              
              {/* Battery body outline */}
              <rect
                x="2"
                y="4"
                width="20"
                height="34"
                rx="3"
                stroke={borderColor}
                strokeWidth="1.5"
                fill="transparent"
              />
              
              {/* Battery fill level */}
              <motion.rect
                x="4"
                width="16"
                rx="2"
                fill={fillColor}
                opacity="0.7"
                initial={{ y: 36, height: 0 }}
                animate={{ 
                  y: 6 + (30 * (1 - fillPercent / 100)), 
                  height: 30 * (fillPercent / 100) 
                }}
                transition={{ delay: index * 0.015 + 0.1, duration: 0.4, ease: "easeOut" }}
              />
              
              {/* Cell number */}
              <text
                x="12"
                y="24"
                textAnchor="middle"
                dominantBaseline="middle"
                fill="currentColor"
                className="text-[8px] font-mono font-bold fill-foreground"
                style={{ fontSize: '8px' }}
              >
                {index + 1}
              </text>
              
              {/* Status indicator dot */}
              {cell.status !== "normal" && (
                <circle
                  cx="18"
                  cy="8"
                  r="2.5"
                  fill={borderColor}
                  className={cell.status === "critical" ? "animate-ping" : ""}
                />
              )}
            </svg>
          </motion.div>
        </TooltipTrigger>
        <TooltipContent side="top" className="bg-card border-border p-3">
          <div className="space-y-2">
            <p className="font-semibold text-foreground">Cell #{index + 1}</p>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
              <div className="flex items-center gap-1">
                <Zap className={cn("w-3 h-3", getVoltageColor(cell.voltage))} />
                <span className="text-muted-foreground">Voltage:</span>
              </div>
              <span className={cn("font-mono", getVoltageColor(cell.voltage))}>
                {cell.voltage}V
              </span>
              
              <div className="flex items-center gap-1">
                <Thermometer className={cn("w-3 h-3", getTempColor(cell.temperature))} />
                <span className="text-muted-foreground">Temp:</span>
              </div>
              <span className={cn("font-mono", getTempColor(cell.temperature))}>
                {cell.temperature}°C
              </span>
              
              <div className="flex items-center gap-1">
                <Battery className="w-3 h-3 text-battery" />
                <span className="text-muted-foreground">SOC:</span>
              </div>
              <span className="font-mono text-battery">{cell.soc}%</span>
              
              <span className="text-muted-foreground">Health:</span>
              <span className="font-mono text-foreground">{cell.health}%</span>
              
              <span className="text-muted-foreground">Status:</span>
              <span className={cn(
                "capitalize font-medium",
                cell.status === "critical" && "text-destructive",
                cell.status === "warning" && "text-warning",
                cell.status === "balancing" && "text-blue-400",
                cell.status === "normal" && "text-success"
              )}>
                {cell.status}
              </span>
            </div>
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
};

const PackStats = ({ cells }: { cells: CellData[] }) => {
  const avgVoltage = cells.reduce((sum, c) => sum + c.voltage, 0) / cells.length;
  const avgTemp = cells.reduce((sum, c) => sum + c.temperature, 0) / cells.length;
  const avgSoc = cells.reduce((sum, c) => sum + c.soc, 0) / cells.length;
  const minVoltage = Math.min(...cells.map(c => c.voltage));
  const maxVoltage = Math.max(...cells.map(c => c.voltage));
  const deltaVoltage = maxVoltage - minVoltage;
  
  return (
    <div className="grid grid-cols-4 gap-2 mt-3">
      <div className="bg-secondary/30 rounded-md px-2 py-1.5">
        <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Avg Voltage</p>
        <p className="text-sm font-mono font-bold text-foreground">{avgVoltage.toFixed(3)}V</p>
      </div>
      <div className="bg-secondary/30 rounded-md px-2 py-1.5">
        <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Delta V</p>
        <p className={cn(
          "text-sm font-mono font-bold",
          deltaVoltage > 0.1 ? "text-warning" : "text-success"
        )}>
          {(deltaVoltage * 1000).toFixed(0)}mV
        </p>
      </div>
      <div className="bg-secondary/30 rounded-md px-2 py-1.5">
        <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Avg Temp</p>
        <p className={cn(
          "text-sm font-mono font-bold",
          avgTemp > 40 ? "text-warning" : "text-foreground"
        )}>
          {avgTemp.toFixed(1)}°C
        </p>
      </div>
      <div className="bg-secondary/30 rounded-md px-2 py-1.5">
        <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Pack SOC</p>
        <p className="text-sm font-mono font-bold text-battery">{avgSoc.toFixed(1)}%</p>
      </div>
    </div>
  );
};

const BatteryCellGrid = ({ device }: BatteryCellGridProps) => {
  // Get hierarchy to find battery array info
  const { data: hierarchy } = useHomeHierarchy();
  
  // Device now uses actual bank ID (e.g., "jkbms_bank_ble", "battery1")
  // Check if device has batteryBankId context field (from DataProvider)
  const batteryBankId = (device as any)?.batteryBankId || device?.id;
  
  // Find battery array from hierarchy by checking all systems
  let batteryArray: any = null;
  if (hierarchy?.systems) {
    for (const system of hierarchy.systems) {
      for (const ba of system.batteryArrays || []) {
        // Check if device ID matches any battery in this array
        const matchingBattery = ba.batteries?.find((b: any) => 
          b.id === batteryBankId || 
          b.batteryBankId === batteryBankId ||
          device?.id === b.id
        );
        if (matchingBattery) {
          batteryArray = ba;
          break;
        }
      }
      if (batteryArray) break;
    }
  }
  
  // Fetch battery telemetry using the actual bank ID
  // This is now a direct lookup instead of fetching all and matching
  const batteryTelemetry = useBatteryTelemetry(batteryBankId, {
    refetchInterval: 5000,
  });
  
  // Get battery data - should be direct match now
  // When bankId is provided, getBatteryNow returns single BatteryData
  // When bankId is not provided, it returns BatteryData[]
  const battery = Array.isArray(batteryTelemetry.data) 
    ? batteryTelemetry.data.find(b => b.id === batteryBankId) || batteryTelemetry.data[0]
    : batteryTelemetry.data;
  
  // Fetch hourly energy for charts
  const { data: hourlyData } = useHourlyEnergy({ inverterId: undefined });
  
  // Calculate aggregated pack summary from all devices
  const packSummary = React.useMemo(() => {
    if (!battery) {
      return {
        totalVoltage: 0,
        totalCurrent: 0,
        totalPower: 0,
        soc: 0,
        health: 0,
        cycles: 0,
        temperature: 0,
        status: "charging" as const,
      };
    }
    
    // Aggregate from all devices if available
    if (battery.devices && battery.devices.length > 0) {
      const totalVoltage = battery.devices.reduce((sum: number, dev: any) => sum + (dev.voltage || 0), 0);
      const totalCurrent = battery.devices.reduce((sum: number, dev: any) => sum + (dev.current || 0), 0);
      const avgSoc = battery.devices.reduce((sum: number, dev: any) => sum + (dev.soc || 0), 0) / battery.devices.length;
      const avgTemp = battery.devices.reduce((sum: number, dev: any) => sum + (dev.temperature || 0), 0) / battery.devices.length;
      const totalCycles = battery.devices.reduce((sum: number, dev: any) => sum + (dev.cycles || 0), 0);
      const avgSoh = battery.devices.reduce((sum: number, dev: any) => sum + (dev.soh || 0), 0) / battery.devices.length;
      
      return {
        totalVoltage: totalVoltage || battery.voltage || 0,
        totalCurrent: totalCurrent || battery.current || 0,
        totalPower: (totalCurrent || battery.current || 0) * (totalVoltage || battery.voltage || 0) / 1000,
        soc: avgSoc || battery.soc || 0,
        health: avgSoh || 94,
        cycles: totalCycles || 0,
        temperature: avgTemp || battery.temperature || 0,
        status: (totalCurrent || battery.current || 0) >= 0 ? "charging" as const : "discharging" as const,
      };
    }
    
    // Fallback to battery-level data
    return {
      totalVoltage: battery.voltage ?? 0,
      totalCurrent: battery.current ?? 0,
      totalPower: (battery.current ?? 0) * (battery.voltage ?? 0) / 1000,
      soc: battery.soc ?? 0,
      health: 94,
      cycles: 0,
      temperature: battery.temperature ?? 0,
      status: (battery.current ?? 0) >= 0 ? "charging" as const : "discharging" as const,
    };
  }, [battery]);
  
  // Transform cells data from battery devices or cells array
  const transformedPacks = React.useMemo(() => {
    if (!battery) return batteryPacks;
    
    const packs: Array<{ id: number; name: string; cells: CellData[] }> = [];
    
    // Check for cells_data in raw (from backend API)
    const rawData = battery.raw as any;
    const cellsData = rawData?.cells_data;
    
    if (cellsData && Array.isArray(cellsData) && cellsData.length > 0) {
      // Use cells_data structure from backend
      cellsData.forEach((batteryData: any, batteryIdx: number) => {
        const cells = batteryData.cells || [];
        if (cells.length > 0) {
          const transformedCells: CellData[] = cells.map((cell: any, idx: number) => {
            const cellVoltage = cell.voltage ?? 0;
            const cellTemp = cell.temperature ?? batteryData.temperature ?? battery.temperature ?? 0;
            const cellSoc = cell.soc ?? batteryData.soc ?? battery.soc ?? 0;
            
            // Determine cell status based on voltage
            let status: CellData["status"] = "normal";
            if (cellVoltage < 3.0) {
              status = "critical";
            } else if (cellVoltage < 3.2) {
              status = "warning";
            } else if (Math.random() > 0.85) {
              status = "balancing";
            }
            
            return {
              id: batteryIdx * 1000 + idx + 1,
              voltage: cellVoltage,
              temperature: cellTemp,
              soc: cellSoc,
              health: batteryData.soh ?? 90 + Math.random() * 10,
              status,
            };
          });
          
          if (transformedCells.length > 0) {
            // Get battery bank name from device name map (preferred) or fallback to array name
            const batteryBankId = batteryArray?.batteryBankIds?.[batteryIdx] || batteryArray?.batteryBankIds?.[0];
            const batteryBankName = (hierarchy as any)?._deviceNames?.batteryBanks?.get(batteryBankId || '') ||
                                   (batteryArray?.name ? batteryArray.name.replace(' Array', ' Battery Bank') : null) ||
                                   "Battery Bank";
            const batteryName = batteryBankName ? 
              `${batteryBankName} #${batteryIdx + 1}` : 
              `Battery #${batteryIdx + 1}`;
            
            packs.push({
              id: batteryData.power || batteryIdx + 1, // Use power field as battery index
              name: batteryName,
              cells: transformedCells,
            });
          }
        }
      });
    } else if (battery.cells && battery.cells.length > 0) {
      // Use cells array, group by batteryIndex
      const cellsByBattery = new Map<number, typeof battery.cells>();
      battery.cells.forEach(cell => {
        const batteryIdx = cell.batteryIndex;
        if (!cellsByBattery.has(batteryIdx)) {
          cellsByBattery.set(batteryIdx, []);
        }
        cellsByBattery.get(batteryIdx)!.push(cell);
      });
      
      cellsByBattery.forEach((cells, batteryIdx) => {
        // Find corresponding device for this battery index
        const device = battery.devices?.find((d: any) => d.index === batteryIdx || d.power === batteryIdx);
        
        const transformedCells: CellData[] = cells.map((cell, idx) => {
          const cellVoltage = cell.voltage ?? 0;
          const cellTemp = cell.temperature ?? device?.temperature ?? battery.temperature ?? 0;
          const cellSoc = cell.soc ?? device?.soc ?? battery.soc ?? 0;
          
          let status: CellData["status"] = "normal";
          if (cellVoltage < 3.0) {
            status = "critical";
          } else if (cellVoltage < 3.2) {
            status = "warning";
          } else if (Math.random() > 0.85) {
            status = "balancing";
          }
          
          return {
            id: batteryIdx * 1000 + idx + 1,
            voltage: cellVoltage,
            temperature: cellTemp,
            soc: cellSoc,
            health: device?.soh ?? 90 + Math.random() * 10,
            status,
          };
        });
        
        if (transformedCells.length > 0) {
          // Get battery bank name from device name map (preferred) or fallback to array name
          const device = battery.devices?.find((d: any) => d.index === batteryIdx || d.power === batteryIdx);
          const batteryBankId = batteryArray?.batteryBankIds?.[batteryIdx] || batteryArray?.batteryBankIds?.[0];
          const batteryBankName = (hierarchy as any)?._deviceNames?.batteryBanks?.get(batteryBankId || '') ||
                                 (batteryArray?.name ? batteryArray.name.replace(' Array', ' Battery Bank') : null) ||
                                 (device ? null : null) ||
                                 "Battery Bank";
          const batteryName = batteryBankName ? 
            `${batteryBankName} #${batteryIdx + 1}` : 
            `Battery #${batteryIdx + 1}`;
          
          packs.push({
            id: batteryIdx + 1,
            name: batteryName,
            cells: transformedCells,
          });
        }
      });
    } else if (battery.devices && battery.devices.length > 0) {
      // Use devices array - treat each device as a pack
      // Calculate cells per battery from battery data
      const cellsPerBattery = battery.cellsPerBattery || 16;
      
      battery.devices.forEach((dev, packIdx) => {
        // Get cells for this device from cells array if available
        const deviceCells = battery.cells?.filter((c: any) => 
          c.batteryIndex === dev.index || c.batteryIndex === packIdx
        ) || [];
        
        let cells: CellData[] = [];
        if (deviceCells.length > 0) {
          // Use actual cell data
          cells = deviceCells.map((cell: any, idx: number) => ({
            id: packIdx * 1000 + idx + 1,
            voltage: cell.voltage ?? 0,
            temperature: cell.temperature ?? dev.temperature ?? battery.temperature ?? 0,
            soc: cell.soc ?? dev.soc ?? battery.soc ?? 0,
            health: dev.soh ?? 90 + Math.random() * 10,
            status: (cell.voltage && cell.voltage < 3.0) ? "critical" as const
              : (cell.voltage && cell.voltage < 3.2) ? "warning" as const
              : Math.random() > 0.85 ? "balancing" as const
              : "normal" as const,
          }));
        } else {
          // Fallback: divide voltage across cells
          const cellVoltage = (dev.voltage ?? battery.voltage ?? 0) / cellsPerBattery;
          cells = Array.from({ length: cellsPerBattery }, (_, idx) => ({
            id: packIdx * 1000 + idx + 1,
            voltage: cellVoltage,
            temperature: dev.temperature ?? battery.temperature ?? 0,
            soc: dev.soc ?? battery.soc ?? 0,
            health: dev.soh ?? 90 + Math.random() * 10,
            status: "normal" as const,
          }));
        }
        
        // Get battery bank name from device name map (preferred) or fallback to array name
        const batteryBankId = batteryArray?.batteryBankIds?.[packIdx] || batteryArray?.batteryBankIds?.[0];
        const batteryBankName = (hierarchy as any)?._deviceNames?.batteryBanks?.get(batteryBankId || '') ||
                               (batteryArray?.name ? batteryArray.name.replace(' Array', ' Battery Bank') : null) ||
                               "Battery Bank";
        const batteryName = batteryBankName ? 
          `${batteryBankName} #${packIdx + 1}` : 
          `Battery #${packIdx + 1}`;
        
        packs.push({
          id: dev.index || packIdx + 1,
          name: batteryName,
          cells,
        });
      });
    }
    
    return packs.length > 0 ? packs : batteryPacks;
  }, [battery]);
  
  // Use hourly data for charts
  const chartData = hourlyData && hourlyData.length > 0
    ? hourlyData.map(item => ({
        time: item.time,
        soc: packSummary.soc,
        voltage: packSummary.totalVoltage,
        current: packSummary.totalCurrent,
        temperature: packSummary.temperature,
        power: packSummary.totalPower,
      }))
    : historicalData;

  return (
    <div className="space-y-6">
      {/* Battery Pack Summary */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-card p-5"
      >
        <h3 className="text-lg font-semibold text-foreground mb-4">Battery Pack Status</h3>
        
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-4">
          <div className="bg-secondary/30 rounded-lg p-3">
            <div className="flex items-center gap-1 mb-1">
              <Zap className="w-3 h-3 text-battery" />
              <span className="text-xs text-muted-foreground">Voltage</span>
            </div>
            <p className="text-lg font-mono font-bold text-foreground">{packSummary.totalVoltage}V</p>
          </div>
          <div className="bg-secondary/30 rounded-lg p-3">
            <div className="flex items-center gap-1 mb-1">
              <Activity className="w-3 h-3 text-success" />
              <span className="text-xs text-muted-foreground">Current</span>
            </div>
            <p className="text-lg font-mono font-bold text-success">+{packSummary.totalCurrent}A</p>
          </div>
          <div className="bg-secondary/30 rounded-lg p-3">
            <div className="flex items-center gap-1 mb-1">
              <Zap className="w-3 h-3 text-solar" />
              <span className="text-xs text-muted-foreground">Power</span>
            </div>
            <p className="text-lg font-mono font-bold text-solar">{packSummary.totalPower}kW</p>
          </div>
          <div className="bg-secondary/30 rounded-lg p-3">
            <div className="flex items-center gap-1 mb-1">
              <Battery className="w-3 h-3 text-battery" />
              <span className="text-xs text-muted-foreground">SOC</span>
            </div>
            <p className="text-lg font-mono font-bold text-battery">{packSummary.soc}%</p>
          </div>
          <div className="bg-secondary/30 rounded-lg p-3">
            <div className="flex items-center gap-1 mb-1">
              <Activity className="w-3 h-3 text-primary" />
              <span className="text-xs text-muted-foreground">Health</span>
            </div>
            <p className="text-lg font-mono font-bold text-foreground">{packSummary.health}%</p>
          </div>
          <div className="bg-secondary/30 rounded-lg p-3">
            <div className="flex items-center gap-1 mb-1">
              <Activity className="w-3 h-3 text-muted-foreground" />
              <span className="text-xs text-muted-foreground">Cycles</span>
            </div>
            <p className="text-lg font-mono font-bold text-foreground">{packSummary.cycles}</p>
          </div>
          <div className="bg-secondary/30 rounded-lg p-3">
            <div className="flex items-center gap-1 mb-1">
              <Thermometer className="w-3 h-3 text-warning" />
              <span className="text-xs text-muted-foreground">Temp</span>
            </div>
            <p className="text-lg font-mono font-bold text-foreground">{packSummary.temperature}°C</p>
          </div>
          <div className="bg-secondary/30 rounded-lg p-3">
            <div className="flex items-center gap-1 mb-1">
              <Battery className="w-3 h-3 text-success" />
              <span className="text-xs text-muted-foreground">Status</span>
            </div>
            <p className="text-lg font-mono font-bold text-success capitalize">{packSummary.status}</p>
          </div>
        </div>
      </motion.div>

      {/* Cell Grid */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="glass-card p-5"
      >
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-foreground">Cell Monitor</h3>
            <p className="text-sm text-muted-foreground">Individual cell voltage, temperature & SOC</p>
          </div>
          <div className="flex items-center gap-3 text-xs">
            <div className="flex items-center gap-1">
              <svg viewBox="0 0 24 40" className="w-3 h-5" fill="none">
                <rect x="8" y="0" width="8" height="3" rx="1" fill="#22c55e" opacity="0.8" />
                <rect x="2" y="4" width="20" height="34" rx="3" stroke="#22c55e" strokeWidth="1.5" fill="transparent" />
                <rect x="4" y="16" width="16" height="20" rx="2" fill="#22c55e" opacity="0.7" />
              </svg>
              <span className="text-muted-foreground">Normal</span>
            </div>
            <div className="flex items-center gap-1">
              <svg viewBox="0 0 24 40" className="w-3 h-5" fill="none">
                <rect x="8" y="0" width="8" height="3" rx="1" fill="#60a5fa" opacity="0.8" />
                <rect x="2" y="4" width="20" height="34" rx="3" stroke="#60a5fa" strokeWidth="1.5" fill="transparent" />
                <rect x="4" y="16" width="16" height="20" rx="2" fill="#60a5fa" opacity="0.7" />
              </svg>
              <span className="text-muted-foreground">Balancing</span>
            </div>
            <div className="flex items-center gap-1">
              <svg viewBox="0 0 24 40" className="w-3 h-5" fill="none">
                <rect x="8" y="0" width="8" height="3" rx="1" fill="#f59e0b" opacity="0.8" />
                <rect x="2" y="4" width="20" height="34" rx="3" stroke="#f59e0b" strokeWidth="1.5" fill="transparent" />
                <rect x="4" y="26" width="16" height="10" rx="2" fill="#f59e0b" opacity="0.7" />
              </svg>
              <span className="text-muted-foreground">Warning</span>
            </div>
            <div className="flex items-center gap-1">
              <svg viewBox="0 0 24 40" className="w-3 h-5" fill="none">
                <rect x="8" y="0" width="8" height="3" rx="1" fill="#ef4444" opacity="0.8" />
                <rect x="2" y="4" width="20" height="34" rx="3" stroke="#ef4444" strokeWidth="1.5" fill="transparent" />
                <rect x="4" y="31" width="16" height="5" rx="2" fill="#ef4444" opacity="0.7" />
              </svg>
              <span className="text-muted-foreground">Critical</span>
            </div>
          </div>
        </div>
        
        <div className="space-y-4">
          {transformedPacks.map((pack) => (
            <div key={pack.id} className="border border-border/50 rounded-lg p-3 bg-secondary/10">
              <div className="flex items-center gap-2 mb-2">
                <Battery className="w-4 h-4 text-battery" />
                <h4 className="font-medium text-sm text-foreground">{pack.name}</h4>
                <span className="text-xs text-muted-foreground">({pack.cells.length} cells)</span>
              </div>
              
              {/* Cell Grid - more columns for compact layout */}
              <div className="grid grid-cols-8 sm:grid-cols-16 gap-1">
                {pack.cells.map((cell, index) => (
                  <CellVisual key={cell.id} cell={cell} index={index} />
                ))}
              </div>
              
              {/* Pack Statistics */}
              <PackStats cells={pack.cells} />
            </div>
          ))}
        </div>
      </motion.div>

      {/* Historical Charts */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="glass-card p-5"
      >
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-foreground">SOC & Power History</h3>
            <p className="text-sm text-muted-foreground">24-hour battery performance</p>
          </div>
          <div className="flex items-center gap-4 text-xs">
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-3 rounded-full bg-battery" />
              <span className="text-muted-foreground">SOC</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-3 rounded-full bg-solar" />
              <span className="text-muted-foreground">Power</span>
            </div>
          </div>
        </div>
        
        <div className="h-[200px]">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="socGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="hsl(var(--battery))" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="hsl(var(--battery))" stopOpacity={0} />
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
                yAxisId="left"
                stroke="hsl(var(--muted-foreground))" 
                fontSize={10}
                tickLine={false}
                axisLine={false}
                domain={[0, 100]}
                tickFormatter={(v) => `${v}%`}
              />
              <YAxis 
                yAxisId="right"
                orientation="right"
                stroke="hsl(var(--muted-foreground))" 
                fontSize={10}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v) => `${v}kW`}
              />
              <RechartsTooltip
                contentStyle={{
                  backgroundColor: "hsl(var(--card))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: "8px",
                  fontSize: "12px",
                }}
              />
              <Area
                yAxisId="left"
                type="monotone"
                dataKey="soc"
                stroke="hsl(var(--battery))"
                fill="url(#socGradient)"
                strokeWidth={2}
                name="SOC"
              />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="power"
                stroke="hsl(var(--solar))"
                strokeWidth={2}
                dot={false}
                name="Power"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </motion.div>

      {/* Temperature History */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="glass-card p-5"
      >
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-foreground">Temperature History</h3>
            <p className="text-sm text-muted-foreground">24-hour thermal performance</p>
          </div>
        </div>
        
        <div className="h-[150px]">
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
                stroke="hsl(var(--muted-foreground))" 
                fontSize={10}
                tickLine={false}
                axisLine={false}
                domain={[20, 45]}
                tickFormatter={(v) => `${v}°C`}
              />
              <RechartsTooltip
                contentStyle={{
                  backgroundColor: "hsl(var(--card))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: "8px",
                  fontSize: "12px",
                }}
              />
              <Line
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

export default BatteryCellGrid;
