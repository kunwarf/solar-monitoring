/**
 * Data Synchronization Service
 * Polls backend for telemetry updates and updates hierarchy objects
 */

import { HierarchyManager } from '../managers/HierarchyManager'
import { telemetryService } from './telemetry'
import { hierarchyService } from './hierarchy'
import type { TelemetryData, HomeTelemetryData, BatteryData } from '../types/telemetry'

export interface DataSyncConfig {
  pollingInterval?: number // Milliseconds between polls (default: 5000)
  enabled?: boolean // Whether polling is enabled (default: true)
  updateHierarchy?: boolean // Whether to update hierarchy on each poll (default: false)
}

export class DataSyncService {
  private hierarchyManager: HierarchyManager
  private pollingInterval: number = 5000 // 5 seconds default
  private enabled: boolean = true
  private updateHierarchy: boolean = false
  private intervalId: NodeJS.Timeout | null = null
  private isPolling: boolean = false

  constructor(config: DataSyncConfig = {}) {
    this.hierarchyManager = HierarchyManager.getInstance()
    this.pollingInterval = config.pollingInterval || 5000
    this.enabled = config.enabled !== false
    this.updateHierarchy = config.updateHierarchy || false
  }

  /**
   * Start polling for telemetry updates
   */
  startPolling(): void {
    if (this.intervalId) {
      // Already polling
      return
    }

    if (!this.enabled) {
      console.log('[DataSyncService] Polling is disabled')
      return
    }

    console.log(`[DataSyncService] Starting polling with interval ${this.pollingInterval}ms`)
    
    // Initial poll
    this.updateTelemetry().catch(err => {
      console.error('[DataSyncService] Initial poll failed:', err)
    })

    // Set up interval
    this.intervalId = setInterval(() => {
      if (!this.isPolling) {
        this.updateTelemetry().catch(err => {
          console.error('[DataSyncService] Poll failed:', err)
        })
      }
    }, this.pollingInterval)
  }

  /**
   * Stop polling
   */
  stopPolling(): void {
    if (this.intervalId) {
      clearInterval(this.intervalId)
      this.intervalId = null
      console.log('[DataSyncService] Polling stopped')
    }
  }

  /**
   * Update telemetry for all devices
   */
  async updateTelemetry(): Promise<void> {
    if (this.isPolling) {
      // Skip if already polling
      return
    }

    this.isPolling = true
    try {
      // Update hierarchy if needed
      if (this.updateHierarchy || !this.hierarchyManager.isLoaded()) {
        await hierarchyService.loadHierarchy()
      }

      // Update system telemetry
      try {
        const systemTelemetry = await telemetryService.getSystemNow()
        // System telemetry is already updated in telemetryService
      } catch (err) {
        console.warn('[DataSyncService] Failed to update home telemetry:', err)
      }

      // Update all inverter telemetry
      const inverters = this.hierarchyManager.getAllInverters()
      for (const inverter of inverters) {
        try {
          await telemetryService.getInverterNow(inverter.id)
          // Telemetry is already updated in telemetryService
        } catch (err) {
          console.warn(`[DataSyncService] Failed to update inverter ${inverter.id} telemetry:`, err)
        }
      }

      // Update all array telemetry
      const systems = this.hierarchyManager.getAllSystems()
      for (const system of systems) {
        for (const array of system.inverterArrays) {
          try {
            await telemetryService.getArrayNow(array.id)
            // Telemetry is already updated in telemetryService
          } catch (err) {
            console.warn(`[DataSyncService] Failed to update array ${array.id} telemetry:`, err)
          }
        }
      }

      // Update all battery pack telemetry
      const batteryPacks = this.hierarchyManager.getAllBatteryPacks()
      for (const pack of batteryPacks) {
        try {
          await telemetryService.getBatteryNow(pack.id)
          // Telemetry is already updated in telemetryService
        } catch (err) {
          console.warn(`[DataSyncService] Failed to update battery pack ${pack.id} telemetry:`, err)
        }
      }

      // Update all battery telemetry (all packs at once)
      try {
        await telemetryService.getBatteryNow()
        // Telemetry is already updated in telemetryService
      } catch (err) {
        console.warn('[DataSyncService] Failed to update all battery telemetry:', err)
      }

    } catch (err) {
      console.error('[DataSyncService] Error updating telemetry:', err)
    } finally {
      this.isPolling = false
    }
  }

  /**
   * Update telemetry for a specific device
   */
  async updateDeviceTelemetry(deviceId: string, deviceType: 'inverter' | 'battery' | 'meter'): Promise<void> {
    try {
      switch (deviceType) {
        case 'inverter':
          await telemetryService.getInverterNow(deviceId)
          break
        case 'battery':
          await telemetryService.getBatteryNow(deviceId)
          break
        case 'meter':
          // Meter telemetry not yet implemented
          console.warn('[DataSyncService] Meter telemetry not yet implemented')
          break
      }
    } catch (err) {
      console.error(`[DataSyncService] Failed to update ${deviceType} ${deviceId} telemetry:`, err)
      throw err
    }
  }

  /**
   * Update telemetry for a specific array
   */
  async updateArrayTelemetry(arrayId: string): Promise<void> {
    try {
      await telemetryService.getArrayNow(arrayId)
    } catch (err) {
      console.error(`[DataSyncService] Failed to update array ${arrayId} telemetry:`, err)
      throw err
    }
  }

  /**
   * Update telemetry for a specific system
   */
  async updateSystemTelemetry(systemId: string): Promise<void> {
    try {
      await telemetryService.getSystemNow()
    } catch (err) {
      console.error(`[DataSyncService] Failed to update system ${systemId} telemetry:`, err)
      throw err
    }
  }

  /**
   * Set polling interval
   */
  setPollingInterval(interval: number): void {
    this.pollingInterval = interval
    if (this.intervalId) {
      // Restart polling with new interval
      this.stopPolling()
      this.startPolling()
    }
  }

  /**
   * Enable or disable polling
   */
  setEnabled(enabled: boolean): void {
    this.enabled = enabled
    if (enabled && !this.intervalId) {
      this.startPolling()
    } else if (!enabled && this.intervalId) {
      this.stopPolling()
    }
  }

  /**
   * Check if polling is active
   */
  isPollingActive(): boolean {
    return this.intervalId !== null
  }

  /**
   * Get current polling interval
   */
  getPollingInterval(): number {
    return this.pollingInterval
  }
}

// Singleton instance
let dataSyncServiceInstance: DataSyncService | null = null

/**
 * Get or create DataSyncService singleton instance
 */
export function getDataSyncService(config?: DataSyncConfig): DataSyncService {
  if (!dataSyncServiceInstance) {
    dataSyncServiceInstance = new DataSyncService(config)
  }
  return dataSyncServiceInstance
}

