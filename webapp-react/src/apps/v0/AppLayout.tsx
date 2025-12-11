import React from 'react'
import { Outlet } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { V0ThemeProvider } from './contexts/V0ThemeContext'
import { V0DataProvider } from './data/V0DataProvider'
import { SharedSidebar } from '../../components/SharedSidebar'
import { MobileBottomNav } from '../../components/MobileBottomNav'
import { useIsMobile } from '../start/src/hooks/use-mobile'
import './styles/globals.css'

// Create a QueryClient instance for v0 app
const queryClient = new QueryClient()

export const V0AppLayout: React.FC = () => {
  const isMobile = useIsMobile()
  
  return (
    <QueryClientProvider client={queryClient}>
      <V0DataProvider>
        <V0ThemeProvider>
          <div className="flex h-screen bg-background text-foreground">
            {/* Show sidebar on desktop, hide on mobile */}
            <div className={isMobile ? 'hidden' : 'block'}>
              <SharedSidebar />
            </div>
            {/* Always render mobile bottom nav but hide on desktop */}
            <div className={isMobile ? 'block' : 'hidden'}>
              <MobileBottomNav />
            </div>
            <main className={`flex-1 overflow-auto bg-background ${isMobile ? 'pb-20' : ''}`}>
              <Outlet />
            </main>
          </div>
        </V0ThemeProvider>
      </V0DataProvider>
    </QueryClientProvider>
  )
}

