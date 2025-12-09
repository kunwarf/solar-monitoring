import React from 'react'
import { SettingsCard } from './SettingsCard'
import { Settings } from 'lucide-react'
import { api } from '../../../../lib/api'

interface WorkModeCardProps {
  inverterId: string
  data?: {
    remote_switch?: string
    grid_charge?: boolean
    generator_charge?: boolean
    force_generator_on?: boolean
    output_shutdown_capacity_pct?: number
    stop_battery_discharge_capacity_pct?: number
    start_battery_discharge_capacity_pct?: number
    start_grid_charge_capacity_pct?: number
    off_grid_mode?: boolean
    off_grid_start_up_battery_capacity_pct?: number
  }
  loading?: boolean
  onDataChange?: () => void
}

export const WorkModeCard: React.FC<WorkModeCardProps> = ({
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
      await api.post(`/api/inverter/work-mode?inverter_id=${inverterId}`, values)
      if (onDataChange) {
        onDataChange()
      }
    } finally {
      setSaving(false)
    }
  }

  return (
    <SettingsCard
      title="Work mode"
      icon={<Settings className="w-5 h-5" />}
      inverterId={inverterId}
      data={safeData}
      loading={loading}
      saving={saving}
      fields={[
        {
          key: 'remote_switch',
          label: 'Remote switch',
          type: 'select',
          options: [
            { value: 'On', label: 'On' },
            { value: 'Off', label: 'Off' }
          ],
          readOnly: true
        },
        {
          key: 'grid_charge',
          label: 'Grid charge',
          type: 'boolean'
        },
        {
          key: 'generator_charge',
          label: 'Generator charge',
          type: 'boolean'
        },
        {
          key: 'force_generator_on',
          label: 'Force generator on',
          type: 'boolean',
          readOnly: true
        },
        {
          key: 'output_shutdown_capacity_pct',
          label: 'Output shutdown capacity',
          type: 'number',
          unit: '%',
          min: 0,
          max: 100,
          step: 1
        },
        {
          key: 'stop_battery_discharge_capacity_pct',
          label: 'Stop battery discharge capacity',
          type: 'number',
          unit: '%',
          min: 0,
          max: 100,
          step: 1
        },
        {
          key: 'start_battery_discharge_capacity_pct',
          label: 'Start battery discharge capacity',
          type: 'number',
          unit: '%',
          min: 0,
          max: 100,
          step: 1
        },
        {
          key: 'start_grid_charge_capacity_pct',
          label: 'Start grid charge capacity',
          type: 'number',
          unit: '%',
          min: 0,
          max: 100,
          step: 1
        },
        {
          key: 'off_grid_mode',
          label: 'Off-Grid Mode',
          type: 'boolean',
          description: 'Enable/disable off-grid mode'
        },
        {
          key: 'off_grid_start_up_battery_capacity_pct',
          label: 'Off-Grid Startup Battery Capacity',
          type: 'number',
          unit: '%',
          min: 0,
          max: 100,
          step: 1,
          description: 'Minimum battery capacity to start in off-grid mode'
        }
      ]}
      onSave={handleSave}
    />
  )
}

