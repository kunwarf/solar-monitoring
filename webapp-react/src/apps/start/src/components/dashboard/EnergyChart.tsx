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

export function EnergyChart({ data, title, className }: EnergyChartProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.3 }}
      className={cn("glass-card p-6 flex flex-col", className)}
    >
      <h3 className="text-lg font-semibold text-foreground mb-6">{title}</h3>
      
      <div className="flex-1 min-h-[300px]">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
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
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(220 13% 20%)" vertical={false} />
            <XAxis
              dataKey="time"
              stroke="hsl(215 14% 55%)"
              fontSize={12}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              stroke="hsl(215 14% 55%)"
              fontSize={12}
              tickLine={false}
              axisLine={false}
              tickFormatter={(value) => `${value}kW`}
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
            />
            <Area
              type="monotone"
              dataKey="consumption"
              stroke="hsl(280 65% 60%)"
              strokeWidth={2}
              fill="url(#consumptionGradient)"
              name="Consumption"
            />
            <Area
              type="monotone"
              dataKey="battery"
              stroke="hsl(160 84% 39%)"
              strokeWidth={2}
              fill="url(#batteryGradient)"
              name="Battery"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </motion.div>
  );
}
