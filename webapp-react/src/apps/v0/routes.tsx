import React from 'react'
import { RouteObject } from 'react-router-dom'
import { DashboardPage } from './pages/DashboardPage'
import { BatteriesPage } from './pages/BatteriesPage'
import { InvertersPage } from './pages/InvertersPage'
import { MetersPage } from './pages/MetersPage'
import { BillingPage } from './pages/BillingPage'
import { SettingsPage } from './pages/SettingsPage'
import { BatterySettingsPage } from './pages/BatterySettingsPage'
import { InverterSettingsPage } from './pages/InverterSettingsPage'
import { V0AppLayout } from './AppLayout'

export const v0AppRoutes = (): RouteObject[] => {
  return [
    {
      path: '/v0',
      element: <V0AppLayout />,
      children: [
        { index: true, element: <DashboardPage /> },
        { path: 'dashboard', element: <DashboardPage /> },
        { path: 'batteries', element: <BatteriesPage /> },
        { path: 'inverters', element: <InvertersPage /> },
        { path: 'meters', element: <MetersPage /> },
        { path: 'billing', element: <BillingPage /> },
        { path: 'settings', element: <SettingsPage /> },
        { path: 'settings/inverter/:id', element: <InverterSettingsPage /> },
        { path: 'settings/battery/:id', element: <BatterySettingsPage /> },
      ],
    },
  ]
}

