import React, { useState, useEffect } from 'react'
import { useTheme } from '../contexts/ThemeContext'
import { api } from '../lib/api'
import { SettingsForm } from './SettingsForm'

interface TOUWindow {
  index: number
  type?: 'charge' | 'discharge' | 'auto'
  start_time: string
  end_time: string
  power_w: number
  target_soc_pct: number
  target_voltage_v?: number
}

interface TOUWindowCapabilities {
  max_windows: number
  bidirectional: boolean
  separate_charge_discharge: boolean
  max_charge_windows: number
  max_discharge_windows: number
}

interface TOUWindowGridProps {
  inverterId: string
  batteryOperation?: 'Voltage' | 'State of charge' | null
}

export const TOUWindowGrid: React.FC<TOUWindowGridProps> = ({ inverterId, batteryOperation }) => {
  const { theme } = useTheme()
  const [windows, setWindows] = useState<TOUWindow[]>([])
  const [capabilities, setCapabilities] = useState<TOUWindowCapabilities | null>(null)
  const [loading, setLoading] = useState(true)
  const [editingWindow, setEditingWindow] = useState<{ index: number; type?: string } | null>(null)
  const [saving, setSaving] = useState(false)

  const textColor = theme === 'dark' ? '#ffffff' : '#1f2937'
  const textSecondary = theme === 'dark' ? 'rgba(255, 255, 255, 0.7)' : '#6b7280'
  const cardBg = theme === 'dark' ? '#1f2937' : '#ffffff'
  const borderColor = theme === 'dark' ? '#4b5563' : '#e5e7eb'
  const innerBg = theme === 'dark' ? '#374151' : '#f9fafb'

  useEffect(() => {
    loadTOUWindows()
  }, [inverterId])

  const loadTOUWindows = async () => {
    try {
      setLoading(true)
      const response = await api.get(`/api/inverter/tou-windows?inverter_id=${inverterId}`) as any
      if (response.windows && response.capabilities) {
        setWindows(response.windows)
        setCapabilities(response.capabilities)
      }
    } catch (error) {
      console.error('Error loading TOU windows:', error)
      setWindows([])
      setCapabilities(null)
    } finally {
      setLoading(false)
    }
  }

  const handleSaveWindow = async (values: Record<string, any>) => {
    if (!editingWindow || !capabilities) return

    try {
      setSaving(true)
      
      const windowData = {
        inverter_id: inverterId,
        window_index: editingWindow.index,
        window_type: editingWindow.type || 'charge',
        start_time: values.start_time || '00:00',
        end_time: values.end_time || '00:00',
        power_w: parseInt(values.power_w) || 0,
        target_soc_pct: values.target_soc_pct ? parseInt(values.target_soc_pct) : (editingWindow ? windows.find(w => w.index === editingWindow.index && w.type === editingWindow.type)?.target_soc_pct || 100 : 100),
        ...(capabilities.bidirectional && {
          type: values.type || 'auto',
          target_voltage_v: values.target_voltage_v ? parseFloat(values.target_voltage_v) : (editingWindow ? windows.find(w => w.index === editingWindow.index && w.type === editingWindow.type)?.target_voltage_v || undefined : undefined)
        })
      }

      await api.post('/api/inverter/tou-windows', windowData)
      
      // Reload windows
      await loadTOUWindows()
      setEditingWindow(null)
      alert('TOU window updated successfully')
    } catch (error: any) {
      console.error('Error saving TOU window:', error)
      alert(`Failed to save TOU window: ${error.message || 'Unknown error'}`)
    } finally {
      setSaving(false)
    }
  }

  const getWindowTypeLabel = (window: TOUWindow): string => {
    if (capabilities?.bidirectional) {
      return window.type === 'auto' ? 'Auto' : window.type === 'charge' ? 'Charge' : 'Discharge'
    }
    return window.type === 'charge' ? 'Charge' : 'Discharge'
  }

  const getWindowTypeColor = (window: TOUWindow): { bg: string; border: string } => {
    if (capabilities?.bidirectional) {
      if (window.type === 'charge') {
        return {
          bg: theme === 'dark' ? '#1e3a5f' : '#dbeafe',
          border: theme === 'dark' ? '#3b82f6' : '#93c5fd'
        }
      }
      if (window.type === 'discharge') {
        return {
          bg: theme === 'dark' ? '#5a3410' : '#fed7aa',
          border: theme === 'dark' ? '#f97316' : '#fb923c'
        }
      }
      return {
        bg: theme === 'dark' ? '#374151' : '#f3f4f6',
        border: theme === 'dark' ? '#4b5563' : '#d1d5db'
      }
    }
    if (window.type === 'charge') {
      return {
        bg: theme === 'dark' ? '#1e3a5f' : '#dbeafe',
        border: theme === 'dark' ? '#3b82f6' : '#93c5fd'
      }
    }
    return {
      bg: theme === 'dark' ? '#5a3410' : '#fed7aa',
      border: theme === 'dark' ? '#f97316' : '#fb923c'
    }
  }

  if (loading) {
    return (
      <div 
        className="rounded-lg p-6"
        style={{
          backgroundColor: cardBg,
          border: `1px solid ${borderColor}`,
        }}
      >
        <div className="text-center" style={{ color: textSecondary }}>Loading TOU windows...</div>
      </div>
    )
  }

  if (!capabilities) {
    return (
      <div 
        className="rounded-lg p-6"
        style={{
          backgroundColor: cardBg,
          border: `1px solid ${borderColor}`,
        }}
      >
        <div className="text-center" style={{ color: textSecondary }}>No TOU window capabilities available</div>
      </div>
    )
  }

  return (
    <div 
      className="rounded-lg p-6"
      style={{
        backgroundColor: cardBg,
        border: `1px solid ${borderColor}`,
      }}
    >
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-semibold" style={{ color: textColor }}>Time of Use (TOU) Windows</h2>
          <p className="text-sm mt-1" style={{ color: textSecondary }}>
            {capabilities.bidirectional 
              ? `Bidirectional windows (up to ${capabilities.max_windows}) - Direction auto-determined by target SOC`
              : `Separate charge/discharge windows (${capabilities.max_charge_windows} charge, ${capabilities.max_discharge_windows} discharge)`}
          </p>
        </div>
      </div>

      {windows.length === 0 ? (
        <div className="text-center py-8" style={{ color: textSecondary }}>
          No TOU windows configured
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {windows.map((window) => {
            const isEditing = editingWindow?.index === window.index && editingWindow?.type === window.type
            const windowKey = `${window.index}-${window.type || 'charge'}`

            const windowColors = getWindowTypeColor(window)
            return (
              <div
                key={windowKey}
                className="border-2 rounded-lg p-4 transition-all hover:shadow-md"
                style={{
                  backgroundColor: windowColors.bg,
                  borderColor: windowColors.border,
                }}
              >
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <h3 className="font-semibold" style={{ color: textColor }}>
                      Window {window.index} {!capabilities.bidirectional && `(${getWindowTypeLabel(window)})`}
                    </h3>
                    {capabilities.bidirectional && (
                      <span className="text-xs" style={{ color: textSecondary }}>{getWindowTypeLabel(window)}</span>
                    )}
                  </div>
                  {!isEditing && (
                    <button
                      onClick={() => setEditingWindow({ index: window.index, type: window.type })}
                      className="text-xs hover:underline font-medium"
                      style={{ color: '#3b82f6' }}
                    >
                      edit
                    </button>
                  )}
                </div>

                {isEditing ? (
                  <SettingsForm
                    title={`Edit TOU Window ${window.index}`}
                    fields={([
                      {
                        key: 'start_time',
                        label: 'Start Time',
                        type: 'text' as const,
                        value: window.start_time,
                        description: 'Format: HH:MM (24-hour)'
                      },
                      {
                        key: 'end_time',
                        label: 'End Time',
                        type: 'text' as const,
                        value: window.end_time,
                        description: 'Format: HH:MM (24-hour)'
                      },
                      {
                        key: 'power_w',
                        label: 'Power',
                        type: 'number' as const,
                        value: window.power_w,
                        min: 0,
                        max: 10000,
                        step: 100,
                        unit: 'W',
                        description: 'Power for this window (charge or discharge)'
                      },
                      // Show target SOC only if battery operation is "State of charge"
                      ...(batteryOperation === 'State of charge' ? [{
                        key: 'target_soc_pct',
                        label: 'Target SOC',
                        type: 'number' as const,
                        value: window.target_soc_pct,
                        min: 0,
                        max: 100,
                        step: 1,
                        unit: '%',
                        description: 'Target battery state of charge'
                      }] : []),
                      // Show target voltage only if battery operation is "Voltage"
                      ...(batteryOperation === 'Voltage' ? [{
                        key: 'target_voltage_v',
                        label: 'Target Voltage',
                        type: 'number' as const,
                        value: window.target_voltage_v,
                        min: 0,
                        max: 100,
                        step: 0.1,
                        unit: 'V',
                        description: 'Target battery voltage'
                      }] : []),
                      ...(capabilities.bidirectional ? [
                        {
                          key: 'type',
                          label: 'Window Type',
                          type: 'select' as const,
                          options: [
                            { value: 'auto', label: 'Auto (determined by target SOC)' },
                            { value: 'charge', label: 'Charge' },
                            { value: 'discharge', label: 'Discharge' }
                          ],
                          value: window.type || 'auto',
                          description: 'Window direction (auto uses target SOC to determine)'
                        }
                      ] : [])
                    ] as any)}
                    onSave={handleSaveWindow}
                    onCancel={() => setEditingWindow(null)}
                    loading={saving}
                  />
                ) : (
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span style={{ color: textSecondary }}>Time:</span>
                      <span className="font-medium" style={{ color: textColor }}>{window.start_time} - {window.end_time}</span>
                    </div>
                    <div className="flex justify-between">
                      <span style={{ color: textSecondary }}>Power:</span>
                      <span className="font-medium" style={{ color: textColor }}>
                        {window.power_w >= 1000 
                          ? `${(window.power_w / 1000).toFixed(2)} kW`
                          : `${window.power_w} W`}
                      </span>
                    </div>
                    {/* Show target SOC only if battery operation is "State of charge" */}
                    {batteryOperation === 'State of charge' && (
                      <div className="flex justify-between">
                        <span style={{ color: textSecondary }}>Target SOC:</span>
                        <span className="font-medium" style={{ color: textColor }}>{window.target_soc_pct}%</span>
                      </div>
                    )}
                    {/* Show target voltage only if battery operation is "Voltage" */}
                    {batteryOperation === 'Voltage' && window.target_voltage_v && (
                      <div className="flex justify-between">
                        <span style={{ color: textSecondary }}>Target Voltage:</span>
                        <span className="font-medium" style={{ color: textColor }}>{window.target_voltage_v} V</span>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

