import React, { useState } from 'react'
import { useTheme } from '../contexts/ThemeContext'

interface SettingField {
  key: string
  label: string
  type: 'text' | 'number' | 'boolean' | 'select'
  value: any
  options?: Array<{ value: any; label: string }>
  min?: number
  max?: number
  step?: number
  unit?: string
  description?: string
}

interface SettingsFormProps {
  title: string
  fields: SettingField[]
  onSave: (values: Record<string, any>) => Promise<void>
  onCancel: () => void
  loading?: boolean
}

export const SettingsForm: React.FC<SettingsFormProps> = ({
  title,
  fields,
  onSave,
  onCancel,
  loading = false
}) => {
  const { theme } = useTheme()
  const [values, setValues] = useState<Record<string, any>>(
    fields.reduce((acc, field) => {
      acc[field.key] = field.value
      return acc
    }, {} as Record<string, any>)
  )
  const [errors, setErrors] = useState<Record<string, string>>({})

  // Theme-aware colors
  const bgColor = theme === 'dark' ? '#1f2937' : '#ffffff'
  const textColor = theme === 'dark' ? '#ffffff' : '#1f2937'
  const textSecondary = theme === 'dark' ? 'rgba(255, 255, 255, 0.7)' : '#6b7280'
  const borderColor = theme === 'dark' ? '#4b5563' : '#d1d5db'
  const inputBg = theme === 'dark' ? '#374151' : '#ffffff'

  const handleChange = (key: string, value: any) => {
    setValues(prev => ({ ...prev, [key]: value }))
    // Clear error when user starts typing
    if (errors[key]) {
      setErrors(prev => ({ ...prev, [key]: '' }))
    }
  }

  const validateField = (field: SettingField, value: any): string => {
    if (field.type === 'number') {
      if (value === '' || value === null || value === undefined) {
        return 'This field is required'
      }
      const numValue = Number(value)
      if (isNaN(numValue)) {
        return 'Must be a valid number'
      }
      if (field.min !== undefined && numValue < field.min) {
        return `Must be at least ${field.min}`
      }
      if (field.max !== undefined && numValue > field.max) {
        return `Must be at most ${field.max}`
      }
    }
    return ''
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    // Validate all fields
    const newErrors: Record<string, string> = {}
    fields.forEach(field => {
      const error = validateField(field, values[field.key])
      if (error) {
        newErrors[field.key] = error
      }
    })

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors)
      return
    }

    try {
      await onSave(values)
    } catch (error) {
      console.error('Error saving settings:', error)
    }
  }

  const renderField = (field: SettingField) => {
    const error = errors[field.key]
    const fieldId = `field-${field.key}`

    return (
      <div key={field.key} className="mb-4">
        <label 
          htmlFor={fieldId} 
          className="block text-sm font-medium mb-1"
          style={{ color: textColor }}
        >
          {field.label}
          {field.unit && (
            <span className="ml-1" style={{ color: textSecondary }}>
              ({field.unit})
            </span>
          )}
        </label>
        
        {field.description && (
          <p className="text-xs mb-2" style={{ color: textSecondary }}>
            {field.description}
          </p>
        )}

        {field.type === 'text' && (
          <input
            id={fieldId}
            type="text"
            value={values[field.key] || ''}
            onChange={(e) => handleChange(field.key, e.target.value)}
            className="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            style={{
              backgroundColor: inputBg,
              color: textColor,
              borderColor: error ? '#ef4444' : borderColor,
            }}
            disabled={loading}
          />
        )}

        {field.type === 'number' && (
          <input
            id={fieldId}
            type="number"
            value={values[field.key] || ''}
            onChange={(e) => handleChange(field.key, e.target.value)}
            min={field.min}
            max={field.max}
            step={field.step}
            className="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            style={{
              backgroundColor: inputBg,
              color: textColor,
              borderColor: error ? '#ef4444' : borderColor,
            }}
            disabled={loading}
          />
        )}

        {field.type === 'boolean' && (
          <div className="flex items-center">
            <input
              id={fieldId}
              type="checkbox"
              checked={Boolean(values[field.key])}
              onChange={(e) => handleChange(field.key, e.target.checked)}
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 rounded"
              style={{ borderColor: borderColor }}
              disabled={loading}
            />
            <label htmlFor={fieldId} className="ml-2 text-sm" style={{ color: textColor }}>
              {values[field.key] ? 'Enabled' : 'Disabled'}
            </label>
          </div>
        )}

        {field.type === 'select' && field.options && (
          <select
            id={fieldId}
            value={values[field.key] || ''}
            onChange={(e) => handleChange(field.key, e.target.value)}
            className="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            style={{
              backgroundColor: inputBg,
              color: textColor,
              borderColor: error ? '#ef4444' : borderColor,
            }}
            disabled={loading}
          >
            {field.options.map(option => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        )}

        {error && (
          <p className="mt-1 text-sm" style={{ color: '#ef4444' }}>{error}</p>
        )}
      </div>
    )
  }

  return (
    <div 
      className="rounded-lg shadow-sm p-6"
      style={{
        backgroundColor: bgColor,
        border: `1px solid ${borderColor}`,
      }}
    >
      <h3 
        className="text-lg font-semibold mb-4"
        style={{ color: textColor }}
      >
        {title}
      </h3>
      
      <form onSubmit={handleSubmit}>
        <div className="space-y-4">
          {fields.map(renderField)}
        </div>

        <div 
          className="flex justify-end space-x-3 mt-6 pt-4"
          style={{ borderTop: `1px solid ${borderColor}` }}
        >
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 text-sm font-medium rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            style={{
              backgroundColor: 'transparent',
              color: textColor,
              border: `1px solid ${borderColor}`,
            }}
            disabled={loading}
          >
            Cancel
          </button>
          <button
            type="submit"
            className="px-4 py-2 text-sm font-medium text-white rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
            style={{
              backgroundColor: loading ? '#6b7280' : '#3b82f6',
            }}
            disabled={loading}
          >
            {loading ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </form>
    </div>
  )
}
