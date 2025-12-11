/**
 * System Class
 * Represents a system (top-level container) containing arrays and meters
 */

import { InverterArray } from './InverterArray'
import { BatteryArray } from './BatteryArray'
import { Meter } from './Meter'
import { Inverter } from './Inverter'
import { BatteryPack } from './BatteryPack'
import type { HomeTelemetryData } from '../types/telemetry'

export interface SystemConfig {
  system_id: string
  name: string
  description?: string
  timezone: string
  inverter_arrays: Array<InverterArray['id']>
  battery_arrays: Array<BatteryArray['id']>
  meters: Array<Meter['id']>
}

export class System {
  systemId: string
  name: string
  description: string | null
  timezone: string
  inverterArrays: InverterArray[] = []
  batteryArrays: BatteryArray[] = []
  meters: Meter[] = []
  private _telemetry: HomeTelemetryData | null = null
  private _telemetryTimestamp: Date | null = null

  constructor(config: SystemConfig) {
    this.systemId = config.system_id
    this.name = config.name
    this.description = config.description || null
    this.timezone = config.timezone
  }

  /**
   * Add an inverter array to this system
   */
  addInverterArray(array: InverterArray): void {
    if (array.systemId !== this.systemId) {
      throw new Error(`Array ${array.id} does not belong to system ${this.systemId}`)
    }
    if (!this.inverterArrays.find(arr => arr.id === array.id)) {
      this.inverterArrays.push(array)
    }
  }

  /**
   * Add a battery array to this system
   */
  addBatteryArray(array: BatteryArray): void {
    if (array.systemId !== this.systemId) {
      throw new Error(`Battery array ${array.id} does not belong to system ${this.systemId}`)
    }
    if (!this.batteryArrays.find(arr => arr.id === array.id)) {
      this.batteryArrays.push(array)
    }
  }

  /**
   * Add a meter to this system
   */
  addMeter(meter: Meter): void {
    if (meter.systemId !== this.systemId) {
      throw new Error(`Meter ${meter.id} does not belong to system ${this.systemId}`)
    }
    if (!this.meters.find(m => m.id === meter.id)) {
      this.meters.push(meter)
    }
  }

  /**
   * Get inverter array by ID
   */
  getInverterArray(arrayId: string): InverterArray | null {
    return this.inverterArrays.find(arr => arr.id === arrayId) || null
  }

  /**
   * Get battery array by ID
   */
  getBatteryArray(arrayId: string): BatteryArray | null {
    return this.batteryArrays.find(arr => arr.id === arrayId) || null
  }

  /**
   * Get meter by ID
   */
  getMeter(meterId: string): Meter | null {
    return this.meters.find(m => m.id === meterId) || null
  }

  /**
   * Get inverter by ID (searches all arrays)
   */
  getInverterById(inverterId: string): Inverter | null {
    for (const array of this.inverterArrays) {
      const inverter = array.getInverter(inverterId)
      if (inverter) return inverter
    }
    return null
  }

  /**
   * Get battery pack by ID (searches all arrays)
   */
  getBatteryPackById(packId: string): BatteryPack | null {
    for (const array of this.batteryArrays) {
      const pack = array.getBatteryPack(packId)
      if (pack) return pack
    }
    return null
  }

  /**
   * Get all inverters from all arrays
   */
  getAllInverters(): Inverter[] {
    const inverters: Inverter[] = []
    for (const array of this.inverterArrays) {
      inverters.push(...array.inverters)
    }
    return inverters
  }

  /**
   * Get all battery packs from all arrays
   */
  getAllBatteryPacks(): BatteryPack[] {
    const packs: BatteryPack[] = []
    for (const array of this.batteryArrays) {
      packs.push(...array.batteryPacks)
    }
    return packs
  }

  /**
   * Update system-level telemetry
   */
  updateTelemetry(telemetry: HomeTelemetryData): void {
    this._telemetry = telemetry
    this._telemetryTimestamp = new Date()
  }

  /**
   * Get system-level telemetry
   */
  getTelemetry(): HomeTelemetryData | null {
    return this._telemetry
  }

  /**
   * Get total PV power from all arrays in kW
   */
  getTotalPower(): number {
    if (this._telemetry) {
      return this._telemetry.pvPower
    }
    return this.inverterArrays.reduce((sum, arr) => sum + arr.getTotalPower(), 0)
  }

  /**
   * Get total load power in kW
   */
  getTotalLoadPower(): number {
    if (this._telemetry) {
      return this._telemetry.loadPower
    }
    return this.inverterArrays.reduce((sum, arr) => sum + arr.getTotalLoadPower(), 0)
  }

  /**
   * Get total grid power in kW
   */
  getTotalGridPower(): number {
    if (this._telemetry) {
      return this._telemetry.gridPower
    }
    return this.inverterArrays.reduce((sum, arr) => sum + arr.getTotalGridPower(), 0)
  }

  /**
   * Get total battery power in kW
   */
  getTotalBatteryPower(): number {
    if (this._telemetry) {
      return this._telemetry.batteryPower
    }
    return this.batteryArrays.reduce((sum, arr) => sum + arr.getTotalPower(), 0)
  }

  /**
   * Get energy-weighted average battery SOC across all battery arrays
   */
  getTotalBatterySOC(): number | null {
    // Try to get from system telemetry first
    if (this._telemetry?.batterySoc !== null && this._telemetry?.batterySoc !== undefined) {
      return this._telemetry.batterySoc
    }

    // Fallback: calculate from battery arrays
    const arraysWithSOC = this.batteryArrays.filter(arr => arr.getTotalSOC() !== null)
    if (arraysWithSOC.length === 0) return null

    // Energy-weighted average across arrays
    let totalCapacity = 0
    let weightedSOC = 0

    for (const array of arraysWithSOC) {
      const capacity = array.getTotalCapacity()
      const soc = array.getTotalSOC()!
      totalCapacity += capacity
      weightedSOC += soc * capacity
    }

    if (totalCapacity === 0) return null
    return weightedSOC / totalCapacity
  }

  /**
   * Get total battery capacity in kWh
   */
  getTotalBatteryCapacity(): number {
    return this.batteryArrays.reduce((sum, arr) => sum + arr.getTotalCapacity(), 0)
  }

  /**
   * Get daily energy data
   */
  getDailyEnergy(): HomeTelemetryData['dailyEnergy'] | null {
    return this._telemetry?.dailyEnergy || null
  }

  /**
   * Get financial metrics
   */
  getFinancialMetrics(): HomeTelemetryData['financialMetrics'] | null {
    return this._telemetry?.financialMetrics || null
  }

  /**
   * Convert to plain object
   */
  toJSON(): SystemConfig {
    return {
      system_id: this.systemId,
      name: this.name,
      description: this.description || undefined,
      timezone: this.timezone,
      inverter_arrays: this.inverterArrays.map(arr => arr.id),
      battery_arrays: this.batteryArrays.map(arr => arr.id),
      meters: this.meters.map(m => m.id),
    }
  }
}

