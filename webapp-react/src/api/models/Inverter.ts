/**
 * Inverter Class
 * Represents an individual inverter device
 */

import { BaseDevice } from './BaseDevice'
import type { TelemetryData } from '../types/telemetry'

export interface InverterConfig {
  inverter_id: string
  name: string
  array_id: string
  system_id: string
  model?: string
  serial_number?: string
  vendor?: string
  phase_type?: string
  adapter?: {
    adapter_id: string
    adapter_type: string
    config: any
  }
}

export class Inverter extends BaseDevice {
  arrayId: string
  model: string | null
  serialNumber: string | null
  vendor: string | null
  phaseType: string | null
  adapter: InverterConfig['adapter'] | null

  constructor(config: InverterConfig) {
    super(config.inverter_id, config.name, config.system_id)
    this.arrayId = config.array_id
    this.model = config.model || null
    this.serialNumber = config.serial_number || null
    this.vendor = config.vendor || null
    this.phaseType = config.phase_type || null
    this.adapter = config.adapter || null
  }

  /**
   * Get inverter power (PV power) in kW
   */
  getPower(): number {
    return this._telemetry?.pvPower || 0
  }

  /**
   * Get inverter efficiency (if available)
   */
  getEfficiency(): number {
    // Default efficiency if not available in telemetry
    return 97.0
  }

  /**
   * Get inverter temperature in °C
   */
  getTemperature(): number | null {
    return this._telemetry?.inverterTemperature || null
  }

  /**
   * Get grid power in kW (positive = import, negative = export)
   */
  getGridPower(): number {
    return this._telemetry?.gridPower || 0
  }

  /**
   * Get load power in kW
   */
  getLoadPower(): number {
    return this._telemetry?.loadPower || 0
  }

  /**
   * Get battery power in kW (positive = charging, negative = discharging)
   */
  getBatteryPower(): number {
    return this._telemetry?.batteryPower || 0
  }

  /**
   * Check if inverter is three-phase
   */
  isThreePhase(): boolean {
    return this._telemetry?.isThreePhase || false
  }

  /**
   * Convert to plain object
   */
  toJSON(): InverterConfig {
    return {
      inverter_id: this.id,
      name: this.name,
      array_id: this.arrayId,
      system_id: this.systemId,
      model: this.model || undefined,
      serial_number: this.serialNumber || undefined,
      vendor: this.vendor || undefined,
      phase_type: this.phaseType || undefined,
      adapter: this.adapter || undefined,
    }
  }
}

