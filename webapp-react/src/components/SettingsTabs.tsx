import React from 'react'

interface SettingsTabsProps {
  tabs: { id: string; label: string; icon?: string }[]
  activeTab: string
  onTabChange: (tabId: string) => void
}

export const SettingsTabs: React.FC<SettingsTabsProps> = ({ tabs, activeTab, onTabChange }) => {
  return (
    <div className="mb-6">
      <div className="flex space-x-2 overflow-x-auto pb-1">
        {tabs.map((tab) => {
          const isActive = activeTab === tab.id
          return (
            <button
              key={tab.id}
              onClick={() => onTabChange(tab.id)}
              className={`
                px-6 py-3 text-sm font-medium whitespace-nowrap
                rounded-full transition-all duration-200
                ${
                  isActive
                    ? 'bg-blue-600 text-white shadow-sm'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200 hover:text-gray-700'
                }
              `}
              style={{
                borderRadius: '100px',
                fontWeight: isActive ? 500 : 400,
              }}
            >
              {tab.icon && <span className="mr-2">{tab.icon}</span>}
              {tab.label}
            </button>
          )
        })}
      </div>
    </div>
  )
}

