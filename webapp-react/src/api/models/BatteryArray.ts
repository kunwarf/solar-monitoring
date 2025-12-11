/**
 * Battery Array Class
 * Represents an array of battery packs
 */

import { BaseArray } from './BaseArray'
import { BatteryPack } from './BatteryPack'
import { InverterArray } from './InverterArray'
import type { TelemetryData } from '../types/telemetry'

export interface BatteryArrayConfig {
  battery_array_id: string
  name: string
  system_id: string
  battery_packs: Array<BatteryPack['id']>
  attached_inverter_array_id?: string | null
}

export class BatteryArray extends BaseArray {
  batteryPacks: BatteryPack[] = []
  attachedInverterArrayId: string | null = null
  private _attachedInverterArray: InverterArray | null = null

  constructor(config: BatteryArrayConfig) {
    super(config.battery_array_id, config.name, config.system_id)
    this.attachedInverterArrayId = config.attached_inverter_array_id || null
  }

  /**
   * Add a battery pack to this array
   */
  addBatteryPack(pack: BatteryPack): void {
    if (pack.batteryArrayId !== this.id) {
      throw new Error(`Battery pack ${pack.id} does not belong to array ${this.id}`)
    }
    if (!this.batteryPacks.find(p => p.id === pack.id)) {
      this.batteryPacks.push(pack)
    }
  }

  /**
   * Get battery pack by ID
   */
  getBatteryPack(packId: string): BatteryPack | null {
    return this.batteryPacks.find(p => p.id === packId) || null
  }

  /**
   * Set attached inverter array
   */
  setAttachedInverterArray(inverterArray: InverterArray | null): void {
    this._attachedInverterArray = inverterArray
    this.attachedInverterArrayId = inverterArray?.id || null
  }

  /**
   * Get attached inverter array
   */
  getAttachedInverterArray(): InverterArray | null {
    return this._attachedInverterArray
  }

  /**
   * Get total battery power in kW (sum of all packs)
   */
  getTotalPower(): number {
    return this.batteryPacks.reduce((sum, pack) => sum + pack.getPower(), 0)
  }

  /**
   * Get energy-weighted average SOC across all packs
   */
  getTotalSOC(): number | null {
    const packsWithSOC = this.batteryPacks.filter(p => p.getSOC() !== null)
    if (packsWithSOC.length === 0) return null

    // Energy-weighted average
    let totalCapacity = 0
    let weightedSOC = 0

    for (const pack of packsWithSOC) {
      const capacity = pack.nominalKwh
      const soc = pack.getSOC()!
      totalCapacity += capacity
      weightedSOC += soc * capacity
    }

    if (totalCapacity === 0) return null
    return weightedSOC / totalCapacity
  }

  /**
   * Get total capacity in kWh
   */
  getTotalCapacity(): number {
    return this.batteryPacks.reduce((sum, pack) => sum + pack.nominalKwh, 0)
  }

  /**
   * Get average voltage across all packs
   */
  getAverageVoltage(): number | null {
    const packsWithVoltage = this.batteryPacks.filter(p => p.getVoltage() !== null)
    if (packsWithVoltage.length === 0) return null

    const sum = packsWithVoltage.reduce((sum, p) => sum + (p.getVoltage() || 0), 0)
    return sum / packsWithVoltage.length
  }

  /**
   * Get total current across all packs
   */
  getTotalCurrent(): number | null {
    const packsWithCurrent = this.batteryPacks.filter(p => p.getCurrent() !== null)
    if (packsWithCurrent.length === 0) return null

    return packsWithCurrent.reduce((sum, p) => sum + (p.getCurrent() || 0), 0)
  }

  /**
   * Get average temperature across all packs
   */
  getAverageTemperature(): number | null {
    const packsWithTemp = this.batteryPacks.filter(p => p.getTemperature() !== null)
    if (packsWithTemp.length === 0) return null

    const sum = packsWithTemp.reduce((sum, p) => sum + (p.getTemperature() || 0), 0)
    return sum / packsWithTemp.length
  }

  /**
   * Get pack count
   */
  getPackCount(): number {
    return this.batteryPacks.length
  }

  /**
   * Convert to plain object
   */
  toJSON(): BatteryArrayConfig {
    return {
      battery_array_id: this.id,
      name: this.name,
      system_id: this.systemId,
      battery_packs: this.batteryPacks.map(p => p.id),
      attached_inverter_array_id: this.attachedInverterArrayId,
    }
  }
}

