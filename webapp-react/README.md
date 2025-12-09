# Solar Monitoring Webapp

A comprehensive React-based web application for monitoring solar system telemetry data.

## Features

### 📊 Comprehensive Telemetry Dashboard
- **Real-time Power Flow**: Live monitoring of solar generation, load consumption, battery status, and grid interaction
- **Battery Status**: SOC, voltage, current, temperature, and charging/discharging status
- **Inverter Information**: Mode, temperature, error codes, device model, and serial number
- **Energy Totals**: Daily and total energy production, consumption, import/export
- **MPPT Details**: Individual MPPT tracker power outputs
- **Configuration**: Grid charge settings, power limits, TOU windows

### 📈 Real-time Charts
- **Power Flow Chart**: Visual representation of power flows over time
- **Color-coded Status**: Intuitive color coding for different states
- **Auto-refresh**: Data updates every 5 seconds

### 🎨 Modern UI
- **Responsive Design**: Works on desktop, tablet, and mobile
- **Clean Interface**: Card-based layout with clear data presentation
- **Status Indicators**: Visual indicators for battery and system status

## API Integration

The webapp connects to the SolarHub backend API to fetch comprehensive telemetry data including:

- Power flows (PV, Load, Battery, Grid)
- Battery parameters (SOC, voltage, current, temperature)
- Inverter status and configuration
- Energy totals and statistics
- MPPT tracker data
- TOU window settings

## Development

### Prerequisites
- Node.js 18+
- npm or yarn

### Installation
```bash
npm install
```

### Development Server
```bash
npm run dev
```

### Build for Production
```bash
npm run build
```

### Preview Production Build
```bash
npm run preview
```

## Configuration

Update the API base URL in `src/config.ts`:
```typescript
export const API_BASE_URL = 'http://localhost:8000';
```

## Components

- **TelemetryDashboard**: Main dashboard component with all telemetry data
- **PowerFlowChart**: Real-time power flow visualization
- **Utility Functions**: Data formatting and processing utilities

## Data Format

The webapp expects telemetry data in the following format:
```typescript
interface TelemetryData {
  ts: string;
  pv_power_w?: number;
  load_power_w?: number;
  batt_power_w?: number;
  grid_power_w?: number;
  batt_soc_pct?: number;
  batt_voltage_v?: number;
  batt_current_a?: number;
  // ... and many more fields
}
```

## Deployment

The built files in the `dist/` directory can be served by any static web server or integrated with the SolarHub backend.