# Inverter Type Detection and Data Publishing

This document describes how the system identifies and handles different inverter types:
- Single vs multiple inverters
- Single phase vs three phase
- Appropriate data publishing based on type

## Overview

The system automatically detects inverter type from register data and publishes appropriate data to:
- Frontend (via API)
- Home Assistant (via MQTT)
- Smart Scheduler
- Logger

## Detection Methods

### 1. Phase Type Detection

**Priority:**
1. Config `phase_type` (if specified in `config.yaml`)
2. Detected from `inverter_type` register
3. Detected from phase-specific data (L1, L2, L3)
4. Detected from `grid_type_setting` register
5. None (unknown)

**Detection Sources:**

#### From inverter_type Register
- **Powdrive**: 
  - Value 5 = "3 Phase Hybrid Inverter" → three-phase
  - Values 2, 3, 4 = Single phase inverters → single-phase

#### From Phase-Specific Data
- Checks for presence of:
  - `load_l1_power_w`, `load_l2_power_w`, `load_l3_power_w`
  - `grid_l1_power_w`, `grid_l2_power_w`, `grid_l3_power_w`
  - `load_l1_voltage_v`, `grid_l1_voltage_v`, etc.
- If any phase-specific data exists → three-phase

#### From grid_type_setting Register
- Value 0 = "Three Phase" → three-phase
- Value 1 = "Single-phase" → single-phase

### 2. Inverter Count Detection

- Counts number of inverters in `solar_app.inverters`
- Single inverter: `inverter_count = 1`
- Array: `inverter_count > 1`

## Configuration

### config.yaml

```yaml
inverters:
  - id: powdrive1
    name: "Powdrive 12k"
    phase_type: "three"  # Optional: "single" | "three" | null (auto-detect)
    adapter:
      type: powdrive
      ...
```

**Note:** If `phase_type` is not specified, it will be auto-detected from register data.

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

**Metadata:**
```json
{
  "_metadata": {
    "phase_type": "single",
    "inverter_count": 1,
    "is_three_phase": false,
    "is_single_phase": true,
    "is_single_inverter": true,
    "is_inverter_array": false
  }
}
```

### Three Phase Inverter

**Published Fields:**
- All basic fields (same as single phase)
- **Plus** phase-specific fields:
  - `load_l1_power_w`, `load_l2_power_w`, `load_l3_power_w`
  - `load_l1_voltage_v`, `load_l2_voltage_v`, `load_l3_voltage_v`
  - `load_l1_current_a`, `load_l2_current_a`, `load_l3_current_a`
  - `grid_l1_power_w`, `grid_l2_power_w`, `grid_l3_power_w`
  - `grid_l1_voltage_v`, `grid_l2_voltage_v`, `grid_l3_voltage_v`
  - `grid_l1_current_a`, `grid_l2_current_a`, `grid_l3_current_a`
  - `grid_line_voltage_ab_v`, `grid_line_voltage_bc_v`, `grid_line_voltage_ca_v`
  - `load_frequency_hz`, `grid_frequency_hz`

**Metadata:**
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

### Single Inverter

**Data Structure:**
- Direct telemetry from single inverter
- All registers from that inverter
- Metadata: `is_single_inverter: true`

### Array (Multiple Inverters)

**Data Structure:**
- Consolidated/aggregated data
- Sums for power and energy
- Averages for voltage, current, SOC
- Metadata: `is_inverter_array: true`, `phase_type: null` (mixed types possible)

**Consolidated View:**
```json
{
  "inverter_id": "all",
  "now": {
    "pv_power_w": 10000,  // Sum of all inverters
    "load_power_w": 6000,  // Sum of all inverters
    "batt_soc_pct": 75.5,  // Average of all inverters
    "_metadata": {
      "phase_type": null,  // Mixed types possible
      "inverter_count": 3,
      "is_three_phase": false,
      "is_single_phase": false,
      "is_single_inverter": false,
      "is_inverter_array": true
    }
  }
}
```

## Home Assistant Publishing

### Single Phase Inverter

**Published Entities:**
- Basic sensors: `pv_power_w`, `load_power_w`, `grid_power_w`, etc.
- Battery sensors: `batt_soc_pct`, `batt_voltage_v`, etc.
- **No phase-specific entities**

### Three Phase Inverter

**Published Entities:**
- All basic sensors (same as single phase)
- **Plus** phase-specific entities:
  - `load_l1_power_w`, `load_l2_power_w`, `load_l3_power_w`
  - `grid_l1_power_w`, `grid_l2_power_w`, `grid_l3_power_w`
  - `load_l1_voltage_v`, `grid_l1_voltage_v`, etc.
  - `grid_line_voltage_ab_v`, `grid_line_voltage_bc_v`, `grid_line_voltage_ca_v`

## Frontend Usage

The frontend can use `_metadata` to:

1. **Determine UI Layout:**
   ```typescript
   const metadata = telemetry._metadata;
   if (metadata.is_three_phase) {
     // Show phase-specific components
     // Display L1, L2, L3 cards
     // Show line voltages
   } else {
     // Show only total power
     // Hide phase-specific components
   }
   ```

2. **Filter Data:**
   ```typescript
   // Only show phase data for three-phase inverters
   if (metadata.is_three_phase) {
     const l1Power = telemetry.load_l1_power_w;
     const l2Power = telemetry.load_l2_power_w;
     const l3Power = telemetry.load_l3_power_w;
   }
   ```

3. **Handle Arrays:**
   ```typescript
   if (metadata.is_inverter_array) {
     // Show consolidated view
     // Display "All Inverters" option
   } else {
     // Show single inverter view
   }
   ```

## API Endpoints

### Single Inverter
```
GET /api/now?inverter_id=powdrive1
```

**Response:**
```json
{
  "inverter_id": "powdrive1",
  "now": {
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
}
```

### All Inverters (Array)
```
GET /api/now?inverter_id=all
```

**Response:**
```json
{
  "inverter_id": "all",
  "now": {
    "pv_power_w": 15000,  // Sum
    "load_power_w": 9000,  // Sum
    "batt_soc_pct": 75.5,  // Average
    "_metadata": {
      "phase_type": null,  // Mixed
      "inverter_count": 3,
      "is_three_phase": false,
      "is_single_phase": false,
      "is_single_inverter": false,
      "is_inverter_array": true
    }
  }
}
```

## MQTT Topics

### Single Inverter
```
solar/fleet/powdrive1/regs
```

**Payload:**
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

## Implementation Status

### ✅ Completed

- [x] `InverterMetadata` class created
- [x] Phase type detection from register data
- [x] Phase type detection from telemetry data
- [x] Config support for `phase_type`
- [x] Metadata added to MQTT payload
- [x] Metadata added to API response
- [x] HA discovery filters phase registers based on type
- [x] Powdrive adapter detects phase type
- [x] Senergy adapter detects phase type

### 📋 Pending

- [ ] Update frontend to use `_metadata` for UI decisions
- [ ] Test with single phase inverter
- [ ] Test with three phase inverter
- [ ] Test with multiple inverters (array)
- [ ] Update documentation with examples

## Usage Examples

### Config Example

```yaml
inverters:
  - id: powdrive1
    name: "Powdrive 12k Three Phase"
    phase_type: "three"  # Explicitly set
    adapter:
      type: powdrive
      serial_port: "/dev/ttyUSB0"
      baudrate: 9600
      
  - id: senergy1
    name: "Senergy 5k Single Phase"
    phase_type: "single"  # Explicitly set
    adapter:
      type: senergy
      serial_port: "/dev/ttyUSB1"
      baudrate: 9600
```

### Auto-Detection Example

```yaml
inverters:
  - id: powdrive1
    name: "Powdrive 12k"
    # phase_type not specified - will be auto-detected
    adapter:
      type: powdrive
      ...
```

The system will:
1. Read `inverter_type` register
2. If value is 5 → detect as three-phase
3. If phase-specific data exists → detect as three-phase
4. Otherwise → detect as single-phase

## Benefits

1. **Automatic Detection**: No manual configuration needed
2. **Appropriate Data**: Only relevant data is published
3. **Frontend Flexibility**: Frontend can adapt UI based on metadata
4. **HA Optimization**: Only necessary entities are created
5. **Backward Compatibility**: All data still available, metadata is additive

