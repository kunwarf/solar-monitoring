import React, { useState } from 'react'
import { useTheme } from '../../../../contexts/ThemeContext'
import { SettingsForm } from '../../../SettingsForm'

interface SettingsCardProps {
  title: string
  icon?: React.ReactNode
  inverterId: string
  data?: Record<string, any>
  fields: Array<{
    key: string
    label: string
    type: 'text' | 'number' | 'boolean' | 'select'
    value?: any
    options?: Array<{ value: any; label: string }>
    min?: number
    max?: number
    step?: number
    unit?: string
    description?: string
    readOnly?: boolean
  }>
  onSave?: (values: Record<string, any>) => Promise<void>
  loading?: boolean
  saving?: boolean
  readOnly?: boolean
}

export const SettingsCard: React.FC<SettingsCardProps> = ({
  title,
  icon,
  inverterId,
  data,
  fields,
  onSave,
  loading = false,
  saving = false,
  readOnly = false
}) => {
  // Ensure data is always an object
  const safeData = data || {}
  const { theme } = useTheme()
  const [editing, setEditing] = useState(false)

  const textColor = theme === 'dark' ? '#ffffff' : '#1f2937'
  const textSecondary = theme === 'dark' ? 'rgba(255, 255, 255, 0.7)' : '#6b7280'
  const cardBg = theme === 'dark' ? '#374151' : '#f3f4f6'
  const borderColor = theme === 'dark' ? '#4b5563' : '#d1d5db'
  const innerBg = theme === 'dark' ? '#1f2937' : '#ffffff'

  // Populate field values from data (handle null/undefined data)
  const populatedFields = fields.map(field => ({
    ...field,
    value: (safeData && safeData[field.key] !== undefined) ? safeData[field.key] : (field.value !== undefined ? field.value : (field.type === 'number' ? 0 : field.type === 'boolean' ? false : ''))
  }))

  const handleSave = async (values: Record<string, any>) => {
    if (onSave) {
      try {
        await onSave(values)
        setEditing(false)
      } catch (error: any) {
        alert(`Failed to save: ${error?.message || 'Unknown error'}`)
        throw error
      }
    }
  }

  const formatValue = (field: typeof populatedFields[0], value: any): string => {
    if (value === null || value === undefined) return '—'
    if (field.type === 'boolean') return value ? 'Enabled' : 'Disabled'
    if (field.type === 'select' && field.options) {
      const option = field.options.find(opt => opt.value === value)
      return option ? option.label : String(value)
    }
    if (field.type === 'number' && field.unit) {
      return `${value} ${field.unit}`
    }
    return String(value)
  }

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
          Loading {title}...
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
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          {icon && <div style={{ color: textColor }}>{icon}</div>}
          <div>
            <h3 className="font-semibold" style={{ color: textColor }}>{title}</h3>
          </div>
        </div>
        {!readOnly && !editing && onSave && (
          <button
            onClick={() => setEditing(true)}
            className="text-sm font-medium hover:underline"
            style={{ color: '#3b82f6' }}
          >
            edit
          </button>
        )}
      </div>

      {editing ? (
        <SettingsForm
          title={`Edit ${title}`}
          fields={populatedFields.filter(f => !f.readOnly)}
          onSave={handleSave}
          onCancel={() => setEditing(false)}
          loading={saving}
        />
      ) : (
        <div className="space-y-3">
          {populatedFields.map(field => {
            const fieldValue = (safeData && safeData[field.key] !== undefined) ? safeData[field.key] : field.value
            return (
              <div key={field.key} className="flex justify-between items-start py-2 border-b" style={{ borderColor: borderColor }}>
                <div className="flex-1">
                  <div className="text-sm font-medium" style={{ color: textColor }}>{field.label}</div>
                  {field.description && (
                    <div className="text-xs mt-1" style={{ color: textSecondary }}>{field.description}</div>
                  )}
                </div>
                <div className="text-sm font-semibold ml-4" style={{ color: textColor }}>
                  {formatValue(field, fieldValue)}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

