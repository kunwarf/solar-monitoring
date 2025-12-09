import React, { useState, useEffect } from 'react'
import { useTheme } from '../../contexts/ThemeContext'
import { api } from '../../lib/api'
import { SenergySettingsPage } from './inverter/pages/SenergySettingsPage'
import { PowdriveSettingsPage } from './inverter/pages/PowdriveSettingsPage'

interface InverterConfigWizardProps {
  config: any
  onSave: (values: any) => Promise<void>
  saving?: boolean
}

export const InverterConfigWizard: React.FC<InverterConfigWizardProps> = ({
  config,
  onSave,
  saving = false
}) => {
  const { theme } = useTheme()
  const [selectedInverter, setSelectedInverter] = useState<string>('all')
  const [inverters, setInverters] = useState<string[]>([])
  const [inverterType, setInverterType] = useState<string | null>(null)
  const [loadingType, setLoadingType] = useState(false)

  const textColor = theme === 'dark' ? '#ffffff' : '#1f2937'
  const textSecondary = theme === 'dark' ? 'rgba(255, 255, 255, 0.7)' : '#6b7280'
  const cardBg = theme === 'dark' ? '#374151' : '#f3f4f6'
  const borderColor = theme === 'dark' ? '#4b5563' : '#d1d5db'

  useEffect(() => {
    const fetchInverters = async () => {
      try {
        const resp: any = await api.get('/api/inverters')
        const ids: string[] = Array.isArray(resp?.inverters) 
          ? resp.inverters.map((inv: any) => typeof inv === 'string' ? inv : (inv.id || inv))
          : []
        setInverters(ids)
        if (ids.length > 0 && selectedInverter === 'all') {
          setSelectedInverter(ids[0])
        }
      } catch (e) {
        console.error('Error loading inverters:', e)
      }
    }
    fetchInverters()
  }, [])

  useEffect(() => {
    const fetchInverterType = async () => {
      if (!selectedInverter || selectedInverter === 'all') {
        setInverterType(null)
        return
      }
      
      setLoadingType(true)
      try {
        const capabilitiesRes = await api.get(`/api/inverter/capabilities?inverter_id=${selectedInverter}`)
        const adapterType = capabilitiesRes?.capabilities?.adapter_type
        setInverterType(adapterType || null)
      } catch (e) {
        console.error('Error loading inverter type:', e)
        setInverterType(null)
      } finally {
        setLoadingType(false)
      }
    }
    fetchInverterType()
  }, [selectedInverter])

  const renderSettingsPage = () => {
    if (!selectedInverter || selectedInverter === 'all' || loadingType) {
      return (
        <div className="text-center py-8" style={{ color: textSecondary }}>
          {loadingType ? 'Loading inverter type...' : 'Please select an inverter'}
        </div>
      )
    }

    switch (inverterType) {
      case 'senergy':
        return <SenergySettingsPage inverterId={selectedInverter} />
      case 'powdrive':
        return <PowdriveSettingsPage inverterId={selectedInverter} />
      default:
        // Fallback: try to infer from capabilities
        return (
          <div className="text-center py-8" style={{ color: textSecondary }}>
            Unknown inverter type. Please check inverter configuration.
          </div>
        )
    }
  }

  return (
    <div className="space-y-6">
      {/* Inverter Selector */}
      {inverters.length > 0 && (
        <div 
          className="p-4 rounded-lg"
          style={{
            backgroundColor: cardBg,
            border: `1px solid ${borderColor}`,
          }}
        >
          <label className="block text-sm font-medium mb-2" style={{ color: textColor }}>
            Select Inverter
          </label>
          <select
            value={selectedInverter}
            onChange={(e) => setSelectedInverter(e.target.value)}
            className="w-full px-3 py-2 rounded-lg text-sm"
            style={{
              backgroundColor: theme === 'dark' ? '#1f2937' : '#ffffff',
              color: textColor,
              border: `1px solid ${borderColor}`,
            }}
          >
            <option value="all">All Inverters</option>
            {inverters.map(id => (
              <option key={id} value={id}>{id}</option>
            ))}
          </select>
        </div>
      )}

      {/* Type-specific Settings Page */}
      {renderSettingsPage()}
    </div>
  )
}
