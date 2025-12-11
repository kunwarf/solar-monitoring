/**
 * Base Device Class
 * Abstract base class for all devices in the hierarchy (Inverter, BatteryPack, Meter)
 */

import type { TelemetryData } from '../types/telemetry'

export abstract class BaseDevice {
  id: string
  name: string
  systemId: string
  protected _telemetry: TelemetryData | null = null
  protected _telemetryTimestamp: Date | null = null

  constructor(id: string, name: string, systemId: string) {
    this.id = id
    this.name = name
    this.systemId = systemId
  }

  /**
   * Update telemetry data for this device
   */
  updateTelemetry(telemetry: TelemetryData): void {
    this._telemetry = telemetry
    this._telemetryTimestamp = new Date()
  }

  /**
   * Get current telemetry data
   */
  getTelemetry(): TelemetryData | null {
    return this._telemetry
  }

  /**
   * Get telemetry timestamp
   */
  getTelemetryTimestamp(): Date | null {
    return this._telemetryTimestamp
  }

  /**
   * Clear telemetry cache
   */
  clearTelemetry(): void {
    this._telemetry = null
    this._telemetryTimestamp = null
  }

  /**
   * Check if device has recent telemetry (within last 10 seconds)
   */
  hasRecentTelemetry(maxAgeSeconds: number = 10): boolean {
    if (!this._telemetryTimestamp) return false
    const age = (Date.now() - this._telemetryTimestamp.getTime()) / 1000
    return age < maxAgeSeconds
  }

  /**
   * Get device status based on telemetry freshness
   */
  getStatus(): 'online' | 'offline' | 'warning' {
    if (this.hasRecentTelemetry(10)) {
      return 'online'
    } else if (this.hasRecentTelemetry(60)) {
      return 'warning'
    } else {
      return 'offline'
    }
  }
}

