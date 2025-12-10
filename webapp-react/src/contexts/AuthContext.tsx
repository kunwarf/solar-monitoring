/**
 * Shared Authentication Context
 * Used by all apps for authentication
 */

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { api } from '../lib/api'

interface User {
  id: string
  email: string
  firstName: string
  lastName: string
}

interface AuthContextType {
  user: User | null
  isLoading: boolean
  login: (email: string, password: string) => Promise<{ success: boolean; error?: string; token?: string }>
  signup: (email: string, password: string, firstName: string, lastName: string) => Promise<{ success: boolean; error?: string; token?: string }>
  logout: () => void
  verifySession: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  // Get token from localStorage
  const getToken = (): string | null => {
    try {
      return localStorage.getItem('auth_token')
    } catch {
      return null
    }
  }

  // Save token to localStorage
  const saveToken = (token: string) => {
    try {
      localStorage.setItem('auth_token', token)
    } catch (e) {
      console.error('Failed to save token:', e)
    }
  }

  // Remove token from localStorage
  const removeToken = () => {
    try {
      localStorage.removeItem('auth_token')
      localStorage.removeItem('auth_user')
    } catch (e) {
      console.error('Failed to remove token:', e)
    }
  }

  // Verify session on mount
  useEffect(() => {
    verifySession()
  }, [])

  const verifySession = async () => {
    const token = getToken()
    if (!token) {
      setIsLoading(false)
      return
    }

    try {
      const response = await api.post<{ status: string; user?: User; error?: string }>('/api/auth/verify', { token })
      
      if (response.status === 'ok' && response.user) {
        setUser(response.user)
        // Also save user to localStorage for quick access
        try {
          localStorage.setItem('auth_user', JSON.stringify(response.user))
        } catch (e) {
          // Ignore
        }
      } else {
        // Invalid token, remove it
        removeToken()
        setUser(null)
      }
    } catch (error) {
      console.error('Session verification failed:', error)
      removeToken()
      setUser(null)
    } finally {
      setIsLoading(false)
    }
  }

  const login = async (email: string, password: string): Promise<{ success: boolean; error?: string; token?: string }> => {
    try {
      const response = await api.post<{ status: string; user?: User; token?: string; error?: string }>('/api/auth/login', {
        email,
        password,
      })

      if (response.status === 'ok' && response.user && response.token) {
        setUser(response.user)
        saveToken(response.token)
        // Also save user to localStorage
        try {
          localStorage.setItem('auth_user', JSON.stringify(response.user))
        } catch (e) {
          // Ignore
        }
        return { success: true, token: response.token }
      } else {
        return { success: false, error: response.error || 'Login failed' }
      }
    } catch (error: any) {
      console.error('Login error:', error)
      return { success: false, error: error?.response?.data?.error || 'Login failed. Please try again.' }
    }
  }

  const signup = async (
    email: string,
    password: string,
    firstName: string,
    lastName: string
  ): Promise<{ success: boolean; error?: string; token?: string }> => {
    try {
      const response = await api.post<{ status: string; user?: User; token?: string; error?: string }>('/api/auth/register', {
        email,
        password,
        firstName,
        lastName,
      })

      if (response.status === 'ok' && response.user && response.token) {
        setUser(response.user)
        saveToken(response.token)
        // Also save user to localStorage
        try {
          localStorage.setItem('auth_user', JSON.stringify(response.user))
        } catch (e) {
          // Ignore
        }
        return { success: true, token: response.token }
      } else {
        return { success: false, error: response.error || 'Registration failed' }
      }
    } catch (error: any) {
      console.error('Signup error:', error)
      return { success: false, error: error?.response?.data?.error || 'Registration failed. Please try again.' }
    }
  }

  const logout = async () => {
    const token = getToken()
    if (token) {
      try {
        await api.post('/api/auth/logout', { token })
      } catch (error) {
        console.error('Logout error:', error)
      }
    }
    
    // Clear state and tokens
    removeToken()
    setUser(null)
    
    // Use window.location.replace to avoid React hydration errors during logout
    // This ensures a clean navigation without React trying to re-render during the transition
    // Similar to how we handle app switching to prevent hydration mismatches
    window.location.replace('/auth')
  }

  return (
    <AuthContext.Provider value={{ user, isLoading, login, signup, logout, verifySession }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

