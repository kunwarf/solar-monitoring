import React from 'react'
import { SettingsCard } from './SettingsCard'
import { Zap } from 'lucide-react'
import { api } from '../../../../lib/api'

interface GridSettingsCardProps {
  inverterId: string
  data?: {
    grid_voltage_high_v?: number
    grid_voltage_low_v?: number
    grid_frequency_hz?: number
    grid_frequency_high_hz?: number
    grid_frequency_low_hz?: number
    grid_peak_shaving?: boolean
    grid_peak_shaving_power_kw?: number
  }
  loading?: boolean
  onDataChange?: () => void
}

export const GridSettingsCard: React.FC<GridSettingsCardProps> = ({
  inverterId,
  data,
  loading = false,
  onDataChange
}) => {
  const safeData = data || {}
  const [saving, setSaving] = React.useState(false)

  const handleSave = async (values: Record<string, any>) => {
    setSaving(true)
    try {
      await api.post(`/api/inverter/grid-settings?inverter_id=${inverterId}`, values)
      if (onDataChange) {
        onDataChange()
      }
    } finally {
      setSaving(false)
    }
  }

  return (
    <SettingsCard
      title="Grid"
      icon={<Zap className="w-5 h-5" />}
      inverterId={inverterId}
      data={safeData}
      loading={loading}
      saving={saving}
      fields={[
        {
          key: 'grid_voltage_high_v',
          label: 'Grid voltage high',
          type: 'number',
          unit: 'V',
          min: 0,
          max: 300,
          step: 1
        },
        {
          key: 'grid_voltage_low_v',
          label: 'Grid voltage low',
          type: 'number',
          unit: 'V',
          min: 0,
          max: 300,
          step: 1
        },
        {
          key: 'grid_frequency_hz',
          label: 'Grid frequency',
          type: 'number',
          unit: 'Hz',
          min: 45,
          max: 55,
          step: 0.1
        },
        {
          key: 'grid_frequency_high_hz',
          label: 'Grid frequency high',
          type: 'number',
          unit: 'Hz',
          min: 45,
          max: 55,
          step: 0.1
        },
        {
          key: 'grid_frequency_low_hz',
          label: 'Grid frequency low',
          type: 'number',
          unit: 'Hz',
          min: 45,
          max: 55,
          step: 0.1
        },
        {
          key: 'grid_peak_shaving',
          label: 'Grid peak shaving',
          type: 'boolean'
        },
        {
          key: 'grid_peak_shaving_power_kw',
          label: 'Grid peak shaving power',
          type: 'number',
          unit: 'kW',
          min: 0,
          max: 100,
          step: 0.1
        }
      ]}
      onSave={handleSave}
    />
  )
}

