import React from 'react'
import { RouteObject } from 'react-router-dom'
import { StartAppLayout } from './AppLayout'
import { AuthLayout } from './AuthLayout'
// Use @/ alias which points to src/apps/start/src
// IMPORTANT: You must copy all files from start-from-code-9c314cf4-main/src to webapp-react/src/apps/start/src/
// Run: cp -r start-from-code-9c314cf4-main/src/* webapp-react/src/apps/start/src/
import Index from '@/pages/Index'
import Devices from '@/pages/Devices'
import DeviceSettings from '@/pages/DeviceSettings'
import DeviceManagement from '@/pages/DeviceManagement'
import Telemetry from '@/pages/Telemetry'
import SmartScheduler from '@/pages/SmartScheduler'
import Settings from '@/pages/Settings'
import Billing from '@/pages/Billing'
import BillingSettings from '@/pages/BillingSettings'
import Notifications from '@/pages/Notifications'
import Profile from '@/pages/Profile'
import NotFound from '@/pages/NotFound'
import Auth from '@/pages/Auth'
import ProtectedRoute from '@/components/ProtectedRoute'

export const startAppRoutes = (): RouteObject[] => {
  return [
    // Auth routes with AuthLayout (providers but no sidebar)
    // Handle both /auth and /start/auth for compatibility
    {
      path: '/auth',
      element: <AuthLayout />,
      children: [
        { index: true, element: <Auth /> },
      ],
    },
    {
      path: '/start/auth',
      element: <AuthLayout />,
      children: [
        { index: true, element: <Auth /> },
      ],
    },
    // Main app routes with StartAppLayout (sidebar + providers)
    {
      path: '/start',
      element: <StartAppLayout />,
      children: [
        { index: true, element: <ProtectedRoute><Index /></ProtectedRoute> },
        { path: 'dashboard', element: <ProtectedRoute><Index /></ProtectedRoute> },
        { path: 'devices', element: <ProtectedRoute><Devices /></ProtectedRoute> },
        { path: 'devices/manage', element: <ProtectedRoute><DeviceManagement /></ProtectedRoute> },
        { path: 'devices/:deviceId/settings', element: <ProtectedRoute><DeviceSettings /></ProtectedRoute> },
        { path: 'telemetry', element: <ProtectedRoute><Telemetry /></ProtectedRoute> },
        { path: 'scheduler', element: <ProtectedRoute><SmartScheduler /></ProtectedRoute> },
        { path: 'settings', element: <ProtectedRoute><Settings /></ProtectedRoute> },
        { path: 'billing', element: <ProtectedRoute><Billing /></ProtectedRoute> },
        { path: 'billing/settings', element: <ProtectedRoute><BillingSettings /></ProtectedRoute> },
        { path: 'notifications', element: <ProtectedRoute><Notifications /></ProtectedRoute> },
        { path: 'profile', element: <ProtectedRoute><Profile /></ProtectedRoute> },
        { path: '*', element: <NotFound /> },
      ],
    },
  ]
}

