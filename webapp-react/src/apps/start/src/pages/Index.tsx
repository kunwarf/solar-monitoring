import { AppHeader } from "@/components/layout/AppHeader";
import { StatCard } from "@/components/dashboard/StatCard";
import { EnergyFlowDiagram } from "@/components/dashboard/EnergyFlowDiagram";
import { EnergyChart } from "@/components/dashboard/EnergyChart";
import { DeviceOverview } from "@/components/dashboard/DeviceOverview";
import { HierarchicalDeviceOverview } from "@/components/dashboard/HierarchicalDeviceOverview";
import { Sun, Battery, Home, Zap, TrendingUp, ArrowDownUp, Leaf, DollarSign, Receipt, Target, Gauge } from "lucide-react";
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
        {/* Financial & Savings Overview */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
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
            value={energyStats.co2Saved.toFixed(1)}
            unit="kg"
            icon={Leaf}
            variant="environment"
            trend={{ value: 15, isPositive: true }}
            delay={0.2}
          />
        </div>

        {/* Real-time Power Stats */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            title="Solar Production"
            value={energyStats.solarPower.toFixed(1)}
            unit="kW"
            icon={Sun}
            variant="solar"
            trend={{ value: 12, isPositive: true }}
            delay={0.3}
          />
          <StatCard
            title="Battery Level"
            value={energyStats.batteryLevel.toString()}
            unit="%"
            icon={Battery}
            variant="battery"
            trend={{ value: 5, isPositive: true }}
            delay={0.4}
          />
          <StatCard
            title="Home Consumption"
            value={energyStats.consumption.toFixed(1)}
            unit="kW"
            icon={Home}
            variant="consumption"
            delay={0.5}
          />
          <StatCard
            title="Grid Export"
            value={energyStats.gridPower.toFixed(1)}
            unit="kW"
            icon={Zap}
            variant="grid"
            trend={{ value: 8, isPositive: true }}
            delay={0.6}
          />
        </div>

        {/* Daily Production Stats */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          <StatCard
            title="Today's Production"
            value={energyStats.dailyProduction.toFixed(1)}
            unit="kWh"
            icon={TrendingUp}
            variant="solar"
            delay={0.7}
          />
          <StatCard
            title="Predicted vs Actual"
            value={`${energyStats.dailyProduction.toFixed(0)}/${energyStats.dailyPrediction.toFixed(0)}`}
            unit="kWh"
            icon={Target}
            variant="prediction"
            trend={{ value: Math.round((energyStats.dailyProduction / energyStats.dailyPrediction) * 100 - 100), isPositive: energyStats.dailyProduction >= energyStats.dailyPrediction }}
            delay={0.8}
          />
          <StatCard
            title="Avg kWh/kWp"
            value={energyStats.avgKwPerKwp.toFixed(2)}
            unit="kWh/kWp"
            icon={Gauge}
            delay={0.9}
          />
          <StatCard
            title="Self-Consumption"
            value={energyStats.selfConsumption.toString()}
            unit="%"
            icon={Home}
            variant="consumption"
            delay={1.0}
          />
          <StatCard
            title="Grid Exported"
            value={energyStats.gridExported.toFixed(1)}
            unit="kWh"
            icon={ArrowDownUp}
            variant="grid"
            delay={1.1}
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
