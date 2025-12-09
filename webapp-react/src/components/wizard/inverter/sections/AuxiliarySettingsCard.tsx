import React from 'react'
import { SettingsCard } from './SettingsCard'
import { Plug } from 'lucide-react'
import { api } from '../../../../lib/api'

interface AuxiliarySettingsCardProps {
  inverterId: string
  data?: {
    auxiliary_port?: string
    generator_connected_to_grid_input?: boolean
    generator_peak_shaving?: boolean
    generator_peak_shaving_power_kw?: number
    generator_stop_capacity_pct?: number
    generator_start_capacity_pct?: number
    generator_max_run_time_h?: number
    generator_down_time_h?: number
  }
  loading?: boolean
  onDataChange?: () => void
}

export const AuxiliarySettingsCard: React.FC<AuxiliarySettingsCardProps> = ({
  inverterId,
  data,
  loading = false,
  onDataChange
}) => {
  // Ensure data is always an object
  const safeData = data || {}
  const [saving, setSaving] = React.useState(false)

  const handleSave = async (values: Record<string, any>) => {
    setSaving(true)
    try {
      await api.post(`/api/inverter/auxiliary-settings?inverter_id=${inverterId}`, values)
      if (onDataChange) {
        onDataChange()
      }
    } finally {
      setSaving(false)
    }
  }

  return (
    <SettingsCard
      title="Auxiliary"
      icon={<Plug className="w-5 h-5" />}
      inverterId={inverterId}
      data={safeData}
      loading={loading}
      saving={saving}
      fields={[
        {
          key: 'auxiliary_port',
          label: 'Auxiliary port',
          type: 'select',
          options: [
            { value: 'Generator input', label: 'Generator input' }
          ],
          readOnly: true
        },
        {
          key: 'generator_connected_to_grid_input',
          label: 'Generator connected to grid input',
          type: 'boolean',
          readOnly: true
        },
        {
          key: 'generator_peak_shaving',
          label: 'Generator peak shaving',
          type: 'boolean'
        },
        {
          key: 'generator_peak_shaving_power_kw',
          label: 'Generator peak shaving power',
          type: 'number',
          unit: 'kW',
          min: 0,
          max: 100,
          step: 0.1
        },
        {
          key: 'generator_stop_capacity_pct',
          label: 'Generator stop capacity',
          type: 'number',
          unit: '%',
          min: 0,
          max: 100,
          step: 1
        },
        {
          key: 'generator_start_capacity_pct',
          label: 'Generator start capacity',
          type: 'number',
          unit: '%',
          min: 0,
          max: 100,
          step: 1
        },
        {
          key: 'generator_max_run_time_h',
          label: 'Generator max run time',
          type: 'number',
          unit: 'h',
          min: 0,
          max: 24,
          step: 0.1
        },
        {
          key: 'generator_down_time_h',
          label: 'Generator down time',
          type: 'number',
          unit: 'h',
          min: 0,
          max: 24,
          step: 0.1
        }
      ]}
      onSave={handleSave}
    />
  )
}

