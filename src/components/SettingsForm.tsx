import React, { useState } from 'react'

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
  const [values, setValues] = useState<Record<string, any>>(
    fields.reduce((acc, field) => {
      acc[field.key] = field.value
      return acc
    }, {} as Record<string, any>)
  )
  const [errors, setErrors] = useState<Record<string, string>>({})

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
        <label htmlFor={fieldId} className="block text-sm font-medium text-gray-700 mb-1">
          {field.label}
          {field.unit && <span className="text-gray-500 ml-1">({field.unit})</span>}
        </label>
        
        {field.description && (
          <p className="text-xs text-gray-500 mb-2">{field.description}</p>
        )}

        {field.type === 'text' && (
          <input
            id={fieldId}
            type="text"
            value={values[field.key] || ''}
            onChange={(e) => handleChange(field.key, e.target.value)}
            className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
              error ? 'border-red-500' : 'border-gray-300'
            }`}
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
            className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
              error ? 'border-red-500' : 'border-gray-300'
            }`}
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
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              disabled={loading}
            />
            <label htmlFor={fieldId} className="ml-2 text-sm text-gray-700">
              {values[field.key] ? 'Enabled' : 'Disabled'}
            </label>
          </div>
        )}

        {field.type === 'select' && field.options && (
          <select
            id={fieldId}
            value={values[field.key] || ''}
            onChange={(e) => handleChange(field.key, e.target.value)}
            className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
              error ? 'border-red-500' : 'border-gray-300'
            }`}
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
          <p className="mt-1 text-sm text-red-600">{error}</p>
        )}
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow-sm p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">{title}</h3>
      
      <form onSubmit={handleSubmit}>
        <div className="space-y-4">
          {fields.map(renderField)}
        </div>

        <div className="flex justify-end space-x-3 mt-6 pt-4 border-t border-gray-200">
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={loading}
          >
            Cancel
          </button>
          <button
            type="submit"
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
            disabled={loading}
          >
            {loading ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </form>
    </div>
  )
}
