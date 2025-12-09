import React, { useState } from 'react'
import { ChevronDown } from 'lucide-react'
import { TimeRangeSelector } from '../components/time-range-selector'
import { EnergyFlowDiagram } from '../components/energy-flow-diagram'
import { StatsCards } from '../components/stats-cards'
import { EnergyChart } from '../components/energy-chart'
import { DevicesList } from '../components/devices-list'
import { BillingCard } from '../components/billing-card'
import { AlertsCard } from '../components/alerts-card'

export const DashboardPage: React.FC = () => {
  const [timeRange, setTimeRange] = useState('today')
  const [selectedHome, setSelectedHome] = useState('main-home')

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">Energy Dashboard</h1>
          <p className="text-muted-foreground">Real-time monitoring of your solar system</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="relative">
            <select
              value={selectedHome}
              onChange={(e) => setSelectedHome(e.target.value)}
              className="appearance-none w-[180px] h-9 px-3 pr-8 text-sm bg-card border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            >
              <option value="main-home">Main Residence</option>
              <option value="vacation-home">Vacation Home</option>
            </select>
            <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
          </div>
          <TimeRangeSelector value={timeRange} onChange={setTimeRange} />
        </div>
      </div>

      {/* Stats Cards */}
      <StatsCards />

      {/* Main Grid */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Energy Flow - Takes 2 columns */}
        <div className="xl:col-span-2">
          <EnergyFlowDiagram />
        </div>

        {/* Alerts */}
        <div>
          <AlertsCard />
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <EnergyChart title="Energy Production" subtitle="Solar generation over time" color="solar" />
        <EnergyChart title="Energy Consumption" subtitle="Home usage over time" color="consumption" />
      </div>

      {/* Devices and Billing */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="xl:col-span-2">
          <DevicesList />
        </div>
        <div>
          <BillingCard />
        </div>
      </div>
    </div>
  )
}
