/**
 * Auth Guard Component
 * Wraps the app router and redirects to auth if not authenticated
 * Allows access to /auth route without authentication
 */

import { useAuth } from '../contexts/AuthContext'
import { AuthPage } from './AuthPage'
import { Loader2 } from 'lucide-react'
import { useEffect } from 'react'

interface AuthGuardProps {
  children: React.ReactNode
}

export const AuthGuard: React.FC<AuthGuardProps> = ({ children }) => {
  const { user, isLoading } = useAuth()

  useEffect(() => {
    // Check if we're on /auth route
    const isAuthRoute = window.location.pathname === '/auth' || window.location.pathname.startsWith('/auth/')
    
    if (!isLoading && !user && !isAuthRoute) {
      // Redirect to auth if not authenticated and not already on auth page
      const returnTo = window.location.pathname + window.location.search
      window.location.href = `/auth?returnTo=${encodeURIComponent(returnTo)}`
    } else if (!isLoading && user && isAuthRoute) {
      // Redirect to default app if authenticated and on auth page
      const returnTo = new URLSearchParams(window.location.search).get('returnTo') || '/start'
      window.location.href = returnTo
    }
  }, [user, isLoading])

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  // Show auth page if not authenticated
  const isAuthRoute = window.location.pathname === '/auth' || window.location.pathname.startsWith('/auth/')
  if (!user && isAuthRoute) {
    return <AuthPage />
  }

  // Show auth page if not authenticated and not on auth route (will redirect in useEffect)
  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  return <>{children}</>
}

