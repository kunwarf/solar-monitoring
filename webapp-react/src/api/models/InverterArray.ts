/**
 * Inverter Array Class
 * Represents an array of inverters
 */

import { BaseArray } from './BaseArray'
import { Inverter } from './Inverter'
import { BatteryArray } from './BatteryArray'
import type { TelemetryData } from '../types/telemetry'

export interface InverterArrayConfig {
  array_id: string
  name: string
  system_id: string
  inverters: Array<Inverter['id']>
  attached_battery_array_id?: string | null
}

export class InverterArray extends BaseArray {
  inverters: Inverter[] = []
  attachedBatteryArrayId: string | null = null
  private _attachedBatteryArray: BatteryArray | null = null

  constructor(config: InverterArrayConfig) {
    super(config.array_id, config.name, config.system_id)
    this.attachedBatteryArrayId = config.attached_battery_array_id || null
  }

  /**
   * Add an inverter to this array
   */
  addInverter(inverter: Inverter): void {
    if (inverter.arrayId !== this.id) {
      throw new Error(`Inverter ${inverter.id} does not belong to array ${this.id}`)
    }
    if (!this.inverters.find(inv => inv.id === inverter.id)) {
      this.inverters.push(inverter)
    }
  }

  /**
   * Get inverter by ID
   */
  getInverter(inverterId: string): Inverter | null {
    return this.inverters.find(inv => inv.id === inverterId) || null
  }

  /**
   * Set attached battery array
   */
  setAttachedBatteryArray(batteryArray: BatteryArray | null): void {
    this._attachedBatteryArray = batteryArray
    this.attachedBatteryArrayId = batteryArray?.id || null
  }

  /**
   * Get attached battery array
   */
  getAttachedBatteryArray(): BatteryArray | null {
    return this._attachedBatteryArray
  }

  /**
   * Get total PV power from all inverters in kW
   */
  getTotalPower(): number {
    if (this._telemetry) {
      return this._telemetry.pvPower
    }
    // Fallback: sum individual inverter powers
    return this.inverters.reduce((sum, inv) => sum + inv.getPower(), 0)
  }

  /**
   * Get total load power in kW
   */
  getTotalLoadPower(): number {
    if (this._telemetry) {
      return this._telemetry.loadPower
    }
    return this.inverters.reduce((sum, inv) => sum + inv.getLoadPower(), 0)
  }

  /**
   * Get total grid power in kW
   */
  getTotalGridPower(): number {
    if (this._telemetry) {
      return this._telemetry.gridPower
    }
    return this.inverters.reduce((sum, inv) => sum + inv.getGridPower(), 0)
  }

  /**
   * Get total battery power in kW
   */
  getTotalBatteryPower(): number {
    if (this._telemetry) {
      return this._telemetry.batteryPower
    }
    // Try to get from attached battery array
    if (this._attachedBatteryArray) {
      return this._attachedBatteryArray.getTotalPower()
    }
    return this.inverters.reduce((sum, inv) => sum + inv.getBatteryPower(), 0)
  }

  /**
   * Get average battery SOC from attached battery array
   */
  getBatterySOC(): number | null {
    if (this._attachedBatteryArray) {
      return this._attachedBatteryArray.getTotalSOC()
    }
    // Fallback: try to get from telemetry
    return this._telemetry?.batterySoc || null
  }

  /**
   * Get average efficiency across all inverters
   */
  getAverageEfficiency(): number {
    if (this.inverters.length === 0) return 0
    const sum = this.inverters.reduce((sum, inv) => sum + inv.getEfficiency(), 0)
    return sum / this.inverters.length
  }

  /**
   * Get inverter count
   */
  getInverterCount(): number {
    return this.inverters.length
  }

  /**
   * Convert to plain object
   */
  toJSON(): InverterArrayConfig {
    return {
      array_id: this.id,
      name: this.name,
      system_id: this.systemId,
      inverters: this.inverters.map(inv => inv.id),
      attached_battery_array_id: this.attachedBatteryArrayId,
    }
  }
}

