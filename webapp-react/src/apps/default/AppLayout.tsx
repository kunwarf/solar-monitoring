/**
 * Default Application Layout
 * This is the layout for the default solar monitoring app
 * Updated to use hierarchy objects from the common API layer
 */

import React, { useState, useMemo } from 'react'
import { Outlet } from 'react-router-dom'
import { useMobile } from '../../hooks/useMobile'
import { useAllSystems } from '../../api/hooks/useHierarchyObjects'
import { SharedSidebar } from '../../components/SharedSidebar'
import { MobileBottomNav } from '../../components/MobileBottomNav'
import { ArrayInfo } from '../../types/telemetry'
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
  const systems = useAllSystems()
  const [selectedArray, setSelectedArray] = useState<string | null>(null)

  // Transform hierarchy objects to ArrayInfo format for backward compatibility
  const arrays: ArrayInfo[] = useMemo(() => {
    const arrayList: ArrayInfo[] = []
    
    systems.forEach(system => {
      system.inverterArrays.forEach(invArray => {
        arrayList.push({
          id: invArray.id,
          name: invArray.name,
          inverter_ids: invArray.inverters.map(inv => inv.id),
          inverter_count: invArray.inverters.length,
          attached_pack_ids: invArray.attachedBatteryArrayId 
            ? [invArray.attachedBatteryArrayId] 
            : [],
          pack_count: invArray.attachedBatteryArrayId ? 1 : 0,
        })
      })
    })
    
    return arrayList
  }, [systems])

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

