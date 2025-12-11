/**
 * Battery Pack Class
 * Represents a battery pack (battery bank)
 */

import { BaseDevice } from './BaseDevice'
import type { BatteryData } from '../types/telemetry'

export interface BatteryPackConfig {
  pack_id: string
  name: string
  battery_array_id: string
  system_id: string
  chemistry: string
  nominal_kwh: number
  max_charge_kw: number
  max_discharge_kw: number
  adapters?: Array<{
    adapter_id: string
    adapter_type: string
    priority: number
    enabled: boolean
    config: any
  }>
}

export class BatteryPack extends BaseDevice {
  batteryArrayId: string
  chemistry: string
  nominalKwh: number
  maxChargeKw: number
  maxDischargeKw: number
  adapters: BatteryPackConfig['adapters']
  protected _batteryTelemetry: BatteryData | null = null

  constructor(config: BatteryPackConfig) {
    super(config.pack_id, config.name, config.system_id)
    this.batteryArrayId = config.battery_array_id
    this.chemistry = config.chemistry
    this.nominalKwh = config.nominal_kwh
    this.maxChargeKw = config.max_charge_kw
    this.maxDischargeKw = config.max_discharge_kw
    this.adapters = config.adapters || []
  }

  /**
   * Update battery-specific telemetry
   */
  updateBatteryTelemetry(telemetry: BatteryData): void {
    this._batteryTelemetry = telemetry
    // Also update base telemetry if available
    if (this._telemetry) {
      this._telemetry.batterySoc = telemetry.soc
      this._telemetry.batteryVoltage = telemetry.voltage
      this._telemetry.batteryCurrent = telemetry.current
      this._telemetry.batteryTemperature = telemetry.temperature
    }
  }

  /**
   * Get battery-specific telemetry
   */
  getBatteryTelemetry(): BatteryData | null {
    return this._batteryTelemetry
  }

  /**
   * Get battery SOC (State of Charge) in %
   */
  getSOC(): number | null {
    return this._batteryTelemetry?.soc || this._telemetry?.batterySoc || null
  }

  /**
   * Get battery power in kW (positive = charging, negative = discharging)
   */
  getPower(): number {
    // Calculate from voltage and current if available
    if (this._batteryTelemetry?.voltage && this._batteryTelemetry?.current) {
      return (this._batteryTelemetry.voltage * this._batteryTelemetry.current) / 1000
    }
    return this._telemetry?.batteryPower || 0
  }

  /**
   * Get battery voltage in V
   */
  getVoltage(): number | null {
    return this._batteryTelemetry?.voltage || this._telemetry?.batteryVoltage || null
  }

  /**
   * Get battery current in A
   */
  getCurrent(): number | null {
    return this._batteryTelemetry?.current || this._telemetry?.batteryCurrent || null
  }

  /**
   * Get battery temperature in °C
   */
  getTemperature(): number | null {
    return this._batteryTelemetry?.temperature || this._telemetry?.batteryTemperature || null
  }

  /**
   * Get battery count (number of individual battery units)
   */
  getBatteryCount(): number {
    return this._batteryTelemetry?.batteryCount || 0
  }

  /**
   * Get cells per battery
   */
  getCellsPerBattery(): number {
    return this._batteryTelemetry?.cellsPerBattery || 0
  }

  /**
   * Get individual battery devices
   */
  getDevices(): BatteryData['devices'] {
    return this._batteryTelemetry?.devices || []
  }

  /**
   * Get cell data
   */
  getCells(): BatteryData['cells'] {
    return this._batteryTelemetry?.cells || []
  }

  /**
   * Check if battery is charging
   */
  isCharging(): boolean {
    const power = this.getPower()
    return power > 0
  }

  /**
   * Check if battery is discharging
   */
  isDischarging(): boolean {
    const power = this.getPower()
    return power < 0
  }

  /**
   * Convert to plain object
   */
  toJSON(): BatteryPackConfig {
    return {
      pack_id: this.id,
      name: this.name,
      battery_array_id: this.batteryArrayId,
      system_id: this.systemId,
      chemistry: this.chemistry,
      nominal_kwh: this.nominalKwh,
      max_charge_kw: this.maxChargeKw,
      max_discharge_kw: this.maxDischargeKw,
      adapters: this.adapters,
    }
  }
}

