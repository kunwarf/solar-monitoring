import React, { memo } from "react";
import { motion } from "framer-motion";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { cn } from "@/lib/utils";

interface DataPoint {
  time: string;
  solar: number;
  consumption: number;
  battery: number;
  grid: number;
}

interface EnergyChartProps {
  data: DataPoint[];
  title: string;
  className?: string;
}

function EnergyChartComponent({ data, title, className }: EnergyChartProps) {
  // Debug logging
  console.log('[EnergyChart] Received data:', {
    hasData: !!data,
    isArray: Array.isArray(data),
    length: data?.length,
    sample: data?.[0],
  });

  // Ensure we have data - if empty, use 24 hours of zeros
  const chartData = data && data.length > 0 
    ? data 
    : Array.from({ length: 24 }, (_, i) => ({
        time: `${i.toString().padStart(2, '0')}:00`,
        solar: 0,
        consumption: 0,
        battery: 0,
        grid: 0,
      }));

  // Check if we have any meaningful data (non-zero values)
  const hasData = chartData.some(item => 
    item.solar > 0 || item.consumption > 0 || Math.abs(item.battery) > 0.01 || Math.abs(item.grid) > 0.01
  );

  console.log('[EnergyChart] Chart data to render:', {
    count: chartData.length,
    hasData,
    sample: chartData[0],
    last: chartData[chartData.length - 1],
    maxValues: {
      solar: Math.max(...chartData.map(d => d.solar)),
      consumption: Math.max(...chartData.map(d => d.consumption)),
      battery: Math.max(...chartData.map(d => Math.abs(d.battery))),
      grid: Math.max(...chartData.map(d => Math.abs(d.grid))),
    },
  });

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.3 }}
      className={cn("glass-card p-6 flex flex-col", className)}
    >
      <h3 className="text-lg font-semibold text-foreground mb-6">{title}</h3>
      
      {!hasData && (
        <div className="flex items-center justify-center h-[300px] text-muted-foreground">
          <div className="text-center">
            <p className="text-sm">No energy data available for today</p>
            <p className="text-xs mt-2">Data will appear as it becomes available</p>
          </div>
        </div>
      )}
      
      <div className={cn("flex-1 w-full", hasData ? "min-h-[300px]" : "hidden")}>
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart 
            data={chartData} 
            margin={{ top: 10, right: 10, left: 10, bottom: 0 }}
          >
            <defs>
              <linearGradient id="solarGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="hsl(45 93% 47%)" stopOpacity={0.3} />
                <stop offset="95%" stopColor="hsl(45 93% 47%)" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="consumptionGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="hsl(280 65% 60%)" stopOpacity={0.3} />
                <stop offset="95%" stopColor="hsl(280 65% 60%)" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="batteryGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="hsl(160 84% 39%)" stopOpacity={0.3} />
                <stop offset="95%" stopColor="hsl(160 84% 39%)" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="gridGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="hsl(217 91% 60%)" stopOpacity={0.3} />
                <stop offset="95%" stopColor="hsl(217 91% 60%)" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(220 13% 20%)" vertical={false} />
            <XAxis
              dataKey="time"
              stroke="hsl(215 14% 55%)"
              fontSize={12}
              tickLine={false}
              axisLine={false}
              interval="preserveStartEnd"
            />
            <YAxis
              stroke="hsl(215 14% 55%)"
              fontSize={12}
              tickLine={false}
              axisLine={false}
              tickFormatter={(value) => `${value}kW`}
              domain={['auto', 'auto']}
              allowDecimals={true}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "hsl(220 18% 10%)",
                border: "1px solid hsl(220 13% 20%)",
                borderRadius: "8px",
                fontSize: "12px",
              }}
              labelStyle={{ color: "hsl(210 20% 92%)" }}
            />
            <Legend
              verticalAlign="top"
              height={36}
              iconType="circle"
              wrapperStyle={{ fontSize: "12px" }}
            />
            <Area
              type="monotone"
              dataKey="solar"
              stroke="hsl(45 93% 47%)"
              strokeWidth={2}
              fill="url(#solarGradient)"
              name="Solar"
              isAnimationActive={false}
              connectNulls={false}
            />
            <Area
              type="monotone"
              dataKey="consumption"
              stroke="hsl(280 65% 60%)"
              strokeWidth={2}
              fill="url(#consumptionGradient)"
              name="Consumption"
              isAnimationActive={false}
              connectNulls={false}
            />
            <Area
              type="monotone"
              dataKey="battery"
              stroke="hsl(160 84% 39%)"
              strokeWidth={2}
              fill="url(#batteryGradient)"
              name="Battery"
              isAnimationActive={false}
              connectNulls={false}
            />
            <Area
              type="monotone"
              dataKey="grid"
              stroke="hsl(217 91% 60%)"
              strokeWidth={2}
              fill="url(#gridGradient)"
              name="Grid"
              isAnimationActive={false}
              connectNulls={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </motion.div>
  );
}

export const EnergyChart = memo(EnergyChartComponent, (prevProps, nextProps) => {
  // Deep comparison for data array
  if (prevProps.data.length !== nextProps.data.length) return false;
  if (prevProps.title !== nextProps.title) return false;
  if (prevProps.className !== nextProps.className) return false;
  
  // Compare data points (only check first, last, and length for performance)
  if (prevProps.data.length > 0 && nextProps.data.length > 0) {
    const prevFirst = prevProps.data[0];
    const nextFirst = nextProps.data[0];
    const prevLast = prevProps.data[prevProps.data.length - 1];
    const nextLast = nextProps.data[nextProps.data.length - 1];
    
    if (
      prevFirst.time !== nextFirst.time ||
      prevFirst.solar !== nextFirst.solar ||
      prevFirst.consumption !== nextFirst.consumption ||
      prevLast.time !== nextLast.time ||
      prevLast.solar !== nextLast.solar ||
      prevLast.consumption !== nextLast.consumption
    ) {
      return false;
    }
  }
  
  return true;
});
