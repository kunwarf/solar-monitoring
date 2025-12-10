import React from 'react'
import { Outlet } from 'react-router-dom'
import { ThemeProvider } from './src/hooks/use-theme'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
// AuthProvider is now at root level, no need to import here
import { BillingConfigProvider } from './src/hooks/use-billing-config'
import { TooltipProvider } from './src/components/ui/tooltip'
import { Toaster } from './src/components/ui/toaster'
import { Toaster as Sonner } from './src/components/ui/sonner'
import './styles/globals.css'

// Create a QueryClient instance
const queryClient = new QueryClient()

export const AuthLayout: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <BillingConfigProvider>
          <TooltipProvider>
            <Toaster />
            <Sonner />
            <div className="min-h-screen bg-background">
              <Outlet />
            </div>
          </TooltipProvider>
        </BillingConfigProvider>
      </ThemeProvider>
    </QueryClientProvider>
  )
}

