import React from 'react'
import { createRoot } from 'react-dom/client'
import { createBrowserRouter, RouterProvider, RouteObject } from 'react-router-dom'
import { ThemeProvider } from './contexts/ThemeContext'
import { AppProvider, useApp } from './contexts/AppContext'
import { AuthProvider } from './contexts/AuthContext'
import { getDefaultApp } from './apps/appRegistry'
import { ErrorBoundary } from './components/ErrorBoundary'
import { AuthPage } from './components/AuthPage'
import './styles.css'

/**
 * Router Component that dynamically loads routes based on current app
 * Uses key prop to force remount when app changes
 * 
 * IMPORTANT: This component prevents hydration errors by:
 * 1. Only creating router after React hydration is complete
 * 2. Checking for navigation state to avoid creating router during navigation
 * 3. Using proper timing to ensure React has finished initial render
 */
const AppRouter: React.FC = () => {
  const { currentApp, isLoading } = useApp()
  const [router, setRouter] = React.useState<ReturnType<typeof createBrowserRouter> | null>(null)
  const [isHydrated, setIsHydrated] = React.useState(false)

  // Mark as hydrated after initial render to prevent hydration mismatches
  // This is critical for mobile devices where hydration can be slower
  React.useEffect(() => {
    // Use a combination of techniques to ensure we wait for hydration
    const markHydrated = () => {
      // Double-check that DOM is ready
      if (document.readyState === 'complete') {
        setIsHydrated(true)
      } else {
        // Wait for page to fully load
        window.addEventListener('load', () => setIsHydrated(true), { once: true })
      }
    }

    // Use requestIdleCallback if available (better for performance)
    if (typeof requestIdleCallback !== 'undefined') {
      requestIdleCallback(markHydrated, { timeout: 200 })
    } else {
      // Fallback: use multiple setTimeout to ensure we're past hydration
      setTimeout(markHydrated, 0)
      setTimeout(() => setIsHydrated(true), 50) // Backup
    }
  }, [])

  // Create router only after hydration is complete and app is loaded
  React.useEffect(() => {
    // Don't create router before hydration or while loading
    if (!isHydrated || isLoading || !currentApp) {
      return
    }

    // Check if we're in the middle of a navigation (from sessionStorage)
    let wasNavigating = false
    try {
      wasNavigating = sessionStorage.getItem('__app_navigating__') === 'true'
    } catch (e) {
      // sessionStorage not available, continue normally
    }
    
    const createRouterWithAuth = () => {
      const appRoutes = currentApp.routes()
      // Add /auth route at the root level
      const routes: RouteObject[] = [
        {
          path: '/auth',
          element: <AuthPage />,
        },
        ...appRoutes,
      ]
      return createBrowserRouter(routes)
    }

    if (wasNavigating) {
      // Wait a bit longer if we just navigated to ensure React has fully hydrated
      const timeoutId = setTimeout(() => {
        try {
          const newRouter = createRouterWithAuth()
          setRouter(newRouter)
        } catch (error) {
          console.error('Error creating router after navigation:', error)
          window.location.reload()
        }
      }, 150) // Longer delay after navigation
      
      return () => clearTimeout(timeoutId)
    }

    // Create router normally (not during navigation)
    try {
      const newRouter = createRouterWithAuth()
      setRouter(newRouter)
    } catch (error) {
      console.error('Error creating router:', error)
      window.location.reload()
    }
  }, [currentApp?.id, isLoading, isHydrated])

  if (isLoading || !router) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-background">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
          <p className="mt-4 text-gray-600 dark:text-gray-400">Loading application...</p>
        </div>
      </div>
    )
  }

  // Using key prop ensures router is recreated when app changes
  return <RouterProvider router={router} key={currentApp.id} />
}

const App: React.FC = () => {
  return (
    <ErrorBoundary>
      <ThemeProvider>
        <AuthProvider>
          <AppProvider>
            <AppRouter />
          </AppProvider>
        </AuthProvider>
      </ThemeProvider>
    </ErrorBoundary>
  )
}

createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
