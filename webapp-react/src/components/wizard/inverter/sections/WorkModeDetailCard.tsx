import React from 'react'
import { SettingsCard } from './SettingsCard'
import { Settings } from 'lucide-react'
import { api } from '../../../../lib/api'

interface WorkModeDetailCardProps {
  inverterId: string
  data?: {
    work_mode?: string
    solar_export_when_battery_full?: boolean
    energy_pattern?: string
    max_sell_power_kw?: number
    max_solar_power_kw?: number
    grid_trickle_feed_w?: number
    max_export_power_w?: number
  }
  loading?: boolean
  onDataChange?: () => void
}

export const WorkModeDetailCard: React.FC<WorkModeDetailCardProps> = ({
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
      await api.post(`/api/inverter/work-mode-detail?inverter_id=${inverterId}`, values)
      if (onDataChange) {
        onDataChange()
      }
    } finally {
      setSaving(false)
    }
  }

  const workModeOptions = [
    { value: 'Zero export to load', label: 'Zero export to load' },
    { value: 'Load first', label: 'Load first' }
  ]

  const energyPatternOptions = [
    { value: 'Load first', label: 'Load first' }
  ]

  return (
    <SettingsCard
      title="Work mode detail"
      icon={<Settings className="w-5 h-5" />}
      inverterId={inverterId}
      data={safeData}
      loading={loading}
      saving={saving}
      fields={[
        {
          key: 'work_mode',
          label: 'Work mode',
          type: 'select',
          options: workModeOptions
        },
        {
          key: 'solar_export_when_battery_full',
          label: 'Solar export when battery full',
          type: 'boolean'
        },
        {
          key: 'energy_pattern',
          label: 'Energy pattern',
          type: 'select',
          options: energyPatternOptions
        },
        {
          key: 'max_sell_power_kw',
          label: 'Max sell power',
          type: 'number',
          unit: 'kW',
          min: 0,
          max: 100,
          step: 0.1
        },
        {
          key: 'max_solar_power_kw',
          label: 'Max solar power',
          type: 'number',
          unit: 'kW',
          min: 0,
          max: 100,
          step: 0.1
        },
        {
          key: 'grid_trickle_feed_w',
          label: 'Grid trickle feed',
          type: 'number',
          unit: 'W',
          min: 0,
          max: 1000,
          step: 1
        },
        {
          key: 'max_export_power_w',
          label: 'Maximum Feed-in Grid Power',
          type: 'number',
          unit: 'W',
          min: 0,
          max: 20000,
          step: 100,
          description: 'Maximum power that can be fed into the grid'
        }
      ]}
      onSave={handleSave}
    />
  )
}

