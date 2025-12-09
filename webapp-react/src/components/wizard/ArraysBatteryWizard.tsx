import React, { useState } from 'react'
import { useTheme } from '../../contexts/ThemeContext'
import { DeviceManager } from '../DeviceManager'
import { HierarchyWizard } from './HierarchyWizard'
import { Layers, Battery, Home } from 'lucide-react'

interface ArraysBatteryWizardProps {
  config: any
  onSave?: (config: any) => void
  saving?: boolean
}

export const ArraysBatteryWizard: React.FC<ArraysBatteryWizardProps> = ({
  config,
  onSave,
  saving
}) => {
  const { theme } = useTheme()
  const [view, setView] = useState<'hierarchy' | 'devices'>('hierarchy')

  const textColor = theme === 'dark' ? '#ffffff' : '#1f2937'
  const textSecondary = theme === 'dark' ? 'rgba(255, 255, 255, 0.7)' : '#6b7280'
  const cardBg = theme === 'dark' ? '#374151' : '#f3f4f6'
  const borderColor = theme === 'dark' ? '#4b5563' : '#d1d5db'
  const buttonBg = theme === 'dark' ? '#4b5563' : '#e5e7eb'
  const activeButtonBg = theme === 'dark' ? '#3b82f6' : '#3b82f6'

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold mb-2" style={{ color: textColor }}>
          System Hierarchy & Device Management
        </h2>
        <p className="text-sm" style={{ color: textSecondary }}>
          Configure home, arrays, battery banks, and their relationships
        </p>
      </div>

      {/* View Toggle */}
      <div className="flex gap-2 mb-4">
        <button
          onClick={() => setView('hierarchy')}
          className="px-4 py-2 rounded-lg font-medium flex items-center gap-2"
          style={{
            backgroundColor: view === 'hierarchy' ? activeButtonBg : buttonBg,
            color: view === 'hierarchy' ? '#ffffff' : textColor,
          }}
        >
          <Home className="w-4 h-4" />
          Hierarchy Configuration
        </button>
        <button
          onClick={() => setView('devices')}
          className="px-4 py-2 rounded-lg font-medium flex items-center gap-2"
          style={{
            backgroundColor: view === 'devices' ? activeButtonBg : buttonBg,
            color: view === 'devices' ? '#ffffff' : textColor,
          }}
        >
          <Layers className="w-4 h-4" />
          Device Manager
        </button>
      </div>

      {view === 'hierarchy' ? (
        <HierarchyWizard config={config} onSave={onSave} saving={saving} />
      ) : (
        <div 
          className="p-6 rounded-lg"
          style={{
            backgroundColor: cardBg,
            border: `1px solid ${borderColor}`,
          }}
        >
          <DeviceManager />
        </div>
      )}
    </div>
  )
}

