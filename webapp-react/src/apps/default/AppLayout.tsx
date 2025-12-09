/**
 * Default Application Layout
 * This is the layout for the default solar monitoring app
 */

import React, { useState, useEffect } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { useMobile } from '../../hooks/useMobile'
import { useTheme } from '../../contexts/ThemeContext'
import { api } from '../../lib/api'
import { ArraysResponse, ArrayInfo } from '../../types/telemetry'
import { SharedSidebar } from '../../components/SharedSidebar'
// Import v0 styles to get CSS variables for consistent theming
import '../v0/styles/globals.css'

// Create a context for array selection
export const ArrayContext = React.createContext<{
  arrays: ArrayInfo[];
  selectedArray: string | null;
  setSelectedArray: (arrayId: string | null) => void;
}>({
  arrays: [],
  selectedArray: null,
  setSelectedArray: () => {},
})

export const DefaultAppLayout: React.FC = () => {
  const { isMobile } = useMobile()
  const { theme } = useTheme()
  const [arrays, setArrays] = useState<ArrayInfo[]>([])
  const [selectedArray, setSelectedArray] = useState<string | null>(null)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [drawerY, setDrawerY] = useState(0)
  const [isDragging, setIsDragging] = useState(false)
  const [startY, setStartY] = useState(0)
  
  const drawerBg = theme === 'dark' ? '#1f2937' : '#ffffff'
  
  // Auto-close drawer after 20 seconds
  useEffect(() => {
    if (sidebarOpen) {
      const timer = setTimeout(() => {
        setSidebarOpen(false)
      }, 20000) // 20 seconds
      
      return () => clearTimeout(timer)
    }
  }, [sidebarOpen])
  
  // Handle drag to close
  const handleTouchStart = (e: React.TouchEvent) => {
    // Only start dragging from the handle bar area
    const target = e.target as HTMLElement
    if (target.closest('.drawer-handle')) {
      setIsDragging(true)
      setStartY(e.touches[0].clientY)
      setDrawerY(0)
    }
  }
  
  const handleTouchMove = (e: React.TouchEvent) => {
    if (!isDragging || !sidebarOpen) return
    
    const currentY = e.touches[0].clientY
    const deltaY = currentY - startY
    
    // Only allow dragging down
    if (deltaY > 0) {
      setDrawerY(deltaY)
    }
  }
  
  const handleTouchEnd = () => {
    if (isDragging) {
      // If dragged more than 100px down, close the drawer
      if (drawerY > 100) {
        setSidebarOpen(false)
      }
      setIsDragging(false)
      setDrawerY(0)
    }
  }

  useEffect(() => {
    const fetchArrays = async () => {
      try {
        const response: ArraysResponse = await api.get('/api/arrays')
        if (response.arrays && response.arrays.length > 0) {
          setArrays(response.arrays)
        }
      } catch (error) {
        console.error('Error loading arrays:', error)
      }
    }
    fetchArrays()
  }, [])

  return (
    <ArrayContext.Provider value={{ arrays, selectedArray, setSelectedArray }}>
      <div className="flex h-screen bg-background text-foreground overflow-hidden">
        {isMobile ? (
          <>
            {/* Mobile Bottom Drawer Overlay */}
            {sidebarOpen && (
              <div 
                className="fixed inset-0 bg-black bg-opacity-50 z-40"
                onClick={() => setSidebarOpen(false)}
              />
            )}
            {/* Mobile Bottom Drawer */}
            <div 
              className={`fixed bottom-0 left-0 right-0 z-50 ${!isDragging ? 'transition-transform duration-300 ease-out' : ''} ${sidebarOpen ? 'translate-y-0' : 'translate-y-full'}`}
              style={{
                maxHeight: '70vh',
                borderTopLeftRadius: '24px',
                borderTopRightRadius: '24px',
                backgroundColor: drawerBg,
                boxShadow: theme === 'dark' ? '0 -4px 20px rgba(0, 0, 0, 0.3)' : '0 -4px 20px rgba(0, 0, 0, 0.1)',
                transform: sidebarOpen ? `translateY(${drawerY}px)` : 'translateY(100%)',
                touchAction: 'pan-y',
              }}
              onTouchStart={handleTouchStart}
              onTouchMove={handleTouchMove}
              onTouchEnd={handleTouchEnd}
            >
              {/* Handle Bar - Draggable area */}
              <div 
                className="drawer-handle flex justify-center pt-3 pb-2 cursor-grab active:cursor-grabbing"
                style={{ touchAction: 'none', userSelect: 'none' }}
              >
                <div 
                  className="w-12 h-1 rounded-full"
                  style={{
                    backgroundColor: theme === 'dark' ? 'rgba(255, 255, 255, 0.3)' : 'rgba(0, 0, 0, 0.2)',
                  }}
                />
              </div>
              {/* Sidebar Content */}
              <div className="overflow-y-auto max-h-[calc(70vh-20px)]">
                <SharedSidebar />
              </div>
            </div>
            {/* Mobile Menu Button - Bottom Right (hidden when drawer is open) */}
            {!sidebarOpen && (
              <button
                onClick={() => setSidebarOpen(true)}
                className="fixed bottom-6 right-6 z-50 p-3 bg-indigo-900 dark:bg-gray-800 text-white rounded-full shadow-lg md:hidden transition-opacity duration-300"
                aria-label="Toggle menu"
                style={{
                  width: '56px',
                  height: '56px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              </button>
            )}
          </>
        ) : (
          <SharedSidebar />
        )}
        <div className={`flex-1 flex flex-col overflow-auto bg-background ${isMobile ? 'w-full' : ''}`}>
          <Outlet />
        </div>
      </div>
    </ArrayContext.Provider>
  )
}

