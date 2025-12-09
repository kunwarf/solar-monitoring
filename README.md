# Solar Monitoring System - Architecture & Module Documentation

## Table of Contents

1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Core Modules](#core-modules)
   - [API Server](#api-server)
   - [Device Adapters](#device-adapters)
   - [Smart Scheduler](#smart-scheduler)
   - [Logger](#logger)
   - [MQTT Publishing for Home Assistant](#mqtt-publishing-for-home-assistant)
   - [Forecasting System](#forecasting-system)
4. [Data Flow](#data-flow)
5. [Configuration](#configuration)
6. [Deployment](#deployment)

---

## Overview

The Solar Monitoring System is a comprehensive platform for monitoring and controlling solar inverters, battery banks, and energy management. It provides real-time telemetry, intelligent scheduling, forecasting, and Home Assistant integration.

### Key Features

- **Multi-Inverter Support**: Handles single or multiple inverters (arrays)
- **Phase Detection**: Automatically detects single-phase vs three-phase inverters
- **Standardized Data Mapping**: Consistent field names across all devices
- **Smart Scheduling**: Tariff-aware battery charging/discharging optimization
- **Forecasting**: Solar, load, battery, and grid power predictions
- **Home Assistant Integration**: Full MQTT discovery and control
- **RESTful API**: Comprehensive API for frontend and mobile apps
- **Data Logging**: SQLite-based historical data storage

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Solar Monitoring System                    │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
   ┌────▼────┐         ┌─────▼─────┐         ┌─────▼─────┐
   │ Device  │         │   Smart  │         │   API     │
   │Adapter  │────────▶│Scheduler │────────▶│  Server   │
   └────┬────┘         └─────┬─────┘         └─────┬─────┘
        │                   │                     │
        │              ┌────▼─────┐              │
        │              │Forecast  │              │
        │              │  Engine  │              │
        │              └────┬─────┘              │
        │                   │                     │
   ┌────▼────┐         ┌────▼─────┐         ┌────▼─────┐
   │ Logger  │         │   MQTT  │         │ Frontend │
   │ (SQLite)│         │Publisher│         │   (React) │
   └─────────┘         └────┬─────┘         └──────────┘
                            │
                     ┌──────▼──────┐
                     │Home Assistant│
                     └─────────────┘
```

### Component Interaction Flow

```
Device (Inverter/Battery)
    ↓
Device Adapter (Modbus RTU/TCP)
    ↓
TelemetryMapper (Standardize field names)
    ↓
SolarApp (Main Application)
    ├─→ Logger (Store in SQLite)
    ├─→ Smart Scheduler (Optimize battery)
    ├─→ MQTT Publisher (Home Assistant)
    └─→ API Server (Frontend/Mobile)
```

---

## Core Modules

### API Server

**Location**: `solarhub/api_server.py`

**Purpose**: Provides RESTful API endpoints for frontend and mobile applications to access telemetry data, configuration, and control inverters.

**Key Functions**:

1. **Telemetry Endpoints**:
   - `GET /api/now?inverter_id=<id>` - Get current telemetry for specific inverter
   - `GET /api/now?inverter_id=all` - Get consolidated telemetry for all inverters
   - Returns standardized field names with metadata (phase type, inverter count)

2. **Configuration Endpoints**:
   - `GET /api/config` - Get system configuration
   - `POST /api/config` - Update system configuration
   - `GET /api/inverter/sensors` - Get inverter sensor definitions
   - `POST /api/inverter/sensors/{sensor_id}` - Update sensor value
   - `POST /api/inverter/registers/{register_name}` - Write register value

3. **Device Management**:
   - `GET /api/devices` - List all devices (inverters, batteries)
   - `GET /api/inverters` - List all inverters
   - `GET /api/inverter/capabilities` - Get inverter capabilities

4. **Data Normalization**:
   - Maps device-specific field names to standardized names
   - Handles single-phase vs three-phase data
   - Consolidates data for multiple inverters (arrays)
   - Adds metadata (`_metadata`) with phase type and inverter count

**Technology**: FastAPI (Python async web framework)

**Example Response**:
```json
{
  "inverter_id": "powdrive1",
  "now": {
    "pv_power_w": 5000,
    "load_power_w": 3000,
    "grid_power_w": -2000,
    "batt_soc_pct": 75.5,
    "_metadata": {
      "phase_type": "three",
      "inverter_count": 1,
      "is_three_phase": true,
      "is_single_inverter": true
    },
    "load_l1_power_w": 1000,
    "load_l2_power_w": 1000,
    "load_l3_power_w": 1000
  }
}
```

---

### Device Adapters

**Location**: `solarhub/adapters/`

**Purpose**: Abstract communication layer between the system and physical devices (inverters, batteries). Handles Modbus RTU/TCP communication and converts device-specific data to standardized format.

**Key Components**:

1. **Base Adapter** (`base.py`):
   - `InverterAdapter` - Abstract base class for inverter adapters
   - `JsonRegisterMixin` - Provides JSON-driven register map support
   - `ModbusClientMixin` - Manages Modbus client connections
   - `read_all_registers()` - Reads all registers from register map

2. **Inverter Adapters**:
   - **PowdriveAdapter** (`powdrive.py`): Powdrive inverter support
   - **SenergyAdapter** (`senergy.py`): Senergy inverter support
   - Both use `TelemetryMapper` to convert device-specific names to standardized names

3. **Battery Adapter**:
   - **PytesBatteryAdapter** (`battery_pytes.py`): Pytes battery bank support

4. **Command Queue** (`command_queue.py`):
   - Manages write commands to devices
   - Serializes Modbus operations
   - Handles command retries and error recovery

**Key Functions**:

1. **Connection Management**:
   - `connect()` - Establishes Modbus connection (RTU/TCP)
   - `disconnect()` - Closes connection
   - Auto-reconnection on connection loss

2. **Data Reading**:
   - `poll()` - Reads all registers from device
   - Uses register map JSON files for data-driven communication
   - Maps device-specific field names to standardized names
   - Detects phase type (single/three phase) from register data

3. **Data Writing**:
   - `write_by_ident()` - Write single register by identifier
   - `write_many_by_ident()` - Write multiple registers
   - Validates values against register specifications

4. **Register Map**:
   - JSON files define all device registers (`register_maps/*.json`)
   - Includes: address, type, size, unit, scale, read/write permissions
   - Supports `standard_id` mapping for standardized field names

**Technology**: PyModbus (Modbus RTU/TCP), PySerial (serial communication)

**Example Register Map Entry**:
```json
{
  "id": "pv_power_w",
  "standard_id": "pv_power_w",
  "name": "PV Power",
  "addr": 625,
  "kind": "holding",
  "type": "S16",
  "size": 1,
  "unit": "W",
  "rw": "RO"
}
```

---

### Smart Scheduler

**Location**: `solarhub/schedulers/smart.py`

**Purpose**: Intelligent battery management system that optimizes charging/discharging based on:
- Time-of-use (TOU) tariffs
- Solar generation forecasts
- Load forecasts
- Battery state of charge (SOC)
- Grid conditions

**Key Functions**:

1. **Forecasting**:
   - **Solar Forecast**: Predicts PV generation for today and tomorrow
   - **Load Forecast**: Predicts load consumption based on historical patterns
   - **Battery Forecast**: Calculates battery capacity and energy requirements
   - **Grid Forecast**: Predicts grid import/export needs

2. **TOU Window Management**:
   - Supports up to 3 TOU windows per day
   - Each window has: start time, end time, tariff type (cheap/normal/peak)
   - Configurable grid charging during cheap windows
   - Configurable battery discharge during peak windows

3. **Battery Optimization**:
   - Targets SOC before sunset (configurable)
   - Uses cheap tariff windows for grid charging
   - Protects blackout reserve (emergency backup)
   - Adds hysteresis to prevent rapid switching
   - Caps grid charge power by current * voltage and model max

4. **Command Execution**:
   - Programs TOU windows to inverters
   - Sets charge/discharge power limits
   - Sets SOC targets
   - Monitors execution and adjusts as needed

**Supporting Modules**:

- **Load Forecasting** (`schedulers/load.py`):
  - Analyzes historical load data
  - Generates hourly load profiles
  - Considers day of week and day of year patterns
  - Uses median/percentile analysis for robustness

- **Solar Forecasting** (`schedulers/bias.py`):
  - Analyzes historical PV generation
  - Generates hourly solar profiles
  - Adjusts for seasonal variations
  - Uses weather forecast integration

- **Sunset Calculator** (`schedulers/sunset_calculator.py`):
   - Calculates sunset time for location
   - Used to determine optimal SOC target timing

**Technology**: Python async, pandas (data analysis), pvlib (solar calculations)

**Example Schedule**:
```python
TOU Windows:
  Window 1: 00:00-06:00 (cheap tariff) - Grid charge to 80% SOC
  Window 2: 06:00-18:00 (normal tariff) - Solar charge, discharge to load
  Window 3: 18:00-22:00 (peak tariff) - Discharge battery to 20% SOC
```

---

### Logger

**Location**: `solarhub/logging/logger.py`

**Purpose**: Stores historical telemetry data in SQLite database for analysis, forecasting, and reporting.

**Key Functions**:

1. **Data Storage**:
   - `insert_sample()` - Stores telemetry samples
   - `upsert_daily_pv()` - Stores daily PV energy totals
   - `insert_battery_bank_sample()` - Stores battery bank telemetry
   - `insert_battery_unit_samples()` - Stores individual battery unit data
   - `insert_battery_cell_samples()` - Stores cell-level battery data

2. **Database Schema**:

   **energy_samples** - Main telemetry table:
   ```sql
   CREATE TABLE energy_samples (
       ts TEXT NOT NULL,              -- Timestamp (ISO 8601)
       inverter_id TEXT NOT NULL,      -- Inverter identifier
       pv_power_w INTEGER,             -- PV power (watts)
       load_power_w INTEGER,            -- Load power (watts)
       grid_power_w INTEGER,           -- Grid power (watts)
       batt_voltage_v REAL,            -- Battery voltage (volts)
       batt_current_a REAL,            -- Battery current (amperes)
       soc REAL,                       -- State of charge (%)
       battery_soc REAL,               -- Battery SOC (alias)
       battery_voltage_v REAL,          -- Battery voltage (alias)
       battery_current_a REAL,         -- Battery current (alias)
       inverter_mode INTEGER,          -- Inverter mode
       inverter_temp_c REAL            -- Inverter temperature (°C)
   )
   ```

   **pv_daily** - Daily PV energy totals:
   ```sql
   CREATE TABLE pv_daily (
       day TEXT NOT NULL,              -- Date (YYYY-MM-DD)
       inverter_id TEXT NOT NULL,      -- Inverter identifier
       pv_kwh REAL NOT NULL,           -- Daily PV energy (kWh)
       PRIMARY KEY(day, inverter_id)
   )
   ```

   **battery_bank_samples** - Battery bank telemetry
   **battery_unit_samples** - Individual battery unit data
   **battery_cell_samples** - Cell-level battery data
   **configuration** - System configuration persistence

3. **Data Retrieval**:
   - Used by forecasting modules for historical analysis
   - Used by energy calculator for daily aggregations
   - Used by API for historical data queries

**Technology**: SQLite3 (embedded database)

**Database Location**: `~/.solarhub/solarhub.db` (user home directory)

---

### MQTT Publishing for Home Assistant

**Location**: `solarhub/mqtt.py`, `solarhub/ha/discovery.py`

**Purpose**: Publishes telemetry data and device configuration to Home Assistant via MQTT using the Home Assistant Discovery protocol.

**Key Functions**:

1. **MQTT Client** (`mqtt.py`):
   - `pub()` - Publish messages to MQTT topics
   - `sub()` - Subscribe to MQTT topics
   - Handles connection, authentication, and reconnection

2. **Home Assistant Discovery** (`ha/discovery.py`):
   - `publish_all_for_inverter()` - Publishes all register entities
   - `publish_register()` - Publishes individual register as HA entity
   - `refresh_device_info()` - Refreshes device information

3. **Entity Publishing**:
   - **Sensors**: Read-only telemetry data (power, voltage, current, temperature, etc.)
   - **Numbers**: Read-write configuration values (charge power, SOC targets, etc.)
   - **Selects**: Enum-based configuration (inverter mode, battery type, etc.)
   - **Switches**: Boolean configuration (grid charge enable, etc.)

4. **Topic Structure**:
   ```
   <base_topic>/<inverter_id>/regs          - State topic (all telemetry)
   <base_topic>/<inverter_id>/availability   - Availability topic
   homeassistant/sensor/<entity_id>/config   - Discovery config
   ```

5. **Phase-Aware Publishing**:
   - Single-phase inverters: Only basic sensors (no phase-specific entities)
   - Three-phase inverters: All sensors including phase-specific (L1, L2, L3)
   - Uses metadata to determine what to publish

**Technology**: Paho MQTT (Python MQTT client)

**Example Discovery Config**:
```json
{
  "name": "PV Power",
  "unique_id": "powdrive1_pv_power_w",
  "state_topic": "solar/fleet/powdrive1/regs",
  "value_template": "{{ value_json.pv_power_w }}",
  "unit_of_measurement": "W",
  "device_class": "power",
  "device": {
    "identifiers": ["powdrive1"],
    "manufacturer": "Powdrive",
    "model": "12k Hybrid",
    "name": "Powdrive 12k"
  }
}
```

---

### Forecasting System

**Location**: `solarhub/forecast/`, `solarhub/schedulers/`

**Purpose**: Predicts future energy generation and consumption to optimize battery management and grid interaction.

#### Solar Forecasting

**Location**: `solarhub/forecast/solar.py`, `solarhub/schedulers/bias.py`

**Methods**:

1. **Historical Analysis** (`bias.py`):
   - Analyzes historical PV generation data
   - Generates hourly solar profiles by day of year
   - Uses median values for robustness against outliers
   - Adjusts for seasonal variations

2. **Weather-Based Forecasting** (`forecast/solar.py`):
   - Integrates with weather APIs (OpenWeatherMap, WeatherAPI, etc.)
   - Uses solar irradiance forecasts
   - Calculates PV generation using pvlib
   - Considers array tilt, azimuth, and performance ratio

3. **Hybrid Approach**:
   - Combines historical patterns with weather forecasts
   - Adjusts historical profiles based on weather conditions
   - Provides both today and tomorrow forecasts

**Output**: Hourly PV generation forecast (kWh) for today and tomorrow

#### Load Forecasting

**Location**: `solarhub/schedulers/load.py`

**Methods**:

1. **Historical Analysis**:
   - Analyzes historical load consumption data
   - Generates hourly load profiles by day of week
   - Uses median/percentile analysis
   - Considers seasonal variations

2. **Pattern Recognition**:
   - Identifies weekday vs weekend patterns
   - Accounts for seasonal load variations
   - Uses recent days (60 days) and seasonal years (3 years) for accuracy

3. **Fallback Handling**:
   - Uses configurable fallback load if insufficient data
   - Smooths transitions between historical and forecast data

**Output**: Hourly load consumption forecast (kWh) for today

#### Battery Forecasting

**Location**: `solarhub/schedulers/smart.py`

**Methods**:

1. **Energy Balance Calculation**:
   - Calculates net energy (PV - Load) for each hour
   - Determines battery charging/discharging needs
   - Accounts for battery efficiency losses

2. **SOC Projection**:
   - Projects battery SOC throughout the day
   - Considers charge/discharge rates
   - Accounts for battery capacity limits

3. **Grid Interaction**:
   - Calculates grid import/export needs
   - Optimizes grid charging during cheap windows
   - Minimizes grid export during peak windows

**Output**: Battery SOC forecast, charge/discharge schedule

#### Grid Power Forecasting

**Location**: `solarhub/schedulers/smart.py`

**Methods**:

1. **Net Power Calculation**:
   - Grid Power = Load Power - PV Power - Battery Power
   - Positive = Grid import (consuming from grid)
   - Negative = Grid export (feeding to grid)

2. **Tariff Optimization**:
   - Minimizes grid import during peak hours
   - Maximizes grid export during peak hours (if profitable)
   - Uses battery to shift load from peak to off-peak

**Output**: Hourly grid power forecast (W) for today

**Technology**: pandas (data analysis), pvlib (solar calculations), weather APIs

**Example Forecast**:
```json
{
  "ts": "2024-01-15T10:00:00+05:00",
  "pv_today_kwh": 25.5,
  "pv_tomorrow_kwh": 28.2,
  "site_pv_hourly_kwh": {
    "0": 0.0, "1": 0.0, "2": 0.0, "3": 0.0,
    "6": 0.1, "7": 0.5, "8": 1.2, "9": 2.5,
    "10": 3.8, "11": 4.2, "12": 4.5, "13": 4.2,
    "14": 3.5, "15": 2.8, "16": 1.5, "17": 0.8,
    "18": 0.2, "19": 0.0, "20": 0.0, "21": 0.0
  },
  "load_hourly_kwh": {
    "0": 0.5, "1": 0.4, "2": 0.3, "3": 0.3,
    "6": 0.8, "7": 1.2, "8": 1.5, "9": 1.2,
    "10": 1.0, "11": 1.1, "12": 1.3, "13": 1.2,
    "14": 1.1, "15": 1.0, "16": 1.2, "17": 1.5,
    "18": 2.0, "19": 1.8, "20": 1.5, "21": 1.2
  }
}
```

---

## Data Flow

### Telemetry Collection Flow

```
1. Device (Inverter/Battery)
   ↓
2. Device Adapter (Modbus RTU/TCP)
   - Reads all registers from register map
   - Decodes values (scale, type conversion)
   ↓
3. TelemetryMapper
   - Maps device-specific names to standardized names
   - Detects phase type (single/three phase)
   ↓
4. Telemetry Object
   - Standardized field names
   - Phase type metadata
   - All register values in 'extra' dict
   ↓
5. SolarApp (Main Application)
   ├─→ Logger: Store in SQLite database
   ├─→ Smart Scheduler: Optimize battery management
   ├─→ MQTT Publisher: Publish to Home Assistant
   └─→ API Server: Serve to frontend/mobile
```

### Command Execution Flow

```
1. API Server / Home Assistant
   - Receives write command
   ↓
2. Command Queue Manager
   - Validates command
   - Queues for execution
   ↓
3. Device Adapter
   - Writes to device register
   - Validates response
   ↓
4. Device (Inverter/Battery)
   - Executes command
   - Updates register value
```

### Forecasting Flow

```
1. Historical Data (Logger)
   - PV generation history
   - Load consumption history
   ↓
2. Forecast Engine
   - Analyzes patterns
   - Generates hourly profiles
   ↓
3. Weather Integration (Optional)
   - Gets weather forecast
   - Adjusts solar forecast
   ↓
4. Smart Scheduler
   - Uses forecasts for optimization
   - Generates battery schedule
   ↓
5. Device Adapter
   - Programs TOU windows
   - Sets charge/discharge limits
```

---

## Configuration

### Main Configuration File

**Location**: `config.yaml`

**Key Sections**:

1. **Inverters**:
   ```yaml
   inverters:
     - id: powdrive1
       name: "Powdrive 12k"
       phase_type: "three"  # Optional: "single" | "three" | null (auto-detect)
       adapter:
         type: powdrive
         transport: rtu
         serial_port: /dev/ttyUSB0
         baudrate: 9600
         register_map_file: register_maps/powdrive_registers.json
   ```

2. **Smart Scheduler**:
   ```yaml
   smart:
     enabled: true
     forecast:
       provider: openweather  # openweather | weatherapi | simple
       lat: 24.8607
       lon: 67.0011
     policy:
       target_soc_before_sunset_pct: 80
       emergency_reserve_hours: 2
   ```

3. **MQTT**:
   ```yaml
   mqtt:
     host: localhost
     port: 1883
     base_topic: solar/fleet
     ha_discovery: true
   ```

4. **Polling**:
   ```yaml
   polling:
     interval_secs: 10.0
     timeout_ms: 1500
     concurrent: 5
   ```

---

## Deployment

### System Requirements

- **Python**: 3.11+
- **Operating System**: Linux (recommended), Windows, macOS
- **Dependencies**: See `requirements.txt`

### Installation

```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate      # Windows

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Run application
python -m solarhub.main --config config.yaml
```

### Systemd Service

See `SYSTEMD_SERVICE_SETUP.md` for systemd service configuration.

### Docker Deployment

See `docker-compose.yml` for Docker deployment configuration.

---

## Module Dependencies

```
SolarApp (Main)
├── Device Adapters
│   ├── Modbus Client (PyModbus)
│   └── Register Maps (JSON)
├── Smart Scheduler
│   ├── Load Forecasting
│   ├── Solar Forecasting
│   └── Weather APIs
├── Logger
│   └── SQLite Database
├── MQTT Publisher
│   └── Paho MQTT Client
└── API Server
    └── FastAPI
```

---

## Standardized Field Names

All modules use standardized field names for consistency:

- **Power**: `pv_power_w`, `load_power_w`, `grid_power_w`, `batt_power_w`
- **Voltage**: `batt_voltage_v`, `grid_l1_voltage_v`, `load_l1_voltage_v`
- **Current**: `batt_current_a`, `grid_l1_current_a`, `load_l1_current_a`
- **Energy**: `today_energy`, `today_load_energy`, `today_import_energy`
- **Battery**: `batt_soc_pct`, `batt_temp_c`
- **Inverter**: `inverter_temp_c`, `inverter_mode`

See `register_maps/STANDARD_FIELD_NAMES.md` for complete list.

---

## Inverter Type Detection

The system automatically detects:

- **Phase Type**: Single-phase vs three-phase
  - From `inverter_type` register
  - From phase-specific data (L1, L2, L3)
  - Configurable override

- **Inverter Count**: Single vs array
  - Counts number of configured inverters
  - Consolidates data for arrays

Metadata is published in all responses:
```json
{
  "_metadata": {
    "phase_type": "three",
    "inverter_count": 1,
    "is_three_phase": true,
    "is_single_phase": false,
    "is_single_inverter": true,
    "is_inverter_array": false
  }
}
```

---

## Additional Resources

- **Telemetry Mapping System**: `TELEMETRY_MAPPING_SYSTEM.md`
- **Inverter Metadata System**: `INVERTER_METADATA_SYSTEM.md`
- **Standard Field Names**: `register_maps/STANDARD_FIELD_NAMES.md`
- **Systemd Service Setup**: `SYSTEMD_SERVICE_SETUP.md`
- **Migration Guide**: `MIGRATION_CHECKLIST.md`

---

## License

[Add your license information here]

---

## Support

[Add support contact information here]

