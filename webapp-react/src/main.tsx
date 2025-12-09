import React from 'react'
import { createRoot } from 'react-dom/client'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import { ThemeProvider } from './contexts/ThemeContext'
import { AppProvider, useApp } from './contexts/AppContext'
import { getDefaultApp } from './apps/appRegistry'
import './styles.css'

/**
 * Router Component that dynamically loads routes based on current app
 * Uses key prop to force remount when app changes
 */
const AppRouter: React.FC = () => {
  const { currentApp, isLoading } = useApp()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading application...</p>
        </div>
      </div>
    )
  }

  // Create router with current app's routes
  // Using key prop ensures router is recreated when app changes
  const routes = currentApp.routes()
  const router = createBrowserRouter(routes)

  return <RouterProvider router={router} key={currentApp.id} />
}

const App: React.FC = () => {
  return (
    <ThemeProvider>
      <AppProvider>
        <AppRouter />
      </AppProvider>
    </ThemeProvider>
  )
}

createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
