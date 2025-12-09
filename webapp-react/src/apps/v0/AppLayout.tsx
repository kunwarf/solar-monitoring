import React from 'react'
import { Outlet } from 'react-router-dom'
import { V0ThemeProvider } from './contexts/V0ThemeContext'
import { SharedSidebar } from '../../components/SharedSidebar'
import './styles/globals.css'

export const V0AppLayout: React.FC = () => {
  return (
    <V0ThemeProvider>
      <div className="flex h-screen bg-background text-foreground">
        <SharedSidebar />
        <main className="flex-1 overflow-auto bg-background">
          <Outlet />
        </main>
      </div>
    </V0ThemeProvider>
  )
}

