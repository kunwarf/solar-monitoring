// Backend response types
export interface BackendHourlyEnergyResponse {
  status: string
  hourly_data?: Array<{
    time: string
    solar?: number
    load?: number
    battery?: number
    grid?: number
    battery_charge?: number
    battery_discharge?: number
    grid_import?: number
    grid_export?: number
  }>
}

export interface BackendDailyEnergyResponse {
  status: string
  daily_summary?: {
    date: string
    solar_kwh?: number
    load_kwh?: number
    battery_charge_kwh?: number
    battery_discharge_kwh?: number
    grid_import_kwh?: number
    grid_export_kwh?: number
    self_consumption_kwh?: number
    self_sufficiency_pct?: number
  }
}

export interface BackendForecastResponse {
  status: string
  forecast?: Array<{
    time: string
    forecast_kw?: number
    actual_kw?: number
  }>
  total_daily_generation_kwh?: number
  source?: string
}

// Normalized frontend types
export interface HourlyEnergyData {
  time: string
  solar: number // kWh
  load: number // kWh
  battery: number // kWh (positive = charge, negative = discharge)
  grid: number // kWh (positive = import, negative = export)
}

export interface DailyEnergyData {
  date: string
  solar: number // kWh
  load: number // kWh
  batteryCharge: number // kWh
  batteryDischarge: number // kWh
  gridImport: number // kWh
  gridExport: number // kWh
  selfConsumption: number // kWh
  selfSufficiency: number // %
}

export interface ForecastData {
  time: string
  forecast: number // kW
  actual: number | null // kW (if available)
}

