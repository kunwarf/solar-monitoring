export interface TelemetryData {
  // Timestamp
  ts: string;
  
  // Power flows
  pv_power_w?: number;
  mppt1_power?: number;
  mppt2_power?: number;
  load_power_w?: number;
  batt_power_w?: number;
  grid_power_w?: number;
  
  // Battery data
  batt_soc_pct?: number;
  batt_voltage_v?: number;
  batt_current_a?: number;
  batt_temp_c?: number;
  
  // Inverter data
  inverter_mode?: string;
  inverter_temp_c?: number;
  error_code?: number;
  
  // Device info
  device_model?: string;
  device_serial_number?: string;
  rated_power?: number;
  
  // Energy totals
  today_energy?: number;
  total_energy?: number;
  today_peak_power?: number;
  today_load_energy?: number;
  today_import_energy?: number;
  today_export_energy?: number;
  
  // Configuration
  grid_charge?: number;
  maximum_grid_charger_power?: number;
  maximum_charger_power?: number;
  maximum_discharger_power?: number;
  off_grid_mode?: number;
  off_grid_start_up_battery_capacity?: number;
  
  // TOU Windows
  charge_start_time_1?: string;
  charge_end_time_1?: string;
  charge_power_1?: number;
  charger_end_soc_1?: number;
  discharge_start_time_1?: string;
  discharge_end_time_1?: string;
  discharge_power_1?: number;
  discharge_end_soc_1?: number;
}

export interface TelemetryResponse {
  inverter_id: string;
  now: TelemetryData | null;
}

export interface PowerFlow {
  pv: number;
  load: number;
  battery: number;
  grid: number;
}

export interface BatteryStatus {
  soc: number;
  voltage: number;
  current: number;
  temperature: number;
  power: number;
  status: 'charging' | 'discharging' | 'idle';
}

export interface InverterStatus {
  mode: string;
  temperature: number;
  errorCode: number;
  model: string;
  serialNumber: string;
  ratedPower: number;
}
