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
  const isNavigatingRef = React.useRef(false)

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
        
        // Check if we just navigated (from sessionStorage)
        let wasNavigating = false
        let navigatingTo: string | null = null
        try {
          wasNavigating = sessionStorage.getItem('__app_navigating__') === 'true'
          navigatingTo = sessionStorage.getItem('__app_navigating_to__')
        } catch (e) {
          // sessionStorage not available, continue normally
        }
        
        if (wasNavigating) {
          // Clear the navigation flag
          try {
            sessionStorage.removeItem('__app_navigating__')
            sessionStorage.removeItem('__app_navigating_to__')
          } catch (e) {
            // Ignore
          }
          
          // If we were navigating to a specific route, wait a bit for React to hydrate
          // This prevents hydration errors
          if (navigatingTo) {
            await new Promise(resolve => setTimeout(resolve, 100))
          }
        }
        
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
              isNavigatingRef.current = true
              window.location.replace(appRegistry[defaultAppId].defaultRoute)
              return // Exit early since we're redirecting
            }
          } else {
            // Use system default
            const defaultApp = getDefaultApp()
            setCurrentApp(defaultApp)
            // Only redirect if we're on root or invalid path
            if (currentPath === '/' || !currentPath.startsWith('/')) {
              isNavigatingRef.current = true
              window.location.replace(defaultApp.defaultRoute)
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
        // Clear navigation flag after initialization
        isNavigatingRef.current = false
        setIsLoading(false)
      }
    }

    initializeApp()
  }, [])

  const switchApp = (appId: string) => {
    const app = appRegistry[appId]
    if (app && app.enabled) {
      // Set navigation flag to prevent any state updates or router creation during navigation
      isNavigatingRef.current = true
      
      // Store navigation flag in sessionStorage so it persists across page reload
      // This helps detect if we're in the middle of a navigation when page reloads
      try {
        sessionStorage.setItem('__app_navigating__', 'true')
        sessionStorage.setItem('__app_navigating_to__', app.defaultRoute)
      } catch (e) {
        // Ignore sessionStorage errors (may not be available in some contexts)
      }

      // Use replace instead of href to avoid adding to history and prevent back button issues
      // This also helps prevent hydration errors by ensuring a clean navigation
      window.location.replace(app.defaultRoute)
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

