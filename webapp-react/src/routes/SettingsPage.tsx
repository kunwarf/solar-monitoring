import React, { useState, useEffect } from 'react'
import { api } from '../lib/api'
import { SettingsWizard } from '../components/SettingsWizard'
import { SystemSettingsWizard } from '../components/wizard/SystemSettingsWizard'
import { SmartSchedulerWizard } from '../components/wizard/SmartSchedulerWizard'
import { ArraysBatteryWizard } from '../components/wizard/ArraysBatteryWizard'
import { InverterConfigWizard } from '../components/wizard/InverterConfigWizard'
import { useTheme } from '../contexts/ThemeContext'
import { Settings, Zap, Layers, Cloud, MapPin, Clock, Wifi, ChevronRight } from 'lucide-react'

interface Config {
  timezone?: string
  mqtt?: {
    host?: string
    port?: number
    base_topic?: string
    client_id?: string
    ha_discovery?: boolean
  }
  smart?: {
    forecast?: {
      enabled?: boolean
      provider?: string
      lat?: number
      lon?: number
      batt_capacity_kwh?: number
      weatherapi_key?: string
      openweather_key?: string
    }
    policy?: {
      enabled?: boolean
      target_full_before_sunset?: boolean
      overnight_min_soc_pct?: number
      blackout_reserve_soc_pct?: number
      max_charge_power_w?: number
      max_discharge_power_w?: number
      primary_mode?: string
    }
  }
}

export const SettingsPage: React.FC = () => {
  const { theme } = useTheme()
  const [config, setConfig] = useState<Config | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [currentStep, setCurrentStep] = useState(0)
  const [showWizard, setShowWizard] = useState(false)
  const [activeSection, setActiveSection] = useState<string | null>(null)

  // Section-specific step definitions
  const systemSteps = [
    {
      id: 'location',
      label: 'Location',
      description: 'System location coordinates',
      icon: <MapPin className="w-5 h-5" />
    },
    {
      id: 'timezone',
      label: 'Timezone',
      description: 'System timezone',
      icon: <Clock className="w-5 h-5" />
    },
    {
      id: 'mqtt',
      label: 'MQTT',
      description: 'MQTT broker connection',
      icon: <Wifi className="w-5 h-5" />
    }
  ]

  const schedulerSteps = [
    {
      id: 'forecast',
      label: 'Forecast',
      description: 'Weather forecast settings',
      icon: <Cloud className="w-5 h-5" />
    },
    {
      id: 'policy',
      label: 'Policy',
      description: 'Battery management policy',
      icon: <Settings className="w-5 h-5" />
    }
  ]

  const arraysSteps = [
    {
      id: 'arrays',
      label: 'Arrays & Battery',
      description: 'Device management',
      icon: <Layers className="w-5 h-5" />
    }
  ]

  const inverterSteps = [
    {
      id: 'inverter',
      label: 'Inverter Config',
      description: 'TOU & controls',
      icon: <Zap className="w-5 h-5" />
    }
  ]

  const getStepsForSection = (section: string) => {
    switch (section) {
      case 'system': return systemSteps
      case 'scheduler': return schedulerSteps
      case 'arrays': return arraysSteps
      case 'inverter': return inverterSteps
      default: return []
    }
  }

  const loadConfig = async () => {
    try {
      setLoading(true)
      const configRes = await api.get('/api/config').catch(() => null)
      if (configRes) {
        const configData = configRes.config || configRes
        setConfig(configData)
      }
      } catch (error) {
      console.error('Error loading config:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadConfig()
  }, [])

  const handleSave = async (values: any, section?: string) => {
    try {
      setSaving(true)
      if (section === 'forecast') {
        await api.post('/api/config', { smart: { forecast: values } })
      } else if (section === 'policy') {
        await api.post('/api/config', { smart: { policy: values } })
      } else if (section === 'location') {
        await api.post('/api/config', { smart: { forecast: { ...config?.smart?.forecast, ...values } } })
      } else if (section === 'timezone') {
        await api.post('/api/config', { timezone: values.timezone })
      } else if (section === 'mqtt') {
        await api.post('/api/config', { mqtt: values })
      }
      await loadConfig()
    } catch (error: any) {
      alert(`Failed to save: ${error?.message || error}`)
    } finally {
      setSaving(false)
    }
  }

  const handleSaveAll = async () => {
    // This can be used to save all settings at once if needed
    // For now, each step saves individually
    alert('All settings have been saved as you configured them.')
  }

  const renderStepContent = () => {
    if (!activeSection) return null

    const steps = getStepsForSection(activeSection)
    const currentStepData = steps[currentStep]

    switch (activeSection) {
      case 'system':
        if (currentStepData?.id === 'location') {
          return (
            <SystemSettingsWizard
              config={config}
              onSave={handleSave}
              saving={saving}
              step="location"
            />
          )
        } else if (currentStepData?.id === 'timezone') {
          return (
            <SystemSettingsWizard
              config={config}
              onSave={handleSave}
              saving={saving}
              step="timezone"
            />
          )
        } else if (currentStepData?.id === 'mqtt') {
          return (
            <SystemSettingsWizard
              config={config}
              onSave={handleSave}
              saving={saving}
              step="mqtt"
            />
          )
        }
        break
      case 'scheduler':
        if (currentStepData?.id === 'forecast') {
          return (
            <SmartSchedulerWizard
              config={config}
              onSave={handleSave}
              saving={saving}
              step="forecast"
            />
          )
        } else if (currentStepData?.id === 'policy') {
          return (
            <SmartSchedulerWizard
              config={config}
              onSave={handleSave}
              saving={saving}
              step="policy"
            />
          )
        }
        break
      case 'arrays':
        return (
          <ArraysBatteryWizard
            config={config}
            onSave={handleSaveAll}
            saving={saving}
          />
        )
      case 'inverter':
        return (
          <InverterConfigWizard
            config={config}
            onSave={handleSave}
            saving={saving}
          />
        )
      default:
        return null
    }
    return null
  }

  if (loading) {
    return (
      <div 
        className="min-h-screen flex items-center justify-center"
        style={{ backgroundColor: theme === 'dark' ? '#111827' : '#f9fafb' }}
      >
        <div 
          className="text-lg"
          style={{ color: theme === 'dark' ? '#ffffff' : '#1f2937' }}
        >
          Loading settings…
        </div>
      </div>
    )
  }

  // Theme-aware colors
  const bgColor = theme === 'dark' ? '#111827' : '#f9fafb'
  const cardBg = theme === 'dark' ? '#1f2937' : '#ffffff'
  const textColor = theme === 'dark' ? '#ffffff' : '#1f2937'
  const textSecondary = theme === 'dark' ? 'rgba(255, 255, 255, 0.7)' : '#6b7280'
  const borderColor = theme === 'dark' ? '#374151' : '#e5e7eb'

  // Helper to get summary for each category
  const getSystemSummary = () => {
    const items = []
    if (config?.smart?.forecast?.lat && config?.smart?.forecast?.lon) {
      items.push(`Location: ${config.smart.forecast.lat.toFixed(4)}, ${config.smart.forecast.lon.toFixed(4)}`)
    } else {
      items.push('Location: Not set')
    }
    if (config?.timezone) {
      items.push(`Timezone: ${config.timezone}`)
    } else {
      items.push('Timezone: Not set')
    }
    if (config?.mqtt?.host) {
      items.push(`MQTT: ${config.mqtt.host}:${config.mqtt.port || 1883}`)
    } else {
      items.push('MQTT: Not configured')
    }
    return items
  }

  const getSchedulerSummary = () => {
    const items = []
    if (config?.smart?.forecast?.enabled) {
      items.push(`Forecast: ${config.smart.forecast.provider || 'naive'}`)
    } else {
      items.push('Forecast: Disabled')
    }
    if (config?.smart?.policy?.enabled) {
      items.push(`Policy: ${config.smart.policy.primary_mode || 'self_use'}`)
    } else {
      items.push('Policy: Disabled')
    }
    return items
  }

  const getArraysSummary = () => {
    return ['Click to configure arrays and battery packs']
  }

  const getInverterSummary = () => {
    return ['Click to configure TOU windows and inverter controls']
  }

  // If wizard is open, show wizard
  if (showWizard && activeSection) {
    const sectionSteps = getStepsForSection(activeSection)
    return (
      <SettingsWizard
        steps={sectionSteps}
        currentStep={currentStep}
        onStepChange={setCurrentStep}
        onSave={handleSaveAll}
        onCancel={() => {
          setShowWizard(false)
          setCurrentStep(0)
          setActiveSection(null)
        }}
        saving={saving}
      >
        {renderStepContent()}
      </SettingsWizard>
    )
  }

  // Show summary view with configure buttons
  const settingsCategories = [
    {
      id: 'system',
      title: 'System Settings',
      description: 'Location, timezone, and MQTT configuration',
      icon: <Settings className="w-6 h-6" />,
      summary: getSystemSummary(),
      status: config?.timezone && config?.mqtt?.host ? 'Configured' : 'Partially configured',
      onClick: () => {
        setActiveSection('system')
        setCurrentStep(0)
        setShowWizard(true)
      }
    },
    {
      id: 'scheduler',
      title: 'Smart Scheduler',
      description: 'Forecast and policy settings for battery management',
      icon: <Cloud className="w-6 h-6" />,
      summary: getSchedulerSummary(),
      status: config?.smart?.forecast?.enabled || config?.smart?.policy?.enabled ? 'Configured' : 'Not configured',
      onClick: () => {
        setActiveSection('scheduler')
        setCurrentStep(0)
        setShowWizard(true)
      }
    },
    {
      id: 'arrays',
      title: 'Arrays & Battery Packs',
      description: 'Manage solar arrays and battery pack configurations',
      icon: <Layers className="w-6 h-6" />,
      summary: getArraysSummary(),
      status: 'Ready to configure',
      onClick: () => {
        setActiveSection('arrays')
        setCurrentStep(0)
        setShowWizard(true)
      }
    },
    {
      id: 'inverter',
      title: 'Inverter Configuration',
      description: 'Time-of-use windows and inverter controls',
      icon: <Zap className="w-6 h-6" />,
      summary: getInverterSummary(),
      status: 'Ready to configure',
      onClick: () => {
        setActiveSection('inverter')
        setCurrentStep(0)
        setShowWizard(true)
      }
    }
  ]

  return (
    <div 
      className="min-h-screen p-6"
      style={{ backgroundColor: bgColor }}
    >
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 
            className="text-3xl font-bold mb-2"
            style={{ color: textColor }}
          >
            Settings & Configuration
          </h1>
          <p 
            className="text-sm"
            style={{ color: textSecondary }}
          >
            Configure your solar monitoring system settings
          </p>
              </div>

        {/* Settings Categories Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {settingsCategories.map((category) => (
            <div
              key={category.id}
              className="p-6 rounded-lg cursor-pointer transition-all hover:shadow-lg"
              style={{
                backgroundColor: cardBg,
                border: `1px solid ${borderColor}`,
              }}
              onClick={category.onClick}
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div 
                    className="p-2 rounded-lg"
                    style={{
                      backgroundColor: theme === 'dark' ? '#374151' : '#f3f4f6',
                      color: textColor,
                    }}
                  >
                    {category.icon}
                  </div>
                  <div>
                    <h3 
                      className="text-lg font-semibold"
                      style={{ color: textColor }}
                    >
                      {category.title}
                    </h3>
                    <p 
                      className="text-sm mt-1"
                      style={{ color: textSecondary }}
                    >
                      {category.description}
                    </p>
                  </div>
              </div>
                <ChevronRight 
                  className="w-5 h-5 flex-shrink-0"
                  style={{ color: textSecondary }}
                />
              </div>
              {/* Summary */}
              <div className="mt-4 mb-4">
                <div className="space-y-1">
                  {category.summary.map((item, idx) => (
                    <div 
                      key={idx}
                      className="text-xs"
                      style={{ color: textSecondary }}
                    >
                      {item}
                    </div>
                  ))}
                </div>
              </div>

              <div className="flex items-center justify-between mt-4 pt-4"
                style={{ borderTop: `1px solid ${borderColor}` }}
              >
                <span 
                  className="text-xs font-medium"
                  style={{ 
                    color: category.status === 'Configured' 
                      ? (theme === 'dark' ? '#10b981' : '#059669')
                      : category.status === 'Partially configured'
                      ? (theme === 'dark' ? '#f59e0b' : '#d97706')
                      : textSecondary 
                  }}
                >
                  {category.status}
                </span>
                <button
                  className="px-4 py-2 text-sm font-medium rounded-lg transition-colors flex items-center gap-2"
                  style={{
                    backgroundColor: '#3b82f6',
                    color: '#ffffff',
                  }}
                  onClick={(e) => {
                    e.stopPropagation()
                    category.onClick()
                  }}
                >
                  Configure
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
