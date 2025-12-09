import React, { useContext, useEffect, useState } from 'react'
import { api } from '../lib/api'
import { ArrayContext } from '../ui/AppLayout'
import { useTheme } from '../contexts/ThemeContext'

interface FilterBarProps {
  showViewMode?: boolean // Show array/inverter view mode toggle (for dashboard)
  showInverter?: boolean // Show inverter selector
  selectedInverter?: string
  onInverterChange?: (inverterId: string) => void
  viewMode?: 'inverter' | 'array'
  onViewModeChange?: (mode: 'inverter' | 'array') => void
  showDate?: boolean // Show date filter
  selectedDate?: string // Selected date in YYYY-MM-DD format
  onDateChange?: (date: string) => void // Callback when date changes
}

export const FilterBar: React.FC<FilterBarProps> = ({
  showViewMode = false,
  showInverter = false,
  selectedInverter,
  onInverterChange,
  viewMode,
  onViewModeChange,
  showDate = false,
  selectedDate,
  onDateChange
}) => {
  const { theme } = useTheme()
  const { selectedArray, arrays, setSelectedArray } = useContext(ArrayContext)
  const [inverters, setInverters] = useState<string[]>([])
  const [filteredInverters, setFilteredInverters] = useState<string[]>([])

  // Theme-aware colors matching NewDashboardPage
  const bgColor = theme === 'dark' ? '#1f2937' : '#ffffff' // gray-800 or white
  const borderColor = theme === 'dark' ? '#374151' : '#e5e7eb' // gray-700 or gray-200
  const textColor = theme === 'dark' ? '#ffffff' : '#1f2937' // white or gray-800
  const textSecondary = theme === 'dark' ? 'rgba(255, 255, 255, 0.7)' : '#6b7280' // gray-400
  const selectBg = theme === 'dark' ? '#374151' : '#ffffff' // gray-700 or white
  const selectBorder = theme === 'dark' ? '#4b5563' : '#d1d5db' // gray-600 or gray-300

  useEffect(() => {
    const fetchInverters = async () => {
      try {
        const resp: any = await api.get('/api/inverters')
        const ids: string[] = Array.isArray(resp?.inverters) 
          ? resp.inverters.map((inv: any) => typeof inv === 'string' ? inv : (inv.id || inv))
          : []
        setInverters(ids)
      } catch (e) {
        console.error('Error loading inverters:', e)
        setInverters([])
      }
    }
    fetchInverters()
  }, [])

  useEffect(() => {
    // Filter inverters by selected array
    if (selectedArray && arrays.length > 0) {
      const selectedArrayInfo = arrays.find(a => a.id === selectedArray)
      if (selectedArrayInfo) {
        const filtered = inverters.filter(id => selectedArrayInfo.inverter_ids.includes(id))
        setFilteredInverters(filtered)
      } else {
        setFilteredInverters(inverters)
      }
    } else {
      setFilteredInverters(inverters)
    }
  }, [selectedArray, arrays, inverters])

  const displayInverters = filteredInverters.length > 0 ? filteredInverters : inverters

  return (
    <div 
      className="border-b px-2 sm:px-4 py-2 sm:py-3 shadow-sm overflow-x-auto"
      style={{
        backgroundColor: bgColor,
        borderColor: borderColor,
      }}
    >
      <div className="flex items-center gap-2 sm:gap-4 flex-wrap min-w-max">
        {/* Array Filter */}
        {arrays.length > 0 && (
          <div className="flex items-center gap-2">
            <label 
              className="text-xs sm:text-sm font-medium whitespace-nowrap"
              style={{ color: textColor }}
            >
              Array:
            </label>
            <select
              className="px-2 sm:px-3 py-1 sm:py-1.5 border rounded-lg text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              style={{
                backgroundColor: selectBg,
                borderColor: selectBorder,
                color: textColor,
              }}
              value={selectedArray || ''}
              onChange={(e) => setSelectedArray(e.target.value || null)}
            >
              <option value="">All Arrays</option>
              {arrays.map(arr => (
                <option key={arr.id} value={arr.id}>
                  {arr.name || arr.id} ({arr.inverter_count} inverters)
                </option>
              ))}
            </select>
          </div>
        )}

        {/* View Mode Toggle (for dashboard) */}
        {showViewMode && selectedArray && (
          <div className="flex items-center gap-2">
            <label 
              className="text-xs sm:text-sm font-medium whitespace-nowrap"
              style={{ color: textColor }}
            >
              View:
            </label>
            <select
              className="px-2 sm:px-3 py-1 sm:py-1.5 border rounded-lg text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              style={{
                backgroundColor: selectBg,
                borderColor: selectBorder,
                color: textColor,
              }}
              value={viewMode || 'inverter'}
              onChange={(e) => onViewModeChange?.(e.target.value as 'inverter' | 'array')}
            >
              <option value="array">Array View</option>
              <option value="inverter">Inverter View</option>
            </select>
          </div>
        )}

        {/* Inverter Selector */}
        {showInverter && (viewMode !== 'array' || !showViewMode) && (
          <div className="flex items-center gap-2">
            <label 
              className="text-xs sm:text-sm font-medium whitespace-nowrap"
              style={{ color: textColor }}
            >
              Inverter:
            </label>
            <select
              className="px-2 sm:px-3 py-1 sm:py-1.5 border rounded-lg text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              style={{
                backgroundColor: selectBg,
                borderColor: selectBorder,
                color: textColor,
              }}
              value={selectedInverter || 'all'}
              onChange={(e) => onInverterChange?.(e.target.value)}
            >
              <option value="all">All Inverters</option>
              {displayInverters.map(id => (
                <option key={id} value={id}>{id}</option>
              ))}
            </select>
          </div>
        )}

        {/* Date Filter */}
        {showDate && (
          <div className="flex items-center gap-2">
            <label 
              className="text-xs sm:text-sm font-medium whitespace-nowrap"
              style={{ color: textColor }}
            >
              Date:
            </label>
            <input
              type="date"
              className="px-2 sm:px-3 py-1 sm:py-1.5 border rounded-lg text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              style={{
                backgroundColor: selectBg,
                borderColor: selectBorder,
                color: textColor,
              }}
              value={selectedDate || new Date().toISOString().split('T')[0]}
              onChange={(e) => onDateChange?.(e.target.value)}
              max={new Date().toISOString().split('T')[0]} // Don't allow future dates
            />
          </div>
        )}

        {/* Filter Status Indicator */}
        {(selectedArray || (selectedInverter && selectedInverter !== 'all')) && (
          <div 
            className="ml-auto text-[10px] sm:text-xs flex items-center gap-1 sm:gap-2 flex-wrap"
            style={{ color: textSecondary }}
          >
            {selectedArray && (
              <span 
                className="inline-flex items-center gap-1 px-1.5 sm:px-2 py-0.5 sm:py-1 rounded text-[10px] sm:text-xs"
                style={{
                  backgroundColor: theme === 'dark' ? '#1e3a8a' : '#dbeafe',
                  color: theme === 'dark' ? '#93c5fd' : '#1e40af',
                }}
              >
                Array: {arrays.find(a => a.id === selectedArray)?.name || selectedArray}
              </span>
            )}
            {selectedInverter && selectedInverter !== 'all' && (
              <span 
                className="inline-flex items-center gap-1 px-1.5 sm:px-2 py-0.5 sm:py-1 rounded text-[10px] sm:text-xs"
                style={{
                  backgroundColor: theme === 'dark' ? '#14532d' : '#dcfce7',
                  color: theme === 'dark' ? '#86efac' : '#166534',
                }}
              >
                Inverter: {selectedInverter}
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

