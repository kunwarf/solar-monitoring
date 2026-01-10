import { useState } from "react";
import { AppHeader } from "@/components/layout/AppHeader";
import { StatCard } from "@/components/dashboard/StatCard";
import { EnergyFlowDiagram } from "@/components/dashboard/EnergyFlowDiagram";
import { EnergyChart } from "@/components/dashboard/EnergyChart";
import { BillingSummary } from "@/components/dashboard/BillingSummary";
import { VisualSystemDiagram } from "@/components/dashboard/VisualSystemDiagram";
import { Sun, Home, TrendingUp, Leaf, DollarSign, Receipt, Target, Gauge, ChevronDown, ChevronUp } from "lucide-react";
import { useEnergyStatsData, useChartData } from "@/data/mockDataHooks";
import { useBillingConfig } from "@/hooks/use-billing-config";
import { Button } from "@/components/ui/button";
import { motion, AnimatePresence } from "framer-motion";

const Index = () => {
  // Get data from API (same structure as mockData)
  const energyStats = useEnergyStatsData();
  const chartData = useChartData();
  const { getCurrencySymbol } = useBillingConfig();
  const [showAllStats, setShowAllStats] = useState(false);

  const priorityStats = [
    {
      title: "Monthly Bill Estimate",
      value: Math.round(energyStats.monthlyBillAmount).toString(),
      unit: getCurrencySymbol(),
      icon: Receipt,
      variant: "financial" as const,
      delay: 0,
    },
    {
      title: "Today's Savings",
      value: Math.round(energyStats.moneySaved).toString(),
      unit: getCurrencySymbol(),
      icon: DollarSign,
      variant: "financial" as const,
      trend: { value: 8, isPositive: true },
      delay: 0.1,
    },
    {
      title: "CO₂ Saved Today",
      value: Math.round(energyStats.co2Saved).toString(),
      unit: "kg",
      icon: Leaf,
      variant: "environment" as const,
      trend: { value: 15, isPositive: true },
      delay: 0.2,
    },
    {
      title: "Today's Production",
      value: Math.round(energyStats.dailyProduction).toString(),
      unit: "kWh",
      icon: TrendingUp,
      variant: "solar" as const,
      delay: 0.3,
    },
  ];

  const additionalStats = [
    {
      title: "Self-Consumption",
      value: Math.round(energyStats.selfConsumption).toString(),
      unit: "%",
      icon: Home,
      variant: "consumption" as const,
      delay: 0.4,
    },
    {
      title: "Predicted vs Actual",
      value: `${Math.round(energyStats.dailyProduction)}/${Math.round(energyStats.dailyPrediction)}`,
      unit: "kWh",
      icon: Target,
      variant: "prediction" as const,
      trend: { value: Math.round((energyStats.dailyProduction / energyStats.dailyPrediction) * 100 - 100), isPositive: energyStats.dailyProduction >= energyStats.dailyPrediction },
      delay: 0.5,
    },
    {
      title: "Avg kWh/kWp",
      value: Math.round(energyStats.avgKwPerKwp).toString(),
      unit: "kWh/kWp",
      icon: Gauge,
      variant: "default" as const,
      delay: 0.6,
    },
  ];

  return (
    <>
      <AppHeader 
        title="Dashboard" 
        subtitle="Real-time energy monitoring and analytics"
      />
      
      <div className="p-3 sm:p-6 space-y-4 sm:space-y-6">
        {/* Dashboard Stats - Desktop: show all in grid */}
        <div className="hidden sm:grid sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-7 gap-4">
          {[...priorityStats, ...additionalStats].map((stat) => (
            <StatCard key={stat.title} {...stat} />
          ))}
        </div>

        {/* Dashboard Stats - Mobile: Priority cards + See More */}
        <div className="sm:hidden space-y-4">
          {/* Priority Stats Grid */}
          <div className="grid grid-cols-2 gap-3">
            {priorityStats.map((stat) => (
              <StatCard key={stat.title} {...stat} />
            ))}
          </div>

          {/* Expandable Additional Stats */}
          <AnimatePresence>
            {showAllStats && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.3 }}
                className="grid grid-cols-2 gap-3 overflow-hidden"
              >
                {additionalStats.map((stat) => (
                  <StatCard key={stat.title} {...stat} />
                ))}
              </motion.div>
            )}
          </AnimatePresence>

          {/* Toggle Button */}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowAllStats(!showAllStats)}
            className="w-full text-muted-foreground hover:text-foreground"
          >
            {showAllStats ? (
              <>
                <ChevronUp className="w-4 h-4 mr-2" />
                Show Less
              </>
            ) : (
              <>
                <ChevronDown className="w-4 h-4 mr-2" />
                See All Stats ({additionalStats.length} more)
              </>
            )}
          </Button>
        </div>

        {/* Energy Flow and Billing Summary - Side by side on desktop, stacked on mobile */}
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 items-stretch">
          {/* Energy Flow */}
          <div>
            <EnergyFlowDiagram
              solarPower={energyStats.solarPower}
              batteryPower={energyStats.batteryPower}
              batteryLevel={energyStats.batteryLevel}
              consumption={energyStats.consumption}
              gridPower={energyStats.gridPower}
              isGridExporting={energyStats.isGridExporting}
              className="h-full"
            />
          </div>

          {/* Billing Summary */}
          <div>
            <BillingSummary />
          </div>
        </div>

        {/* Energy Chart - Full Width */}
        <EnergyChart data={chartData} title="Energy Overview - Today" />

        {/* Visual System Diagram */}
        <VisualSystemDiagram />
      </div>
    </>
  );
};

export default Index;
