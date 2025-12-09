# Inverter Metadata System

This document describes the system for identifying and managing inverter metadata:
- Single vs multiple inverters
- Single phase vs three phase
- Automatic detection from register data
- Configuration-based specification

## Overview

The system automatically detects inverter type (single phase vs three phase) from register data and allows configuration to override this detection. It publishes appropriate data to the frontend and Home Assistant based on:
1. **Inverter Count**: Single inverter vs array of inverters
2. **Phase Type**: Single phase vs three phase

## Components

### 1. InverterMetadata (`solarhub/inverter_metadata.py`)

Manages inverter metadata including:
- `phase_type`: "single", "three", or None (unknown)
- `inverter_count`: Number of inverters in the system

**Methods:**
- `detect_phase_type_from_telemetry()`: Detects phase type from telemetry data
- `detect_phase_type_from_register()`: Detects phase type from inverter_type register
- `get_inverter_metadata()`: Gets metadata from telemetry and config
- `get_publishable_fields()`: Gets fields that should be published based on phase type

### 2. Configuration (`solarhub/config.py`)

Added `phase_type` field to `InverterConfig`:
```python
class InverterConfig(BaseModel):
    ...
    phase_type: Optional[str] = None  # "single" | "three" | None (auto-detect)
```

**Priority:**
1. Config `phase_type` (if specified)
2. Detected from telemetry data
3. None (unknown)

### 3. Device Adapters

#### PowdriveAdapter
- Reads `inverter_type` register
- Detects phase type from register value (5 = "3 Phase Hybrid Inverter")
- Stores `phase_type` in `tel.extra`

#### SenergyAdapter
- Can detect phase type from phase-specific data
- Stores `phase_type` in `tel.extra` if detected

### 4. MQTT Publishing (`solarhub/app.py`)

- Adds `_metadata` to MQTT payload with:
  - `phase_type`: "single", "three", or None
  - `inverter_count`: Number of inverters
  - `is_three_phase`: Boolean
  - `is_single_phase`: Boolean
  - `is_single_inverter`: Boolean
  - `is_inverter_array`: Boolean

### 5. API Server (`solarhub/api_server.py`)

- Adds `_metadata` to API response
- Includes metadata for both single inverter and consolidated ("all") views

### 6. Home Assistant Discovery (`solarhub/ha/discovery.py`)

- Only publishes phase-specific registers for three-phase inverters
- Skips phase-specific registers for single-phase inverters
- Uses metadata to determine what to publish

## Detection Methods

### Phase Type Detection

1. **From Phase-Specific Data** (Most Reliable):
   - Checks for `load_l1_power_w`, `grid_l1_power_w`, etc.
   - If any phase-specific data exists → three-phase

2. **From inverter_type Register**:
   - Powdrive: 5 = "3 Phase Hybrid Inverter" → three-phase
   - Other values (2, 3, 4) → single-phase

3. **From grid_type_setting Register**:
   - 0 = "Three Phase" → three-phase
   - 1 = "Single-phase" → single-phase

### Inverter Count Detection

- Counts number of inverters in `solar_app.inverters`
- Single inverter: `inverter_count = 1`
- Array: `inverter_count > 1`

## Data Publishing

### Single Phase Inverter

**Published Fields:**
- Basic power flows: `pv_power_w`, `load_power_w`, `grid_power_w`, `batt_power_w`
- Battery data: `batt_soc_pct`, `batt_voltage_v`, `batt_current_a`
- Inverter data: `inverter_temp_c`, `inverter_mode`
- Energy totals: `today_energy`, `today_load_energy`, etc.

**Not Published:**
- Phase-specific fields (L1, L2, L3)
- Line voltages (AB, BC, CA)

### Three Phase Inverter

**Published Fields:**
- All basic fields (same as single phase)
- Phase-specific fields:
  - `load_l1_power_w`, `load_l2_power_w`, `load_l3_power_w`
  - `load_l1_voltage_v`, `load_l2_voltage_v`, `load_l3_voltage_v`
  - `load_l1_current_a`, `load_l2_current_a`, `load_l3_current_a`
  - `grid_l1_power_w`, `grid_l2_power_w`, `grid_l3_power_w`
  - `grid_l1_voltage_v`, `grid_l2_voltage_v`, `grid_l3_voltage_v`
  - `grid_l1_current_a`, `grid_l2_current_a`, `grid_l3_current_a`
  - `grid_line_voltage_ab_v`, `grid_line_voltage_bc_v`, `grid_line_voltage_ca_v`
  - `load_frequency_hz`, `grid_frequency_hz`

### Single Inverter vs Array

**Single Inverter:**
- Direct telemetry data
- Metadata: `is_single_inverter: true`, `is_inverter_array: false`

**Array (Multiple Inverters):**
- Consolidated/aggregated data
- Sums for power and energy
- Averages for voltage, current, SOC
- Metadata: `is_single_inverter: false`, `is_inverter_array: true`
- `phase_type: null` (mixed phase types possible)

## Usage

### Configuration

```yaml
inverters:
  - id: powdrive1
    name: "Powdrive 12k"
    phase_type: "three"  # Optional: "single" | "three" | null (auto-detect)
    adapter:
      type: powdrive
      ...
```

### API Response

```json
{
  "inverter_id": "powdrive1",
  "now": {
    "pv_power_w": 5000,
    "load_power_w": 3000,
    "grid_power_w": -2000,
    "_metadata": {
      "phase_type": "three",
      "inverter_count": 1,
      "is_three_phase": true,
      "is_single_phase": false,
      "is_single_inverter": true,
      "is_inverter_array": false
    },
    "load_l1_power_w": 1000,
    "load_l2_power_w": 1000,
    "load_l3_power_w": 1000,
    ...
  }
}
```

### MQTT Payload

```json
{
  "id": "powdrive1",
  "pv_power_w": 5000,
  "load_power_w": 3000,
  "_metadata": {
    "phase_type": "three",
    "inverter_count": 1,
    "is_three_phase": true,
    "is_single_phase": false,
    "is_single_inverter": true,
    "is_inverter_array": false
  },
  "load_l1_power_w": 1000,
  "load_l2_power_w": 1000,
  "load_l3_power_w": 1000,
  ...
}
```

## Frontend Usage

The frontend can use `_metadata` to:
1. Determine if phase-specific data should be displayed
2. Show/hide phase-specific UI components
3. Adjust data visualization based on inverter type

Example:
```typescript
const metadata = telemetry._metadata;
if (metadata.is_three_phase) {
  // Show phase-specific data (L1, L2, L3)
  // Display phase cards, line voltages, etc.
} else {
  // Show only total power, voltage, current
  // Hide phase-specific components
}
```

## Home Assistant Usage

Home Assistant entities are published based on phase type:
- **Single phase**: Only basic sensors (no phase-specific entities)
- **Three phase**: All sensors including phase-specific entities (L1, L2, L3)

The frontend can use `_metadata` to determine which entities are available.

## Benefits

1. **Automatic Detection**: No manual configuration needed (can be overridden)
2. **Appropriate Data**: Only relevant data is published based on inverter type
3. **Frontend Flexibility**: Frontend can adapt UI based on metadata
4. **HA Optimization**: Only necessary entities are created
5. **Backward Compatibility**: All data still available, metadata is additive

## Future Enhancements

1. **Mixed Arrays**: Handle arrays with mixed phase types
2. **Phase Balancing**: Show phase imbalance for three-phase systems
3. **Power Factor**: Include power factor data for three-phase systems
4. **Harmonic Analysis**: Include harmonic data if available

