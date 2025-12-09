import React, { useState, useEffect } from 'react'
import { useTheme } from '../../../../contexts/ThemeContext'
import { SettingsForm } from '../../../SettingsForm'
import { api } from '../../../../lib/api'
import { Zap } from 'lucide-react'

interface InverterControlsCardProps {
  inverterId: string
  loading?: boolean
}

export const InverterControlsCard: React.FC<InverterControlsCardProps> = ({
  inverterId,
  loading = false
}) => {
  const { theme } = useTheme()
  const [sensors, setSensors] = useState<any[]>([])
  const [editingSensor, setEditingSensor] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [loadingSensors, setLoadingSensors] = useState(false)

  const textColor = theme === 'dark' ? '#ffffff' : '#1f2937'
  const textSecondary = theme === 'dark' ? 'rgba(255, 255, 255, 0.7)' : '#6b7280'
  const cardBg = theme === 'dark' ? '#374151' : '#f3f4f6'
  const borderColor = theme === 'dark' ? '#4b5563' : '#d1d5db'
  const innerBg = theme === 'dark' ? '#1f2937' : '#ffffff'

  useEffect(() => {
    const fetchSensors = async () => {
      if (!inverterId || inverterId === 'all') return
      setLoadingSensors(true)
      try {
        const sensorsRes = await api.get(`/api/inverter/sensors?inverter_id=${inverterId}`)
        if (sensorsRes?.sensors) {
          setSensors(sensorsRes.sensors)
        }
      } catch (e) {
        console.error('Error loading sensors:', e)
      } finally {
        setLoadingSensors(false)
      }
    }
    fetchSensors()
  }, [inverterId])

  const handleSensorSave = async (values: any) => {
    if (!editingSensor) return
    setSaving(true)
    try {
      await api.post(`/api/inverter/sensors/${editingSensor}`, {
        inverter_id: inverterId,
        value: values.value
      })
      setEditingSensor(null)
      // Reload sensors
      const sensorsRes = await api.get(`/api/inverter/sensors?inverter_id=${inverterId}`)
      if (sensorsRes?.sensors) {
        setSensors(sensorsRes.sensors)
      }
    } catch (error: any) {
      alert(`Failed to save: ${error?.message || error}`)
      throw error
    } finally {
      setSaving(false)
    }
  }

  if (loading || loadingSensors) {
    return (
      <div 
        className="p-6 rounded-lg"
        style={{
          backgroundColor: cardBg,
          border: `1px solid ${borderColor}`,
        }}
      >
        <div className="text-center" style={{ color: textSecondary }}>
          Loading inverter controls...
        </div>
      </div>
    )
  }

  if (sensors.length === 0) {
    return null
  }

  return (
    <div 
      className="p-6 rounded-lg"
      style={{
        backgroundColor: cardBg,
        border: `1px solid ${borderColor}`,
      }}
    >
      <div className="flex items-center gap-3 mb-4">
        <Zap className="w-5 h-5" style={{ color: textColor }} />
        <div>
          <h3 className="font-semibold" style={{ color: textColor }}>Inverter Controls</h3>
          <p className="text-sm" style={{ color: textSecondary }}>
            Direct control of inverter parameters
          </p>
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {sensors.map(sensor => (
          <div 
            key={sensor.id} 
            className="p-4 rounded-lg"
            style={{
              backgroundColor: innerBg,
              border: `1px solid ${borderColor}`,
            }}
          >
            <div className="flex items-center justify-between mb-3">
              <h4 className="font-semibold" style={{ color: textColor }}>{sensor.name}</h4>
              {editingSensor !== sensor.id && (
                <button
                  onClick={() => setEditingSensor(sensor.id)}
                  className="text-sm font-medium hover:underline"
                  style={{ color: '#3b82f6' }}
                >
                  Edit
                </button>
              )}
            </div>
            
            {editingSensor === sensor.id ? (
              <SettingsForm
                title={`Edit ${sensor.name}`}
                fields={[{
                  key: 'value',
                  label: sensor.name,
                  type: sensor.type,
                  value: sensor.current_value,
                  options: sensor.options,
                  min: sensor.min,
                  max: sensor.max,
                  step: sensor.step,
                  unit: sensor.unit,
                  description: sensor.description
                }]}
                onSave={handleSensorSave}
                onCancel={() => setEditingSensor(null)}
                loading={saving}
              />
            ) : (
              <div>
                <div className="mb-2">
                  <span className="text-xs" style={{ color: textSecondary }}>Current: </span>
                  <span className="text-sm font-semibold" style={{ color: textColor }}>
                    {sensor.type === 'boolean'
                      ? (sensor.current_value ? 'Enabled' : 'Disabled')
                      : `${sensor.current_value}${sensor.unit ? ' ' + sensor.unit : ''}`}
                  </span>
                </div>
                {sensor.description && (
                  <p className="text-xs" style={{ color: textSecondary }}>{sensor.description}</p>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

