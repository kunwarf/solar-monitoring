import React, { useEffect, useState } from 'react'
import { api } from '../lib/api'
import { TelemetryResponse, TelemetryData } from '../types/telemetry'
import { SettingsForm } from '../components/SettingsForm'

interface ConfigData {
  mqtt?: {
    host?: string
    port?: number
    base_topic?: string
    client_id?: string
    ha_discovery?: boolean
  }
  polling?: {
    interval_secs?: number
  }
  smart?: {
    forecast?: {
      enabled?: boolean
      provider?: string
      lat?: number
      lon?: number
      tz?: string
      pv_dc_kw?: number
      pv_perf_ratio?: number
      tilt_deg?: number
      azimuth_deg?: number
      albedo?: number
      batt_capacity_kwh?: number
    }
    policy?: {
      enabled?: boolean
      target_full_before_sunset?: boolean
      overnight_min_soc_pct?: number
      blackout_reserve_soc_pct?: number
      conserve_on_bad_tomorrow?: boolean
      smart_tick_interval_secs?: number
      max_charge_power_w?: number
      max_discharge_power_w?: number
      max_battery_soc_pct?: number
    }
  }
}

interface InverterSensor {
  id: string
  name: string
  type: 'text' | 'number' | 'boolean' | 'select'
  unit?: string
  min?: number
  max?: number
  step?: number
  options?: Array<{ value: any; label: string }>
  current_value: any
  description?: string
}

const Row: React.FC<{label: string, value?: React.ReactNode}> = ({ label, value }) => (
  <div className="flex justify-between py-2 border-b border-gray-100">
    <div className="text-gray-600">{label}</div>
    <div className="font-medium text-gray-900 text-right">{value ?? '—'}</div>
  </div>
)

const Section: React.FC<{title: string, children: React.ReactNode, onEdit?: () => void}> = ({ title, children, onEdit }) => (
  <div className="bg-white rounded-lg shadow-sm p-6">
    <div className="flex items-center justify-between mb-4">
      <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
      {onEdit && (
        <button onClick={onEdit} className="text-blue-600 text-sm font-medium hover:underline">edit</button>
      )}
    </div>
    {children}
  </div>
)

export const SettingsPage: React.FC = () => {
  const [data, setData] = useState<TelemetryData | null>(null)
  const [config, setConfig] = useState<ConfigData | null>(null)
  const [inverterSensors, setInverterSensors] = useState<InverterSensor[]>([])
  const [loading, setLoading] = useState(true)
  const [editingConfig, setEditingConfig] = useState<string | null>(null)
  const [editingSensor, setEditingSensor] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [retryCount, setRetryCount] = useState(0)

  useEffect(() => {
    loadData()
  }, [])

  const retryLoadData = () => {
    setRetryCount(prev => prev + 1)
    loadData()
  }

  const loadData = async () => {
    try {
      setLoading(true)
      console.log('Loading settings data...')
      
      // Load telemetry data
      try {
        const telemetryRes = await api.get<TelemetryResponse>(`/api/now?inverter_id=senergy1`)
        setData(telemetryRes.now)
        console.log('Telemetry data loaded:', telemetryRes.now)
      } catch (error) {
        console.error('Error loading telemetry data:', error)
        setData(null)
      }
      
      // Load configuration
      try {
        const configRes = await api.get<{config: ConfigData}>('/api/config')
        setConfig(configRes.config)
        console.log('Configuration loaded:', configRes.config)
      } catch (error) {
        console.error('Error loading configuration:', error)
        setConfig(null)
      }
      
      // Load inverter sensors
      try {
        const sensorsRes = await api.get<{sensors: InverterSensor[]}>('/api/inverter/sensors?inverter_id=senergy1')
        setInverterSensors(sensorsRes.sensors)
        console.log('Inverter sensors loaded:', sensorsRes.sensors)
      } catch (error) {
        console.error('Error loading inverter sensors:', error)
        setInverterSensors([])
      }
      
    } catch (error) {
      console.error('Error loading settings data:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleConfigEdit = (section: string) => {
    setEditingConfig(section)
  }

  const handleConfigSave = async (values: Record<string, any>) => {
    try {
      setSaving(true)
      
      // Map flat keys to proper nested structure based on the section being edited
      let configUpdates: Record<string, any> = {}
      
      if (editingConfig === 'mqtt') {
        // MQTT configuration updates
        for (const [key, value] of Object.entries(values)) {
          configUpdates[`mqtt.${key}`] = value
        }
      } else if (editingConfig === 'smart') {
        // Smart scheduler configuration updates
        for (const [key, value] of Object.entries(values)) {
          configUpdates[`smart.policy.${key}`] = value
        }
      } else {
        // For other sections, use the values as-is
        configUpdates = values
      }
      
      // Update configuration via API
      await api.post('/api/config', configUpdates)
      
      // Reload data
      await loadData()
      setEditingConfig(null)
      
    } catch (error) {
      console.error('Error saving configuration:', error)
      alert('Failed to save configuration. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  const handleSensorEdit = (sensorId: string) => {
    setEditingSensor(sensorId)
  }

  const handleSensorSave = async (values: Record<string, any>) => {
    try {
      setSaving(true)
      
      // Update sensor via API
      await api.post(`/api/inverter/sensors/${editingSensor}`, values)
      
      // Reload data
      await loadData()
      setEditingSensor(null)
      
    } catch (error) {
      console.error('Error saving sensor:', error)
      alert('Failed to save sensor value. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  const fmtPower = (w?: number) => w == null ? '—' : w >= 1000 ? `${(w/1000).toFixed(2)} kW` : `${w} W`
  const fmt = (v?: number | string, unit?: string) => v == null ? '—' : `${v}${unit ? ' ' + unit : ''}`

  if (loading) return <div className="p-8 text-gray-700">Loading settings…</div>

  return (
    <div className="p-6 bg-gray-50 min-h-screen">
      <h1 className="text-2xl font-bold mb-6 text-gray-900">Settings & Configuration</h1>
      
      {/* API Connection Status */}
      {!config && !data && (
        <div className="mb-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-yellow-800">
                API Server Not Available
              </h3>
              <div className="mt-2 text-sm text-yellow-700">
                <p>Unable to connect to the API server. Please ensure the backend is running.</p>
                <p className="mt-1">Some settings may not be available until the connection is restored.</p>
                <button 
                  onClick={retryLoadData}
                  className="mt-2 px-3 py-1 text-xs bg-yellow-100 text-yellow-800 rounded hover:bg-yellow-200"
                >
                  Retry Connection
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="space-y-6">
        {/* System Information */}
        <Section title="System Information">
          <Row label="Driver" value="Senergy" />
          <Row label="Model name" value={data?.device_model ?? 'SM-ONYX-UL-6KW'} />
          <Row label="Serial number" value={data?.device_serial_number} />
          <Row label="Production type" value="Hybrid with generator" />
          <Row label="Max AC output power" value={fmt(6000, 'W')} />
          <Row label="Grid phases" value={fmt(1)} />
          <Row label="MPPT connections" value={fmt(2)} />
        </Section>

        {/* MQTT Configuration */}
        {editingConfig === 'mqtt' ? (
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
            onSave={handleConfigSave}
            onCancel={() => setEditingConfig(null)}
            loading={saving}
          />
        ) : (
          <Section title="MQTT Configuration" onEdit={config ? () => handleConfigEdit('mqtt') : undefined}>
            <Row label="Host" value={config?.mqtt?.host || '—'} />
            <Row label="Port" value={config?.mqtt?.port || '—'} />
            <Row label="Base Topic" value={config?.mqtt?.base_topic || '—'} />
            <Row label="Client ID" value={config?.mqtt?.client_id || '—'} />
            <Row label="HA Discovery" value={config?.mqtt?.ha_discovery ? 'Enabled' : 'Disabled'} />
          </Section>
        )}

        {/* Smart Scheduler Configuration */}
        {editingConfig === 'smart' ? (
          <SettingsForm
            title="Smart Scheduler Configuration"
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
              }
            ]}
            onSave={handleConfigSave}
            onCancel={() => setEditingConfig(null)}
            loading={saving}
          />
        ) : (
          <Section title="Smart Scheduler Configuration" onEdit={config ? () => handleConfigEdit('smart') : undefined}>
            <Row label="Enabled" value={config?.smart?.policy?.enabled ? 'Yes' : 'No'} />
            <Row label="Target Full Before Sunset" value={config?.smart?.policy?.target_full_before_sunset ? 'Yes' : 'No'} />
            <Row label="Overnight Min SOC" value={fmt(config?.smart?.policy?.overnight_min_soc_pct, '%')} />
            <Row label="Blackout Reserve SOC" value={fmt(config?.smart?.policy?.blackout_reserve_soc_pct, '%')} />
            <Row label="Max Charge Power" value={fmtPower(config?.smart?.policy?.max_charge_power_w)} />
            <Row label="Max Discharge Power" value={fmtPower(config?.smart?.policy?.max_discharge_power_w)} />
          </Section>
        )}

        {/* Inverter Sensors */}
        <div className="bg-white rounded-lg shadow-sm p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Inverter Controls</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {inverterSensors.map(sensor => (
              <div key={sensor.id} className="border border-gray-200 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-medium text-gray-900">{sensor.name}</h3>
                  <button
                    onClick={() => handleSensorEdit(sensor.id)}
                    className="text-blue-600 text-sm font-medium hover:underline"
                  >
                    edit
                  </button>
                </div>
                
                {editingSensor === sensor.id ? (
                  <SettingsForm
                    title={`Edit ${sensor.name}`}
                    fields={[
                      {
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
                      }
                    ]}
                    onSave={handleSensorSave}
                    onCancel={() => setEditingSensor(null)}
                    loading={saving}
                  />
                ) : (
                  <div>
                    <p className="text-sm text-gray-600 mb-1">
                      Current: {sensor.type === 'boolean' 
                        ? (sensor.current_value ? 'Enabled' : 'Disabled')
                        : `${sensor.current_value}${sensor.unit ? ' ' + sensor.unit : ''}`
                      }
                    </p>
                    {sensor.description && (
                      <p className="text-xs text-gray-500">{sensor.description}</p>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
