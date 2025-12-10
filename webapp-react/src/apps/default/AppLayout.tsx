/**
 * Default Application Layout
 * This is the layout for the default solar monitoring app
 */

import React, { useState, useEffect } from 'react'
import { Outlet } from 'react-router-dom'
import { useMobile } from '../../hooks/useMobile'
import { api } from '../../lib/api'
import { ArraysResponse, ArrayInfo } from '../../types/telemetry'
import { SharedSidebar } from '../../components/SharedSidebar'
import { MobileBottomNav } from '../../components/MobileBottomNav'
// Import main styles to get CSS variables for consistent theming
import '../../styles.css'

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
  const [arrays, setArrays] = useState<ArrayInfo[]>([])
  const [selectedArray, setSelectedArray] = useState<string | null>(null)

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
        {/* Show sidebar on desktop, hide on mobile */}
        <div className={isMobile ? 'hidden' : 'block'}>
          <SharedSidebar />
        </div>
        {/* Always render mobile bottom nav but hide on desktop */}
        <div className={isMobile ? 'block' : 'hidden'}>
          <MobileBottomNav />
        </div>
        <div className={`flex-1 flex flex-col overflow-auto bg-background ${isMobile ? 'w-full pb-20' : ''}`}>
          <Outlet />
        </div>
      </div>
    </ArrayContext.Provider>
  )
}

