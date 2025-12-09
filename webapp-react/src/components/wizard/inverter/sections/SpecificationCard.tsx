import React from 'react'
import { useTheme } from '../../../../contexts/ThemeContext'
import { Info } from 'lucide-react'

interface SpecificationCardProps {
  inverterId: string
  data?: {
    driver?: string
    serial_number?: string
    protocol_version?: number
    max_ac_output_power_kw?: number
    mppt_connections?: number
    parallel?: string
    modbus_number?: number
  }
  loading?: boolean
}

export const SpecificationCard: React.FC<SpecificationCardProps> = ({
  inverterId,
  data,
  loading = false
}) => {
  const { theme } = useTheme()

  const textColor = theme === 'dark' ? '#ffffff' : '#1f2937'
  const textSecondary = theme === 'dark' ? 'rgba(255, 255, 255, 0.7)' : '#6b7280'
  const cardBg = theme === 'dark' ? '#374151' : '#f3f4f6'
  const borderColor = theme === 'dark' ? '#4b5563' : '#d1d5db'

  // Ensure data is always an object
  const safeData = data || {}

  const fields = [
    { key: 'driver', label: 'Driver', value: safeData.driver },
    { key: 'serial_number', label: 'Serial number', value: safeData.serial_number },
    { key: 'protocol_version', label: 'Protocol version', value: safeData.protocol_version },
    { key: 'max_ac_output_power_kw', label: 'Max AC output power', value: safeData.max_ac_output_power_kw, unit: 'kW' },
    { key: 'mppt_connections', label: 'MPPT connections', value: safeData.mppt_connections },
    { key: 'parallel', label: 'Parallel', value: safeData.parallel },
    { key: 'modbus_number', label: 'Modbus number', value: safeData.modbus_number }
  ]

  if (loading) {
    return (
      <div 
        className="p-6 rounded-lg"
        style={{
          backgroundColor: cardBg,
          border: `1px solid ${borderColor}`,
        }}
      >
        <div className="text-center" style={{ color: textSecondary }}>
          Loading specification...
        </div>
      </div>
    )
  }

  return (
    <div 
      className="p-6 rounded-lg"
      style={{
        backgroundColor: cardBg,
        border: `1px solid ${borderColor}`,
      }}
    >
      <div className="flex items-center gap-3 mb-4">
        <Info className="w-5 h-5" style={{ color: textColor }} />
        <h3 className="font-semibold" style={{ color: textColor }}>Specification</h3>
      </div>

      <div className="space-y-3">
        {fields.map(field => (
          <div key={field.key} className="flex justify-between items-start py-2 border-b" style={{ borderColor: borderColor }}>
            <div className="flex-1">
              <div className="text-sm font-medium" style={{ color: textColor }}>{field.label}</div>
            </div>
            <div className="text-sm font-semibold ml-4" style={{ color: textColor }}>
              {field.value !== null && field.value !== undefined 
                ? `${field.value}${field.unit ? ' ' + field.unit : ''}`
                : '—'}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

