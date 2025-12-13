/**
 * Meter Class
 * Represents an energy meter device
 */

import { BaseDevice } from './BaseDevice'
import type { TelemetryData } from '../types/telemetry'

export interface MeterConfig {
  meter_id: string
  name: string
  system_id: string
  model?: string
  serial_number?: string
  vendor?: string
  meter_type?: string
  attachment_target?: string
  adapter?: {
    adapter_id: string
    adapter_type: string
    config: any
  }
}

export class Meter extends BaseDevice {
  model: string | null
  serialNumber: string | null
  vendor: string | null
  meterType: string | null
  attachmentTarget: string | null
  adapter: MeterConfig['adapter'] | null

  constructor(config: MeterConfig) {
    super(config.meter_id, config.name, config.system_id)
    this.model = config.model || null
    this.serialNumber = config.serial_number || null
    this.vendor = config.vendor || null
    this.meterType = config.meter_type || null
    this.attachmentTarget = config.attachment_target || null
    this.adapter = config.adapter || null
  }

  /**
   * Get meter power in kW (positive = import, negative = export)
   */
  getPower(): number {
    if (this._telemetry) {
      // Meter power is in gridPower field (already in kW from normalization)
      return this._telemetry.gridPower || 0
    }
    return 0
  }

  /**
   * Get import energy in kWh
   */
  getImportEnergy(): number {
    if (this._telemetry && this._telemetry.raw) {
      // Import energy is stored in raw._metadata or raw.import_kwh
      return (this._telemetry.raw as any).import_kwh || 
             (this._telemetry.raw as any)._metadata?.import_kwh || 0
    }
    return 0
  }

  /**
   * Get export energy in kWh
   */
  getExportEnergy(): number {
    if (this._telemetry && this._telemetry.raw) {
      // Export energy is stored in raw._metadata or raw.export_kwh
      return (this._telemetry.raw as any).export_kwh || 
             (this._telemetry.raw as any)._metadata?.export_kwh || 0
    }
    return 0
  }

  /**
   * Convert to plain object
   */
  toJSON(): MeterConfig {
    return {
      meter_id: this.id,
      name: this.name,
      system_id: this.systemId,
      model: this.model || undefined,
      serial_number: this.serialNumber || undefined,
      vendor: this.vendor || undefined,
      meter_type: this.meterType || undefined,
      attachment_target: this.attachmentTarget || undefined,
      adapter: this.adapter || undefined,
    }
  }
}

