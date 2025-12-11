import { api, CACHE_TTL } from '../client'
import type {
  BackendArraysResponse,
  BackendConfigResponse,
} from '../types/hierarchy'
import type {
  InverterArray,
  BatteryArray,
  HomeHierarchy,
  SystemConfig,
} from '../types/hierarchy'

/**
 * Hierarchy service - handles home/array/battery hierarchy
 */
export const hierarchyService = {
  /**
   * Get all arrays
   */
  async getArrays(): Promise<InverterArray[]> {
    const response = await api.get<BackendArraysResponse>(
      '/api/arrays',
      { ttl: CACHE_TTL.HIERARCHY, key: 'hierarchy:arrays' }
    )
    
    if (!response.arrays) {
      return []
    }
    
    return response.arrays.map((arr) => ({
      id: arr.id,
      name: arr.name || arr.id,
      inverterIds: arr.inverter_ids || [],
      batteryArrayId: arr.attached_pack_ids?.[0] || null, // Simplified - assumes single attachment
    }))
  },

  /**
   * Get system configuration (home hierarchy)
   */
  async getConfig(): Promise<SystemConfig> {
    const response = await api.get<BackendConfigResponse>(
      '/api/config',
      { ttl: CACHE_TTL.CONFIG, key: 'hierarchy:config' }
    )
    
    if (!response.config) {
      throw new Error('No configuration available')
    }
    
    const config = response.config
    
    return {
      home: {
        id: config.home?.id || 'home',
        name: config.home?.name || 'Home',
        description: config.home?.description,
      },
      arrays: (config.arrays || []).map((arr) => ({
        id: arr.id,
        name: arr.name || arr.id,
        inverterIds: arr.inverter_ids || [],
      })),
      batteryBankArrays: (config.battery_bank_arrays || []).map((bat) => ({
        id: bat.id,
        name: bat.name || bat.id,
        batteryBankIds: bat.battery_bank_ids || [],
      })),
      batteryBankArrayAttachments: config.battery_bank_array_attachments || [],
    }
  },

  /**
   * Get complete home hierarchy
   */
  async getHomeHierarchy(): Promise<HomeHierarchy> {
    const config = await this.getConfig()
    
    // Get device name maps from config response
    const response = await api.get<BackendConfigResponse>(
      '/api/config',
      { ttl: CACHE_TTL.CONFIG, key: 'hierarchy:config:full' }
    )
    
    const inverterNameMap = new Map<string, string>()
    const batteryNameMap = new Map<string, string>()
    const meterNameMap = new Map<string, string>()
    
    if (response.config) {
      // Map inverter IDs to names
      if (response.config.inverters) {
        response.config.inverters.forEach((inv) => {
          if (inv.name) {
            inverterNameMap.set(inv.id, inv.name)
          }
        })
      }
      
      // Map battery bank IDs to names
      if (response.config.battery_banks) {
        response.config.battery_banks.forEach((bank) => {
          if (bank.name) {
            batteryNameMap.set(bank.id, bank.name)
          }
        })
      }
      
      // Map meter IDs to names
      if (response.config.meters) {
        response.config.meters.forEach((meter) => {
          if (meter.name) {
            meterNameMap.set(meter.id, meter.name)
          }
        })
      }
    }
    
    // Build battery arrays with attachments
    const batteryArrays: BatteryArray[] = config.batteryBankArrays.map((bat) => {
      const attachment = config.batteryBankArrayAttachments.find(
        (att) => att.batteryBankArrayId === bat.id
      )
      return {
        id: bat.id,
        name: bat.name,
        batteryBankIds: bat.batteryBankIds,
        attachedInverterArrayId: attachment?.inverterArrayId || null,
      }
    })
    
    // Build inverter arrays with battery attachments
    const inverterArrays: InverterArray[] = config.arrays.map((arr) => {
      const attachment = config.batteryBankArrayAttachments.find(
        (att) => att.inverterArrayId === arr.id
      )
      return {
        id: arr.id,
        name: arr.name,
        inverterIds: arr.inverterIds,
        batteryArrayId: attachment?.batteryBankArrayId || null,
      }
    })
    
    return {
      id: config.home.id,
      name: config.home.name,
      inverterArrays,
      batteryArrays,
      // Include name maps for use in DataProvider
      _deviceNames: {
        inverters: inverterNameMap,
        batteries: batteryNameMap,
        meters: meterNameMap,
      } as any,
    }
  },
}

