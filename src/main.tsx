import React from 'react'
import { createRoot } from 'react-dom/client'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import { AppLayout } from './ui/AppLayout'
import { DashboardPage } from './routes/DashboardPage'
import { IndexPage } from './routes/IndexPage'
import { AnalyticsPage } from './routes/AnalyticsPage'
import { BatteryPage } from './routes/BatteryPage'
import { SettingsPage } from './routes/SettingsPage'
import './styles.css'

const router = createBrowserRouter([
  {
    path: '/',
    element: <AppLayout />,
    children: [
      { index: true, element: <IndexPage /> },
      { path: 'dashboard', element: <DashboardPage /> },
      { path: 'battery', element: <BatteryPage /> },
      { path: 'settings', element: <SettingsPage /> },
      { path: 'analytics', element: <AnalyticsPage /> },
    ],
  },
])

createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>
)

