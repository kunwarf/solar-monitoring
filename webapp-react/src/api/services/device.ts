import { api, CACHE_TTL } from '../client'

export interface DeviceSettings {
  status: string
  device_id: string
  device_type: 'inverter' | 'battery' | 'meter'
  general?: {
    name?: string
    model?: string
    serial_number?: string
    vendor?: string
    chemistry?: string
    nominal_kwh?: number
    max_charge_kw?: number
    max_discharge_kw?: number
    meter_type?: string
    array_id?: string
    specification?: {
      driver?: string
      serialNumber?: string
      protocolVersion?: number
      maxAcOutputPower?: number
      mpptConnections?: number
      parallelMode?: boolean
      modbusNumber?: number
    }
  }
  adapter?: {
    adapter_type?: string
    transport?: 'rtu' | 'tcp'
    serial_port?: string
    baudrate?: number
    host?: string
    port?: number
    unit_id?: number
    timeout?: number
    parity?: string
    stopbits?: number
    bytesize?: number
    register_map_file?: string
  }
  safety?: {
    max_batt_voltage_v?: number
    max_charge_a?: number
    max_discharge_a?: number
    grid?: {
      voltageHigh?: number
      voltageLow?: number
      frequency?: number
      frequencyHigh?: number
      frequencyLow?: number
      peakShavingEnabled?: boolean
      peakShavingPower?: number
    }
  }
  solar?: {
    arrays?: Array<{
      pv_dc_kw?: number
      tilt_deg?: number
      azimuth_deg?: number
      perf_ratio?: number
      albedo?: number
    }>
    battery?: Record<string, any>
    workMode?: Record<string, any>
  }
  scheduling?: {
    touWindows?: Array<{
      mode: string
      startTime: string
      endTime: string
      power: number
      targetSoc: number
      enabled: boolean
    }>
  }
}

/**
 * Device service - handles device settings
 */
export const deviceService = {
  /**
   * Get device settings by device ID
   */
  async getDeviceSettings(deviceId: string): Promise<DeviceSettings> {
    const response = await api.get<DeviceSettings>(
      `/api/device/${deviceId}/settings`,
      { ttl: CACHE_TTL.CONFIG, key: `device:settings:${deviceId}` }
    )
    return response
  },

  /**
   * Save device settings
   */
  async saveDeviceSettings(
    deviceId: string,
    settings: {
      general?: Record<string, any>
      adapter?: Record<string, any>
      safety?: Record<string, any>
      solar?: Record<string, any>
      scheduling?: Record<string, any>
    }
  ): Promise<{ status: string; message: string }> {
    const response = await api.post<{ status: string; message: string }>(
      `/api/device/${deviceId}/settings`,
      settings
    )
    return response
  },
}

