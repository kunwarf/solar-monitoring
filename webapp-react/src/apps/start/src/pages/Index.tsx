import { AppHeader } from "@/components/layout/AppHeader";
import { StatCard } from "@/components/dashboard/StatCard";
import { EnergyFlowDiagram } from "@/components/dashboard/EnergyFlowDiagram";
import { EnergyChart } from "@/components/dashboard/EnergyChart";
import { DeviceOverview } from "@/components/dashboard/DeviceOverview";
import { HierarchicalDeviceOverview } from "@/components/dashboard/HierarchicalDeviceOverview";
import { Sun, Battery, Home, Zap, TrendingUp, ArrowDownUp, Leaf, DollarSign, Receipt, Target, Gauge, ArrowDown, ArrowUp } from "lucide-react";
import { useEnergyStatsData, useChartData } from "@/data/mockDataHooks";

const Index = () => {
  // Get data from API (same structure as mockData)
  const energyStats = useEnergyStatsData();
  const chartData = useChartData();
  return (
    <div className="min-h-screen bg-background text-foreground">
      <AppHeader 
        title="Dashboard" 
        subtitle="Real-time energy monitoring and analytics"
      />
      
      <div className="p-6 space-y-6">
        {/* Row 1: Financial & Daily Energy Stats (6 cards) */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
          <StatCard
            title="Monthly Bill Estimate"
            value={energyStats.monthlyBillAmount.toFixed(2)}
            unit="$"
            icon={Receipt}
            variant="financial"
            delay={0}
          />
          <StatCard
            title="Today's Savings"
            value={energyStats.moneySaved.toFixed(2)}
            unit="$"
            icon={DollarSign}
            variant="financial"
            trend={{ value: 8, isPositive: true }}
            delay={0.1}
          />
          <StatCard
            title="CO₂ Saved Today"
            value={energyStats.co2Saved.toFixed(2)}
            unit="kg"
            icon={Leaf}
            variant="environment"
            trend={{ value: 15, isPositive: true }}
            delay={0.2}
          />
          <StatCard
            title="Battery Charge Energy"
            value={energyStats.batteryChargeEnergy.toFixed(2)}
            unit="kWh"
            icon={ArrowDown}
            variant="battery"
            delay={0.3}
          />
          <StatCard
            title="Battery Discharge Energy"
            value={energyStats.batteryDischargeEnergy.toFixed(2)}
            unit="kWh"
            icon={ArrowUp}
            variant="battery"
            delay={0.4}
          />
          <StatCard
            title="Load Energy"
            value={energyStats.loadEnergy.toFixed(2)}
            unit="kWh"
            icon={Home}
            variant="consumption"
            delay={0.5}
          />
        </div>

        {/* Row 2: Grid Import & Production Stats (6 cards) */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
          <StatCard
            title="Grid Import"
            value={energyStats.gridImportEnergy.toFixed(2)}
            unit="kWh"
            icon={ArrowDown}
            variant="grid"
            delay={0.6}
          />
          <StatCard
            title="Today's Production"
            value={energyStats.dailyProduction.toFixed(2)}
            unit="kWh"
            icon={Sun}
            variant="solar"
            delay={0.8}
          />
          <StatCard
            title="Predicted vs Actual"
            value={`${energyStats.dailyProduction.toFixed(2)}/${energyStats.dailyPrediction.toFixed(2)}`}
            unit="kWh"
            icon={Target}
            variant="prediction"
            trend={energyStats.dailyPrediction > 0 ? { value: Math.round((energyStats.dailyProduction / energyStats.dailyPrediction) * 100 - 100), isPositive: energyStats.dailyProduction >= energyStats.dailyPrediction } : undefined}
            delay={0.9}
          />
          <StatCard
            title="Avg kWh/kWp"
            value={energyStats.avgKwPerKwp.toFixed(2)}
            unit="kWh/kWp"
            icon={Gauge}
            delay={1.0}
          />
          <StatCard
            title="Self-Consumption"
            value={energyStats.selfConsumption.toFixed(2)}
            unit="%"
            icon={Home}
            variant="consumption"
            delay={1.1}
          />
          <StatCard
            title="Grid Exported"
            value={energyStats.gridExportEnergy.toFixed(2)}
            unit="kWh"
            icon={ArrowUp}
            variant="grid"
            delay={1.2}
          />
        </div>

        {/* Main Content Grid */}
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

          {/* Chart */}
          <div>
            <EnergyChart data={chartData} title="Energy Overview - Today" className="h-full" />
          </div>
        </div>

        {/* Hierarchical Device Overview */}
        <HierarchicalDeviceOverview />
        
      </div>
    </div>
  );
};

export default Index;
