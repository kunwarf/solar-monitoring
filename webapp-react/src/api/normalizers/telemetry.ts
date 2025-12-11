import type {
  BackendTelemetryData,
  BackendHomeTelemetry,
  BackendArrayTelemetry,
  BackendBatteryData,
  TelemetryData,
  HomeTelemetryData,
  BatteryData,
} from '../types/telemetry'

/**
 * Normalize backend telemetry data to frontend format
 */
export function normalizeTelemetry(
  data: BackendTelemetryData,
  source: 'inverter' | 'array' | 'home' = 'inverter',
  sourceId?: string
): TelemetryData {
  return {
    ts: data.ts,
    pvPower: (data.pv_power_w || 0) / 1000, // Convert W to kW
    loadPower: (data.load_power_w || 0) / 1000,
    gridPower: (data.grid_power_w || 0) / 1000,
    batteryPower: (data.batt_power_w || 0) / 1000,
    batterySoc: data.batt_soc_pct ?? null,
    batteryVoltage: data.batt_voltage_v ?? null,
    batteryCurrent: data.batt_current_a ?? null,
    batteryTemperature: data.batt_temp_c ?? null,
    inverterTemperature: data.inverter_temp_c ?? null,
    isThreePhase: data._metadata?.is_three_phase ?? false,
    loadL1: data.load_l1_power_w ? data.load_l1_power_w / 1000 : undefined,
    loadL2: data.load_l2_power_w ? data.load_l2_power_w / 1000 : undefined,
    loadL3: data.load_l3_power_w ? data.load_l3_power_w / 1000 : undefined,
    gridL1: data.grid_l1_power_w ? data.grid_l1_power_w / 1000 : undefined,
    gridL2: data.grid_l2_power_w ? data.grid_l2_power_w / 1000 : undefined,
    gridL3: data.grid_l3_power_w ? data.grid_l3_power_w / 1000 : undefined,
    metadata: {
      phaseType: data._metadata?.phase_type ?? null,
      inverterCount: data._metadata?.inverter_count,
      isSingleInverter: data._metadata?.is_single_inverter ?? false,
      isInverterArray: data._metadata?.is_inverter_array ?? false,
    },
    source,
    sourceId,
    raw: data,
  }
}

/**
 * Normalize home telemetry data
 */
export function normalizeHomeTelemetry(
  data: BackendHomeTelemetry
): HomeTelemetryData {
  const base = normalizeTelemetry(
    {
      ts: data.ts,
      pv_power_w: data.total_pv_power_w,
      load_power_w: data.total_load_power_w,
      grid_power_w: data.total_grid_power_w,
      batt_power_w: data.total_batt_power_w,
      batt_soc_pct: data.avg_batt_soc_pct,
      _metadata: data._metadata || data.metadata,
    },
    'home',
    data.home_id
  )

  return {
    ...base,
    arrays: data.arrays?.map((arr) => ({
      id: arr.array_id,
      name: arr.name,
      pvPower: (arr.pv_power_w || 0) / 1000,
      loadPower: (arr.load_power_w || 0) / 1000,
      gridPower: (arr.grid_power_w || 0) / 1000,
      batteryPower: (arr.batt_power_w || 0) / 1000,
      batterySoc: arr.batt_soc_pct ?? null,
    })),
    meters: data.meters?.map((meter) => ({
      id: meter.meter_id,
      name: meter.name,
      power: (meter.power_w || 0) / 1000,
      importKwh: meter.import_kwh || 0,
      exportKwh: meter.export_kwh || 0,
    })),
    financialMetrics: data.financial_metrics ? {
      totalBillPkr: data.financial_metrics.total_bill_pkr || 0,
      totalSavedPkr: data.financial_metrics.total_saved_pkr || 0,
      co2PreventedKg: data.financial_metrics.co2_prevented_kg || 0,
    } : undefined,
    dailyEnergy: data.daily_energy ? {
      solar: data.daily_energy.solar_energy_kwh || 0,
      load: data.daily_energy.load_energy_kwh || 0,
      batteryCharge: data.daily_energy.battery_charge_energy_kwh || 0,
      batteryDischarge: data.daily_energy.battery_discharge_energy_kwh || 0,
      gridImport: data.daily_energy.grid_import_energy_kwh || 0,
      gridExport: data.daily_energy.grid_export_energy_kwh || 0,
      selfConsumption: data.daily_energy.self_consumption_kwh || 0,
      selfSufficiency: data.daily_energy.self_sufficiency_pct || 0,
    } : undefined,
  }
}

/**
 * Normalize array telemetry data
 */
export function normalizeArrayTelemetry(
  data: BackendArrayTelemetry
): TelemetryData {
  const normalized = normalizeTelemetry(
    {
      ts: data.ts,
      pv_power_w: data.pv_power_w,
      load_power_w: data.load_power_w,
      grid_power_w: data.grid_power_w,
      batt_power_w: data.batt_power_w,
      batt_soc_pct: data.batt_soc_pct,
      batt_voltage_v: data.batt_voltage_v,
      batt_current_a: data.batt_current_a,
      _metadata: data._metadata,
    },
    'array',
    data.array_id
  )
  
  // Preserve inverters and packs in raw data for access by components
  return {
    ...normalized,
    raw: {
      ...normalized.raw,
      inverters: data.inverters,
      packs: data.packs,
    },
  }
}

/**
 * Normalize battery data
 */
export function normalizeBatteryData(data: BackendBatteryData): BatteryData {
  const cells: BatteryData['cells'] = []
  
  if (data.cells_data) {
    for (const cellData of data.cells_data) {
      if (cellData.cells) {
        for (const cell of cellData.cells) {
          cells.push({
            batteryIndex: cellData.power,
            cellIndex: cell.cell,
            voltage: cell.voltage,
            temperature: cell.temperature,
            soc: cell.soc,
          })
        }
      }
    }
  }

  return {
    id: data.id,
    ts: data.ts || new Date().toISOString(),
    voltage: data.voltage ?? null,
    current: data.current ?? null,
    temperature: data.temperature ?? null,
    soc: data.soc ?? null,
    batteryCount: data.batteries_count || 0,
    cellsPerBattery: data.cells_per_battery || 0,
    devices: (data.devices || []).map((dev) => ({
      index: dev.power,
      voltage: dev.voltage,
      current: dev.current,
      temperature: dev.temperature,
      soc: dev.soc,
      soh: dev.soh,
      cycles: dev.cycles,
      status: dev.basic_st || 'Unknown',
    })),
    cells,
    info: data.extra
      ? {
          serialNumber: data.extra.serial_number || data.extra.barcode,
          manufacturer: data.extra.manufacturer,
          model: data.extra.model,
          specification: data.extra.specification,
        }
      : undefined,
    raw: data,
  }
}

