import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { appRegistry, AppConfig, getDefaultApp } from '../apps/appRegistry'
import { getAppPreference, setAppPreference } from '../api/appPreferences'

interface AppContextType {
  currentApp: AppConfig
  availableApps: AppConfig[]
  switchApp: (appId: string) => void
  setDefaultApp: (appId: string) => Promise<void>
  isLoading: boolean
}

const AppContext = createContext<AppContextType | undefined>(undefined)

export const AppProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [currentApp, setCurrentApp] = useState<AppConfig>(getDefaultApp())
  const [isLoading, setIsLoading] = useState(true)

  const availableApps = Object.values(appRegistry).filter(app => app.enabled)

  // Debug logging
  useEffect(() => {
    console.log('App registry keys:', Object.keys(appRegistry))
    console.log('Available apps:', availableApps.map(a => ({ id: a.id, name: a.name, enabled: a.enabled })))
  }, [availableApps])

  // Initialize app on mount
  useEffect(() => {
    const initializeApp = async () => {
      try {
        setIsLoading(true)
        
        // Try to detect current app from URL by checking which app's routes match
        const currentPath = window.location.pathname
        let detectedApp: AppConfig | null = null
        
        // Check each app's routes to see if current path matches
        for (const app of availableApps) {
          const routes = app.routes()
          // Simple check: if path starts with app's default route or matches any route pattern
          if (currentPath === app.defaultRoute || currentPath.startsWith(app.defaultRoute + '/')) {
            detectedApp = app
            break
          }
        }
        
        if (detectedApp) {
          setCurrentApp(detectedApp)
        } else {
          // No app detected from URL, load user preference or use default
          const defaultAppId = await getAppPreference()
          
          if (defaultAppId && appRegistry[defaultAppId]?.enabled) {
            setCurrentApp(appRegistry[defaultAppId])
            // Only redirect if we're not on a valid route
            if (currentPath === '/' || !currentPath.startsWith('/')) {
              window.location.href = appRegistry[defaultAppId].defaultRoute
              return // Exit early since we're redirecting
            }
          } else {
            // Use system default
            const defaultApp = getDefaultApp()
            setCurrentApp(defaultApp)
            // Only redirect if we're on root or invalid path
            if (currentPath === '/' || !currentPath.startsWith('/')) {
              window.location.href = defaultApp.defaultRoute
              return // Exit early since we're redirecting
            }
          }
        }
      } catch (error) {
        console.error('Error initializing app:', error)
        // Fallback to default app
        const defaultApp = getDefaultApp()
        setCurrentApp(defaultApp)
      } finally {
        setIsLoading(false)
      }
    }

    initializeApp()
  }, [])

  const switchApp = (appId: string) => {
    const app = appRegistry[appId]
    if (app && app.enabled) {
      setCurrentApp(app)
      // Navigate to the app's default route
      // This will cause a full page reload, which will recreate the router
      window.location.href = app.defaultRoute
    }
  }

  const setDefaultApp = async (appId: string) => {
    try {
      await setAppPreference(appId)
      // Optionally switch to the new default app
      // switchApp(appId)
    } catch (error) {
      console.error('Error setting default app:', error)
      throw error
    }
  }

  return (
    <AppContext.Provider value={{
      currentApp,
      availableApps,
      switchApp,
      setDefaultApp,
      isLoading,
    }}>
      {children}
    </AppContext.Provider>
  )
}

export const useApp = () => {
  const context = useContext(AppContext)
  if (context === undefined) {
    throw new Error('useApp must be used within an AppProvider')
  }
  return context
}

