import React, { useState, useEffect } from 'react'
import { useTheme } from '../../contexts/ThemeContext'
import { SettingsForm } from '../SettingsForm'
import { api } from '../../lib/api'
import { MapPin, Clock, Wifi } from 'lucide-react'

interface SystemSettingsWizardProps {
  config: any
  onSave: (values: any, section?: string) => Promise<void>
  saving?: boolean
  step?: 'location' | 'timezone' | 'mqtt'
}

export const SystemSettingsWizard: React.FC<SystemSettingsWizardProps> = ({
  config,
  onSave,
  saving = false,
  step
}) => {
  const { theme } = useTheme()
  const [location, setLocation] = useState<{ lat: number; lon: number } | null>(null)
  const [locationLoading, setLocationLoading] = useState(false)
  const [editingSection, setEditingSection] = useState<'location' | 'timezone' | 'mqtt' | null>(step || null)

  const textColor = theme === 'dark' ? '#ffffff' : '#1f2937'
  const textSecondary = theme === 'dark' ? 'rgba(255, 255, 255, 0.7)' : '#6b7280'
  const cardBg = theme === 'dark' ? '#374151' : '#f3f4f6'
  const borderColor = theme === 'dark' ? '#4b5563' : '#d1d5db'

  // Auto-detect location
  const detectLocation = async () => {
    setLocationLoading(true)
    try {
      if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
          (position) => {
            setLocation({
              lat: position.coords.latitude,
              lon: position.coords.longitude
            })
            setLocationLoading(false)
          },
          (error) => {
            console.error('Error getting location:', error)
            setLocationLoading(false)
          }
        )
      } else {
        alert('Geolocation is not supported by your browser')
        setLocationLoading(false)
      }
    } catch (error) {
      console.error('Error detecting location:', error)
      setLocationLoading(false)
    }
  }

  useEffect(() => {
    // Try to get location from config if available
    if (config?.smart?.forecast?.lat && config?.smart?.forecast?.lon) {
      setLocation({
        lat: config.smart.forecast.lat,
        lon: config.smart.forecast.lon
      })
    }
  }, [config])

  useEffect(() => {
    // Set editing section based on step prop
    if (step) {
      setEditingSection(step)
    }
  }, [step])

  const handleSave = async (values: any, section: string) => {
    if (section === 'location' && location) {
      values.lat = location.lat
      values.lon = location.lon
    }
    await onSave(values, section)
    setEditingSection(null)
  }

  // Render content based on step
  const renderContent = () => {
    if (step === 'location') {
      return (
        <>
          <div>
            <h2 className="text-2xl font-bold mb-2" style={{ color: textColor }}>
              Location Settings
            </h2>
            <p className="text-sm" style={{ color: textSecondary }}>
              Configure system location coordinates for weather and timezone detection
            </p>
          </div>
          {/* Location Settings */}
          <div 
            className="p-6 rounded-lg"
            style={{
              backgroundColor: cardBg,
              border: `1px solid ${borderColor}`,
            }}
          >
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <MapPin className="w-5 h-5" style={{ color: textColor }} />
                <div>
                  <h3 className="font-semibold" style={{ color: textColor }}>Location</h3>
                  <p className="text-sm" style={{ color: textSecondary }}>
                    System location for weather and timezone detection
                  </p>
                </div>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={detectLocation}
                  disabled={locationLoading}
                  className="px-4 py-2 text-sm rounded-lg font-medium transition-colors"
                  style={{
                    backgroundColor: theme === 'dark' ? '#1f2937' : '#ffffff',
                    color: textColor,
                    border: `1px solid ${borderColor}`,
                  }}
                >
                  {locationLoading ? 'Detecting...' : 'Auto-Detect'}
                </button>
                <button
                  onClick={() => setEditingSection('location')}
                  className="px-4 py-2 text-sm rounded-lg font-medium transition-colors"
                  style={{
                    backgroundColor: theme === 'dark' ? '#1f2937' : '#ffffff',
                    color: textColor,
                    border: `1px solid ${borderColor}`,
                  }}
                >
                  Edit
                </button>
              </div>
            </div>

            {editingSection === 'location' ? (
              <SettingsForm
                title="Location Settings"
                fields={[
                  {
                    key: 'lat',
                    label: 'Latitude',
                    type: 'number',
                    value: location?.lat || config?.smart?.forecast?.lat || 0,
                    min: -90,
                    max: 90,
                    step: 0.0001,
                    description: 'Latitude coordinate (-90 to 90)'
                  },
                  {
                    key: 'lon',
                    label: 'Longitude',
                    type: 'number',
                    value: location?.lon || config?.smart?.forecast?.lon || 0,
                    min: -180,
                    max: 180,
                    step: 0.0001,
                    description: 'Longitude coordinate (-180 to 180)'
                  }
                ]}
                onSave={(values) => handleSave(values, 'location')}
                onCancel={() => setEditingSection(null)}
                loading={saving}
              />
            ) : (
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-xs mb-1" style={{ color: textSecondary }}>Latitude</div>
                  <div className="font-medium" style={{ color: textColor }}>
                    {location?.lat?.toFixed(6) || config?.smart?.forecast?.lat?.toFixed(6) || 'Not set'}
                  </div>
                </div>
                <div>
                  <div className="text-xs mb-1" style={{ color: textSecondary }}>Longitude</div>
                  <div className="font-medium" style={{ color: textColor }}>
                    {location?.lon?.toFixed(6) || config?.smart?.forecast?.lon?.toFixed(6) || 'Not set'}
                  </div>
                </div>
              </div>
            )}
          </div>
        </>
      )
    }

    if (step === 'timezone') {
      return (
        <>
          <div>
            <h2 className="text-2xl font-bold mb-2" style={{ color: textColor }}>
              Timezone Settings
            </h2>
            <p className="text-sm" style={{ color: textSecondary }}>
              Configure system timezone for scheduling and reporting
            </p>
          </div>
          {/* Timezone Settings */}
          <div 
            className="p-6 rounded-lg"
            style={{
              backgroundColor: cardBg,
              border: `1px solid ${borderColor}`,
            }}
          >
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <Clock className="w-5 h-5" style={{ color: textColor }} />
                <div>
                  <h3 className="font-semibold" style={{ color: textColor }}>Timezone</h3>
                  <p className="text-sm" style={{ color: textSecondary }}>
                    System timezone for scheduling and reporting
                  </p>
                </div>
              </div>
              <button
                onClick={() => setEditingSection('timezone')}
                className="px-4 py-2 text-sm rounded-lg font-medium transition-colors"
                style={{
                  backgroundColor: theme === 'dark' ? '#1f2937' : '#ffffff',
                  color: textColor,
                  border: `1px solid ${borderColor}`,
                }}
              >
                Edit
              </button>
            </div>

            {editingSection === 'timezone' ? (
              <SettingsForm
                title="Timezone Settings"
                fields={[{
                  key: 'timezone',
                  label: 'Timezone',
                  type: 'text',
                  value: config?.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone,
                  description: 'System timezone (e.g., Asia/Karachi, America/New_York)'
                }]}
                onSave={(values) => handleSave(values, 'timezone')}
                onCancel={() => setEditingSection(null)}
                loading={saving}
              />
            ) : (
              <div>
                <div className="text-xs mb-1" style={{ color: textSecondary }}>Current Timezone</div>
                <div className="font-medium" style={{ color: textColor }}>
                  {config?.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone}
                </div>
              </div>
            )}
          </div>
        </>
      )
    }

    if (step === 'mqtt') {
      return (
        <>
          <div>
            <h2 className="text-2xl font-bold mb-2" style={{ color: textColor }}>
              MQTT Configuration
            </h2>
            <p className="text-sm" style={{ color: textSecondary }}>
              Configure MQTT broker connection settings
            </p>
          </div>
          {/* MQTT Settings */}
          <div 
            className="p-6 rounded-lg"
            style={{
              backgroundColor: cardBg,
              border: `1px solid ${borderColor}`,
            }}
          >
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <Wifi className="w-5 h-5" style={{ color: textColor }} />
                <div>
                  <h3 className="font-semibold" style={{ color: textColor }}>MQTT Configuration</h3>
                  <p className="text-sm" style={{ color: textSecondary }}>
                    MQTT broker connection settings
                  </p>
                </div>
              </div>
              <button
                onClick={() => setEditingSection('mqtt')}
                className="px-4 py-2 text-sm rounded-lg font-medium transition-colors"
                style={{
                  backgroundColor: theme === 'dark' ? '#1f2937' : '#ffffff',
                  color: textColor,
                  border: `1px solid ${borderColor}`,
                }}
              >
                Edit
              </button>
            </div>

            {editingSection === 'mqtt' ? (
              <SettingsForm
                title="MQTT Configuration"
                fields={[
                  {
                    key: 'host',
                    label: 'MQTT Host',
                    type: 'text',
                    value: config?.mqtt?.host || '',
                    description: 'MQTT broker hostname or IP address'
                  },
                  {
                    key: 'port',
                    label: 'MQTT Port',
                    type: 'number',
                    value: config?.mqtt?.port || 1883,
                    min: 1,
                    max: 65535,
                    description: 'MQTT broker port number'
                  },
                  {
                    key: 'base_topic',
                    label: 'Base Topic',
                    type: 'text',
                    value: config?.mqtt?.base_topic || '',
                    description: 'Base MQTT topic for all messages'
                  },
                  {
                    key: 'client_id',
                    label: 'Client ID',
                    type: 'text',
                    value: config?.mqtt?.client_id || '',
                    description: 'MQTT client identifier'
                  },
                  {
                    key: 'ha_discovery',
                    label: 'Home Assistant Discovery',
                    type: 'boolean',
                    value: config?.mqtt?.ha_discovery || false,
                    description: 'Enable Home Assistant device discovery'
                  }
                ]}
                onSave={(values) => handleSave(values, 'mqtt')}
                onCancel={() => setEditingSection(null)}
                loading={saving}
              />
            ) : (
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-xs mb-1" style={{ color: textSecondary }}>Host</div>
                  <div className="font-medium" style={{ color: textColor }}>
                    {config?.mqtt?.host || 'Not configured'}
                  </div>
                </div>
                <div>
                  <div className="text-xs mb-1" style={{ color: textSecondary }}>Port</div>
                  <div className="font-medium" style={{ color: textColor }}>
                    {config?.mqtt?.port || '1883'}
                  </div>
                </div>
                <div>
                  <div className="text-xs mb-1" style={{ color: textSecondary }}>Base Topic</div>
                  <div className="font-medium" style={{ color: textColor }}>
                    {config?.mqtt?.base_topic || 'Not configured'}
                  </div>
                </div>
                <div>
                  <div className="text-xs mb-1" style={{ color: textSecondary }}>Client ID</div>
                  <div className="font-medium" style={{ color: textColor }}>
                    {config?.mqtt?.client_id || 'Not configured'}
                  </div>
                </div>
              </div>
            )}
          </div>
        </>
      )
    }

    return (
      <div>
        <h2 className="text-2xl font-bold mb-2" style={{ color: textColor }}>
          System Settings
        </h2>
        <p className="text-sm" style={{ color: textSecondary }}>
          Please select a configuration step
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {renderContent()}
    </div>
  )
}

