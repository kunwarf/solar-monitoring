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

export const appRegistry: Record<string, AppConfig> = {
  default: {
    id: 'default',
    name: 'Solar Monitoring',
    description: 'Default solar monitoring dashboard',
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
 */
export const getDefaultApp = (): AppConfig => {
  return appRegistry.default
}

