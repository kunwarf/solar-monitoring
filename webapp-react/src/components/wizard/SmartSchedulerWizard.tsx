import React, { useState, useEffect } from 'react'
import { useTheme } from '../../contexts/ThemeContext'
import { SettingsForm } from '../SettingsForm'
import { Cloud, Settings as SettingsIcon } from 'lucide-react'

interface SmartSchedulerWizardProps {
  config: any
  onSave: (values: any, section: 'forecast' | 'policy') => Promise<void>
  saving?: boolean
  step?: 'forecast' | 'policy'
}

export const SmartSchedulerWizard: React.FC<SmartSchedulerWizardProps> = ({
  config,
  onSave,
  saving = false,
  step
}) => {
  const { theme } = useTheme()
  const [editingSection, setEditingSection] = useState<'forecast' | 'policy' | null>(step || null)

  useEffect(() => {
    // Set editing section based on step prop
    if (step) {
      setEditingSection(step)
    }
  }, [step])

  const textColor = theme === 'dark' ? '#ffffff' : '#1f2937'
  const textSecondary = theme === 'dark' ? 'rgba(255, 255, 255, 0.7)' : '#6b7280'
  const cardBg = theme === 'dark' ? '#374151' : '#f3f4f6'
  const borderColor = theme === 'dark' ? '#4b5563' : '#d1d5db'

  const fmt = (val: any, unit?: string) => {
    if (val === null || val === undefined) return '—'
    return unit ? `${val} ${unit}` : String(val)
  }

  const fmtPower = (w?: number) => {
    if (!w) return '—'
    if (w >= 1000) return `${(w / 1000).toFixed(2)} kW`
    return `${w} W`
  }

  // Render content based on step
  const renderContent = () => {
    if (step === 'forecast') {
      return (
        <>
          <div>
            <h2 className="text-2xl font-bold mb-2" style={{ color: textColor }}>
              Forecast Settings
            </h2>
            <p className="text-sm" style={{ color: textSecondary }}>
              Weather forecast and solar generation prediction
            </p>
          </div>
          {/* Forecast Settings */}
          <div 
            className="p-6 rounded-lg"
            style={{
              backgroundColor: cardBg,
              border: `1px solid ${borderColor}`,
            }}
          >
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <Cloud className="w-5 h-5" style={{ color: textColor }} />
                <div>
                  <h3 className="font-semibold" style={{ color: textColor }}>Forecast Settings</h3>
                  <p className="text-sm" style={{ color: textSecondary }}>
                    Weather forecast and solar generation prediction
                  </p>
                </div>
              </div>
              <button
                onClick={() => setEditingSection('forecast')}
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

            {editingSection === 'forecast' ? (
              <SettingsForm
                title="Forecast Configuration"
                fields={[
                  {
                    key: 'enabled',
                    label: 'Forecast Enabled',
                    type: 'boolean',
                    value: config?.smart?.forecast?.enabled || false,
                    description: 'Enable solar forecasting'
                  },
                  {
                    key: 'provider',
                    label: 'Weather Provider',
                    type: 'select',
                    options: [
                      { value: 'naive', label: 'Naive' },
                      { value: 'openmeteo', label: 'OpenMeteo' },
                      { value: 'weatherapi', label: 'WeatherAPI' },
                      { value: 'openweather', label: 'OpenWeather' },
                      { value: 'simple', label: 'Simple' }
                    ],
                    value: config?.smart?.forecast?.provider || 'openweather',
                    description: 'Weather forecast provider'
                  },
                  {
                    key: 'batt_capacity_kwh',
                    label: 'Battery Capacity',
                    type: 'number',
                    value: config?.smart?.forecast?.batt_capacity_kwh || 20,
                    min: 1,
                    max: 1000,
                    step: 0.1,
                    unit: 'kWh',
                    description: 'Total battery capacity in kWh'
                  },
                  {
                    key: 'weatherapi_key',
                    label: 'WeatherAPI Key',
                    type: 'text',
                    value: config?.smart?.forecast?.weatherapi_key || '',
                    description: 'API key for WeatherAPI.com (if using weatherapi provider)'
                  },
                  {
                    key: 'openweather_key',
                    label: 'OpenWeather Key',
                    type: 'text',
                    value: config?.smart?.forecast?.openweather_key || '',
                    description: 'API key for OpenWeatherMap (if using openweather provider)'
                  }
                ]}
                onSave={(values) => onSave(values, 'forecast')}
                onCancel={() => setEditingSection(null)}
                loading={saving}
              />
            ) : (
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <div>
                  <div className="text-xs mb-1" style={{ color: textSecondary }}>Enabled</div>
                  <div className="font-medium" style={{ color: textColor }}>
                    {config?.smart?.forecast?.enabled ? 'Yes' : 'No'}
                  </div>
                </div>
                <div>
                  <div className="text-xs mb-1" style={{ color: textSecondary }}>Provider</div>
                  <div className="font-medium" style={{ color: textColor }}>
                    {config?.smart?.forecast?.provider || '—'}
                  </div>
                </div>
                <div>
                  <div className="text-xs mb-1" style={{ color: textSecondary }}>Battery Capacity</div>
                  <div className="font-medium" style={{ color: textColor }}>
                    {fmt(config?.smart?.forecast?.batt_capacity_kwh, 'kWh')}
                  </div>
                </div>
              </div>
            )}
          </div>
        </>
      )
    }

    if (step === 'policy') {
      return (
        <>
          <div>
            <h2 className="text-2xl font-bold mb-2" style={{ color: textColor }}>
              Policy Settings
            </h2>
            <p className="text-sm" style={{ color: textSecondary }}>
              Smart scheduler behavior and battery management policies
            </p>
          </div>
          {/* Policy Settings */}
          <div 
            className="p-6 rounded-lg"
            style={{
              backgroundColor: cardBg,
              border: `1px solid ${borderColor}`,
            }}
          >
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <SettingsIcon className="w-5 h-5" style={{ color: textColor }} />
                <div>
                  <h3 className="font-semibold" style={{ color: textColor }}>Policy Settings</h3>
                  <p className="text-sm" style={{ color: textSecondary }}>
                    Smart scheduler behavior and battery management policies
                  </p>
                </div>
              </div>
              <button
                onClick={() => setEditingSection('policy')}
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

            {editingSection === 'policy' ? (
              <SettingsForm
                title="Policy Configuration"
                fields={[
                  {
                    key: 'enabled',
                    label: 'Smart Scheduler Enabled',
                    type: 'boolean',
                    value: config?.smart?.policy?.enabled || false,
                    description: 'Enable or disable the smart scheduler'
                  },
                  {
                    key: 'target_full_before_sunset',
                    label: 'Target Full Before Sunset',
                    type: 'boolean',
                    value: config?.smart?.policy?.target_full_before_sunset || false,
                    description: 'Try to reach full charge before sunset'
                  },
                  {
                    key: 'overnight_min_soc_pct',
                    label: 'Overnight Minimum SOC',
                    type: 'number',
                    value: config?.smart?.policy?.overnight_min_soc_pct || 30,
                    min: 0,
                    max: 100,
                    unit: '%',
                    description: 'Minimum battery SOC to maintain overnight'
                  },
                  {
                    key: 'blackout_reserve_soc_pct',
                    label: 'Blackout Reserve SOC',
                    type: 'number',
                    value: config?.smart?.policy?.blackout_reserve_soc_pct || 30,
                    min: 0,
                    max: 100,
                    unit: '%',
                    description: 'SOC reserve for blackout situations'
                  },
                  {
                    key: 'max_charge_power_w',
                    label: 'Maximum Charge Power',
                    type: 'number',
                    value: config?.smart?.policy?.max_charge_power_w || 5000,
                    min: 0,
                    max: 10000,
                    step: 100,
                    unit: 'W',
                    description: 'Maximum battery charging power'
                  },
                  {
                    key: 'max_discharge_power_w',
                    label: 'Maximum Discharge Power',
                    type: 'number',
                    value: config?.smart?.policy?.max_discharge_power_w || 5000,
                    min: 0,
                    max: 10000,
                    step: 100,
                    unit: 'W',
                    description: 'Maximum battery discharging power'
                  },
                  {
                    key: 'primary_mode',
                    label: 'Primary Mode',
                    type: 'select',
                    options: [
                      { value: 'self_use', label: 'Self Use' },
                      { value: 'time_based', label: 'Time Based' }
                    ],
                    value: config?.smart?.policy?.primary_mode || 'self_use',
                    description: 'Primary operating mode'
                  }
                ]}
                onSave={(values) => onSave(values, 'policy')}
                onCancel={() => setEditingSection(null)}
                loading={saving}
              />
            ) : (
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <div>
                  <div className="text-xs mb-1" style={{ color: textSecondary }}>Enabled</div>
                  <div className="font-medium" style={{ color: textColor }}>
                    {config?.smart?.policy?.enabled ? 'Yes' : 'No'}
                  </div>
                </div>
                <div>
                  <div className="text-xs mb-1" style={{ color: textSecondary }}>Overnight Min SOC</div>
                  <div className="font-medium" style={{ color: textColor }}>
                    {fmt(config?.smart?.policy?.overnight_min_soc_pct, '%')}
                  </div>
                </div>
                <div>
                  <div className="text-xs mb-1" style={{ color: textSecondary }}>Max Charge Power</div>
                  <div className="font-medium" style={{ color: textColor }}>
                    {fmtPower(config?.smart?.policy?.max_charge_power_w)}
                  </div>
                </div>
                <div>
                  <div className="text-xs mb-1" style={{ color: textSecondary }}>Primary Mode</div>
                  <div className="font-medium" style={{ color: textColor }}>
                    {config?.smart?.policy?.primary_mode || '—'}
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
          Smart Scheduler Settings
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

