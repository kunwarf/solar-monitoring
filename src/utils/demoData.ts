import { TelemetryData } from '../types/telemetry';

export function generateDemoTelemetry(): TelemetryData {
  const now = new Date();
  const hour = now.getHours();
  
  // Simulate realistic solar data based on time of day
  const solarMultiplier = Math.max(0, Math.sin((hour - 6) * Math.PI / 12));
  const baseSolarPower = 3000 * solarMultiplier;
  const solarPower = baseSolarPower + (Math.random() - 0.5) * 500;
  
  // Simulate load (higher during day, lower at night)
  const loadMultiplier = 0.3 + 0.7 * Math.max(0, Math.sin((hour - 6) * Math.PI / 12));
  const loadPower = 800 * loadMultiplier + (Math.random() - 0.5) * 200;
  
  // Simulate battery behavior
  const soc = 45 + Math.random() * 30; // SOC between 45-75%
  const batteryPower = solarPower - loadPower + (Math.random() - 0.5) * 200;
  
  // Grid power (negative = import, positive = export)
  const gridPower = -(solarPower - loadPower - batteryPower);
  
  return {
    ts: now.toISOString(),
    
    // Power flows
    pv_power_w: Math.max(0, solarPower),
    mppt1_power: Math.max(0, solarPower * 0.6),
    mppt2_power: Math.max(0, solarPower * 0.4),
    load_power_w: Math.max(0, loadPower),
    batt_power_w: batteryPower,
    grid_power_w: gridPower,
    
    // Battery data
    batt_soc_pct: soc,
    batt_voltage_v: 53.2 + (Math.random() - 0.5) * 0.5,
    batt_current_a: batteryPower / (53.2 + (Math.random() - 0.5) * 0.5),
    batt_temp_c: 35.3 + (Math.random() - 0.5) * 5,
    
    // Inverter data
    inverter_mode: 'Time-based control',
    inverter_temp_c: 35 + (Math.random() - 0.5) * 10,
    error_code: 0,
    
    // Device info
    device_model: 'SM-ONYX-UL-6KW',
    device_serial_number: '2426-12950373PH',
    rated_power: 6000,
    
    // Energy totals
    today_energy: 15.2 + Math.random() * 5,
    total_energy: 1250 + Math.random() * 100,
    today_peak_power: 3200 + Math.random() * 500,
    today_load_energy: 12.5 + Math.random() * 3,
    today_import_energy: 2.1 + Math.random() * 1,
    today_export_energy: 8.5 + Math.random() * 2,
    
    // Configuration
    grid_charge: 1,
    maximum_grid_charger_power: 2000,
    maximum_charger_power: 5000,
    maximum_discharger_power: 5000,
    off_grid_mode: 0,
    off_grid_start_up_battery_capacity: 30,
    
    // TOU Windows
    charge_start_time_1: '09:00',
    charge_end_time_1: '15:00',
    charge_power_1: 3000,
    charger_end_soc_1: 98,
    discharge_start_time_1: '16:00',
    discharge_end_time_1: '06:00',
    discharge_power_1: 2500,
    discharge_end_soc_1: 20,
  };
}
