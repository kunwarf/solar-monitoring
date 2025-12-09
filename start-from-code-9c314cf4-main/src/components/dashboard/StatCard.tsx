import { motion } from "framer-motion";
import { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface StatCardProps {
  title: string;
  value: string;
  unit: string;
  icon: LucideIcon;
  trend?: {
    value: number;
    isPositive: boolean;
  };
  variant?: "solar" | "battery" | "consumption" | "grid" | "environment" | "financial" | "prediction" | "default";
  delay?: number;
}

const variantStyles = {
  solar: {
    iconBg: "bg-solar/20",
    iconColor: "text-solar",
    valueColor: "text-solar",
    glow: "energy-glow-solar",
  },
  battery: {
    iconBg: "bg-battery/20",
    iconColor: "text-battery",
    valueColor: "text-battery",
    glow: "energy-glow-primary",
  },
  consumption: {
    iconBg: "bg-consumption/20",
    iconColor: "text-consumption",
    valueColor: "text-consumption",
    glow: "",
  },
  grid: {
    iconBg: "bg-grid/20",
    iconColor: "text-grid",
    valueColor: "text-grid",
    glow: "energy-glow-accent",
  },
  environment: {
    iconBg: "bg-emerald-500/20",
    iconColor: "text-emerald-500",
    valueColor: "text-emerald-500",
    glow: "",
  },
  financial: {
    iconBg: "bg-amber-500/20",
    iconColor: "text-amber-500",
    valueColor: "text-amber-500",
    glow: "",
  },
  prediction: {
    iconBg: "bg-violet-500/20",
    iconColor: "text-violet-500",
    valueColor: "text-violet-500",
    glow: "",
  },
  default: {
    iconBg: "bg-primary/20",
    iconColor: "text-primary",
    valueColor: "text-foreground",
    glow: "",
  },
};

export function StatCard({
  title,
  value,
  unit,
  icon: Icon,
  trend,
  variant = "default",
  delay = 0,
}: StatCardProps) {
  const styles = variantStyles[variant];

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.4 }}
      className={cn("stat-card", styles.glow)}
    >
      <div className="flex items-start justify-between mb-4">
        <div className={cn("w-12 h-12 rounded-xl flex items-center justify-center", styles.iconBg)}>
          <Icon className={cn("w-6 h-6", styles.iconColor)} />
        </div>
        {trend && (
          <div
            className={cn(
              "text-xs font-medium px-2 py-1 rounded-full",
              trend.isPositive ? "bg-success/20 text-success" : "bg-destructive/20 text-destructive"
            )}
          >
            {trend.isPositive ? "+" : ""}{trend.value}%
          </div>
        )}
      </div>

      <div className="space-y-1">
        <p className="data-label">{title}</p>
        <div className="flex items-baseline gap-1">
          <span className={cn("data-value text-3xl", styles.valueColor)}>{value}</span>
          <span className="text-sm text-muted-foreground">{unit}</span>
        </div>
      </div>
    </motion.div>
  );
}
