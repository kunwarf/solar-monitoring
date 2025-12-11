/**
 * Hierarchy Manager
 * Singleton manager that loads and maintains the complete system hierarchy
 */

import {
  System,
  InverterArray,
  BatteryArray,
  Inverter,
  BatteryPack,
  Meter,
  type SystemConfig,
  type InverterArrayConfig,
  type BatteryArrayConfig,
  type InverterConfig,
  type BatteryPackConfig,
  type MeterConfig,
} from '../models'
import { hierarchyService } from '../services/hierarchy'
import { telemetryService } from '../services/telemetry'
import { CACHE_TTL } from '../client'
import type { TelemetryData, HomeTelemetryData, BatteryData } from '../types/telemetry'

interface BackendHierarchyResponse {
  hierarchy?: {
    systems?: Array<{
      system_id: string
      name: string
      description?: string
      timezone: string
      inverter_arrays?: Array<{
        array_id: string
        name: string
        system_id: string
        inverters?: Array<InverterConfig>
        attached_battery_array_id?: string | null
      }>
      battery_arrays?: Array<{
        battery_array_id: string
        name: string
        system_id: string
        battery_packs?: Array<BatteryPackConfig>
        attached_inverter_array_id?: string | null
      }>
      meters?: Array<MeterConfig>
    }>
  }
}

export class HierarchyManager {
  private static instance: HierarchyManager | null = null

  private systems: Map<string, System> = new Map()
  private inverters: Map<string, Inverter> = new Map()
  private batteryPacks: Map<string, BatteryPack> = new Map()
  private meters: Map<string, Meter> = new Map()
  private isLoading: boolean = false
  private lastLoadTime: Date | null = null

  private constructor() {
    // Private constructor for singleton
  }

  /**
   * Get singleton instance
   */
  static getInstance(): HierarchyManager {
    if (!HierarchyManager.instance) {
      HierarchyManager.instance = new HierarchyManager()
    }
    return HierarchyManager.instance
  }

  /**
   * Load hierarchy from backend
   */
  async loadHierarchy(): Promise<void> {
    if (this.isLoading) {
      // Wait for existing load to complete
      while (this.isLoading) {
        await new Promise(resolve => setTimeout(resolve, 100))
      }
      return
    }

    this.isLoading = true
    try {
      // Get config from backend
      const response = await hierarchyService.getConfig()
      
      // Try to get full hierarchy from /api/config
      // Use the API client to ensure proper base URL and error handling
      const { api } = await import('../client')
      const fullResponse = await api.get<BackendHierarchyResponse>('/api/config', {
        ttl: CACHE_TTL.CONFIG,
        key: 'hierarchy:config:full'
      })
      
      // Clear existing data
      this.systems.clear()
      this.inverters.clear()
      this.batteryPacks.clear()
      this.meters.clear()

      // Load from hierarchy if available
      if (fullResponse.hierarchy?.systems) {
        for (const systemData of fullResponse.hierarchy.systems) {
          await this._loadSystem(systemData)
        }
      } else {
        // Fallback: build from config response (legacy)
        await this._loadFromConfig(response)
      }

      this.lastLoadTime = new Date()
    } catch (error) {
      console.error('[HierarchyManager] Failed to load hierarchy:', error)
      throw error
    } finally {
      this.isLoading = false
    }
  }

  /**
   * Load system from backend data
   */
  private async _loadSystem(systemData: BackendHierarchyResponse['hierarchy']['systems'][0]): Promise<void> {
    // Create system
    const system = new System({
      system_id: systemData.system_id,
      name: systemData.name,
      description: systemData.description,
      timezone: systemData.timezone,
      inverter_arrays: [],
      battery_arrays: [],
      meters: [],
    })

    // Load inverter arrays
    if (systemData.inverter_arrays) {
      for (const arrayData of systemData.inverter_arrays) {
        const array = new InverterArray({
          array_id: arrayData.array_id,
          name: arrayData.name,
          system_id: arrayData.system_id,
          inverters: [],
          attached_battery_array_id: arrayData.attached_battery_array_id,
        })

        // Load inverters
        if (arrayData.inverters) {
          for (const invData of arrayData.inverters) {
            const inverter = new Inverter(invData)
            array.addInverter(inverter)
            this.inverters.set(inverter.id, inverter)
          }
        }

        system.addInverterArray(array)
      }
    }

    // Load battery arrays
    if (systemData.battery_arrays) {
      for (const arrayData of systemData.battery_arrays) {
        const batteryArray = new BatteryArray({
          battery_array_id: arrayData.battery_array_id,
          name: arrayData.name,
          system_id: arrayData.system_id,
          battery_packs: [],
          attached_inverter_array_id: arrayData.attached_inverter_array_id,
        })

        // Load battery packs
        if (arrayData.battery_packs) {
          for (const packData of arrayData.battery_packs) {
            const pack = new BatteryPack(packData)
            batteryArray.addBatteryPack(pack)
            this.batteryPacks.set(pack.id, pack)
          }
        }

        system.addBatteryArray(batteryArray)
      }
    }

    // Load meters
    if (systemData.meters) {
      for (const meterData of systemData.meters) {
        const meter = new Meter(meterData)
        system.addMeter(meter)
        this.meters.set(meter.id, meter)
      }
    }

    // Establish relationships between arrays
    this._establishArrayRelationships(system)

    this.systems.set(system.systemId, system)
  }

  /**
   * Load from legacy config format (fallback)
   */
  private async _loadFromConfig(config: any): Promise<void> {
    // This is a simplified fallback - would need to be implemented based on legacy config structure
    console.warn('[HierarchyManager] Using legacy config format - full hierarchy may not be available')
  }

  /**
   * Establish relationships between arrays (inverter arrays <-> battery arrays)
   */
  private _establishArrayRelationships(system: System): void {
    // Link inverter arrays to battery arrays
    for (const invArray of system.inverterArrays) {
      if (invArray.attachedBatteryArrayId) {
        const batteryArray = system.getBatteryArray(invArray.attachedBatteryArrayId)
        if (batteryArray) {
          invArray.setAttachedBatteryArray(batteryArray)
          batteryArray.setAttachedInverterArray(invArray)
        }
      }
    }
  }

  /**
   * Update telemetry for a device
   */
  updateTelemetry(deviceId: string, telemetry: TelemetryData): void {
    // Try inverter first
    const inverter = this.inverters.get(deviceId)
    if (inverter) {
      inverter.updateTelemetry(telemetry)
      return
    }

    // Try battery pack
    const pack = this.batteryPacks.get(deviceId)
    if (pack) {
      pack.updateTelemetry(telemetry)
      return
    }

    // Try meter
    const meter = this.meters.get(deviceId)
    if (meter) {
      meter.updateTelemetry(telemetry)
      return
    }
  }

  /**
   * Update battery telemetry
   */
  updateBatteryTelemetry(packId: string, telemetry: BatteryData): void {
    const pack = this.batteryPacks.get(packId)
    if (pack) {
      pack.updateBatteryTelemetry(telemetry)
    }
  }

  /**
   * Update system telemetry
   */
  updateSystemTelemetry(systemId: string, telemetry: HomeTelemetryData): void {
    const system = this.systems.get(systemId)
    if (system) {
      system.updateTelemetry(telemetry)
    }
  }

  /**
   * Update array telemetry
   */
  updateArrayTelemetry(arrayId: string, telemetry: TelemetryData): void {
    // Try inverter array first
    for (const system of this.systems.values()) {
      const array = system.getInverterArray(arrayId)
      if (array) {
        array.updateTelemetry(telemetry)
        return
      }

      // Try battery array
      const batteryArray = system.getBatteryArray(arrayId)
      if (batteryArray) {
        batteryArray.updateTelemetry(telemetry)
        return
      }
    }
  }

  /**
   * Get system by ID
   */
  getSystem(systemId: string): System | null {
    return this.systems.get(systemId) || null
  }

  /**
   * Get inverter by ID
   */
  getInverter(inverterId: string): Inverter | null {
    return this.inverters.get(inverterId) || null
  }

  /**
   * Get battery pack by ID
   */
  getBatteryPack(packId: string): BatteryPack | null {
    return this.batteryPacks.get(packId) || null
  }

  /**
   * Get meter by ID
   */
  getMeter(meterId: string): Meter | null {
    return this.meters.get(meterId) || null
  }

  /**
   * Get all systems
   */
  getAllSystems(): System[] {
    return Array.from(this.systems.values())
  }

  /**
   * Get all inverters
   */
  getAllInverters(): Inverter[] {
    return Array.from(this.inverters.values())
  }

  /**
   * Get all battery packs
   */
  getAllBatteryPacks(): BatteryPack[] {
    return Array.from(this.batteryPacks.values())
  }

  /**
   * Get all meters
   */
  getAllMeters(): Meter[] {
    return Array.from(this.meters.values())
  }

  /**
   * Get system total power
   */
  getSystemTotalPower(systemId: string): number {
    const system = this.getSystem(systemId)
    return system?.getTotalPower() || 0
  }

  /**
   * Get system total battery SOC
   */
  getSystemTotalBatterySOC(systemId: string): number | null {
    const system = this.getSystem(systemId)
    return system?.getTotalBatterySOC() || null
  }

  /**
   * Check if hierarchy is loaded
   */
  isLoaded(): boolean {
    return this.systems.size > 0
  }

  /**
   * Get last load time
   */
  getLastLoadTime(): Date | null {
    return this.lastLoadTime
  }

  /**
   * Clear all data
   */
  clear(): void {
    this.systems.clear()
    this.inverters.clear()
    this.batteryPacks.clear()
    this.meters.clear()
    this.lastLoadTime = null
  }
}

