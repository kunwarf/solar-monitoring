import React, { useEffect, useMemo, useState } from 'react'
import { api } from '../lib/api'
import { DeviceHealthIndicator } from './DeviceHealthIndicator'

type InverterAdapterType = 'senergy' | 'powdrive'
type BatteryAdapterType = 'pytes'

interface SerialPort {
  device: string
  description?: string
  hwid?: string
}

interface InverterAdapterConfig {
  type: InverterAdapterType
  transport?: 'rtu' | 'tcp'
  unit_id?: number
  serial_port?: string | null
  baudrate?: number
  parity?: string
  stopbits?: number
  bytesize?: number
  register_map_file?: string | null
}

interface InverterConfigItem {
  id: string
  name?: string
  adapter: InverterAdapterConfig
  connected?: boolean
}

interface BatteryAdapterConfig {
  type: BatteryAdapterType
  serial_port?: string | null
  baudrate?: number
  parity?: string
  stopbits?: number
  bytesize?: number
  batteries?: number
  cells_per_battery?: number
}

interface BatteryBankConfig {
  id?: string
  name?: string
  adapter: BatteryAdapterConfig
  connected?: boolean
}

export const DeviceManager: React.FC = () => {
  const [ports, setPorts] = useState<SerialPort[]>([])
  const [adapters, setAdapters] = useState<{ inverter_adapters: { value: InverterAdapterType, label: string }[], battery_adapters: { value: BatteryAdapterType, label: string }[] }>({ inverter_adapters: [], battery_adapters: [] })
  const [inverters, setInverters] = useState<InverterConfigItem[]>([])
  const [battery, setBattery] = useState<BatteryBankConfig | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [hasConnections, setHasConnections] = useState(false)
  const [lastUpdate, setLastUpdate] = useState<string>('')

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      try {
        const [p, a, d] = await Promise.all([
          api.get('/api/devices/serial-ports'),
          api.get('/api/adapters'),
          api.get('/api/devices'),
        ])
        setPorts(p.ports || [])
        setAdapters(a)
        setInverters((d.inverters || []).map((x: any) => ({
          id: x.id,
          name: x.name || x.id,
          connected: x.connected || false,
          adapter: {
            type: (x.adapter?.type || 'senergy') as InverterAdapterType,
            transport: (x.adapter?.transport || 'rtu'),
            unit_id: x.adapter?.unit_id ?? 1,
            serial_port: x.adapter?.serial_port || null,
            baudrate: x.adapter?.baudrate ?? 9600,
            parity: x.adapter?.parity || 'N',
            stopbits: x.adapter?.stopbits ?? 1,
            bytesize: x.adapter?.bytesize ?? 8,
            register_map_file: x.adapter?.register_map_file || null,
          }
        })))
        const batteryConfig = d.battery_bank || null
        if (batteryConfig) {
          setBattery({ ...batteryConfig, connected: batteryConfig.connected || false })
        } else {
          setBattery(null)
        }
        setHasConnections(d.has_connections || false)
        setLastUpdate(new Date().toLocaleTimeString())
      } finally {
        setLoading(false)
      }
    }
    load()
    const interval = setInterval(load, 10000) // Refresh every 10 seconds
    return () => clearInterval(interval)
  }, [])

  const addInverter = () => {
    const idx = inverters.length + 1
    setInverters(prev => ([...prev, {
      id: `inv${idx}`,
      name: `Inverter ${idx}`,
      adapter: { type: 'senergy', transport: 'rtu', unit_id: 1, serial_port: null, baudrate: 9600, parity: 'N', stopbits: 1, bytesize: 8, register_map_file: null }
    }]))
  }

  const removeInverter = (id: string) => setInverters(prev => prev.filter(i => i.id !== id))

  const updateInv = (id: string, patch: Partial<InverterConfigItem>) => setInverters(prev => prev.map(i => i.id === id ? { ...i, ...patch, adapter: { ...i.adapter, ...(patch as any).adapter } } : i))
  const updateInvAdapter = (id: string, patch: Partial<InverterAdapterConfig>) => setInverters(prev => prev.map(i => i.id === id ? { ...i, adapter: { ...i.adapter, ...patch } } : i))

  const saveAndConnect = async () => {
    try {
      setSaving(true)
      await api.post('/api/devices', { inverters, battery_bank: battery })
      await api.post('/api/devices/connect', {})
      // Reload to get connection status
      const d = await api.get('/api/devices')
      setInverters((d.inverters || []).map((x: any) => ({
        id: x.id,
        name: x.name || x.id,
        connected: x.connected || false,
        adapter: {
          type: (x.adapter?.type || 'senergy') as InverterAdapterType,
          transport: (x.adapter?.transport || 'rtu'),
          unit_id: x.adapter?.unit_id ?? 1,
          serial_port: x.adapter?.serial_port || null,
          baudrate: x.adapter?.baudrate ?? 9600,
          parity: x.adapter?.parity || 'N',
          stopbits: x.adapter?.stopbits ?? 1,
          bytesize: x.adapter?.bytesize ?? 8,
          register_map_file: x.adapter?.register_map_file || null,
        }
      })))
      const batteryConfig = d.battery_bank || null
      if (batteryConfig) {
        setBattery({ ...batteryConfig, connected: batteryConfig.connected || false })
      } else {
        setBattery(null)
      }
      setHasConnections(d.has_connections || false)
      alert('Devices saved and connection attempted. Check status and telemetry.')
    } catch (e: any) {
      alert(`Failed to save/connect: ${e?.message || e}`)
    } finally {
      setSaving(false)
    }
  }

  const disconnect = async () => {
    try {
      setSaving(true)
      await api.post('/api/devices/disconnect', {})
      // Wait a bit for the polling loop to process the disconnect
      await new Promise(resolve => setTimeout(resolve, 500))
      // Poll until we get the disconnected state (with timeout)
      let attempts = 0
      const maxAttempts = 10
      while (attempts < maxAttempts) {
        const d = await api.get('/api/devices')
        const hasConnections = d.has_connections || false
        if (!hasConnections) {
          // Disconnected state confirmed
          break
        }
        attempts++
        await new Promise(resolve => setTimeout(resolve, 300))
      }
      // Final reload to get updated connection status
      const d = await api.get('/api/devices')
      setInverters((d.inverters || []).map((x: any) => ({
        id: x.id,
        name: x.name || x.id,
        connected: x.connected || false,
        adapter: {
          type: (x.adapter?.type || 'senergy') as InverterAdapterType,
          transport: (x.adapter?.transport || 'rtu'),
          unit_id: x.adapter?.unit_id ?? 1,
          serial_port: x.adapter?.serial_port || null,
          baudrate: x.adapter?.baudrate ?? 9600,
          parity: x.adapter?.parity || 'N',
          stopbits: x.adapter?.stopbits ?? 1,
          bytesize: x.adapter?.bytesize ?? 8,
          register_map_file: x.adapter?.register_map_file || null,
        }
      })))
      const batteryConfig = d.battery_bank || null
      if (batteryConfig) {
        setBattery({ ...batteryConfig, connected: batteryConfig.connected || false })
      } else {
        setBattery(null)
      }
      setHasConnections(d.has_connections || false)
      alert('Devices disconnected successfully.')
    } catch (e: any) {
      alert(`Failed to disconnect: ${e?.message || e}`)
    } finally {
      setSaving(false)
    }
  }

  const portOptions = useMemo(() => ports.map(p => ({ value: p.device, label: p.description ? `${p.device} - ${p.description}` : p.device })), [ports])

  if (loading) return (
    <div className="bg-white rounded-lg shadow-sm p-6 mb-6"><div className="text-gray-600">Loading devices...</div></div>
  )

  const testConnection = async (deviceId: string, type: 'inverter' | 'battery') => {
    try {
      // Test connection logic would go here
      alert(`Testing connection for ${deviceId}...`)
    } catch (e: any) {
      alert(`Connection test failed: ${e?.message || e}`)
    }
  }

  return (
    <div className="space-y-4">
      {/* Connection Summary Banner */}
      <div className="bg-white rounded-lg shadow-sm p-4 border border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <span className={`inline-flex items-center px-3 py-1.5 rounded-full text-sm font-medium ${
              hasConnections 
                ? 'bg-green-100 text-green-800' 
                : 'bg-gray-100 text-gray-800'
            }`}>
              <span className={`w-2 h-2 rounded-full mr-2 ${
                hasConnections ? 'bg-green-500' : 'bg-gray-400'
              }`}></span>
              {hasConnections ? 'All devices connected' : 'No active connections'}
            </span>
            {lastUpdate && (
              <span className="text-sm text-gray-500">
                Last update: {lastUpdate}
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow-sm p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Devices</h2>
            <p className="text-sm text-gray-600 mt-1">Configure inverters and battery connections. Multiple inverters are supported.</p>
          </div>
          <div className="flex gap-2">
            <button 
              onClick={addInverter} 
              disabled={hasConnections || saving}
              className="px-3 py-1.5 text-sm rounded bg-blue-600 text-white disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Add inverter
            </button>
            {hasConnections ? (
              <button 
                onClick={disconnect} 
                disabled={saving}
                className="px-3 py-1.5 text-sm rounded bg-red-600 text-white disabled:opacity-50"
              >
                {saving ? 'Disconnecting…' : 'Disconnect'}
              </button>
            ) : (
              <button 
                onClick={saveAndConnect} 
                disabled={saving}
                className="px-3 py-1.5 text-sm rounded bg-green-600 text-white disabled:opacity-50"
              >
                {saving ? 'Connecting…' : 'Connect'}
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="space-y-4">
        {inverters.map(inv => (
          <div key={inv.id} className="border rounded-md p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <div className="font-medium">{inv.name} <span className="text-gray-400">({inv.id})</span></div>
                <DeviceHealthIndicator
                  connected={inv.connected || false}
                  warning={false}
                  lastUpdate={lastUpdate}
                  onTest={() => testConnection(inv.id, 'inverter')}
                />
              </div>
              {!hasConnections && (
                <button onClick={() => removeInverter(inv.id)} className="text-xs text-red-600 hover:underline">remove</button>
              )}
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div>
                <label className="block text-sm text-gray-600 mb-1">Model</label>
                <select 
                  value={inv.adapter.type}
                  onChange={e => updateInvAdapter(inv.id, { type: e.target.value as InverterAdapterType })}
                  disabled={hasConnections}
                  className="w-full border rounded px-2 py-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {adapters.inverter_adapters.map(opt => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm text-gray-600 mb-1">Connections</label>
                <select 
                  value={inv.adapter.serial_port || ''}
                  onChange={e => updateInvAdapter(inv.id, { serial_port: e.target.value })}
                  disabled={hasConnections}
                  className="w-full border rounded px-2 py-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <option value="">Select port…</option>
                  {portOptions.map(p => <option key={p.value} value={p.value}>{p.label}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm text-gray-600 mb-1">Unit ID</label>
                <input 
                  type="number" 
                  value={inv.adapter.unit_id || 1} 
                  onChange={e => updateInvAdapter(inv.id, { unit_id: parseInt(e.target.value || '1', 10) })} 
                  disabled={hasConnections}
                  className="w-full border rounded px-2 py-1.5 disabled:opacity-50 disabled:cursor-not-allowed" 
                />
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-6">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <div className="font-medium">Battery</div>
            <DeviceHealthIndicator
              connected={battery?.connected || false}
              warning={false}
              lastUpdate={lastUpdate}
              onTest={() => battery && testConnection(battery.id || 'battery', 'battery')}
            />
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div>
            <label className="block text-sm text-gray-600 mb-1">Battery</label>
            <select 
              value={(battery?.adapter?.type || 'pytes') as BatteryAdapterType}
              onChange={e => setBattery({ id: battery?.id || 'battery', name: battery?.name || 'Battery Bank', adapter: { ...(battery?.adapter || {}), type: e.target.value as BatteryAdapterType } })}
              disabled={hasConnections}
              className="w-full border rounded px-2 py-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {adapters.battery_adapters.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">Connections</label>
            <select 
              value={battery?.adapter?.serial_port || ''}
              onChange={e => setBattery(prev => ({ id: prev?.id || 'battery', name: prev?.name || 'Battery Bank', adapter: { ...(prev?.adapter || { type: 'pytes' }), serial_port: e.target.value } }))}
              disabled={hasConnections}
              className="w-full border rounded px-2 py-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <option value="">Select port…</option>
              {portOptions.map(p => <option key={p.value} value={p.value}>{p.label}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">Batteries</label>
            <input 
              type="number" 
              value={battery?.adapter?.batteries || 1} 
              onChange={e => setBattery(prev => ({ id: prev?.id || 'battery', name: prev?.name || 'Battery Bank', adapter: { ...(prev?.adapter || { type: 'pytes' }), batteries: parseInt(e.target.value || '1', 10) } }))} 
              disabled={hasConnections}
              className="w-full border rounded px-2 py-1.5 disabled:opacity-50 disabled:cursor-not-allowed" 
            />
          </div>
        </div>
      </div>
    </div>
  )
}


