/**
 * Base Array Class
 * Abstract base class for arrays (InverterArray, BatteryArray)
 */

import type { TelemetryData } from '../types/telemetry'

export abstract class BaseArray {
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
   * Update telemetry data for this array
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
   * Check if array has recent telemetry
   */
  hasRecentTelemetry(maxAgeSeconds: number = 10): boolean {
    if (!this._telemetryTimestamp) return false
    const age = (Date.now() - this._telemetryTimestamp.getTime()) / 1000
    return age < maxAgeSeconds
  }
}

