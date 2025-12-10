import type {
  BackendHourlyEnergyResponse,
  BackendDailyEnergyResponse,
  BackendForecastResponse,
  HourlyEnergyData,
  DailyEnergyData,
  ForecastData,
} from '../types/energy'

/**
 * Normalize hourly energy data
 */
export function normalizeHourlyEnergy(
  response: BackendHourlyEnergyResponse
): HourlyEnergyData[] {
  if (!response.hourly_data || !Array.isArray(response.hourly_data)) {
    return []
  }

  return response.hourly_data.map((item) => ({
    time: item.time,
    solar: item.solar || 0,
    load: item.load || 0,
    battery:
      item.battery !== undefined
        ? item.battery
        : (item.battery_charge || 0) - (item.battery_discharge || 0),
    grid:
      item.grid !== undefined
        ? item.grid
        : (item.grid_import || 0) - (item.grid_export || 0),
  }))
}

/**
 * Normalize daily energy data
 */
export function normalizeDailyEnergy(
  response: BackendDailyEnergyResponse
): DailyEnergyData | null {
  if (!response.daily_summary) {
    return null
  }

  const summary = response.daily_summary
  return {
    date: summary.date,
    solar: summary.solar_kwh || 0,
    load: summary.load_kwh || 0,
    batteryCharge: summary.battery_charge_kwh || 0,
    batteryDischarge: summary.battery_discharge_kwh || 0,
    gridImport: summary.grid_import_kwh || 0,
    gridExport: summary.grid_export_kwh || 0,
    selfConsumption: summary.self_consumption_kwh || 0,
    selfSufficiency: summary.self_sufficiency_pct || 0,
  }
}

/**
 * Normalize forecast data
 */
export function normalizeForecast(
  response: BackendForecastResponse
): ForecastData[] {
  if (!response.forecast || !Array.isArray(response.forecast)) {
    return []
  }

  return response.forecast.map((item) => ({
    time: item.time,
    forecast: item.forecast_kw || 0,
    actual: item.actual_kw ?? null,
  }))
}

