import React, { useState, useEffect } from 'react'
import { api } from '../../lib/api'
import { useTheme } from '../../contexts/ThemeContext'
import { Home, Layers, Battery, Link2, Plus, Trash2, Save, X } from 'lucide-react'

interface HierarchyWizardProps {
  config: any
  onSave?: (config: any) => void
  saving?: boolean
}

interface HomeConfig {
  id: string
  name?: string
  description?: string
}

interface ArrayConfig {
  id: string
  name?: string
  inverter_ids: string[]
}

interface BatteryBankConfig {
  id: string
  name?: string
}

interface BatteryBankArrayConfig {
  id: string
  name?: string
  battery_bank_ids: string[]
}

interface Attachment {
  battery_bank_array_id: string
  inverter_array_id: string
  attached_since: string
  detached_at: string | null
}

export const HierarchyWizard: React.FC<HierarchyWizardProps> = ({
  config,
  onSave,
  saving: externalSaving = false
}) => {
  const { theme } = useTheme()
  const [home, setHome] = useState<HomeConfig>({ id: 'home', name: '', description: '' })
  const [arrays, setArrays] = useState<ArrayConfig[]>([])
  const [batteryBanks, setBatteryBanks] = useState<BatteryBankConfig[]>([])
  const [batteryBankArrays, setBatteryBankArrays] = useState<BatteryBankArrayConfig[]>([])
  const [attachments, setAttachments] = useState<Attachment[]>([])
  const [availableInverters, setAvailableInverters] = useState<Array<{id: string, name: string}>>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  
  const isSaving = externalSaving || saving

  const textColor = theme === 'dark' ? '#ffffff' : '#1f2937'
  const textSecondary = theme === 'dark' ? 'rgba(255, 255, 255, 0.7)' : '#6b7280'
  const cardBg = theme === 'dark' ? '#374151' : '#f3f4f6'
  const borderColor = theme === 'dark' ? '#4b5563' : '#d1d5db'
  const buttonBg = theme === 'dark' ? '#4b5563' : '#e5e7eb'
  const buttonHoverBg = theme === 'dark' ? '#6b7280' : '#d1d5db'

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      // Load current config
      const homeConfig = config?.home || { id: 'home', name: '', description: '' }
      setHome(homeConfig)
      
      // Load arrays
      const arraysRes = await api.get('/api/arrays') as any
      setArrays(arraysRes?.arrays || [])
      
      // Load inverters
      const invertersRes = await api.get('/api/inverters') as any
      const inverters = invertersRes?.inverters?.map((inv: any) => ({
        id: inv.id || inv,
        name: inv.name || inv.id || inv
      })) || []
      setAvailableInverters(inverters)
      
      // Load battery banks
      const batteryRes = await api.get('/api/battery/configured_banks') as any
      const banks = batteryRes?.configured_banks || []
      setBatteryBanks(banks.map((b: any) => ({ id: b.id, name: b.name })))
      
      // Load battery bank arrays and attachments from config
      if (config?.battery_bank_arrays) {
        setBatteryBankArrays(config.battery_bank_arrays)
      }
      if (config?.battery_bank_array_attachments) {
        setAttachments(config.battery_bank_array_attachments)
      }
    } catch (e) {
      console.error('Error loading hierarchy data:', e)
    } finally {
      setLoading(false)
    }
  }

  const addArray = () => {
    const newId = `array${arrays.length + 1}`
    setArrays([...arrays, { id: newId, name: '', inverter_ids: [] }])
  }

  const removeArray = (arrayId: string) => {
    setArrays(arrays.filter(a => a.id !== arrayId))
    // Remove attachments for this array
    setAttachments(attachments.filter(a => a.inverter_array_id !== arrayId))
  }

  const updateArray = (arrayId: string, updates: Partial<ArrayConfig>) => {
    setArrays(arrays.map(a => a.id === arrayId ? { ...a, ...updates } : a))
  }

  const toggleInverterInArray = (arrayId: string, inverterId: string) => {
    const array = arrays.find(a => a.id === arrayId)
    if (!array) return
    
    if (array.inverter_ids.includes(inverterId)) {
      updateArray(arrayId, { inverter_ids: array.inverter_ids.filter(id => id !== inverterId) })
    } else {
      updateArray(arrayId, { inverter_ids: [...array.inverter_ids, inverterId] })
    }
  }

  const addBatteryBankArray = () => {
    const newId = `battery_array${batteryBankArrays.length + 1}`
    setBatteryBankArrays([...batteryBankArrays, { id: newId, name: '', battery_bank_ids: [] }])
  }

  const removeBatteryBankArray = (arrayId: string) => {
    setBatteryBankArrays(batteryBankArrays.filter(a => a.id !== arrayId))
    // Remove attachments for this array
    setAttachments(attachments.filter(a => a.battery_bank_array_id !== arrayId))
  }

  const updateBatteryBankArray = (arrayId: string, updates: Partial<BatteryBankArrayConfig>) => {
    setBatteryBankArrays(batteryBankArrays.map(a => a.id === arrayId ? { ...a, ...updates } : a))
  }

  const toggleBatteryBankInArray = (arrayId: string, bankId: string) => {
    const array = batteryBankArrays.find(a => a.id === arrayId)
    if (!array) return
    
    if (array.battery_bank_ids.includes(bankId)) {
      updateBatteryBankArray(arrayId, { battery_bank_ids: array.battery_bank_ids.filter(id => id !== bankId) })
    } else {
      updateBatteryBankArray(arrayId, { battery_bank_ids: [...array.battery_bank_ids, bankId] })
    }
  }

  const attachBatteryBankArrayToInverterArray = (batteryArrayId: string, inverterArrayId: string) => {
    // Remove any existing attachment for this battery array
    const filtered = attachments.filter(a => a.battery_bank_array_id !== batteryArrayId)
    
    // Add new attachment
    const newAttachment: Attachment = {
      battery_bank_array_id: batteryArrayId,
      inverter_array_id: inverterArrayId,
      attached_since: new Date().toISOString(),
      detached_at: null
    }
    
    setAttachments([...filtered, newAttachment])
  }

  const detachBatteryBankArray = (batteryArrayId: string) => {
    setAttachments(attachments.map(a => 
      a.battery_bank_array_id === batteryArrayId 
        ? { ...a, detached_at: new Date().toISOString() }
        : a
    ))
  }

  const getAttachedInverterArray = (batteryArrayId: string): string | null => {
    const attachment = attachments.find(a => 
      a.battery_bank_array_id === batteryArrayId && a.detached_at === null
    )
    return attachment?.inverter_array_id || null
  }

  const handleSave = async () => {
    try {
      setSaving(true)
      
      // Prepare configuration updates
      const configUpdate: any = {}
      
      // Update home configuration
      if (home.id || home.name || home.description) {
        configUpdate.home = home
      }
      
      // Update arrays
      if (arrays.length > 0) {
        configUpdate.arrays = arrays
        
        // Also update inverter array_ids
        const inverterUpdates: any = {}
        arrays.forEach(array => {
          array.inverter_ids.forEach(invId => {
            if (!inverterUpdates[invId]) {
              inverterUpdates[invId] = { array_id: array.id }
            }
          })
        })
        // Note: Inverter array_id updates would need to be done separately
        // or through a different endpoint
      }
      
      // Update battery bank arrays
      if (batteryBankArrays.length > 0) {
        configUpdate.battery_bank_arrays = batteryBankArrays
      }
      
      // Update attachments (only active ones)
      const activeAttachments = attachments.filter(a => a.detached_at === null)
      if (activeAttachments.length > 0) {
        configUpdate.battery_bank_array_attachments = activeAttachments
      }
      
      // Save via API
      const response = await api.post('/api/config', configUpdate) as any
      
      if (response?.status === 'success' || response?.status === 'ok') {
        alert('Hierarchy configuration saved successfully!')
        if (onSave) {
          await onSave(configUpdate)
        }
      } else {
        alert(`Failed to save: ${response?.message || 'Unknown error'}`)
      }
    } catch (error: any) {
      console.error('Error saving hierarchy:', error)
      alert(`Failed to save hierarchy configuration: ${error?.message || error}`)
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return <div className="text-center py-8" style={{ color: textColor }}>Loading...</div>
  }

  return (
    <div className="space-y-6">
      {/* Home Configuration */}
      <div 
        className="p-6 rounded-lg"
        style={{
          backgroundColor: cardBg,
          border: `1px solid ${borderColor}`,
        }}
      >
        <div className="flex items-center gap-3 mb-4">
          <Home className="w-5 h-5" style={{ color: textColor }} />
          <div>
            <h3 className="font-semibold" style={{ color: textColor }}>Home Configuration</h3>
            <p className="text-sm" style={{ color: textSecondary }}>
              Top-level home settings
            </p>
          </div>
        </div>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1" style={{ color: textColor }}>
              Home ID
            </label>
            <input
              type="text"
              value={home.id}
              onChange={(e) => setHome({ ...home, id: e.target.value })}
              className="w-full px-3 py-2 rounded-lg text-sm"
              style={{
                backgroundColor: theme === 'dark' ? '#1f2937' : '#ffffff',
                color: textColor,
                border: `1px solid ${borderColor}`,
              }}
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-1" style={{ color: textColor }}>
              Home Name
            </label>
            <input
              type="text"
              value={home.name || ''}
              onChange={(e) => setHome({ ...home, name: e.target.value })}
              className="w-full px-3 py-2 rounded-lg text-sm"
              style={{
                backgroundColor: theme === 'dark' ? '#1f2937' : '#ffffff',
                color: textColor,
                border: `1px solid ${borderColor}`,
              }}
              placeholder="My Solar Home"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-1" style={{ color: textColor }}>
              Description
            </label>
            <textarea
              value={home.description || ''}
              onChange={(e) => setHome({ ...home, description: e.target.value })}
              className="w-full px-3 py-2 rounded-lg text-sm"
              rows={2}
              style={{
                backgroundColor: theme === 'dark' ? '#1f2937' : '#ffffff',
                color: textColor,
                border: `1px solid ${borderColor}`,
              }}
              placeholder="Main residential solar system"
            />
          </div>
        </div>
      </div>

      {/* Arrays of Inverters */}
      <div 
        className="p-6 rounded-lg"
        style={{
          backgroundColor: cardBg,
          border: `1px solid ${borderColor}`,
        }}
      >
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <Layers className="w-5 h-5" style={{ color: textColor }} />
            <div>
              <h3 className="font-semibold" style={{ color: textColor }}>Arrays of Inverters</h3>
              <p className="text-sm" style={{ color: textSecondary }}>
                Group inverters into arrays
              </p>
            </div>
          </div>
          <button
            onClick={addArray}
            className="px-3 py-2 rounded-lg text-sm font-medium flex items-center gap-2"
            style={{
              backgroundColor: buttonBg,
              color: textColor,
            }}
          >
            <Plus className="w-4 h-4" />
            Add Array
          </button>
        </div>
        
        <div className="space-y-4">
          {arrays.map((array) => (
            <div
              key={array.id}
              className="p-4 rounded-lg"
              style={{
                backgroundColor: theme === 'dark' ? '#1f2937' : '#ffffff',
                border: `1px solid ${borderColor}`,
              }}
            >
              <div className="flex items-center justify-between mb-3">
                <div className="flex-1">
                  <input
                    type="text"
                    value={array.id}
                    onChange={(e) => updateArray(array.id, { id: e.target.value })}
                    className="text-sm font-medium mb-1 px-2 py-1 rounded"
                    style={{
                      backgroundColor: theme === 'dark' ? '#374151' : '#f3f4f6',
                      color: textColor,
                      border: `1px solid ${borderColor}`,
                    }}
                    placeholder="Array ID"
                  />
                  <input
                    type="text"
                    value={array.name || ''}
                    onChange={(e) => updateArray(array.id, { name: e.target.value })}
                    className="text-sm w-full px-2 py-1 rounded"
                    style={{
                      backgroundColor: theme === 'dark' ? '#374151' : '#f3f4f6',
                      color: textColor,
                      border: `1px solid ${borderColor}`,
                    }}
                    placeholder="Array Name"
                  />
                </div>
                <button
                  onClick={() => removeArray(array.id)}
                  className="p-2 rounded-lg hover:opacity-80"
                  style={{ color: '#ef4444' }}
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
              
              <div>
                <label className="block text-xs font-medium mb-2" style={{ color: textSecondary }}>
                  Select Inverters:
                </label>
                <div className="flex flex-wrap gap-2">
                  {availableInverters.map((inv) => (
                    <label
                      key={inv.id}
                      className="flex items-center gap-2 px-3 py-1 rounded-lg cursor-pointer"
                      style={{
                        backgroundColor: array.inverter_ids.includes(inv.id) 
                          ? (theme === 'dark' ? '#3b82f6' : '#dbeafe')
                          : buttonBg,
                        color: array.inverter_ids.includes(inv.id) ? '#ffffff' : textColor,
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={array.inverter_ids.includes(inv.id)}
                        onChange={() => toggleInverterInArray(array.id, inv.id)}
                        className="hidden"
                      />
                      <span className="text-xs">{inv.name || inv.id}</span>
                    </label>
                  ))}
                </div>
              </div>
            </div>
          ))}
          
          {arrays.length === 0 && (
            <div className="text-center py-8 text-sm" style={{ color: textSecondary }}>
              No arrays configured. Click "Add Array" to create one.
            </div>
          )}
        </div>
      </div>

      {/* Arrays of Battery Banks */}
      <div 
        className="p-6 rounded-lg"
        style={{
          backgroundColor: cardBg,
          border: `1px solid ${borderColor}`,
        }}
      >
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <Battery className="w-5 h-5" style={{ color: textColor }} />
            <div>
              <h3 className="font-semibold" style={{ color: textColor }}>Arrays of Battery Banks</h3>
              <p className="text-sm" style={{ color: textSecondary }}>
                Group battery banks into arrays
              </p>
            </div>
          </div>
          <button
            onClick={addBatteryBankArray}
            className="px-3 py-2 rounded-lg text-sm font-medium flex items-center gap-2"
            style={{
              backgroundColor: buttonBg,
              color: textColor,
            }}
          >
            <Plus className="w-4 h-4" />
            Add Battery Array
          </button>
        </div>
        
        <div className="space-y-4">
          {batteryBankArrays.map((batteryArray) => {
            const attachedTo = getAttachedInverterArray(batteryArray.id)
            return (
              <div
                key={batteryArray.id}
                className="p-4 rounded-lg"
                style={{
                  backgroundColor: theme === 'dark' ? '#1f2937' : '#ffffff',
                  border: `1px solid ${borderColor}`,
                }}
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="flex-1">
                    <input
                      type="text"
                      value={batteryArray.id}
                      onChange={(e) => updateBatteryBankArray(batteryArray.id, { id: e.target.value })}
                      className="text-sm font-medium mb-1 px-2 py-1 rounded"
                      style={{
                        backgroundColor: theme === 'dark' ? '#374151' : '#f3f4f6',
                        color: textColor,
                        border: `1px solid ${borderColor}`,
                      }}
                      placeholder="Battery Array ID"
                    />
                    <input
                      type="text"
                      value={batteryArray.name || ''}
                      onChange={(e) => updateBatteryBankArray(batteryArray.id, { name: e.target.value })}
                      className="text-sm w-full px-2 py-1 rounded"
                      style={{
                        backgroundColor: theme === 'dark' ? '#374151' : '#f3f4f6',
                        color: textColor,
                        border: `1px solid ${borderColor}`,
                      }}
                      placeholder="Battery Array Name"
                    />
                  </div>
                  <button
                    onClick={() => removeBatteryBankArray(batteryArray.id)}
                    className="p-2 rounded-lg hover:opacity-80"
                    style={{ color: '#ef4444' }}
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
                
                <div className="mb-3">
                  <label className="block text-xs font-medium mb-2" style={{ color: textSecondary }}>
                    Select Battery Banks:
                  </label>
                  <div className="flex flex-wrap gap-2">
                    {batteryBanks.map((bank) => (
                      <label
                        key={bank.id}
                        className="flex items-center gap-2 px-3 py-1 rounded-lg cursor-pointer"
                        style={{
                          backgroundColor: batteryArray.battery_bank_ids.includes(bank.id)
                            ? (theme === 'dark' ? '#3b82f6' : '#dbeafe')
                            : buttonBg,
                          color: batteryArray.battery_bank_ids.includes(bank.id) ? '#ffffff' : textColor,
                        }}
                      >
                        <input
                          type="checkbox"
                          checked={batteryArray.battery_bank_ids.includes(bank.id)}
                          onChange={() => toggleBatteryBankInArray(batteryArray.id, bank.id)}
                          className="hidden"
                        />
                        <span className="text-xs">{bank.name || bank.id}</span>
                      </label>
                    ))}
                  </div>
                </div>
                
                {/* Attachment to Inverter Array */}
                <div>
                  <label className="block text-xs font-medium mb-2" style={{ color: textSecondary }}>
                    Attach to Inverter Array (1:1):
                  </label>
                  {attachedTo ? (
                    <div className="flex items-center gap-2">
                      <span className="text-sm px-3 py-1 rounded-lg" style={{ 
                        backgroundColor: theme === 'dark' ? '#10b981' : '#d1fae5',
                        color: theme === 'dark' ? '#ffffff' : '#065f46'
                      }}>
                        Attached to: {attachedTo}
                      </span>
                      <button
                        onClick={() => detachBatteryBankArray(batteryArray.id)}
                        className="px-2 py-1 rounded text-xs"
                        style={{
                          backgroundColor: buttonBg,
                          color: textColor,
                        }}
                      >
                        Detach
                      </button>
                    </div>
                  ) : (
                    <select
                      value=""
                      onChange={(e) => {
                        if (e.target.value) {
                          attachBatteryBankArrayToInverterArray(batteryArray.id, e.target.value)
                        }
                      }}
                      className="w-full px-3 py-2 rounded-lg text-sm"
                      style={{
                        backgroundColor: theme === 'dark' ? '#1f2937' : '#ffffff',
                        color: textColor,
                        border: `1px solid ${borderColor}`,
                      }}
                    >
                      <option value="">Select Inverter Array...</option>
                      {arrays.map((arr) => (
                        <option key={arr.id} value={arr.id}>
                          {arr.name || arr.id}
                        </option>
                      ))}
                    </select>
                  )}
                </div>
              </div>
            )
          })}
          
          {batteryBankArrays.length === 0 && (
            <div className="text-center py-8 text-sm" style={{ color: textSecondary }}>
              No battery bank arrays configured. Click "Add Battery Array" to create one.
            </div>
          )}
        </div>
      </div>

      {/* Save Button */}
      <div className="flex justify-end gap-3">
        <button
          onClick={handleSave}
          disabled={isSaving}
          className="px-6 py-2 rounded-lg font-medium flex items-center gap-2"
          style={{
            backgroundColor: isSaving ? buttonBg : '#3b82f6',
            color: '#ffffff',
            opacity: isSaving ? 0.6 : 1,
            cursor: isSaving ? 'not-allowed' : 'pointer',
          }}
        >
          <Save className="w-4 h-4" />
          {isSaving ? 'Saving...' : 'Save Configuration'}
        </button>
      </div>
    </div>
  )
}

