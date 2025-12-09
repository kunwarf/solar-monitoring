import React from 'react'
import { SettingsCard } from './SettingsCard'
import { Battery } from 'lucide-react'
import { api } from '../../../../lib/api'

interface BatteryTypeCardProps {
  inverterId: string
  data?: {
    battery_type?: number | string
    battery_capacity_ah?: number
    battery_operation?: string
  }
  loading?: boolean
  onDataChange?: () => void
}

export const BatteryTypeCard: React.FC<BatteryTypeCardProps> = ({
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
      await api.post(`/api/inverter/battery-type?inverter_id=${inverterId}`, values)
      if (onDataChange) {
        onDataChange()
      }
    } finally {
      setSaving(false)
    }
  }

  // Map battery type enum values
  const batteryTypeOptions = [
    { value: 0, label: 'Lead Battery' },
    { value: 1, label: 'Lithium Battery' }
  ]

  const operationOptions = [
    { value: 'State of charge', label: 'State of charge' },
    { value: 'Voltage', label: 'Voltage' }
  ]

  return (
    <SettingsCard
      title="Battery type"
      icon={<Battery className="w-5 h-5" />}
      inverterId={inverterId}
      data={safeData}
      loading={loading}
      saving={saving}
      fields={[
        {
          key: 'battery_type',
          label: 'Battery type',
          type: 'select',
          options: batteryTypeOptions
        },
        {
          key: 'battery_capacity_ah',
          label: 'Battery capacity',
          type: 'number',
          unit: 'Ah',
          min: 0,
          max: 10000,
          step: 1
        },
        {
          key: 'battery_operation',
          label: 'Battery operation',
          type: 'select',
          options: operationOptions
        }
      ]}
      onSave={handleSave}
    />
  )
}

