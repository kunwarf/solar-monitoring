// Backend response types
export interface BackendArrayInfo {
  id: string
  name?: string
  inverter_ids?: string[]
  inverter_count?: number
  attached_pack_ids?: string[]
  pack_count?: number
}

export interface BackendArraysResponse {
  status: string
  arrays?: BackendArrayInfo[]
}

export interface BackendConfigResponse {
  status: string
  config?: {
    home?: {
      id: string
      name?: string
      description?: string
    }
    arrays?: Array<{
      id: string
      name?: string
      inverter_ids?: string[]
    }>
    battery_bank_arrays?: Array<{
      id: string
      name?: string
      battery_bank_ids?: string[]
    }>
    battery_bank_array_attachments?: Array<{
      battery_bank_array_id: string
      inverter_array_id: string
      attached_since?: string
      detached_at?: string | null
    }>
  }
}

// Normalized frontend types
export interface InverterArray {
  id: string
  name: string
  inverterIds: string[]
  batteryArrayId: string | null
}

export interface BatteryArray {
  id: string
  name: string
  batteryBankIds: string[]
  attachedInverterArrayId: string | null
}

export interface HomeHierarchy {
  id: string
  name: string
  inverterArrays: InverterArray[]
  batteryArrays: BatteryArray[]
}

