# Array System Implementation - Progress Summary

## Overview

This document tracks the implementation of the Array-based architecture enhancement, which introduces:
- **Arrays**: Logical groups of inverters (mixed vendors allowed)
- **Battery Packs**: Battery units with pack-level limits/capacity/SOC
- **Attachments**: Time-bounded relationships between packs and arrays

## Implementation Status

### ✅ Completed

#### 1. Configuration Schema (`solarhub/config.py`)
- ✅ Added `ArrayConfig` with per-array scheduler configuration
- ✅ Added `BatteryPackConfig` with pack specifications
- ✅ Added `BatteryPackAttachment` for time-bounded attachments
- ✅ Added `BatteryUnitConfig` for individual battery units
- ✅ Updated `InverterConfig` to require `array_id`
- ✅ Updated `HubConfig` to include `arrays`, `battery_packs`, and `attachments`

#### 2. Domain Models (`solarhub/array_models.py`)
- ✅ Created `Array`, `BatteryPack`, `BatteryPackAttachment` runtime models
- ✅ Created `ArrayTelemetry` for aggregated array data
- ✅ Created `BatteryPackTelemetry` for pack-level data
- ✅ Updated `Telemetry` model to include `array_id`

#### 3. Database Schema (`solarhub/database_migrations.py`)
- ✅ Created `migrate_to_arrays()` function
- ✅ New tables: `arrays`, `battery_packs`, `battery_pack_attachments`, `array_samples`
- ✅ Updated `energy_samples` table with `array_id` column
- ✅ Updated `battery_bank_samples` with `pack_id` and `array_id` columns
- ✅ Created indexes for performance
- ✅ Added `backfill_array_ids()` function for data migration

#### 4. Array Aggregator (`solarhub/array_aggregator.py`)
- ✅ Created `ArrayAggregator` class
- ✅ Implements `aggregate_array_telemetry()` method
- ✅ Sums powers/energies across inverters
- ✅ Calculates energy-weighted SOC across packs
- ✅ Provides per-inverter and per-pack breakdowns
- ✅ Handles metadata (phase mix, vendor mix, inverter count)

#### 5. Logger Updates (`solarhub/logging/logger.py`)
- ✅ Updated `insert_sample()` to include `array_id`
- ✅ Added `insert_array_sample()` method
- ✅ Integrated database migration on initialization
- ✅ Automatic schema migration on startup

### 🚧 In Progress / Pending

#### 6. Adapter Updates
- ⏳ Update all adapters to include `array_id` in telemetry emissions
- ⏳ Ensure `TelemetryMapper` preserves `array_id`
- ⏳ Update `PowdriveAdapter` and `SenergyAdapter`

#### 7. API Server (`solarhub/api_server.py`)
- ✅ Add `/api/arrays` endpoint (list arrays)
- ✅ Add `/api/arrays/{array_id}/now` endpoint
- ✅ Update `/api/now` to support `array_id` filter parameter
- ⏳ Add `/api/arrays/{array_id}/forecast` endpoint
- ⏳ Add `/api/arrays/{array_id}/scheduler` endpoint
- ⏳ Add `POST /api/arrays/{array_id}/attach_pack` endpoint
- ⏳ Add `POST /api/arrays/{array_id}/scheduler/override` endpoint
- ⏳ Update other endpoints with `array_id` filters (e.g., `/api/devices`)

#### 8. Smart Scheduler (`solarhub/schedulers/smart.py`)
- ⏳ Instantiate one scheduler per active array
- ⏳ Handle multi-pack allocation
- ⏳ Respect per-pack limits (max_charge_kw, max_discharge_kw)
- ⏳ Distribute power across packs (headroom, health, cycle aging)
- ⏳ Support per-array TOU windows and policies
- ⏳ Fan out commands to inverters and packs

#### 9. MQTT/Home Assistant (`solarhub/mqtt.py`, `solarhub/ha/discovery.py`)
- ⏳ Publish array-level topics: `<base>/arrays/<array_id>/state`
- ⏳ Publish pack-level topics: `<base>/packs/<pack_id>/state`
- ⏳ Update HA discovery for arrays and packs
- ⏳ Add device relationships (array as parent, inverters/packs as children)
- ⏳ Maintain backward compatibility with existing topics

#### 10. Backward Compatibility & Migration
- ⏳ Create default array for legacy configs
- ⏳ Map existing inverters to default array
- ⏳ Migrate existing battery_bank to battery_packs
- ⏳ Backfill `array_id` in existing `energy_samples` data
- ⏳ Update `config_manager.py` to handle migration

#### 11. App Integration (`solarhub/app.py`)
- ⏳ Initialize arrays from config
- ⏳ Track array-to-inverter mappings
- ⏳ Track pack-to-array attachments
- ⏳ Aggregate telemetry per array
- ⏳ Publish array telemetry to MQTT
- ⏳ Write array samples to database

## Configuration Example

```yaml
arrays:
  - id: array_north
    name: "North Roof"
    inverter_ids: [senergy_1, powdrive_1]
    scheduler:
      enabled: true
      policy:
        target_soc_before_sunset_pct: 80
        emergency_reserve_hours: 2
      tou_windows:
        - { start: "00:00", end: "06:00", tariff: cheap, grid_charge_to_soc_pct: 80 }
        - { start: "06:00", end: "18:00", tariff: normal }
        - { start: "18:00", end: "22:00", tariff: peak, discharge_to_soc_pct: 20 }

inverters:
  - id: senergy_1
    name: "Senergy 12k #1"
    array_id: array_north  # Required
    phase_type: auto
    adapter:
      type: senergy
      transport: rtu
      serial_port: /dev/ttyUSB0
      baudrate: 9600

  - id: powdrive_1
    name: "Powdrive 12k #1"
    array_id: array_north
    adapter:
      type: powdrive
      transport: tcp
      host: 192.168.1.52
      port: 502

battery_packs:
  - id: pytes_pack_A
    name: "Pytes 10kWh Pack A"
    chemistry: LFP
    nominal_kwh: 10.24
    max_charge_kw: 5
    max_discharge_kw: 5
    units:
      - { id: A_u1, serial: "..." }
      - { id: A_u2, serial: "..." }

attachments:
  - pack_id: pytes_pack_A
    array_id: array_north
    attached_since: "2025-10-01T00:00:00+05:00"
```

## Database Schema

### New Tables

```sql
-- Arrays catalog
CREATE TABLE arrays (
    array_id TEXT PRIMARY KEY,
    name TEXT
);

-- Battery packs catalog
CREATE TABLE battery_packs (
    pack_id TEXT PRIMARY KEY,
    name TEXT,
    chemistry TEXT,
    nominal_kwh REAL,
    max_charge_kw REAL,
    max_discharge_kw REAL
);

-- Pack attachments (time-bounded)
CREATE TABLE battery_pack_attachments (
    pack_id TEXT,
    array_id TEXT,
    attached_since TEXT NOT NULL,
    detached_at TEXT,  -- NULL = active
    PRIMARY KEY (pack_id, attached_since)
);

-- Per-array aggregated samples
CREATE TABLE array_samples (
    ts TEXT NOT NULL,
    array_id TEXT NOT NULL,
    pv_power_w INTEGER,
    load_power_w INTEGER,
    grid_power_w INTEGER,
    batt_power_w INTEGER,
    batt_soc_pct REAL,
    batt_voltage_v REAL,
    batt_current_a REAL,
    PRIMARY KEY (ts, array_id)
);
```

### Updated Tables

```sql
-- Added array_id column
ALTER TABLE energy_samples ADD COLUMN array_id TEXT;

-- Added pack_id and array_id columns
ALTER TABLE battery_bank_samples ADD COLUMN pack_id TEXT;
ALTER TABLE battery_bank_samples ADD COLUMN array_id TEXT;
```

## API Response Structure

### Array "Now" Response

```json
{
  "array_id": "array_north",
  "ts": "2025-11-07T14:10:00+05:00",
  "now": {
    "pv_power_w": 9820,
    "load_power_w": 4210,
    "grid_power_w": -5610,
    "batt_power_w": 0,
    "batt_soc_pct": 72.3,
    "_metadata": {
      "inverter_count": 2,
      "attached_pack_ids": ["pytes_pack_A"],
      "phase_mix": ["three", "three"],
      "vendor_mix": ["senergy", "powdrive"]
    }
  },
  "inverters": [
    {
      "inverter_id": "senergy_1",
      "pv_power_w": 5200,
      "phase_type": "three"
    },
    {
      "inverter_id": "powdrive_1",
      "pv_power_w": 4620,
      "phase_type": "three"
    }
  ],
  "packs": [
    {
      "pack_id": "pytes_pack_A",
      "soc_pct": 72.3,
      "voltage_v": 51.3,
      "current_a": 0.0
    }
  ]
}
```

## Next Steps

1. **Complete Adapter Updates**: Ensure all adapters emit `array_id`
2. **Implement API Endpoints**: Add all array-related endpoints
3. **Update Smart Scheduler**: Per-array instantiation and multi-pack support
4. **MQTT/HA Integration**: Publish array and pack entities
5. **Backward Compatibility**: Migration helper for legacy configs
6. **App Integration**: Wire everything together in `SolarApp`
7. **Testing**: Comprehensive testing of array aggregation and scheduling

## Notes

- All changes maintain backward compatibility
- Legacy configs without arrays will get a default array created
- Existing data will be backfilled with `array_id` where possible
- MQTT topics maintain backward compatibility (old topics still work)

