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
   * Get meter power in kW
   */
  getPower(): number {
    // Meters typically report power in the telemetry
    // This would need to be extracted from meter-specific telemetry
    return 0 // Placeholder - needs meter telemetry structure
  }

  /**
   * Get import energy in kWh
   */
  getImportEnergy(): number {
    // This would come from meter telemetry
    return 0 // Placeholder
  }

  /**
   * Get export energy in kWh
   */
  getExportEnergy(): number {
    // This would come from meter telemetry
    return 0 // Placeholder
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

