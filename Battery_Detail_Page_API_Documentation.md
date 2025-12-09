# Battery Detail Page API Documentation

## Overview

The Battery Detail Page (`/battery-detail`) displays comprehensive battery information including device details, health metrics, system status, and per-battery unit data. This document describes the API endpoints and data structure required to support this page.

## API Endpoint

### GET `/api/battery/now`

Returns the latest battery bank telemetry data including all device information, health metrics, and status flags.

**Request:**
```http
GET /api/battery/now
```

**Response Format:**
```json
{
  "status": "ok",
  "battery": {
    "ts": "2025-01-18T12:00:00+00:00",
    "id": "battery1",
    "batteries_count": 2,
    "cells_per_battery": 15,
    "voltage": 53.2,
    "current": -0.4,
    "temperature": 35.3,
    "soc": 96,
    "devices": [
      {
        "power": 1,
        "voltage": 53.2,
        "current": -0.4,
        "temperature": 35.3,
        "soc": 96,
        "soh": 95,
        "cycles": 1234,
        "basic_st": "Normal",
        "volt_st": "OK",
        "temp_st": "OK",
        "current_st": "OK",
        "coul_st": "OK",
        "soh_st": "OK",
        "heater_st": "OFF"
      }
    ],
    "cells_data": [
      {
        "power": 1,
        "voltage_min": 3.305,
        "voltage_max": 3.331,
        "voltage_delta": 0.026,
        "temperature_min": 33.2,
        "temperature_max": 35.3,
        "temperature_delta": 2.1,
        "cells": [
          {
            "power": 1,
            "cell": 1,
            "voltage": 3.327,
            "temperature": 35.1,
            "soc": 96
          }
        ]
      }
    ],
    "extra": {
      // Device Information (from 'info' command)
      "serial_number": "HPTBH02240A03193",
      "barcode": "HPTBH02240A03193",
      "manufacturer": "Pylon",
      "model": "US2KBPL",
      "device_name": "US2KBPL",
      "device_address": 1,
      "specification": "48V/50AH",
      "cell_number": 15,
      
      // State of Health (from 'soh' command)
      "soh_percent": 95,
      "cycle_count": 1234,
      "cycles": 1234,
      "remaining_capacity": 47.5,
      
      // System Status (from 'stat'/'status' command)
      "system_status": "Normal",
      "has_alarm": false,
      "alarms": [],
      "has_warning": false,
      "warnings": [],
      "has_fault": false,
      "faults": [],
      "has_error": false,
      "errors": [],
      
      // Config data
      "dev_name": "Battery Bank 1",
      "manufacturer": "Pylon",
      "model": "US2KBPL"
    }
  }
}
```

## Data Fields Reference

### Top-Level Fields

| Field | Type | Description |
|-------|------|-------------|
| `ts` | string | Timestamp (ISO 8601) |
| `id` | string | Battery bank ID |
| `batteries_count` | number | Number of battery units |
| `cells_per_battery` | number | Number of cells per battery |
| `voltage` | number | Average bank voltage (V) |
| `current` | number | Total bank current (A) |
| `temperature` | number | Average bank temperature (°C) |
| `soc` | number | Average State of Charge (%) |
| `devices` | array | Array of battery unit objects |
| `cells_data` | array | Array of cell data per battery |
| `extra` | object | Additional device information and status |

### Device Information (`extra` object)

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `serial_number` | string | `info` command | Device serial number (Barcode) |
| `barcode` | string | `info` command | Same as serial_number |
| `manufacturer` | string | `info` command | Manufacturer name (e.g., "Pylon") |
| `model` | string | `info` command | Device model name |
| `device_name` | string | `info` command | Device name |
| `device_address` | number | `info` command | Device Modbus address |
| `specification` | string | `info` command | Battery specification (e.g., "48V/50AH") |
| `cell_number` | number | `info` command | Number of cells |

### Health Metrics (`extra` object)

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `soh_percent` | number | `soh` command | State of Health percentage (0-100) |
| `cycle_count` | number | `soh` command | Total cycle count |
| `cycles` | number | `soh` command | Same as cycle_count |
| `remaining_capacity` | number | `soh` command | Remaining capacity (Ah) |

### System Status (`extra` object)

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `system_status` | string | `stat` command | Overall system status |
| `has_alarm` | boolean | `stat` command | Whether alarms are present |
| `alarms` | array | `stat` command | Array of alarm messages |
| `has_warning` | boolean | `stat` command | Whether warnings are present |
| `warnings` | array | `stat` command | Array of warning messages |
| `has_fault` | boolean | `stat` command | Whether faults are present |
| `faults` | array | `stat` command | Array of fault messages |
| `has_error` | boolean | `stat` command | Whether errors are present |
| `errors` | array | `stat` command | Array of error messages |

### Battery Unit (`devices` array items)

| Field | Type | Description |
|-------|------|-------------|
| `power` | number | Battery unit number (1, 2, 3, ...) |
| `voltage` | number | Unit voltage (V) |
| `current` | number | Unit current (A, positive=charging, negative=discharging) |
| `temperature` | number | Unit temperature (°C) |
| `soc` | number | State of Charge (%) |
| `soh` | number | State of Health (%) |
| `cycles` | number | Cycle count for this unit |
| `basic_st` | string | Basic status |
| `volt_st` | string | Voltage status |
| `temp_st` | string | Temperature status |
| `current_st` | string | Current status |
| `coul_st` | string | Coulomb status |
| `soh_st` | string | SOH status |
| `heater_st` | string | Heater status |

### Cell Data (`cells_data` array items)

| Field | Type | Description |
|-------|------|-------------|
| `power` | number | Battery unit number |
| `voltage_min` | number | Minimum cell voltage (V) |
| `voltage_max` | number | Maximum cell voltage (V) |
| `voltage_delta` | number | Voltage difference (V) |
| `temperature_min` | number | Minimum cell temperature (°C) |
| `temperature_max` | number | Maximum cell temperature (°C) |
| `temperature_delta` | number | Temperature difference (°C) |
| `cells` | array | Array of individual cell objects |

### Cell Object (`cells` array items)

| Field | Type | Description |
|-------|------|-------------|
| `power` | number | Battery unit number |
| `cell` | number | Cell number |
| `voltage` | number | Cell voltage (V) |
| `temperature` | number | Cell temperature (°C) |
| `soc` | number | Cell State of Charge (%) |

## Frontend Usage

The Battery Detail Page component uses this API as follows:

```typescript
const fetchBattery = async () => {
  try {
    const res = await api.get('/api/battery/now') as any
    if (res && res.status === 'ok') {
      setBank(res.battery as BatteryBank)
      setError(null)
    } else {
      setError('No battery data')
    }
  } catch (e: any) {
    setError(e?.message || 'Failed to load battery')
  } finally {
    setLoading(false)
  }
}
```

## Data Flow

1. **Battery Adapter** (`solarhub/adapters/battery_pytes.py`):
   - Polls battery via serial console commands
   - Executes `info` command → populates `device_info`
   - Executes `soh` command → populates SOH data
   - Executes `stat` command → populates system status
   - Creates `BatteryBankTelemetry` object with `extra` field

2. **Application** (`solarhub/app.py`):
   - Stores latest telemetry in `self.battery_last`
   - Publishes to MQTT

3. **API Server** (`solarhub/api_server.py`):
   - Endpoint `/api/battery/now` retrieves `battery_last`
   - Calls `model_dump()` to serialize to JSON
   - Returns `{"status": "ok", "battery": {...}}`

4. **Frontend** (`webapp-react/src/routes/BatteryDetailPage.tsx`):
   - Fetches from `/api/battery/now` every 5 seconds
   - Extracts data from `bank.extra` for device info, health, and status
   - Displays in organized cards and panels

## Status Values

### Status Flags (Color Coding)

- **Green (Normal/OK)**: `"Normal"`, `"OK"`, `"normal"`, `"ok"`
- **Yellow (Warning)**: `"Warning"`, `"Caution"`, `"warning"`, `"caution"`
- **Orange (Alert)**: `"Alert"`, `"alert"`
- **Red (Fault/Error)**: `"Fault"`, `"Error"`, `"Critical"`, `"fault"`, `"error"`, `"critical"`

### SOH Status Levels

- **Excellent (Green)**: 80-100%
- **Good (Yellow)**: 60-79%
- **Fair (Orange)**: 40-59%
- **Poor (Red)**: <40%

## Error Handling

The API returns error responses in the following format:

```json
{
  "status": "error",
  "error": "Error message description"
}
```

The frontend handles these cases:
- `status === "ok"` but `battery === null` → Shows "No battery data"
- `status === "error"` → Shows error message
- Network errors → Shows "Failed to load battery"

## Current Implementation Status

✅ **Implemented:**
- `/api/battery/now` endpoint exists
- Returns `BatteryBankTelemetry` with `extra` field
- Includes device info from `info` command
- Includes SOH data from `soh` command
- Includes system status from `stat` command
- Includes per-battery unit data
- Includes cell-level data

✅ **Frontend Integration:**
- Battery Detail Page fetches from `/api/battery/now`
- Extracts all required fields from `bank.extra`
- Handles missing/null values gracefully
- Updates every 5 seconds

## Testing

To test the API endpoint:

```bash
# Using curl
curl http://localhost:8090/api/battery/now

# Using browser
http://localhost:8090/api/battery/now
```

Expected response should include:
- `status: "ok"`
- `battery` object with all fields
- `extra` object with device info, health metrics, and status
- `devices` array with per-battery data
- `cells_data` array with cell-level information

## Notes

1. **Data Availability**: Some fields may be `null` or `undefined` if:
   - Battery adapter hasn't polled yet
   - Commands (`info`, `soh`, `stat`) failed
   - Device doesn't support certain features

2. **Fallback Values**: The frontend uses fallback values (e.g., `'N/A'`) when data is missing

3. **Real-time Updates**: The page polls every 5 seconds to get latest data

4. **Serial Number**: Can be accessed via `extra.serial_number` or `extra.barcode` (both are the same)

5. **Cycle Count**: Can be accessed via `extra.cycle_count` or `extra.cycles` (both are the same)

