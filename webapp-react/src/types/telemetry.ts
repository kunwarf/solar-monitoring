export interface TelemetryData {
  // Timestamp
  ts: string;
  
  // Power flows
  pv_power_w?: number;
  pv1_power_w?: number;
  pv2_power_w?: number;
  mppt1_power?: number;
  mppt2_power?: number;
  load_power_w?: number;
  batt_power_w?: number;
  grid_power_w?: number;
  
  // Three-phase Load data (for three-phase inverters)
  load_l1_power_w?: number;
  load_l2_power_w?: number;
  load_l3_power_w?: number;
  load_l1_voltage_v?: number;
  load_l2_voltage_v?: number;
  load_l3_voltage_v?: number;
  load_l1_current_a?: number;
  load_l2_current_a?: number;
  load_l3_current_a?: number;
  load_frequency_hz?: number;
  
  // Three-phase Grid data (for three-phase inverters)
  grid_l1_power_w?: number;
  grid_l2_power_w?: number;
  grid_l3_power_w?: number;
  grid_l1_voltage_v?: number;
  grid_l2_voltage_v?: number;
  grid_l3_voltage_v?: number;
  grid_l1_current_a?: number;
  grid_l2_current_a?: number;
  grid_l3_current_a?: number;
  grid_frequency_hz?: number;
  grid_line_voltage_ab_v?: number;
  grid_line_voltage_bc_v?: number;
  grid_line_voltage_ca_v?: number;
  
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
  rated_power_w?: number;
  
  // Energy totals
  today_energy?: number;
  total_energy?: number;
  today_peak_power?: number;
  today_load_energy?: number;
  today_import_energy?: number;
  today_export_energy?: number;
  today_battery_charge_energy?: number;
  today_battery_discharge_energy?: number;
  
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
  
  // Extra fields (for accessing any additional data from API)
  extra?: Record<string, any>;
  
  // Inverter metadata (phase type, inverter count)
  _metadata?: {
    phase_type?: "single" | "three" | null;
    inverter_count?: number;
    is_three_phase?: boolean;
    is_single_phase?: boolean;
    is_single_inverter?: boolean;
    is_inverter_array?: boolean;
  };
}

export interface TelemetryResponse {
  inverter_id?: string;
  array_id?: string;
  now: TelemetryData | null;
}

export interface ArrayInfo {
  id: string;
  name?: string;
  inverter_ids: string[];
  inverter_count: number;
  attached_pack_ids: string[];
  pack_count: number;
}

export interface ArraysResponse {
  status: string;
  arrays: ArrayInfo[];
}

export interface ArrayTelemetryResponse {
  status: string;
  array_id: string;
  now: ArrayTelemetryData;
}

export interface ArrayTelemetryData {
  array_id: string;
  ts: string;
  pv_power_w?: number;
  load_power_w?: number;
  grid_power_w?: number;
  batt_power_w?: number;
  batt_soc_pct?: number;
  batt_voltage_v?: number;
  batt_current_a?: number;
  inverters?: Array<{
    inverter_id: string;
    pv_power_w?: number;
    load_power_w?: number;
    grid_power_w?: number;
    batt_power_w?: number;
    phase_type?: string;
  }>;
  packs?: Array<{
    pack_id: string;
    soc_pct?: number;
    voltage_v?: number;
    current_a?: number;
    power_w?: number;
  }>;
  _metadata?: {
    inverter_count?: number;
    attached_pack_ids?: string[];
    phase_mix?: string[];
    vendor_mix?: string[];
  };
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
