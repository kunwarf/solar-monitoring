// Backend response types
export interface BackendDeviceInfo {
  id: string
  name?: string
  type: 'inverter' | 'battery' | 'meter'
  model?: string
  serial_number?: string
  status?: 'online' | 'offline' | 'warning'
  [key: string]: any
}

export interface BackendDevicesResponse {
  status: string
  devices?: BackendDeviceInfo[]
}

// Normalized frontend types
export interface Device {
  id: string
  name: string
  type: 'inverter' | 'battery' | 'meter'
  model: string | null
  serialNumber: string | null
  status: 'online' | 'offline' | 'warning'
  metadata?: Record<string, any>
}

