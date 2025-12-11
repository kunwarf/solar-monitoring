# Complete Hierarchy Structure - Database & Configuration Mapping

## Executive Summary

This document defines the complete hierarchical structure for the solar monitoring system, mapping it to database tables, configuration files, and identifying gaps that need to be addressed.

**Key Architectural Change**: The system now uses **database as the primary source of truth** for all configuration. `config.yaml` is **redundant** and serves only as a **fallback mechanism**. The system automatically:
- Discovers devices via USB serial port scanning
- Creates a default system structure if none exists
- Auto-configures discovered devices
- Allows users to manage configuration via frontend UI or API

---

## 1. HIERARCHY STRUCTURE

### Visual Hierarchy

```
System (Multiple systems supported)
│
├── Inverter Arrays (Logical groups of inverters)
│   ├── Inverter 1
│   ├── Inverter 2
│   └── ...
│
├── Battery Arrays (Logical groups of battery packs)
│   ├── Battery Pack 1
│   │   ├── Battery 1 (Individual battery unit)
│   │   │   ├── Cell 1
│   │   │   ├── Cell 2
│   │   │   └── ...
│   │   ├── Battery 2
│   │   │   ├── Cell 1
│   │   │   └── ...
│   │   └── ...
│   ├── Battery Pack 2
│   └── ...
│
└── Energy Meters (Attached to system level)
    ├── Meter 1 (Grid meter)
    └── Meter 2 (Consumption meter)
```

### Relationships

1. **System → Inverter Arrays**: One-to-many (one system has multiple inverter arrays)
2. **System → Battery Arrays**: One-to-many (one system has multiple battery arrays)
3. **System → Meters**: One-to-many (one system has multiple meters)
4. **Inverter Array → Inverters**: One-to-many (one array has multiple inverters)
5. **Battery Array → Battery Packs**: One-to-many (one array has multiple battery packs)
6. **Battery Pack → Batteries**: One-to-many (one pack has multiple battery units)
7. **Battery → Cells**: One-to-many (one battery has multiple cells)
8. **Battery Array ↔ Inverter Array**: One-to-one attachment (one battery array attached to one inverter array)
9. **Adapter Base → Adapters**: One-to-many (one adapter type has multiple adapter instances)
10. **Inverter → Adapter**: Many-to-one (each inverter has one adapter)
11. **Battery Pack → Adapter(s)**: Many-to-many (battery packs can have multiple adapters with priorities for failover)
12. **Meter → Adapter**: Many-to-one (each meter has one adapter)

---

## 2. DATABASE SCHEMA ANALYSIS

### 2.1 Current Tables

#### ✅ Existing Tables

| Table Name | Purpose | Status | Notes |
|------------|---------|--------|-------|
| `arrays` | Inverter array catalog | ✅ Exists | Missing `system_id` foreign key |
| `battery_packs` | Battery pack catalog | ✅ Exists | Missing `battery_array_id` and `system_id` |
| `battery_pack_attachments` | Pack-to-array attachments | ✅ Exists | Legacy structure (pack → array) |
| `energy_samples` | Inverter telemetry samples | ✅ Exists | Has `array_id`, missing `system_id` |
| `array_samples` | Array aggregated samples | ✅ Exists | Missing `system_id` |
| `battery_bank_samples` | Battery bank telemetry | ✅ Exists | Has `pack_id` and `array_id`, missing `system_id` |
| `battery_unit_samples` | Individual battery unit samples | ✅ Exists | Missing `pack_id`, `battery_id`, `system_id` |
| `battery_cell_samples` | Cell-level samples | ✅ Exists | Missing `battery_id`, `pack_id`, `system_id` |
| `meter_samples` | Meter telemetry samples | ✅ Exists | Has `array_id`, missing `system_id` |
| `meter_daily` | Daily meter summaries | ✅ Exists | Has `array_id`, missing `system_id` |
| `meter_hourly_energy` | Hourly meter energy | ✅ Exists | Missing `system_id` |
| `hourly_energy` | Hourly energy summaries | ✅ Exists | Missing `array_id` and `system_id` |
| `daily_summary` | Daily summaries | ✅ Exists | Missing `array_id` and `system_id` |
| `inverter_config` | Inverter configuration | ✅ Exists | Missing `array_id` and `system_id` |
| `inverter_setpoints` | Scheduler setpoints | ✅ Exists | Has `array_id`, missing `system_id` |

#### ❌ Missing Tables

| Table Name | Purpose | Required Fields |
|------------|---------|----------------|
| `systems` | System catalog | `system_id` (PK), `name`, `description`, `timezone`, `created_at`, `updated_at` |
| `inverters` | Inverter catalog | `inverter_id` (PK), `array_id` (FK), `system_id` (FK), `name`, `model`, `serial_number`, `vendor`, `phase_type`, `created_at` |
| `battery_arrays` | Battery array catalog | `battery_array_id` (PK), `system_id` (FK), `name`, `created_at` |
| `battery_array_attachments` | Battery array to inverter array attachments | `battery_array_id` (FK), `inverter_array_id` (FK), `attached_since`, `detached_at` |
| `batteries` | Individual battery unit catalog | `battery_id` (PK), `pack_id` (FK), `battery_array_id` (FK), `system_id` (FK), `serial_number`, `model`, `created_at` |
| `battery_cells` | Cell catalog | `cell_id` (PK), `battery_id` (FK), `pack_id` (FK), `battery_array_id` (FK), `system_id` (FK), `cell_index`, `nominal_voltage`, `created_at` |
| `meters` | Meter catalog | `meter_id` (PK), `system_id` (FK), `array_id` (FK, nullable), `adapter_id` (FK), `name`, `model`, `type`, `attachment_target`, `created_at` |
| `adapter_base` | Supported adapter types catalog | `adapter_type` (PK), `device_category`, `name`, `description`, `config_schema`, `supported_transports`, `default_config`, `version`, `created_at` |
| `adapters` | Adapter instances | `adapter_id` (PK), `adapter_type` (FK), `device_category`, `name`, `config_json`, `device_id`, `device_type`, `priority`, `enabled`, `created_at` |
| `battery_pack_adapters` | Battery pack to adapter associations | `pack_id` (FK), `adapter_id` (FK), `priority`, `enabled`, `created_at` |
| `device_discovery` | Auto-discovered devices | `device_id` (PK), `device_type`, `serial_number`, `port`, `adapter_config`, `status`, `is_auto_discovered`, `created_at` | ✅ Exists | Used for auto-discovery, needs integration with catalog tables |

#### ⚠️ Tables Needing Updates

1. **`arrays`**: Add `system_id` foreign key
2. **`battery_packs`**: Add `battery_array_id` and `system_id` foreign keys
3. **`battery_pack_attachments`**: Should reference `battery_array_id` instead of direct `array_id` (or keep both for backward compatibility)
4. **All sample tables**: Add `system_id` foreign key for multi-system support
5. **All summary tables**: Add `system_id` and `array_id` where missing

---

## 3. CONFIGURATION ARCHITECTURE ANALYSIS

### 3.1 Configuration Source Priority

**Primary Source: Database**
- All configuration is stored in database tables (`systems`, `arrays`, `inverters`, `battery_packs`, `meters`, `adapters`)
- Configuration can be managed via:
  - Frontend UI (primary method for users)
  - REST API (programmatic access)
  - Auto-discovery (automatic device detection and configuration)

**Fallback Source: config.yaml**
- `config.yaml` is now **redundant** and serves as a fallback mechanism
- Used only when:
  - Initial system setup (first-time installation)
  - Database recovery (if database is corrupted or empty)
  - Manual configuration import

### 3.2 Current config.yaml Structure (Fallback Reference)

```yaml
home:                          # ✅ Exists - Top level (maps to system in DB)
  id: system  # Note: config uses "home" but DB uses "system"
  name: "My Solar System"
  description: "Main residential solar system"

arrays:                       # ✅ Exists - Inverter arrays
  - id: array1
    name: "Ground Floor"
    inverter_ids: [powdrive2, senergy1]

inverters:                    # ✅ Exists - Individual inverters
  - id: powdrive1
    name: Powdrive
    array_id: array2          # ✅ Has array_id

battery_banks:                # ✅ Exists - Individual battery banks (packs)
  - id: battery1
    name: Pylontech Battery Bank
    adapter: {...}

battery_bank_arrays:          # ✅ Exists - Battery arrays
  - id: battery_array1
    name: "Ground Floor Battery Array"
    battery_bank_ids: [jkbms_bank_ble]

battery_bank_array_attachments: # ✅ Exists - Attachments
  - battery_bank_array_id: battery_array1
    inverter_array_id: array1

meters:                       # ✅ Exists - Energy meters
  - id: grid_meter_1
    name: IAMMeter
    array_id: home            # ✅ Can attach to home or array
```

### 3.3 Config Structure Mapping (Fallback Reference)

| Config Section | Maps To | Database Table | Status |
|----------------|---------|---------------|--------|
| `home` | System entity (config uses "home", DB uses "system") | `systems` | ❌ Table missing |
| `arrays` | Inverter arrays | `arrays` | ✅ Exists (needs `system_id`) |
| `inverters` | Individual inverters | `inverters` | ❌ Table missing |
| `inverters[].adapter` | Inverter adapter instance | `adapters` | ❌ Table missing |
| `battery_banks` | Battery packs | `battery_packs` | ✅ Exists (needs `battery_array_id`, `system_id`) |
| `battery_banks[].adapter` or `battery_banks[].adapters[]` | Battery adapter instance(s) | `adapters` + `battery_pack_adapters` | ❌ Tables missing |
| `battery_bank_arrays` | Battery arrays | `battery_arrays` | ❌ Table missing |
| `battery_bank_array_attachments` | Attachments | `battery_array_attachments` | ❌ Table missing |
| `meters` | Energy meters | `meters` | ❌ Table missing |
| `meters[].adapter` | Meter adapter instance | `adapters` | ❌ Table missing |
| Adapter types (powdrive, senergy, pytes, jkbms_*, iammeter) | Supported adapter definitions | `adapter_base` | ❌ Table missing |

### 3.4 Auto-Discovery Integration

**Device Discovery → Database Catalog Flow**:

1. **Device Discovery** (`device_discovery` table):
   - Scans USB ports and identifies devices
   - Stores: `device_id`, `device_type`, `serial_number`, `port`, `adapter_config`, `status`

2. **Auto-Creation of Catalog Entries**:
   - **Inverters**: Auto-discovered inverters → `inverters` table → assigned to default `array1`
   - **Battery Packs**: Auto-discovered batteries → `battery_packs` table → assigned to default `battery_array1`
   - **Meters**: Auto-discovered meters → `meters` table → attached to system level

3. **Auto-Creation of Adapters**:
   - Adapter instances created in `adapters` table from `device_discovery.adapter_config`
   - Linked to devices via `adapter_id` foreign keys

4. **Auto-Creation of System Structure**:
   - If no system exists → create default system ("system")
   - If no inverter array exists → create default array ("array1")
   - If no battery array exists → create default array ("battery_array1")
   - Auto-attach battery array to inverter array

---

## 4. PROPOSED COMPLETE DATABASE SCHEMA

### 4.1 Catalog Tables (Device Definitions)

```sql
-- ============= SYSTEM CATALOG =============
CREATE TABLE systems (
    system_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    timezone TEXT DEFAULT 'Asia/Karachi',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============= INVERTER ARRAY CATALOG =============
CREATE TABLE arrays (
    array_id TEXT PRIMARY KEY,
    system_id TEXT NOT NULL,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (system_id) REFERENCES systems(system_id) ON DELETE CASCADE
);

-- ============= INVERTER CATALOG =============
CREATE TABLE inverters (
    inverter_id TEXT PRIMARY KEY,
    array_id TEXT NOT NULL,
    system_id TEXT NOT NULL,
    adapter_id TEXT,  -- Foreign key to adapters table
    name TEXT NOT NULL,
    model TEXT,
    serial_number TEXT,
    vendor TEXT,  -- 'powdrive', 'senergy', etc. (can be derived from adapter_type)
    phase_type TEXT,  -- 'single', 'three', 'auto'
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (array_id) REFERENCES arrays(array_id) ON DELETE CASCADE,
    FOREIGN KEY (system_id) REFERENCES systems(system_id) ON DELETE CASCADE,
    FOREIGN KEY (adapter_id) REFERENCES adapters(adapter_id) ON DELETE SET NULL
);

-- ============= BATTERY ARRAY CATALOG =============
CREATE TABLE battery_arrays (
    battery_array_id TEXT PRIMARY KEY,
    system_id TEXT NOT NULL,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (system_id) REFERENCES systems(system_id) ON DELETE CASCADE
);

-- ============= BATTERY PACK CATALOG =============
CREATE TABLE battery_packs (
    pack_id TEXT PRIMARY KEY,
    battery_array_id TEXT NOT NULL,
    system_id TEXT NOT NULL,
    name TEXT NOT NULL,
    chemistry TEXT,  -- 'LFP', 'NMC', etc.
    nominal_kwh REAL,
    max_charge_kw REAL,
    max_discharge_kw REAL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (battery_array_id) REFERENCES battery_arrays(battery_array_id) ON DELETE CASCADE,
    FOREIGN KEY (system_id) REFERENCES systems(system_id) ON DELETE CASCADE
);

-- ============= BATTERY PACK ADAPTER ASSOCIATIONS =============
-- Many-to-many relationship: Battery packs can have multiple adapters (for failover)
CREATE TABLE battery_pack_adapters (
    pack_id TEXT NOT NULL,
    adapter_id TEXT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 1,  -- Lower number = higher priority
    enabled BOOLEAN DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (pack_id, adapter_id),
    FOREIGN KEY (pack_id) REFERENCES battery_packs(pack_id) ON DELETE CASCADE,
    FOREIGN KEY (adapter_id) REFERENCES adapters(adapter_id) ON DELETE CASCADE
);

-- ============= INDIVIDUAL BATTERY UNIT CATALOG =============
CREATE TABLE batteries (
    battery_id TEXT PRIMARY KEY,
    pack_id TEXT NOT NULL,
    battery_array_id TEXT NOT NULL,
    system_id TEXT NOT NULL,
    battery_index INTEGER NOT NULL,  -- Index within pack (0-based)
    serial_number TEXT,
    model TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (pack_id) REFERENCES battery_packs(pack_id) ON DELETE CASCADE,
    FOREIGN KEY (battery_array_id) REFERENCES battery_arrays(battery_array_id) ON DELETE CASCADE,
    FOREIGN KEY (system_id) REFERENCES systems(system_id) ON DELETE CASCADE,
    UNIQUE(pack_id, battery_index)
);

-- ============= BATTERY CELL CATALOG =============
CREATE TABLE battery_cells (
    cell_id TEXT PRIMARY KEY,
    battery_id TEXT NOT NULL,
    pack_id TEXT NOT NULL,
    battery_array_id TEXT NOT NULL,
    system_id TEXT NOT NULL,
    cell_index INTEGER NOT NULL,  -- Index within battery (0-based)
    nominal_voltage REAL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (battery_id) REFERENCES batteries(battery_id) ON DELETE CASCADE,
    FOREIGN KEY (pack_id) REFERENCES battery_packs(pack_id) ON DELETE CASCADE,
    FOREIGN KEY (battery_array_id) REFERENCES battery_arrays(battery_array_id) ON DELETE CASCADE,
    FOREIGN KEY (system_id) REFERENCES systems(system_id) ON DELETE CASCADE,
    UNIQUE(battery_id, cell_index)
);

-- ============= BATTERY ARRAY ATTACHMENTS =============
CREATE TABLE battery_array_attachments (
    battery_array_id TEXT NOT NULL,
    inverter_array_id TEXT NOT NULL,
    attached_since TEXT NOT NULL,
    detached_at TEXT,  -- NULL = active attachment
    PRIMARY KEY (battery_array_id, attached_since),
    FOREIGN KEY (battery_array_id) REFERENCES battery_arrays(battery_array_id) ON DELETE CASCADE,
    FOREIGN KEY (inverter_array_id) REFERENCES arrays(array_id) ON DELETE CASCADE
);

-- ============= ENERGY METER CATALOG =============
CREATE TABLE meters (
    meter_id TEXT PRIMARY KEY,
    system_id TEXT NOT NULL,
    array_id TEXT,  -- NULL = system-level meter, otherwise array-level
    adapter_id TEXT,  -- Foreign key to adapters table
    name TEXT NOT NULL,
    model TEXT,
    type TEXT,  -- 'grid', 'consumption', etc.
    attachment_target TEXT,  -- 'system' or array_id
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (system_id) REFERENCES systems(system_id) ON DELETE CASCADE,
    FOREIGN KEY (array_id) REFERENCES arrays(array_id) ON DELETE SET NULL,
    FOREIGN KEY (adapter_id) REFERENCES adapters(adapter_id) ON DELETE SET NULL
);

-- ============= ADAPTER BASE CATALOG =============
-- Defines all supported adapter types with their base configuration schema
CREATE TABLE adapter_base (
    adapter_type TEXT PRIMARY KEY,  -- e.g., 'powdrive', 'senergy', 'pytes', 'jkbms_tcpip', 'jkbms_ble', 'iammeter'
    device_category TEXT NOT NULL,  -- 'inverter', 'battery', 'meter'
    name TEXT NOT NULL,  -- Human-readable name, e.g., 'Powdrive Inverter Adapter'
    description TEXT,
    config_schema TEXT NOT NULL,  -- JSON schema defining required/optional configuration fields
    supported_transports TEXT,  -- JSON array of supported transports, e.g., '["rtu", "tcp"]'
    default_config TEXT,  -- JSON object with default configuration values
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============= ADAPTER INSTANCES =============
-- Actual adapter instances with device-specific configuration
CREATE TABLE adapters (
    adapter_id TEXT PRIMARY KEY,  -- Unique ID for this adapter instance
    adapter_type TEXT NOT NULL,  -- References adapter_base.adapter_type
    device_category TEXT NOT NULL,  -- 'inverter', 'battery', 'meter'
    name TEXT,  -- Optional name for this adapter instance
    config_json TEXT NOT NULL,  -- JSON object with complete adapter configuration
    device_id TEXT,  -- ID of the device this adapter is attached to (inverter_id, pack_id, or meter_id)
    device_type TEXT,  -- 'inverter', 'battery_pack', 'meter'
    priority INTEGER DEFAULT 1,  -- For failover adapters (lower = higher priority)
    enabled BOOLEAN DEFAULT 1,  -- Whether this adapter is currently enabled
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (adapter_type) REFERENCES adapter_base(adapter_type) ON DELETE RESTRICT
);
```

### 4.2 Sample Tables (Time-Series Data)

```sql
-- ============= INVERTER SAMPLES =============
CREATE TABLE energy_samples (
    ts TEXT NOT NULL,
    inverter_id TEXT NOT NULL,
    array_id TEXT NOT NULL,
    system_id TEXT NOT NULL,
    pv_power_w INTEGER,
    load_power_w INTEGER,
    grid_power_w INTEGER,
    batt_voltage_v REAL,
    batt_current_a REAL,
    soc REAL,
    battery_soc REAL,
    battery_voltage_v REAL,
    battery_current_a REAL,
    inverter_mode INTEGER,
    inverter_temp_c REAL,
    grid_import_wh REAL,
    grid_export_wh REAL,
    PRIMARY KEY (ts, inverter_id),
    FOREIGN KEY (inverter_id) REFERENCES inverters(inverter_id) ON DELETE CASCADE,
    FOREIGN KEY (array_id) REFERENCES arrays(array_id) ON DELETE CASCADE,
    FOREIGN KEY (system_id) REFERENCES systems(system_id) ON DELETE CASCADE
);

-- ============= ARRAY AGGREGATED SAMPLES =============
CREATE TABLE array_samples (
    ts TEXT NOT NULL,
    array_id TEXT NOT NULL,
    system_id TEXT NOT NULL,
    pv_power_w INTEGER,
    load_power_w INTEGER,
    grid_power_w INTEGER,
    batt_power_w INTEGER,
    batt_soc_pct REAL,
    batt_voltage_v REAL,
    batt_current_a REAL,
    PRIMARY KEY (ts, array_id),
    FOREIGN KEY (array_id) REFERENCES arrays(array_id) ON DELETE CASCADE,
    FOREIGN KEY (system_id) REFERENCES systems(system_id) ON DELETE CASCADE
);

-- ============= BATTERY PACK SAMPLES =============
CREATE TABLE battery_bank_samples (
    ts TEXT NOT NULL,
    pack_id TEXT NOT NULL,
    battery_array_id TEXT NOT NULL,
    system_id TEXT NOT NULL,
    voltage REAL,
    current REAL,
    temperature REAL,
    soc REAL,
    batteries_count INTEGER,
    cells_per_battery INTEGER,
    PRIMARY KEY (ts, pack_id),
    FOREIGN KEY (pack_id) REFERENCES battery_packs(pack_id) ON DELETE CASCADE,
    FOREIGN KEY (battery_array_id) REFERENCES battery_arrays(battery_array_id) ON DELETE CASCADE,
    FOREIGN KEY (system_id) REFERENCES systems(system_id) ON DELETE CASCADE
);

-- ============= INDIVIDUAL BATTERY UNIT SAMPLES =============
CREATE TABLE battery_unit_samples (
    ts TEXT NOT NULL,
    battery_id TEXT NOT NULL,
    pack_id TEXT NOT NULL,
    battery_array_id TEXT NOT NULL,
    system_id TEXT NOT NULL,
    power INTEGER NOT NULL,
    voltage REAL,
    current REAL,
    temperature REAL,
    soc REAL,
    basic_st TEXT,
    volt_st TEXT,
    current_st TEXT,
    temp_st TEXT,
    soh_st TEXT,
    coul_st TEXT,
    heater_st TEXT,
    bat_events INTEGER,
    power_events INTEGER,
    sys_events INTEGER,
    PRIMARY KEY (ts, battery_id),
    FOREIGN KEY (battery_id) REFERENCES batteries(battery_id) ON DELETE CASCADE,
    FOREIGN KEY (pack_id) REFERENCES battery_packs(pack_id) ON DELETE CASCADE,
    FOREIGN KEY (battery_array_id) REFERENCES battery_arrays(battery_array_id) ON DELETE CASCADE,
    FOREIGN KEY (system_id) REFERENCES systems(system_id) ON DELETE CASCADE
);

-- ============= BATTERY CELL SAMPLES =============
CREATE TABLE battery_cell_samples (
    ts TEXT NOT NULL,
    cell_id TEXT NOT NULL,
    battery_id TEXT NOT NULL,
    pack_id TEXT NOT NULL,
    battery_array_id TEXT NOT NULL,
    system_id TEXT NOT NULL,
    power INTEGER NOT NULL,
    cell INTEGER NOT NULL,  -- Cell index within battery
    voltage REAL,
    temperature REAL,
    soc REAL,
    volt_st TEXT,
    temp_st TEXT,
    PRIMARY KEY (ts, cell_id),
    FOREIGN KEY (cell_id) REFERENCES battery_cells(cell_id) ON DELETE CASCADE,
    FOREIGN KEY (battery_id) REFERENCES batteries(battery_id) ON DELETE CASCADE,
    FOREIGN KEY (pack_id) REFERENCES battery_packs(pack_id) ON DELETE CASCADE,
    FOREIGN KEY (battery_array_id) REFERENCES battery_arrays(battery_array_id) ON DELETE CASCADE,
    FOREIGN KEY (system_id) REFERENCES systems(system_id) ON DELETE CASCADE
);

-- ============= METER SAMPLES =============
CREATE TABLE meter_samples (
    ts TEXT NOT NULL,
    meter_id TEXT NOT NULL,
    system_id TEXT NOT NULL,
    array_id TEXT,  -- NULL for system-level meters
    grid_power_w INTEGER,
    grid_voltage_v REAL,
    grid_current_a REAL,
    grid_frequency_hz REAL,
    grid_import_wh INTEGER,
    grid_export_wh INTEGER,
    energy_kwh REAL,
    power_factor REAL,
    voltage_phase_a REAL,
    voltage_phase_b REAL,
    voltage_phase_c REAL,
    current_phase_a REAL,
    current_phase_b REAL,
    current_phase_c REAL,
    power_phase_a INTEGER,
    power_phase_b INTEGER,
    power_phase_c INTEGER,
    PRIMARY KEY (ts, meter_id),
    FOREIGN KEY (meter_id) REFERENCES meters(meter_id) ON DELETE CASCADE,
    FOREIGN KEY (system_id) REFERENCES systems(system_id) ON DELETE CASCADE,
    FOREIGN KEY (array_id) REFERENCES arrays(array_id) ON DELETE SET NULL
);
```

### 4.3 Aggregated Summary Tables (Hourly/Daily)

```sql
-- ============= HOURLY ENERGY SUMMARIES =============
CREATE TABLE hourly_energy (
    inverter_id TEXT NOT NULL,
    array_id TEXT NOT NULL,
    system_id TEXT NOT NULL,
    date TEXT NOT NULL,
    hour_start INTEGER NOT NULL,
    solar_energy_kwh REAL,
    load_energy_kwh REAL,
    battery_charge_energy_kwh REAL,
    battery_discharge_energy_kwh REAL,
    grid_import_energy_kwh REAL,
    grid_export_energy_kwh REAL,
    avg_solar_power_w REAL,
    avg_load_power_w REAL,
    avg_battery_power_w REAL,
    avg_grid_power_w REAL,
    sample_count INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (inverter_id, date, hour_start),
    FOREIGN KEY (inverter_id) REFERENCES inverters(inverter_id) ON DELETE CASCADE,
    FOREIGN KEY (array_id) REFERENCES arrays(array_id) ON DELETE CASCADE,
    FOREIGN KEY (system_id) REFERENCES systems(system_id) ON DELETE CASCADE
);

-- ============= ARRAY HOURLY ENERGY =============
CREATE TABLE array_hourly_energy (
    array_id TEXT NOT NULL,
    system_id TEXT NOT NULL,
    date TEXT NOT NULL,
    hour_start INTEGER NOT NULL,
    solar_energy_kwh REAL,
    load_energy_kwh REAL,
    battery_charge_energy_kwh REAL,
    battery_discharge_energy_kwh REAL,
    grid_import_energy_kwh REAL,
    grid_export_energy_kwh REAL,
    avg_solar_power_w REAL,
    avg_load_power_w REAL,
    avg_battery_power_w REAL,
    avg_grid_power_w REAL,
    sample_count INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (array_id, date, hour_start),
    FOREIGN KEY (array_id) REFERENCES arrays(array_id) ON DELETE CASCADE,
    FOREIGN KEY (system_id) REFERENCES systems(system_id) ON DELETE CASCADE
);

-- ============= SYSTEM HOURLY ENERGY =============
CREATE TABLE system_hourly_energy (
    system_id TEXT NOT NULL,
    date TEXT NOT NULL,
    hour_start INTEGER NOT NULL,
    solar_energy_kwh REAL,
    load_energy_kwh REAL,
    battery_charge_energy_kwh REAL,
    battery_discharge_energy_kwh REAL,
    grid_import_energy_kwh REAL,
    grid_export_energy_kwh REAL,
    avg_solar_power_w REAL,
    avg_load_power_w REAL,
    avg_battery_power_w REAL,
    avg_grid_power_w REAL,
    sample_count INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (system_id, date, hour_start),
    FOREIGN KEY (system_id) REFERENCES systems(system_id) ON DELETE CASCADE
);

-- ============= DAILY SUMMARIES =============
CREATE TABLE daily_summary (
    date TEXT NOT NULL,
    inverter_id TEXT NOT NULL,
    array_id TEXT NOT NULL,
    system_id TEXT NOT NULL,
    day_of_year INTEGER NOT NULL,
    year INTEGER NOT NULL,
    pv_energy_kwh REAL,
    pv_max_power_w REAL,
    pv_avg_power_w REAL,
    pv_peak_hour INTEGER,
    load_energy_kwh REAL,
    load_max_power_w REAL,
    load_avg_power_w REAL,
    load_peak_hour INTEGER,
    battery_min_soc_pct REAL,
    battery_max_soc_pct REAL,
    battery_avg_soc_pct REAL,
    battery_cycles REAL,
    grid_energy_imported_kwh REAL,
    grid_energy_exported_kwh REAL,
    grid_max_import_w REAL,
    grid_max_export_w REAL,
    weather_factor REAL,
    sample_count INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (date, inverter_id),
    FOREIGN KEY (inverter_id) REFERENCES inverters(inverter_id) ON DELETE CASCADE,
    FOREIGN KEY (array_id) REFERENCES arrays(array_id) ON DELETE CASCADE,
    FOREIGN KEY (system_id) REFERENCES systems(system_id) ON DELETE CASCADE
);

-- ============= ARRAY DAILY SUMMARIES =============
CREATE TABLE array_daily_summary (
    date TEXT NOT NULL,
    array_id TEXT NOT NULL,
    system_id TEXT NOT NULL,
    day_of_year INTEGER NOT NULL,
    year INTEGER NOT NULL,
    pv_energy_kwh REAL,
    pv_max_power_w REAL,
    pv_avg_power_w REAL,
    pv_peak_hour INTEGER,
    load_energy_kwh REAL,
    load_max_power_w REAL,
    load_avg_power_w REAL,
    load_peak_hour INTEGER,
    battery_min_soc_pct REAL,
    battery_max_soc_pct REAL,
    battery_avg_soc_pct REAL,
    battery_cycles REAL,
    grid_energy_imported_kwh REAL,
    grid_energy_exported_kwh REAL,
    grid_max_import_w REAL,
    grid_max_export_w REAL,
    weather_factor REAL,
    sample_count INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (date, array_id),
    FOREIGN KEY (array_id) REFERENCES arrays(array_id) ON DELETE CASCADE,
    FOREIGN KEY (system_id) REFERENCES systems(system_id) ON DELETE CASCADE
);

-- ============= SYSTEM DAILY SUMMARIES =============
CREATE TABLE system_daily_summary (
    date TEXT NOT NULL,
    system_id TEXT NOT NULL,
    day_of_year INTEGER NOT NULL,
    year INTEGER NOT NULL,
    pv_energy_kwh REAL,
    pv_max_power_w REAL,
    pv_avg_power_w REAL,
    pv_peak_hour INTEGER,
    load_energy_kwh REAL,
    load_max_power_w REAL,
    load_avg_power_w REAL,
    load_peak_hour INTEGER,
    battery_min_soc_pct REAL,
    battery_max_soc_pct REAL,
    battery_avg_soc_pct REAL,
    battery_cycles REAL,
    grid_energy_imported_kwh REAL,
    grid_energy_exported_kwh REAL,
    grid_max_import_w REAL,
    grid_max_export_w REAL,
    weather_factor REAL,
    sample_count INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (date, system_id),
    FOREIGN KEY (system_id) REFERENCES systems(system_id) ON DELETE CASCADE
);

-- ============= METER HOURLY ENERGY =============
CREATE TABLE meter_hourly_energy (
    meter_id TEXT NOT NULL,
    system_id TEXT NOT NULL,
    array_id TEXT,  -- NULL for system-level meters
    date TEXT NOT NULL,
    hour_start INTEGER NOT NULL,
    import_energy_kwh REAL DEFAULT 0.0,
    export_energy_kwh REAL DEFAULT 0.0,
    avg_power_w REAL,
    sample_count INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (meter_id, date, hour_start),
    FOREIGN KEY (meter_id) REFERENCES meters(meter_id) ON DELETE CASCADE,
    FOREIGN KEY (system_id) REFERENCES systems(system_id) ON DELETE CASCADE,
    FOREIGN KEY (array_id) REFERENCES arrays(array_id) ON DELETE SET NULL
);

-- ============= METER DAILY SUMMARIES =============
CREATE TABLE meter_daily (
    day TEXT NOT NULL,
    meter_id TEXT NOT NULL,
    system_id TEXT NOT NULL,
    array_id TEXT,  -- NULL for system-level meters
    import_energy_kwh REAL NOT NULL DEFAULT 0,
    export_energy_kwh REAL NOT NULL DEFAULT 0,
    net_energy_kwh REAL NOT NULL DEFAULT 0,
    max_import_power_w INTEGER,
    max_export_power_w INTEGER,
    avg_voltage_v REAL,
    avg_current_a REAL,
    avg_frequency_hz REAL,
    sample_count INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(day, meter_id),
    FOREIGN KEY (meter_id) REFERENCES meters(meter_id) ON DELETE CASCADE,
    FOREIGN KEY (system_id) REFERENCES systems(system_id) ON DELETE CASCADE,
    FOREIGN KEY (array_id) REFERENCES arrays(array_id) ON DELETE SET NULL
);

-- ============= BATTERY BANK HOURLY ENERGY =============
CREATE TABLE battery_bank_hourly (
    pack_id TEXT NOT NULL,
    battery_array_id TEXT NOT NULL,
    system_id TEXT NOT NULL,
    date TEXT NOT NULL,
    hour_start INTEGER NOT NULL,
    charge_energy_kwh REAL DEFAULT 0.0,
    discharge_energy_kwh REAL DEFAULT 0.0,
    net_energy_kwh REAL DEFAULT 0.0,
    avg_power_w REAL,
    avg_soc_pct REAL,
    min_soc_pct REAL,
    max_soc_pct REAL,
    avg_voltage_v REAL,
    avg_current_a REAL,
    avg_temperature_c REAL,
    sample_count INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (pack_id, date, hour_start),
    FOREIGN KEY (pack_id) REFERENCES battery_packs(pack_id) ON DELETE CASCADE,
    FOREIGN KEY (battery_array_id) REFERENCES battery_arrays(battery_array_id) ON DELETE CASCADE,
    FOREIGN KEY (system_id) REFERENCES systems(system_id) ON DELETE CASCADE
);

-- ============= BATTERY BANK DAILY SUMMARIES =============
CREATE TABLE battery_bank_daily (
    date TEXT NOT NULL,
    pack_id TEXT NOT NULL,
    battery_array_id TEXT NOT NULL,
    system_id TEXT NOT NULL,
    day_of_year INTEGER NOT NULL,
    year INTEGER NOT NULL,
    charge_energy_kwh REAL DEFAULT 0.0,
    discharge_energy_kwh REAL DEFAULT 0.0,
    net_energy_kwh REAL DEFAULT 0.0,
    min_soc_pct REAL,
    max_soc_pct REAL,
    avg_soc_pct REAL,
    min_voltage_v REAL,
    max_voltage_v REAL,
    avg_voltage_v REAL,
    min_temperature_c REAL,
    max_temperature_c REAL,
    avg_temperature_c REAL,
    min_current_a REAL,
    max_current_a REAL,
    avg_current_a REAL,
    cycles REAL,
    sample_count INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (date, pack_id),
    FOREIGN KEY (pack_id) REFERENCES battery_packs(pack_id) ON DELETE CASCADE,
    FOREIGN KEY (battery_array_id) REFERENCES battery_arrays(battery_array_id) ON DELETE CASCADE,
    FOREIGN KEY (system_id) REFERENCES systems(system_id) ON DELETE CASCADE
);
```

### 4.4 Indexes

```sql
-- System indexes
CREATE INDEX idx_arrays_system_id ON arrays(system_id);
CREATE INDEX idx_inverters_system_id ON inverters(system_id);
CREATE INDEX idx_inverters_array_id ON inverters(array_id);
CREATE INDEX idx_battery_arrays_system_id ON battery_arrays(system_id);
CREATE INDEX idx_battery_packs_system_id ON battery_packs(system_id);
CREATE INDEX idx_battery_packs_battery_array_id ON battery_packs(battery_array_id);
CREATE INDEX idx_batteries_system_id ON batteries(system_id);
CREATE INDEX idx_batteries_pack_id ON batteries(pack_id);
CREATE INDEX idx_battery_cells_system_id ON battery_cells(system_id);
CREATE INDEX idx_battery_cells_battery_id ON battery_cells(battery_id);
CREATE INDEX idx_meters_system_id ON meters(system_id);
CREATE INDEX idx_meters_array_id ON meters(array_id);
CREATE INDEX idx_meters_adapter_id ON meters(adapter_id);
CREATE INDEX idx_inverters_adapter_id ON inverters(adapter_id);
CREATE INDEX idx_adapters_adapter_type ON adapters(adapter_type);
CREATE INDEX idx_adapters_device_id ON adapters(device_id, device_type);
CREATE INDEX idx_adapters_device_category ON adapters(device_category);
CREATE INDEX idx_battery_pack_adapters_pack_id ON battery_pack_adapters(pack_id);
CREATE INDEX idx_battery_pack_adapters_adapter_id ON battery_pack_adapters(adapter_id);

-- Sample table indexes
CREATE INDEX idx_energy_samples_system_id ON energy_samples(system_id);
CREATE INDEX idx_energy_samples_array_id ON energy_samples(array_id);
CREATE INDEX idx_energy_samples_ts ON energy_samples(ts DESC);
CREATE INDEX idx_array_samples_system_id ON array_samples(system_id);
CREATE INDEX idx_array_samples_ts ON array_samples(ts DESC);
CREATE INDEX idx_battery_bank_samples_system_id ON battery_bank_samples(system_id);
CREATE INDEX idx_battery_bank_samples_ts ON battery_bank_samples(ts DESC);
CREATE INDEX idx_battery_unit_samples_system_id ON battery_unit_samples(system_id);
CREATE INDEX idx_battery_unit_samples_ts ON battery_unit_samples(ts DESC);
CREATE INDEX idx_battery_cell_samples_system_id ON battery_cell_samples(system_id);
CREATE INDEX idx_battery_cell_samples_ts ON battery_cell_samples(ts DESC);
CREATE INDEX idx_meter_samples_system_id ON meter_samples(system_id);
CREATE INDEX idx_meter_samples_ts ON meter_samples(ts DESC);

-- Summary table indexes
CREATE INDEX idx_hourly_energy_system_id ON hourly_energy(system_id);
CREATE INDEX idx_hourly_energy_array_id ON hourly_energy(array_id);
CREATE INDEX idx_hourly_energy_date ON hourly_energy(date DESC);
CREATE INDEX idx_array_hourly_energy_system_id ON array_hourly_energy(system_id);
CREATE INDEX idx_array_hourly_energy_date ON array_hourly_energy(date DESC);
CREATE INDEX idx_system_hourly_energy_date ON system_hourly_energy(date DESC);
CREATE INDEX idx_daily_summary_system_id ON daily_summary(system_id);
CREATE INDEX idx_daily_summary_array_id ON daily_summary(array_id);
CREATE INDEX idx_daily_summary_date ON daily_summary(date DESC);
CREATE INDEX idx_array_daily_summary_system_id ON array_daily_summary(system_id);
CREATE INDEX idx_array_daily_summary_date ON array_daily_summary(date DESC);
CREATE INDEX idx_system_daily_summary_date ON system_daily_summary(date DESC);
CREATE INDEX idx_battery_bank_hourly_pack_id ON battery_bank_hourly(pack_id);
CREATE INDEX idx_battery_bank_hourly_system_id ON battery_bank_hourly(system_id);
CREATE INDEX idx_battery_bank_hourly_date ON battery_bank_hourly(date DESC);
CREATE INDEX idx_battery_bank_daily_pack_id ON battery_bank_daily(pack_id);
CREATE INDEX idx_battery_bank_daily_system_id ON battery_bank_daily(system_id);
CREATE INDEX idx_battery_bank_daily_date ON battery_bank_daily(date DESC);

---

## 5. ADAPTER ARCHITECTURE

### 5.1 Adapter Base vs Adapter Instances

**Adapter Base (`adapter_base` table)**:
- Defines all **supported** adapter types in the system
- Stores the **schema** and **default configuration** for each adapter type
- Examples: `powdrive`, `senergy`, `pytes`, `jkbms_tcpip`, `jkbms_ble`, `iammeter`
- Populated on system initialization (from code/definitions)
- Acts as a catalog/template

**Adapter Instances (`adapters` table)**:
- Stores **actual** adapter configurations for each device
- Each adapter instance references an `adapter_type` from `adapter_base`
- Contains device-specific configuration (serial port, IP address, etc.)
- Extracted from `config.yaml` during configuration load

### 5.2 Adapter Relationships

1. **Inverters**: One adapter per inverter (via `inverters.adapter_id` foreign key)
2. **Battery Packs**: Multiple adapters per pack (via `battery_pack_adapters` junction table) for failover support
3. **Meters**: One adapter per meter (via `meters.adapter_id` foreign key)

### 5.3 Example Adapter Base Entries

```sql
-- Inverter Adapters
INSERT INTO adapter_base (adapter_type, device_category, name, description, config_schema, supported_transports) VALUES
('powdrive', 'inverter', 'Powdrive Inverter Adapter', 'Adapter for Powdrive inverters', '{"type": "object", "properties": {"type": {"type": "string"}, "transport": {"type": "string", "enum": ["rtu", "tcp"]}, "serial_port": {"type": "string"}, "baudrate": {"type": "integer"}, ...}}', '["rtu", "tcp"]'),
('senergy', 'inverter', 'Senergy Inverter Adapter', 'Adapter for Senergy inverters', '{"type": "object", "properties": {"type": {"type": "string"}, "transport": {"type": "string", "enum": ["rtu", "tcp"]}, ...}}', '["rtu", "tcp"]');

-- Battery Adapters
INSERT INTO adapter_base (adapter_type, device_category, name, description, config_schema, supported_transports) VALUES
('pytes', 'battery', 'Pytes Battery Adapter', 'Adapter for Pytes/Pylontech batteries', '{"type": "object", "properties": {"type": {"type": "string"}, "serial_port": {"type": "string"}, "baudrate": {"type": "integer"}, ...}}', '["serial"]'),
('jkbms_tcpip', 'battery', 'JK BMS TCP/IP Adapter', 'JK BMS via TCP/IP gateway', '{"type": "object", "properties": {"type": {"type": "string"}, "host": {"type": "string"}, "port": {"type": "integer"}, ...}}', '["tcpip"]'),
('jkbms_ble', 'battery', 'JK BMS Bluetooth Adapter', 'JK BMS via Bluetooth Low Energy', '{"type": "object", "properties": {"type": {"type": "string"}, "bt_addresses": {"type": "array"}, ...}}', '["ble"]');

-- Meter Adapters
INSERT INTO adapter_base (adapter_type, device_category, name, description, config_schema, supported_transports) VALUES
('iammeter', 'meter', 'IAMMeter Adapter', 'Adapter for IAMMeter energy meters', '{"type": "object", "properties": {"type": {"type": "string"}, "transport": {"type": "string", "enum": ["rtu", "tcp"]}, ...}}', '["rtu", "tcp"]');
```

### 5.4 Example Adapter Instance Entries

```sql
-- Inverter Adapter Instance
INSERT INTO adapters (adapter_id, adapter_type, device_category, device_id, device_type, config_json) VALUES
('powdrive1_adapter', 'powdrive', 'inverter', 'powdrive1', 'inverter', '{"type": "powdrive", "transport": "rtu", "serial_port": "/dev/serial/by-id/...", "baudrate": 9600, "unit_id": 1, ...}');

-- Battery Adapter Instance (Primary)
INSERT INTO adapters (adapter_id, adapter_type, device_category, device_id, device_type, priority, config_json) VALUES
('battery1_adapter_primary', 'pytes', 'battery', 'battery1', 'battery_pack', 1, '{"type": "pytes", "serial_port": "/dev/serial/by-id/...", "baudrate": 115200, "batteries": 4, "cells_per_battery": 15, ...}');

-- Battery Adapter Instance (Failover)
INSERT INTO adapters (adapter_id, adapter_type, device_category, device_id, device_type, priority, config_json) VALUES
('jkbms_bank_ble_adapter_primary', 'jkbms_tcpip', 'battery', 'jkbms_bank_ble', 'battery_pack', 1, '{"type": "jkbms_tcpip", "host": "192.168.88.48", "port": 5022, ...}'),
('jkbms_bank_ble_adapter_failover', 'jkbms_ble', 'battery', 'jkbms_bank_ble', 'battery_pack', 2, '{"type": "jkbms_ble", "bt_addresses": ["C8:47:80:1A:1F:04", ...], ...}');

-- Meter Adapter Instance
INSERT INTO adapters (adapter_id, adapter_type, device_category, device_id, device_type, config_json) VALUES
('grid_meter_1_adapter', 'iammeter', 'meter', 'grid_meter_1', 'meter', '{"type": "iammeter", "transport": "tcp", "host": "192.168.88.23", "port": 502, "unit_id": 1, ...}');
```

### 5.5 Battery Pack Adapter Associations

```sql
-- Link battery pack to multiple adapters (failover)
INSERT INTO battery_pack_adapters (pack_id, adapter_id, priority, enabled) VALUES
('jkbms_bank_ble', 'jkbms_bank_ble_adapter_primary', 1, 1),  -- Primary adapter
('jkbms_bank_ble', 'jkbms_bank_ble_adapter_failover', 2, 1);  -- Failover adapter
```

---

## 6. CONFIGURATION ARCHITECTURE

### 6.1 Primary Configuration Source: Database

**Database is the primary source of truth** for all system configuration:
- Systems, arrays, devices, and adapters are stored in database tables
- Configuration can be managed via:
  - **Frontend UI**: Users can create/edit systems, arrays, and devices through web interface
  - **Auto-Discovery**: System automatically discovers and configures devices
  - **API**: REST API endpoints for programmatic configuration management

### 6.2 config.yaml as Fallback/Initial Seed

**`config.yaml` is now redundant and serves as a failover mechanism**:
- **Primary Use Case**: Initial system setup or database recovery
- **Fallback Use Case**: If database is empty or corrupted, system can load from `config.yaml`
- **Migration Path**: On first startup, if `config.yaml` exists, it's loaded into the database, then the database becomes the source of truth
- **Optional**: System can operate entirely without `config.yaml` if devices are auto-discovered or configured via UI/API

### 6.3 Auto-Discovery and Auto-Configuration

**System automatically discovers and configures devices**:

1. **Device Discovery**:
   - Scans USB serial ports (`/dev/ttyUSB*`, `COM*`) for connected devices
   - Attempts to identify device type (inverter, battery, meter) by trying different adapters
   - Reads device serial numbers to uniquely identify devices
   - Stores discovered devices in `device_discovery` table

2. **Auto-Creation of Basic System**:
   - If no system exists in database, creates a default system (id: "system")
   - If no inverter array exists, creates a default inverter array (id: "array1")
   - If no battery array exists, creates a default battery array (id: "battery_array1")
   - Auto-attaches battery array to inverter array

3. **Auto-Configuration of Devices**:
   - **Inverters**: Auto-discovered inverters are assigned to the default inverter array
   - **Battery Packs**: Auto-discovered battery packs are assigned to the default battery array
   - **Meters**: Auto-discovered meters are attached to the system level
   - Adapter configurations are automatically created based on discovered device types and ports

4. **Configuration Priority**:
   - **Priority 1**: Database configuration (user-defined via UI/API)
   - **Priority 2**: Auto-discovered configuration (from device discovery)
   - **Priority 3**: `config.yaml` fallback (if database is empty)

### 6.4 Device Discovery Process

The system uses a 4-phase discovery process:

1. **Phase 1: Check Known Devices from Database**
   - Load all known devices from `device_discovery` table
   - Try to connect to saved ports
   - Verify serial numbers match

2. **Phase 2: Search for Missing Known Devices**
   - For devices not found on saved ports, scan all available ports
   - Update port assignments if device is found on a different port

3. **Phase 3: Discover New Devices**
   - Scan unused ports for new devices
   - Identify device type and serial number
   - Create new entries in `device_discovery` table
   - Auto-create device entries in `inverters`, `battery_packs`, or `meters` tables

4. **Phase 4: Finalize and Cleanup**
   - Mark devices as active/inactive based on discovery results
   - Set retry timers for temporarily missing devices
   - Permanently disable devices after max failures

### 6.5 Auto-Created Basic System Structure

When no configuration exists, the system automatically creates:

```sql
-- Default System
INSERT INTO systems (system_id, name, description, timezone) VALUES
('system', 'My Solar System', 'Auto-created default system', 'Asia/Karachi');

-- Default Inverter Array
INSERT INTO arrays (array_id, system_id, name) VALUES
('array1', 'system', 'Default Inverter Array');

-- Default Battery Array
INSERT INTO battery_arrays (battery_array_id, system_id, name) VALUES
('battery_array1', 'system', 'Default Battery Array');

-- Auto-attach battery array to inverter array
INSERT INTO battery_array_attachments (battery_array_id, inverter_array_id, attached_since) VALUES
('battery_array1', 'array1', CURRENT_TIMESTAMP);
```

### 6.6 Frontend Configuration Management

**Users can manage configuration via web UI**:
- Create/edit/delete systems
- Create/edit/delete arrays
- Add/remove devices to/from arrays
- Configure device adapters
- View auto-discovered devices
- Approve/reject auto-discovered devices

---

## 7. CONFIGURATION FILE STRUCTURE (Fallback)

### 7.1 config.yaml as Fallback/Initial Seed

**Note**: `config.yaml` is now **optional** and serves as a fallback mechanism. The database is the primary source of truth.

The following structure is used only when:
- Initial system setup (first-time installation)
- Database recovery (if database is corrupted or empty)
- Manual configuration import

```yaml
# ============= SYSTEM CONFIGURATION =============
# Note: config.yaml uses "home" but database uses "system"
home:
  id: system  # Maps to system_id in database
  name: "My Solar System"
  description: "Main residential solar system"
  timezone: "Asia/Karachi"

# ============= INVERTER ARRAYS =============
arrays:
  - id: array1
    name: "Ground Floor"
    system_id: system  # Explicit system reference (config may use home_id, maps to system_id)
    inverter_ids:
      - powdrive2
      - senergy1
  
  - id: array2
    name: "First Floor"
    system_id: system  # Explicit system reference (config may use home_id, maps to system_id)
    inverter_ids:
      - powdrive1

# ============= INDIVIDUAL INVERTERS =============
inverters:
  - id: powdrive1
    name: Powdrive
    system_id: system  # Explicit system reference
    array_id: array2
    model: "Powdrive 12k"
    serial_number: "PD-001"
    vendor: powdrive
    phase_type: three
    adapter:
      type: powdrive
      # ... adapter config ...

# ============= BATTERY ARRAYS =============
battery_bank_arrays:
  - id: battery_array1
    name: "Ground Floor Battery Array"
    system_id: system  # Explicit system reference
    battery_bank_ids: 
      - jkbms_bank_ble
  
  - id: battery_array2
    name: "First Floor Battery Array"
    system_id: system  # Explicit system reference (config may use home_id, maps to system_id)
    battery_bank_ids:
      - battery1

# ============= BATTERY PACKS (Banks) =============
battery_banks:
  - id: battery1
    name: Pylontech Battery Bank
    system_id: system  # Explicit system reference
    battery_array_id: battery_array2  # Explicit array reference
    batteries: 4  # Number of battery units in pack
    cells_per_battery: 15  # Cells per battery unit
    # Note: adapter config moved to adapters table
    # Multiple adapters can be linked via battery_pack_adapters table

# ============= BATTERY ARRAY ATTACHMENTS =============
battery_bank_array_attachments:
  - battery_bank_array_id: battery_array1
    inverter_array_id: array1
    attached_since: "2025-01-01T00:00:00+05:00"
    detached_at: null

# ============= ENERGY METERS =============
meters:
  - id: grid_meter_1
    name: IAMMeter
    system_id: system  # Explicit system reference
    array_id: null  # null = system-level meter
    adapter_id: grid_meter_1_adapter  # References adapters table
    attachment_target: system  # Explicit attachment target (config may use "home", maps to "system")
    type: grid
    # Note: adapter config moved to adapters table

# ============= ADAPTER BASE DEFINITIONS =============
# These are stored in adapter_base table (populated on system initialization)
# Example entries:
# - adapter_type: 'powdrive', device_category: 'inverter', name: 'Powdrive Inverter Adapter'
# - adapter_type: 'senergy', device_category: 'inverter', name: 'Senergy Inverter Adapter'
# - adapter_type: 'pytes', device_category: 'battery', name: 'Pytes Battery Adapter'
# - adapter_type: 'jkbms_tcpip', device_category: 'battery', name: 'JK BMS TCP/IP Adapter'
# - adapter_type: 'jkbms_ble', device_category: 'battery', name: 'JK BMS Bluetooth Adapter'
# - adapter_type: 'iammeter', device_category: 'meter', name: 'IAMMeter Adapter'

# ============= ADAPTER INSTANCES =============
# These are stored in adapters table (extracted from device configs)
# Example entries:
# - adapter_id: 'powdrive1_adapter', adapter_type: 'powdrive', device_id: 'powdrive1', device_type: 'inverter'
# - adapter_id: 'battery1_adapter_primary', adapter_type: 'pytes', device_id: 'battery1', device_type: 'battery_pack', priority: 1
# - adapter_id: 'grid_meter_1_adapter', adapter_type: 'iammeter', device_id: 'grid_meter_1', device_type: 'meter'
```

```

---

## 8. GAP ANALYSIS

### 8.1 Missing Database Tables

| Table | Priority | Impact |
|-------|----------|--------|
| `systems` | **CRITICAL** | Cannot support multiple systems |
| `inverters` | **HIGH** | Cannot track individual inverter metadata |
| `battery_arrays` | **HIGH** | Cannot track battery array catalog |
| `battery_array_attachments` | **HIGH** | Cannot track attachments properly |
| `batteries` | **MEDIUM** | Cannot track individual battery units |
| `battery_cells` | **LOW** | Cannot track individual cells (optional) |
| `meters` | **HIGH** | Cannot track meter catalog |
| `adapter_base` | **HIGH** | Cannot define supported adapter types and their schemas |
| `adapters` | **HIGH** | Cannot track adapter instances and configurations |
| `battery_pack_adapters` | **MEDIUM** | Cannot support multiple adapters per battery pack (failover) |
| `device_discovery` | ✅ Exists | Used for auto-discovery, needs integration with catalog tables |

### 8.2 Missing Foreign Keys

| Table | Missing FK | Impact |
|-------|-----------|--------|
| `arrays` | `system_id` | Cannot support multiple systems |
| `battery_packs` | `battery_array_id`, `system_id` | Cannot link packs to arrays/systems |
| `inverters` | `adapter_id` | Cannot link inverters to adapter instances |
| `meters` | `adapter_id` | Cannot link meters to adapter instances |
| `energy_samples` | `system_id` | Cannot filter by system |
| `array_samples` | `system_id` | Cannot filter by system |
| `battery_bank_samples` | `system_id` | Cannot filter by system |
| `battery_unit_samples` | `pack_id`, `battery_id`, `system_id` | Cannot link to pack/battery/system |
| `battery_cell_samples` | `battery_id`, `pack_id`, `system_id` | Cannot link to battery/pack/system |
| `meter_samples` | `system_id` | Cannot filter by system |
| `hourly_energy` | `array_id`, `system_id` | Cannot aggregate by array/system |
| `daily_summary` | `array_id`, `system_id` | Cannot aggregate by array/system |

### 8.3 Missing Aggregated Tables

| Table | Purpose | Priority |
|-------|---------|----------|
| `array_hourly_energy` | Hourly energy per array | **HIGH** |
| `system_hourly_energy` | Hourly energy per system | **HIGH** |
| `battery_bank_hourly` | Hourly energy per battery pack | **HIGH** |
| `array_daily_summary` | Daily summary per array | **HIGH** |
| `system_daily_summary` | Daily summary per system | **HIGH** |
| `battery_bank_daily` | Daily summary per battery pack | **HIGH** |

### 8.4 Auto-Discovery and Auto-Configuration Gaps

1. **Auto-System Creation**: System should automatically create a default system if none exists
2. **Auto-Array Creation**: System should automatically create default inverter and battery arrays if none exist
3. **Auto-Device Assignment**: Auto-discovered devices should be automatically assigned to default arrays
4. **Frontend Configuration UI**: Need UI for users to manage systems, arrays, and devices
5. **Device Discovery Integration**: Need to integrate device discovery with database catalog tables
6. **Configuration Migration**: Need logic to migrate from `config.yaml` to database on first startup

---

## 9. MIGRATION STRATEGY

### 9.1 Phase 1: Add System Support (Critical)

1. Create `systems` table
2. **Auto-create default system** if none exists (id: "system", name: "My Solar System")
3. **Fallback**: If `config.yaml` exists and database is empty, load system from `config.yaml` `home` section
4. Add `system_id` column to all existing tables
5. Backfill `system_id` with default system ID
6. Add foreign key constraints

### 9.2 Phase 2: Add Adapter Tables (High Priority)

1. Create `adapter_base` table
2. Populate with all supported adapter types from code definitions
3. Create `adapters` table
4. Create `battery_pack_adapters` table

### 9.3 Phase 3: Extract and Link Adapters (High Priority)

1. **Primary**: Extract adapter configurations from auto-discovered devices (`device_discovery` table)
2. **Fallback**: Extract adapter configurations from `config.yaml` if database is empty
3. Populate `adapters` table with adapter instances
4. Link inverters to their adapters (update `inverters.adapter_id`)
5. Link meters to their adapters (update `meters.adapter_id`)
6. Link battery packs to their adapters via `battery_pack_adapters` table (including failover adapters)

### 9.4 Phase 4: Add Missing Catalog Tables (High Priority)

1. Create `inverters` table
2. **Primary**: Populate from auto-discovered devices (`device_discovery` table), assign to default array
3. **Fallback**: Populate from `config.yaml` if database is empty
4. Link to `adapters` table
5. Create `battery_arrays` table
6. **Auto-create default battery array** if none exists (id: "battery_array1")
7. **Primary**: Populate from auto-discovered battery devices
8. **Fallback**: Populate from `config.yaml` if database is empty
9. Create `battery_array_attachments` table
10. **Auto-attach default battery array to default inverter array** if no attachment exists
11. **Fallback**: Populate from `config.yaml` if database is empty
12. Create `meters` table
13. **Primary**: Populate from auto-discovered meter devices
14. **Fallback**: Populate from `config.yaml` if database is empty
15. Link to `adapters` table

### 9.5 Phase 5: Add Battery Unit & Cell Support (Medium Priority)

1. Create `batteries` table
2. Populate from `battery_banks` config (infer from `batteries` count)
3. Create `battery_cells` table
4. Populate from `battery_banks` config (infer from `cells_per_battery`)
5. Update `battery_unit_samples` and `battery_cell_samples` with foreign keys

### 9.6 Phase 6: Add Aggregated Tables (High Priority)

1. Create `array_hourly_energy` table
2. Create `system_hourly_energy` table
3. Create `battery_bank_hourly` table
4. Create `array_daily_summary` table
5. Create `system_daily_summary` table
6. Create `battery_bank_daily` table
7. Backfill from existing `hourly_energy` and `daily_summary` tables
8. Backfill battery bank aggregated tables from `battery_bank_samples`

---

### 9.7 Phase 7: Auto-Discovery and Auto-Configuration (High Priority)

1. Integrate device discovery with database catalog tables
2. Implement auto-creation of default system if none exists
3. Implement auto-creation of default arrays (inverter and battery) if none exist
4. Implement auto-assignment of discovered devices to default arrays
5. Implement auto-attachment of default battery array to default inverter array
6. Create frontend UI for system/array/device configuration
7. Implement configuration migration from `config.yaml` to database on first startup
8. Update device discovery to populate `inverters`, `battery_packs`, and `meters` tables
9. Update device discovery to create adapter instances in `adapters` table

---

## 10. IMPLEMENTATION CHECKLIST

### Database Schema
- [ ] Create `systems` table
- [ ] Create `adapter_base` table
- [ ] Populate `adapter_base` with supported adapter types
- [ ] Create `adapters` table
- [ ] Create `inverters` table
- [ ] Create `battery_arrays` table
- [ ] Create `battery_array_attachments` table
- [ ] Create `batteries` table
- [ ] Create `battery_cells` table
- [ ] Create `battery_pack_adapters` table
- [ ] Create `meters` table
- [ ] Add `system_id` to all existing tables
- [ ] Add `battery_array_id` to `battery_packs` table
- [ ] Add `adapter_id` to `inverters` and `meters` tables
- [ ] Add foreign key constraints
- [ ] Create aggregated summary tables (array_hourly_energy, system_hourly_energy, battery_bank_hourly, array_daily_summary, system_daily_summary, battery_bank_daily)
- [ ] Create indexes

### Auto-Discovery and Auto-Configuration
- [ ] Integrate device discovery with database catalog tables
- [ ] Implement auto-creation of default system if none exists
- [ ] Implement auto-creation of default arrays (inverter and battery) if none exist
- [ ] Implement auto-assignment of discovered devices to default arrays
- [ ] Implement auto-attachment of default battery array to default inverter array
- [ ] Update device discovery to populate `inverters`, `battery_packs`, and `meters` tables
- [ ] Update device discovery to create adapter instances in `adapters` table

### Configuration Management
- [ ] Create frontend UI for system/array/device configuration
- [ ] Implement configuration migration from `config.yaml` to database on first startup
- [ ] Update config loader to use database as primary source, `config.yaml` as fallback
- [ ] Add API endpoints for system/array/device management

### Backend Code Updates
- [ ] Update `config.py` models to include new fields
- [ ] Update `database_migrations.py` with migration functions
- [ ] Create adapter extraction logic to populate `adapters` table from auto-discovery
- [ ] Create adapter extraction logic to populate `adapters` table from `config.yaml` (fallback)
- [ ] Update device initialization to load adapters from database (primary) or `config.yaml` (fallback)
- [ ] Update device discovery to create entries in catalog tables (`inverters`, `battery_packs`, `meters`)
- [ ] Implement auto-creation of default system and arrays on startup if none exist
- [ ] Update `logger.py` to write to new tables
- [ ] Update aggregation logic to use new tables
- [ ] Update API endpoints to return system_id and adapter information
- [ ] Create API endpoints for system/array/device management (CRUD operations)

### Frontend Updates
- [ ] Update API types to include system_id
- [ ] Update DataProvider to handle multi-system
- [ ] Create UI for system management (create/edit/delete systems)
- [ ] Create UI for array management (create/edit/delete arrays)
- [ ] Create UI for device management (add/remove devices, configure adapters)
- [ ] Create UI for viewing auto-discovered devices (approve/reject)
- [ ] Update UI to support system selection (if multi-system)

---

## 11. NOTES

1. **Backward Compatibility**: All migrations should maintain backward compatibility with existing data
2. **Default System**: System automatically creates a default system (id: "system") if none exists
3. **Default Arrays**: System automatically creates default inverter array ("array1") and battery array ("battery_array1") if none exist
4. **Auto-Attachment**: Default battery array is automatically attached to default inverter array
5. **config.yaml as Fallback**: `config.yaml` is now optional and serves as a fallback mechanism. Database is the primary source of truth.
6. **Auto-Discovery**: System automatically discovers devices via USB serial port scanning and creates device entries in database
7. **Frontend Configuration**: Users can manage all configuration via web UI (systems, arrays, devices, adapters)
8. **Cell Tracking**: Cell-level tracking is optional and can be added later if needed
9. **Multi-System Support**: The schema supports multiple systems, but initial implementation can focus on single-system with auto-creation
10. **Legacy Tables**: Keep `battery_pack_attachments` for backward compatibility, but prefer `battery_array_attachments`
11. **Device Discovery Table**: The existing `device_discovery` table is used for auto-discovery and should be integrated with catalog tables

---

## 12. EXAMPLE QUERIES

### Get all devices for a system
```sql
SELECT 
    'inverter' as type, inverter_id as id, name, array_id
FROM inverters
WHERE system_id = 'system'
UNION ALL
SELECT 
    'battery_pack' as type, pack_id as id, name, battery_array_id
FROM battery_packs
WHERE system_id = 'system'
UNION ALL
SELECT 
    'meter' as type, meter_id as id, name, array_id
FROM meters
WHERE system_id = 'system';
```

### Get system-level aggregated energy for today
```sql
SELECT 
    hour_start,
    SUM(solar_energy_kwh) as total_solar,
    SUM(load_energy_kwh) as total_load,
    SUM(battery_charge_energy_kwh) as total_battery_charge,
    SUM(battery_discharge_energy_kwh) as total_battery_discharge,
    SUM(grid_import_energy_kwh) as total_grid_import,
    SUM(grid_export_energy_kwh) as total_grid_export
FROM system_hourly_energy
WHERE system_id = 'system' AND date = DATE('now')
GROUP BY hour_start
ORDER BY hour_start;
```

### Get battery pack hierarchy for a system
```sql
SELECT 
    ba.battery_array_id,
    ba.name as array_name,
    bp.pack_id,
    bp.name as pack_name,
    b.battery_id,
    b.battery_index,
    COUNT(bc.cell_id) as cell_count
FROM battery_arrays ba
JOIN battery_packs bp ON ba.battery_array_id = bp.battery_array_id
JOIN batteries b ON bp.pack_id = b.pack_id
LEFT JOIN battery_cells bc ON b.battery_id = bc.battery_id
WHERE ba.system_id = 'system'
GROUP BY ba.battery_array_id, bp.pack_id, b.battery_id
ORDER BY ba.battery_array_id, bp.pack_id, b.battery_index;
```

### Get battery bank hourly energy for today
```sql
SELECT 
    hour_start,
    pack_id,
    charge_energy_kwh,
    discharge_energy_kwh,
    avg_power_w,
    avg_soc_pct,
    avg_voltage_v,
    avg_temperature_c
FROM battery_bank_hourly
WHERE pack_id = 'battery1' AND date = DATE('now')
ORDER BY hour_start;
```

### Get battery bank daily summary for a date range
```sql
SELECT 
    date,
    pack_id,
    charge_energy_kwh,
    discharge_energy_kwh,
    net_energy_kwh,
    min_soc_pct,
    max_soc_pct,
    avg_soc_pct,
    cycles
FROM battery_bank_daily
WHERE pack_id = 'battery1' AND date >= DATE('now', '-7 days')
ORDER BY date DESC;
```

---

### Auto-create default system and arrays (if none exist)
```sql
-- Check if system exists, if not create default
INSERT INTO systems (system_id, name, description, timezone)
SELECT 'system', 'My Solar System', 'Auto-created default system', 'Asia/Karachi'
WHERE NOT EXISTS (SELECT 1 FROM systems WHERE system_id = 'system');

-- Check if inverter array exists, if not create default
INSERT INTO arrays (array_id, system_id, name)
SELECT 'array1', 'system', 'Default Inverter Array'
WHERE NOT EXISTS (SELECT 1 FROM arrays WHERE array_id = 'array1');

-- Check if battery array exists, if not create default
INSERT INTO battery_arrays (battery_array_id, system_id, name)
SELECT 'battery_array1', 'system', 'Default Battery Array'
WHERE NOT EXISTS (SELECT 1 FROM battery_arrays WHERE battery_array_id = 'battery_array1');

-- Auto-attach battery array to inverter array (if not already attached)
INSERT INTO battery_array_attachments (battery_array_id, inverter_array_id, attached_since)
SELECT 'battery_array1', 'array1', CURRENT_TIMESTAMP
WHERE NOT EXISTS (
    SELECT 1 FROM battery_array_attachments 
    WHERE battery_array_id = 'battery_array1' AND inverter_array_id = 'array1' AND detached_at IS NULL
);
```

### Get auto-discovered devices pending approval
```sql
SELECT 
    device_id,
    device_type,
    serial_number,
    port,
    status,
    is_auto_discovered,
    discovery_timestamp
FROM device_discovery
WHERE is_auto_discovered = 1 AND status = 'active'
ORDER BY discovery_timestamp DESC;
```

---

**Document Version**: 1.1  
**Last Updated**: 2025-01-XX  
**Status**: Draft - Pending Implementation

