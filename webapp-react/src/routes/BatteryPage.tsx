import React, { useContext } from 'react'
import { BatteryBankView } from '../components/BatteryBankView'
import { FilterBar } from '../components/FilterBar'
import { useTheme } from '../contexts/ThemeContext'
import { ArrayContext } from '../ui/AppLayout'

export const BatteryPage: React.FC = () => {
  const { selectedArray, arrays } = useContext(ArrayContext)
  const { theme } = useTheme()
  
  // Theme-aware colors
  const pageBackgroundColor = theme === 'dark' ? '#1B2234' : '#F9FAFB'
  const cardBackgroundColor = theme === 'dark' 
    ? 'rgba(255, 255, 255, 0.08)' 
    : 'rgba(255, 255, 255, 1)'
  const boxShadowColor = theme === 'dark' 
    ? 'rgba(0, 0, 0, 0.08)' 
    : 'rgba(0, 0, 0, 0.1)'
  const borderColor = theme === 'dark' ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)'
  const textColor = theme === 'dark' ? '#FFFFFF' : '#1B2234'
  
  return (
    <div className="min-h-screen overflow-x-hidden" style={{ backgroundColor: pageBackgroundColor }}>
      {/* Unified Filter Bar */}
      <FilterBar />

      <section className="p-2 sm:p-4 md:p-6 max-w-7xl mx-auto w-full overflow-x-hidden">
        <div 
          className="mb-4 shadow-sm border-b p-3 sm:p-4 rounded-lg"
          style={{
            backgroundColor: cardBackgroundColor,
            boxShadow: `0px 4px 40px ${boxShadowColor}`,
            borderColor: borderColor,
          }}
        >
          <h1 className="text-xl sm:text-2xl font-bold" style={{ color: textColor }}>Battery Status</h1>
        </div>
        <BatteryBankView />
      </section>
    </div>
  )
}
