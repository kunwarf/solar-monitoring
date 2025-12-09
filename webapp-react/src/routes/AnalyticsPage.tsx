import React, { useContext } from 'react'
import { FilterBar } from '../components/FilterBar'
import { ArrayContext } from '../ui/AppLayout'

export const AnalyticsPage: React.FC = () => {
  const { selectedArray, arrays } = useContext(ArrayContext)
  
  return (
    <div className="bg-gray-50 min-h-screen overflow-x-hidden">
      {/* Unified Filter Bar */}
      <FilterBar />

      <section className="p-2 sm:p-4 md:p-6 max-w-7xl mx-auto w-full overflow-x-hidden">
        <div className="mb-4 bg-white shadow-sm border-b border-gray-200 p-3 sm:p-4 rounded-lg">
          <h1 className="text-xl sm:text-2xl font-bold text-gray-900">Analytics</h1>
        </div>
        <div className="bg-white rounded-lg shadow p-4 sm:p-6">
          <p className="text-sm sm:text-base text-gray-600">Historical charts and reports will go here.</p>
          {selectedArray && (
            <p className="text-xs sm:text-sm text-gray-500 mt-2">
              Array-specific analytics for <span className="font-semibold">{selectedArray}</span> will be displayed here.
            </p>
          )}
        </div>
      </section>
    </div>
  )
}

