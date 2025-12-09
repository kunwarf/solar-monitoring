/**
 * Default Application Routes
 * This is the current solar monitoring application
 */

import { RouteObject } from 'react-router-dom'
import { NewDashboardPage } from '../../routes/NewDashboardPage'
import { TelemetryPage } from '../../routes/TelemetryPage'
import { GridDetailPage } from '../../routes/GridDetailPage'
import { SolarDetailPage } from '../../routes/SolarDetailPage'
import { LoadDetailPage } from '../../routes/LoadDetailPage'
import { InverterDetailPage } from '../../routes/InverterDetailPage'
import { BatteryPage } from '../../routes/BatteryPage'
import { BatteryDetailPage } from '../../routes/BatteryDetailPage'
import { MeterPage } from '../../routes/MeterPage'
import { SettingsPage } from '../../routes/SettingsPage'
import { BillingSetupPage } from '../../routes/BillingSetupPage'
import { BillingDashboardPage } from '../../routes/BillingDashboardPage'
import { DashboardPage } from '../../routes/DashboardPage'
import { DefaultAppLayout } from './AppLayout'

export const defaultAppRoutes = (): RouteObject[] => {
  return [
    {
      path: '/',
      element: <DefaultAppLayout />,
      children: [
        { index: true, element: <NewDashboardPage /> },
        { path: 'dashboard-new', element: <NewDashboardPage /> },
        { path: 'telemetry', element: <TelemetryPage /> },
        { path: 'grid-detail', element: <GridDetailPage /> },
        { path: 'solar-detail', element: <SolarDetailPage /> },
        { path: 'load-detail', element: <LoadDetailPage /> },
        { path: 'inverter-detail', element: <InverterDetailPage /> },
        { path: 'battery', element: <BatteryPage /> },
        { path: 'battery-detail', element: <BatteryDetailPage /> },
        { path: 'meter', element: <MeterPage /> },
        { path: 'settings', element: <SettingsPage /> },
        { path: 'billing-setup', element: <BillingSetupPage /> },
        { path: 'billing', element: <BillingDashboardPage /> },
        { path: 'analytics', element: <DashboardPage /> }, // Analytics links to old dashboard
      ],
    },
  ]
}

