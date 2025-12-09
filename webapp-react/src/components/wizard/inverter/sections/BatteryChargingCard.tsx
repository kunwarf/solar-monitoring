import React from 'react'
import { SettingsCard } from './SettingsCard'
import { Battery } from 'lucide-react'
import { api } from '../../../../lib/api'

interface BatteryChargingCardProps {
  inverterId: string
  data?: {
    max_discharge_current_a?: number
    max_charge_current_a?: number
    max_grid_charge_current_a?: number
    max_generator_charge_current_a?: number
    battery_float_charge_voltage_v?: number
    battery_absorption_charge_voltage_v?: number
    battery_equalization_charge_voltage_v?: number
    max_grid_charger_power_w?: number
    max_charger_power_w?: number
    max_discharger_power_w?: number
  }
  batteryOperation?: 'Voltage' | 'State of charge' | null
  loading?: boolean
  onDataChange?: () => void
}

export const BatteryChargingCard: React.FC<BatteryChargingCardProps> = ({
  inverterId,
  data,
  batteryOperation,
  loading = false,
  onDataChange
}) => {
  const safeData = data || {}
  const [saving, setSaving] = React.useState(false)
  
  // Determine if we should show voltage fields
  // Show voltage fields only if battery operation is "Voltage" mode
  const showVoltageFields = batteryOperation === 'Voltage'

  const handleSave = async (values: Record<string, any>) => {
    setSaving(true)
    try {
      await api.post(`/api/inverter/battery-charging?inverter_id=${inverterId}`, values)
      if (onDataChange) {
        onDataChange()
      }
    } finally {
      setSaving(false)
    }
  }

  return (
    <SettingsCard
      title="Battery charging"
      icon={<Battery className="w-5 h-5" />}
      inverterId={inverterId}
      data={safeData}
      loading={loading}
      saving={saving}
      fields={[
        {
          key: 'max_discharge_current_a',
          label: 'Max discharge current',
          type: 'number',
          unit: 'A',
          min: 0,
          max: 500,
          step: 1
        },
        {
          key: 'max_charge_current_a',
          label: 'Max charge current',
          type: 'number',
          unit: 'A',
          min: 0,
          max: 500,
          step: 1
        },
        {
          key: 'max_grid_charge_current_a',
          label: 'Max grid charge current',
          type: 'number',
          unit: 'A',
          min: 0,
          max: 500,
          step: 1
        },
        {
          key: 'max_generator_charge_current_a',
          label: 'Max generator charge current',
          type: 'number',
          unit: 'A',
          min: 0,
          max: 500,
          step: 1
        },
        // Voltage fields - only show if battery operation is "Voltage" mode
        ...(showVoltageFields ? [
          {
            key: 'battery_float_charge_voltage_v',
            label: 'Battery float charge voltage',
            type: 'number' as const,
            unit: 'V',
            min: 0,
            max: 100,
            step: 0.1
          },
          {
            key: 'battery_absorption_charge_voltage_v',
            label: 'Battery absorption charge voltage',
            type: 'number' as const,
            unit: 'V',
            min: 0,
            max: 100,
            step: 0.1
          },
          {
            key: 'battery_equalization_charge_voltage_v',
            label: 'Battery equalization charge voltage',
            type: 'number' as const,
            unit: 'V',
            min: 0,
            max: 100,
            step: 0.1
          }
        ] : []),
        {
          key: 'max_grid_charger_power_w',
          label: 'Maximum Grid Charger Power',
          type: 'number',
          unit: 'W',
          min: 0,
          max: 10000,
          step: 100,
          description: 'Maximum power for grid charging'
        },
        {
          key: 'max_charger_power_w',
          label: 'Maximum Charger Power',
          type: 'number',
          unit: 'W',
          min: 0,
          max: 10000,
          step: 100,
          description: 'Maximum total charging power'
        },
        {
          key: 'max_discharger_power_w',
          label: 'Maximum Discharger Power',
          type: 'number',
          unit: 'W',
          min: 0,
          max: 10000,
          step: 100,
          description: 'Maximum discharging power'
        }
      ]}
      onSave={handleSave}
    />
  )
}

