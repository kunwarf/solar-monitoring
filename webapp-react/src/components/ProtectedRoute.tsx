/**
 * Shared Protected Route Component
 * Redirects to login if user is not authenticated
 */

import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { Loader2 } from 'lucide-react'

interface ProtectedRouteProps {
  children: React.ReactNode
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const { user, isLoading } = useAuth()
  const location = useLocation()

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  if (!user) {
    // Preserve the intended destination so we can redirect back after login
    const returnTo = location.pathname + location.search
    // Redirect to /auth (shared auth page)
    return <Navigate to={`/auth?returnTo=${encodeURIComponent(returnTo)}`} replace />
  }

  return <>{children}</>
}

