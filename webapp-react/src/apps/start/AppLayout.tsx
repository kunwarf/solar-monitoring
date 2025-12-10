import React from 'react'
import { Outlet } from 'react-router-dom'
import { SharedSidebar } from '../../components/SharedSidebar'
import { MobileBottomNav } from '../../components/MobileBottomNav'
import { ThemeProvider } from './src/hooks/use-theme'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
// AuthProvider is now at root level, no need to import here
import { BillingConfigProvider } from './src/hooks/use-billing-config'
import { TooltipProvider } from './src/components/ui/tooltip'
import { Toaster } from './src/components/ui/toaster'
import { Toaster as Sonner } from './src/components/ui/sonner'
import { DataProvider } from './src/data/DataProvider'
import './styles/globals.css'

// Create a QueryClient instance
const queryClient = new QueryClient()

export const StartAppLayout: React.FC = () => {
  // Initialize mobile state safely to prevent hydration mismatches
  // CRITICAL: Always start with false to ensure server and client render the same initial state
  // This prevents React error #310 (hydration mismatch) on mobile devices
  // The actual value will be set in useEffect after hydration completes
  const [isMobile, setIsMobile] = React.useState(false)
  
  React.useEffect(() => {
    // Set the actual mobile value after React has hydrated
    // This ensures server and client render the same initial state, preventing hydration errors
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768)
    }
    
    // Set immediately after mount (hydration is complete at this point)
    checkMobile()
    
    // Listen for resize events
    window.addEventListener('resize', checkMobile)
    return () => window.removeEventListener('resize', checkMobile)
  }, [])
  
  return (
    <QueryClientProvider client={queryClient}>
      <DataProvider>
        <ThemeProvider>
          <BillingConfigProvider>
            <TooltipProvider>
              <Toaster />
              <Sonner />
              <div className="flex h-screen overflow-hidden bg-background text-foreground">
              {/* Show sidebar on desktop, hide on mobile */}
              <div className={isMobile ? 'hidden' : 'block'}>
                <SharedSidebar />
              </div>
              {/* Always render mobile bottom nav but hide on desktop */}
              <div className={isMobile ? 'block' : 'hidden'}>
                <MobileBottomNav />
              </div>
              <main className={`flex-1 overflow-y-auto bg-background text-foreground ${isMobile ? 'pb-20' : ''}`}>
                <Outlet />
              </main>
            </div>
          </TooltipProvider>
        </BillingConfigProvider>
      </ThemeProvider>
      </DataProvider>
    </QueryClientProvider>
  )
}

