/**
 * Application Registry
 * Defines all available applications in the system
 */

import { RouteObject } from 'react-router-dom'

export interface AppConfig {
  id: string
  name: string
  description: string
  icon?: string // Icon name or path
  defaultRoute: string // Default route when app is selected
  routes: () => RouteObject[] // Function that returns routes for this app
  layout?: React.ComponentType<any> // Optional custom layout component
  enabled: boolean // Whether this app is enabled
}

// Import app configurations
import { defaultAppRoutes } from './default/routes'
import { v0AppRoutes } from './v0/routes'
import { startAppRoutes } from './start/routes'

export const appRegistry: Record<string, AppConfig> = {
  start: {
    id: 'start',
    name: 'Solar Monitoring',
    description: 'Modern solar monitoring dashboard',
    icon: 'sun',
    defaultRoute: '/start',
    routes: startAppRoutes,
    enabled: true,
  },
  default: {
    id: 'default',
    name: 'Legacy Dashboard',
    description: 'Legacy solar monitoring dashboard',
    icon: 'sun',
    defaultRoute: '/',
    routes: defaultAppRoutes,
    enabled: true,
  },
  v0: {
    id: 'v0',
    name: 'Analytics',
    description: 'Advanced analytics view',
    icon: 'chart',
    defaultRoute: '/v0',
    routes: v0AppRoutes,
    enabled: true,
  },
}

// Debug: Log registry on import
if (typeof window !== 'undefined') {
  console.log('App Registry loaded:', Object.keys(appRegistry).map(key => ({
    id: appRegistry[key].id,
    name: appRegistry[key].name,
    enabled: appRegistry[key].enabled
  })))
}

/**
 * Get all enabled applications
 */
export const getEnabledApps = (): AppConfig[] => {
  return Object.values(appRegistry).filter(app => app.enabled)
}

/**
 * Get application by ID
 */
export const getApp = (appId: string): AppConfig | undefined => {
  return appRegistry[appId]
}

/**
 * Get default application
 * Returns the "start" app (Solar Monitoring - Modern Dashboard) as the default
 * This is the default for both mobile and desktop devices
 */
export const getDefaultApp = (): AppConfig => {
  return appRegistry.start // Modern Solar Monitoring dashboard is the default for all devices
}

