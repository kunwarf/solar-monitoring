import React, { useState, useEffect, useContext } from 'react'
import { TelemetryDashboard } from '../components/TelemetryDashboard'
import { FilterBar } from '../components/FilterBar'
import { ArrayContext } from '../ui/AppLayout'
import { useTheme } from '../contexts/ThemeContext'

export const TelemetryPage: React.FC = () => {
  const { selectedArray } = useContext(ArrayContext)
  const { theme } = useTheme()
  const [selectedInverter, setSelectedInverter] = useState<string>('all')

  // Theme-aware colors matching NewDashboardPage
  const bgColor = theme === 'dark' ? '#111827' : '#f9fafb' // gray-900 or gray-50
  const cardBg = theme === 'dark' ? '#1f2937' : '#ffffff' // gray-800 or white
  const borderColor = theme === 'dark' ? '#374151' : '#e5e7eb' // gray-700 or gray-200
  const textColor = theme === 'dark' ? '#ffffff' : '#1f2937' // white or gray-800
  const textSecondary = theme === 'dark' ? 'rgba(255, 255, 255, 0.7)' : '#6b7280' // gray-400

  return (
    <div 
      className="min-h-screen" 
      style={{ 
        minHeight: '100vh', 
        paddingBottom: '2rem',
        backgroundColor: bgColor
      }}
    >
      {/* Filter Bar */}
      <div 
        className="border-b"
        style={{
          backgroundColor: cardBg,
          borderColor: borderColor
        }}
      >
        <FilterBar
          showInverter={true}
          selectedInverter={selectedInverter}
          onInverterChange={setSelectedInverter}
        />
      </div>

      {/* Main Content */}
      <div className="p-6 pb-12">
        <div className="max-w-7xl mx-auto">
          <TelemetryDashboard
            inverterId={selectedInverter === 'all' ? 'all' : selectedInverter}
            refreshInterval={5000}
          />
        </div>
      </div>
    </div>
  )
}

