// Backend response types (raw API responses)
export interface BackendTelemetryResponse {
  inverter_id?: string
  array_id?: string
  now: BackendTelemetryData | null
}

export interface BackendTelemetryData {
  ts: string
  pv_power_w?: number
  load_power_w?: number
  grid_power_w?: number
  batt_power_w?: number
  batt_soc_pct?: number
  batt_voltage_v?: number
  batt_current_a?: number
  inverter_temp_c?: number
  // Three-phase data
  load_l1_power_w?: number
  load_l2_power_w?: number
  load_l3_power_w?: number
  grid_l1_power_w?: number
  grid_l2_power_w?: number
  grid_l3_power_w?: number
  // Metadata
  _metadata?: {
    phase_type?: 'single' | 'three' | null
    inverter_count?: number
    is_three_phase?: boolean
    is_single_phase?: boolean
    is_single_inverter?: boolean
    is_inverter_array?: boolean
  }
  [key: string]: any // Allow additional fields
}

export interface BackendHomeTelemetryResponse {
  status: string
  home: BackendHomeTelemetry
}

export interface BackendHomeTelemetry {
  home_id: string
  ts: string
  total_pv_power_w?: number
  total_load_power_w?: number
  total_grid_power_w?: number
  total_batt_power_w?: number
  avg_batt_soc_pct?: number
  arrays?: Array<{
    array_id: string
    name?: string
    pv_power_w?: number
    load_power_w?: number
    grid_power_w?: number
    batt_power_w?: number
    batt_soc_pct?: number
  }>
  meters?: Array<{
    meter_id: string
    name?: string
    power_w?: number
    import_kwh?: number
    export_kwh?: number
  }>
  _metadata?: Record<string, any>
  metadata?: Record<string, any>
}

export interface BackendArrayTelemetryResponse {
  status: string
  array_id: string
  now: BackendArrayTelemetry
}

export interface BackendArrayTelemetry {
  array_id: string
  ts: string
  pv_power_w?: number
  load_power_w?: number
  grid_power_w?: number
  batt_power_w?: number
  batt_soc_pct?: number
  batt_voltage_v?: number
  batt_current_a?: number
  inverters?: Array<{
    inverter_id: string
    pv_power_w?: number
    load_power_w?: number
    grid_power_w?: number
    batt_power_w?: number
    phase_type?: string
  }>
  packs?: Array<{
    pack_id: string
    soc_pct?: number
    voltage_v?: number
    current_a?: number
    power_w?: number
  }>
  _metadata?: Record<string, any>
}

export interface BackendBatteryResponse {
  status: string
  battery?: BackendBatteryData
  banks?: BackendBatteryData[]
  configured_banks?: Array<{
    id: string
    name?: string
    manufacturer?: string
    model?: string
    type?: string
  }>
}

export interface BackendBatteryData {
  ts?: string
  id: string
  bank_id?: string
  batteries_count?: number
  cells_per_battery?: number
  voltage?: number
  current?: number
  temperature?: number
  soc?: number
  devices?: Array<{
    power: number
    voltage?: number
    current?: number
    temperature?: number
    soc?: number
    soh?: number
    cycles?: number
    basic_st?: string
    volt_st?: string
    temp_st?: string
    current_st?: string
    coul_st?: string
    soh_st?: string
    heater_st?: string
  }>
  cells_data?: Array<{
    power: number
    voltage_min?: number
    voltage_max?: number
    voltage_delta?: number
    temperature_min?: number
    temperature_max?: number
    temperature_delta?: number
    cells?: Array<{
      power: number
      cell: number
      voltage?: number
      temperature?: number
      soc?: number
    }>
  }>
  extra?: Record<string, any>
}

// Normalized frontend types (consistent format across all apps)
export interface TelemetryData {
  ts: string
  // Power flows
  pvPower: number // kW
  loadPower: number // kW
  gridPower: number // kW (positive = import, negative = export)
  batteryPower: number // kW (positive = charging, negative = discharging)
  // Battery
  batterySoc: number | null // %
  batteryVoltage: number | null // V
  batteryCurrent: number | null // A
  batteryTemperature: number | null // °C
  // Inverter
  inverterTemperature: number | null // °C
  // Three-phase data (if applicable)
  isThreePhase: boolean
  loadL1?: number
  loadL2?: number
  loadL3?: number
  gridL1?: number
  gridL2?: number
  gridL3?: number
  // Metadata
  metadata?: {
    phaseType?: 'single' | 'three' | null
    inverterCount?: number
    isSingleInverter?: boolean
    isInverterArray?: boolean
    [key: string]: any
  }
  // Source info
  source: 'inverter' | 'array' | 'home'
  sourceId?: string
  // Additional raw data
  raw?: Record<string, any>
}

export interface HomeTelemetryData extends TelemetryData {
  source: 'home'
  arrays?: Array<{
    id: string
    name?: string
    pvPower: number
    loadPower: number
    gridPower: number
    batteryPower: number
    batterySoc: number | null
  }>
  meters?: Array<{
    id: string
    name?: string
    power: number
    importKwh: number
    exportKwh: number
  }>
}

export interface BatteryData {
  id: string
  ts: string
  voltage: number | null
  current: number | null
  temperature: number | null
  soc: number | null
  batteryCount: number
  cellsPerBattery: number
  devices: Array<{
    index: number
    voltage?: number
    current?: number
    temperature?: number
    soc?: number
    soh?: number
    cycles?: number
    status: string
  }>
  cells: Array<{
    batteryIndex: number
    cellIndex: number
    voltage?: number
    temperature?: number
    soc?: number
  }>
  info?: {
    serialNumber?: string
    manufacturer?: string
    model?: string
    specification?: string
  }
  raw?: Record<string, any>
}

