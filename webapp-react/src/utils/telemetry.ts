import { TelemetryData, PowerFlow, BatteryStatus, InverterStatus } from '../types/telemetry';

export function formatPower(watts?: number): string {
  if (watts === undefined || watts === null) return 'N/A';
  if (watts >= 1000) {
    return `${(watts / 1000).toFixed(1)} kW`;
  }
  return `${watts.toFixed(0)} W`;
}

export function formatEnergy(kwh?: number): string {
  if (kwh === undefined || kwh === null) return 'N/A';
  return `${kwh.toFixed(1)} kWh`;
}

export function formatTemperature(celsius?: number): string {
  if (celsius === undefined || celsius === null) return 'N/A';
  return `${celsius.toFixed(1)}°C`;
}

export function formatVoltage(volts?: number): string {
  if (volts === undefined || volts === null) return 'N/A';
  return `${volts.toFixed(1)} V`;
}

export function formatCurrent(amps?: number): string {
  if (amps === undefined || amps === null) return 'N/A';
  return `${amps.toFixed(1)} A`;
}

export function formatPercentage(percent?: number): string {
  if (percent === undefined || percent === null) return 'N/A';
  return `${percent.toFixed(1)}%`;
}

export function formatFrequency(hz?: number): string {
  if (hz === undefined || hz === null) return 'N/A';
  return `${hz.toFixed(1)} Hz`;
}

export function getBatteryStatus(data: TelemetryData): BatteryStatus {
  const power = data.batt_power_w || 0;
  const status = power > 50 ? 'charging' : power < -50 ? 'discharging' : 'idle';
  
  return {
    soc: data.batt_soc_pct || 0,
    voltage: data.batt_voltage_v || 0,
    current: data.batt_current_a || 0,
    temperature: data.batt_temp_c || 0,
    power: power,
    status: status
  };
}

export function getPowerFlow(data: TelemetryData): PowerFlow {
  return {
    pv: data.pv_power_w || 0,
    load: data.load_power_w || 0,
    battery: data.batt_power_w || 0,
    grid: data.grid_power_w || 0
  };
}

export function getInverterStatus(data: TelemetryData): InverterStatus {
  return {
    mode: data.inverter_mode || 'Unknown',
    temperature: data.inverter_temp_c || 0,
    errorCode: data.error_code || 0,
    model: data.device_model || 'Unknown',
    serialNumber: data.device_serial_number || 'Unknown',
    ratedPower: data.rated_power || 0
  };
}

export function getBatteryStatusColor(status: 'charging' | 'discharging' | 'idle'): string {
  switch (status) {
    case 'charging': return '#10b981'; // green
    case 'discharging': return '#f59e0b'; // amber
    case 'idle': return '#6b7280'; // gray
    default: return '#6b7280';
  }
}

export function getSOCColor(soc: number): string {
  if (soc >= 80) return '#10b981'; // green
  if (soc >= 50) return '#f59e0b'; // amber
  if (soc >= 20) return '#ef4444'; // red
  return '#dc2626'; // dark red
}

export function getPowerColor(power: number): string {
  if (power > 0) return '#10b981'; // green (charging)
  if (power < 0) return '#f59e0b'; // amber (discharging)
  return '#6b7280'; // gray (idle)
}
