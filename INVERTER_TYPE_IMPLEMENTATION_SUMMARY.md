# Inverter Type Detection and Data Publishing - Implementation Summary

## ✅ Completed Implementation

### 1. Core Infrastructure

#### InverterMetadata Module (`solarhub/inverter_metadata.py`)
- ✅ `InverterMetadata` class for managing phase type and inverter count
- ✅ `detect_phase_type_from_telemetry()` - Detects from telemetry data
- ✅ `detect_phase_type_from_register()` - Detects from inverter_type register
- ✅ `get_inverter_metadata()` - Gets metadata from config or telemetry
- ✅ `get_publishable_fields()` - Gets fields to publish based on phase type

#### Configuration (`solarhub/config.py`)
- ✅ Added `phase_type` field to `InverterConfig`
- ✅ Optional: "single" | "three" | None (auto-detect)

### 2. Device Adapters

#### PowdriveAdapter (`solarhub/adapters/powdrive.py`)
- ✅ Reads `inverter_type` register
- ✅ Detects phase type from register value (5 = "3 Phase Hybrid Inverter")
- ✅ Stores `phase_type` in `tel.extra`
- ✅ Stores `inverter_type` in `tel.extra` for detection

#### SenergyAdapter (`solarhub/adapters/senergy.py`)
- ✅ Detects phase type from phase-specific data
- ✅ Stores `phase_type` in `tel.extra` if detected

### 3. MQTT Publishing (`solarhub/app.py`)

- ✅ Adds `_metadata` to MQTT payload
- ✅ Includes phase type and inverter count
- ✅ All registers still published (metadata is additive)
- ✅ Passes inverter count to HA discovery

### 4. API Server (`solarhub/api_server.py`)

- ✅ Adds `_metadata` to API response
- ✅ Includes metadata for single inverter view
- ✅ Includes metadata for consolidated ("all") view
- ✅ Uses mapper when available for consistency

### 5. Home Assistant Discovery (`solarhub/ha/discovery.py`)

- ✅ Filters phase-specific registers based on phase type
- ✅ Only publishes phase registers for three-phase inverters
- ✅ Skips phase registers for single-phase inverters
- ✅ Uses metadata to determine what to publish

### 6. Frontend (`webapp-react/src`)

- ✅ Added `_metadata` to `TelemetryData` type
- ✅ Updated `isThreePhase()` to use metadata first
- ✅ Falls back to phase-specific data detection

## 📊 Data Flow

```
Device Register (inverter_type)
    ↓
Adapter.poll() → reads inverter_type register
    ↓
InverterMetadata.detect_phase_type_from_register() → detects phase type
    ↓
Stores phase_type in tel.extra
    ↓
get_inverter_metadata() → combines config + detected type
    ↓
_metadata added to payload
    ↓
├─→ MQTT: <base_topic>/<inverter_id>/regs (with _metadata)
├─→ API: /api/now (with _metadata)
├─→ HA: Only phase registers for three-phase
└─→ Frontend: Uses _metadata for UI decisions
```

## 🔍 Detection Priority

### Phase Type Detection

1. **Config `phase_type`** (if specified in `config.yaml`)
2. **inverter_type register** (Powdrive: 5 = three-phase)
3. **Phase-specific data** (L1, L2, L3 registers)
4. **grid_type_setting register** (0 = three-phase, 1 = single-phase)
5. **None** (unknown)

### Inverter Count Detection

- Counts number of inverters in `solar_app.inverters`
- Single: `inverter_count = 1`
- Array: `inverter_count > 1`

## 📤 Published Data

### Single Phase Inverter

**MQTT Payload:**
```json
{
  "id": "senergy1",
  "pv_power_w": 5000,
  "load_power_w": 3000,
  "grid_power_w": -2000,
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

**HA Entities:**
- Basic sensors only (no phase-specific entities)

### Three Phase Inverter

**MQTT Payload:**
```json
{
  "id": "powdrive1",
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
  "grid_l1_voltage_v": 230.0,
  "grid_l2_voltage_v": 230.0,
  "grid_l3_voltage_v": 230.0,
  ...
}
```

**HA Entities:**
- All basic sensors
- **Plus** phase-specific entities (L1, L2, L3)

### Array (Multiple Inverters)

**API Response:**
```json
{
  "inverter_id": "all",
  "now": {
    "pv_power_w": 15000,  // Sum
    "load_power_w": 9000,  // Sum
    "batt_soc_pct": 75.5,  // Average
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

## 🎯 Usage Examples

### Configuration

```yaml
inverters:
  - id: powdrive1
    name: "Powdrive 12k Three Phase"
    phase_type: "three"  # Explicitly set
    adapter:
      type: powdrive
      ...
      
  - id: senergy1
    name: "Senergy 5k Single Phase"
    phase_type: "single"  # Explicitly set
    adapter:
      type: senergy
      ...
```

### Auto-Detection

```yaml
inverters:
  - id: powdrive1
    name: "Powdrive 12k"
    # phase_type not specified - will be auto-detected
    adapter:
      type: powdrive
      ...
```

### Frontend Usage

```typescript
const metadata = telemetry._metadata;

// Check if three-phase
if (metadata?.is_three_phase) {
  // Show phase-specific UI
  const l1Power = telemetry.load_l1_power_w;
  const l2Power = telemetry.load_l2_power_w;
  const l3Power = telemetry.load_l3_power_w;
}

// Check if array
if (metadata?.is_inverter_array) {
  // Show consolidated view
  // Display "All Inverters" option
}
```

## ✅ Verification Checklist

- [x] InverterMetadata module created
- [x] Phase type detection from register data
- [x] Phase type detection from telemetry data
- [x] Config support for phase_type
- [x] Powdrive adapter detects phase type
- [x] Senergy adapter detects phase type
- [x] Metadata added to MQTT payload
- [x] Metadata added to API response
- [x] HA discovery filters phase registers
- [x] Frontend types updated
- [x] Frontend uses metadata for detection

## 📋 Next Steps

1. **Test with real devices:**
   - Test with single phase inverter
   - Test with three phase inverter
   - Test with multiple inverters (array)

2. **Frontend enhancements:**
   - Update UI to show/hide phase components based on metadata
   - Add phase imbalance indicators for three-phase
   - Add array view for multiple inverters

3. **Documentation:**
   - Add examples to user guide
   - Document configuration options

## 🎉 Summary

The system now:
- ✅ Automatically detects inverter type (single/three phase)
- ✅ Supports configuration override
- ✅ Publishes appropriate data based on type
- ✅ Filters HA entities based on phase type
- ✅ Provides metadata to frontend for UI decisions
- ✅ Handles both single inverter and arrays
- ✅ Maintains backward compatibility

All components are using the standardized mapping system and metadata is consistently published across all modules.

