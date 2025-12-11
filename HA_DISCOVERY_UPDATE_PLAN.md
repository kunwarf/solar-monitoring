# Home Assistant Discovery Update Plan
## Telemetry & Hierarchy Specification Implementation

## Overview

This plan outlines the updates needed to align Home Assistant discovery with the complete telemetry and hierarchy specification. The specification defines 6 hierarchical levels with specific telemetry requirements at each level.

---

## Current State Analysis

### Existing Implementation
- ✅ System-level discovery (`publish_system_entities`) - partial (only power sensors)
- ✅ Array-level discovery (`publish_array_entities`) - partial (only power sensors)
- ✅ Battery array-level discovery (`publish_battery_array_entities`) - partial
- ✅ Inverter-level discovery (`publish_all_for_inverter`) - complete (all registers)
- ✅ Battery pack-level discovery (`publish_pack_entities`) - partial (only basic sensors)
- ✅ Battery unit-level discovery (`publish_battery_unit_entities`) - partial
- ✅ Cell-level discovery (`publish_battery_cell_entities`) - exists but needs verification
- ✅ Meter-level discovery (`publish_meter_entities`) - complete

### Gaps Identified
1. **Missing Energy Telemetry**: No cumulative (`total_*`) or daily (`today_*`) energy sensors at any level
2. **Incomplete System-Level**: Missing energy telemetry (only has power sensors)
3. **Incomplete Array-Level**: Missing energy telemetry for both inverter and battery arrays
4. **Incomplete Battery Pack-Level**: Missing energy telemetry
5. **Incomplete Battery Unit-Level**: Missing energy telemetry
6. **Naming Inconsistencies**: Field names don't match specification exactly
7. **Missing via_device Relationships**: Some levels don't properly link to parent devices

---

## Implementation Plan

### Phase 1: System-Level Device Discovery

**File**: `solarhub/ha/discovery.py`  
**Method**: `publish_system_entities()`

**Required Sensors**:

#### Real-time Power Telemetry (W)
- `load_power` - Load power (instantaneous)
- `solar_power` - Solar/PV power (instantaneous)
- `grid_power` - Grid power (positive = import, negative = export)
- `battery_power` - Battery power (positive = discharge, negative = charge)

#### Aggregated Energy Telemetry (kWh) - Cumulative/Lifetime
- `total_load_energy` - Total load energy (cumulative)
- `total_grid_import` - Total grid import energy (cumulative)
- `total_grid_export` - Total grid export energy (cumulative)
- `total_solar_energy` - Total solar energy (cumulative)
- `total_battery_discharge` - Total battery discharge energy (cumulative)
- `total_battery_charge` - Total battery charge energy (cumulative)

#### Daily Energy Telemetry (kWh) - "Today"
- `today_load_energy` - Today's load energy
- `today_grid_import` - Today's grid import energy
- `today_grid_export` - Today's grid export energy
- `today_solar_energy` - Today's solar energy
- `today_battery_discharge` - Today's battery discharge energy
- `today_battery_charge` - Today's battery charge energy

**State Topic**: `{base_topic}/systems/{system_id}/state`

**Device Info**:
- `identifiers`: `["system:{system_id}"]`
- `name`: System name
- `model`: "Solar System"
- `manufacturer`: "SolarHub"
- `via_device`: None (top-level device)

**Implementation Notes**:
- All energy sensors should use `device_class: "energy"` and `state_class: "total_increasing"` for cumulative values
- Daily energy sensors should use `state_class: "total_increasing"` (resets daily)
- Power sensors should use `device_class: "power"` and `state_class: "measurement"`

---

### Phase 2: Array-Level Device Discovery

**File**: `solarhub/ha/discovery.py`  
**Methods**: 
- `publish_array_entities()` - For inverter arrays
- `publish_battery_array_entities()` - For battery arrays (already exists, needs update)

#### 2.1 Inverter Array Discovery

**Required Sensors** (same as system-level, but for array only):

**Real-time Power**:
- `load_power` (W)
- `solar_power` (W)
- `grid_power` (W)
- `battery_power` (W)

**Cumulative Energy**:
- `total_load_energy` (kWh)
- `total_grid_import` (kWh)
- `total_grid_export` (kWh)
- `total_solar_energy` (kWh)
- `total_battery_discharge` (kWh)
- `total_battery_charge` (kWh)

**Daily Energy**:
- `today_load_energy` (kWh)
- `today_grid_import` (kWh)
- `today_grid_export` (kWh)
- `today_solar_energy` (kWh)
- `today_battery_discharge` (kWh)
- `today_battery_charge` (kWh)

**State Topic**: `{base_topic}/arrays/{array_id}/state`

**Device Info**:
- `identifiers`: `["array:{array_id}"]`
- `name`: Array name
- `model`: "Inverter Array"
- `manufacturer`: "SolarHub"
- `via_device`: `"system:{system_id}"` (if system_id provided)

#### 2.2 Battery Array Discovery

**Required Sensors**:

**Real-time Power**:
- `battery_power` (W) - Total power from all packs in array

**Cumulative Energy**:
- `total_battery_discharge` (kWh)
- `total_battery_charge` (kWh)

**Daily Energy**:
- `today_battery_discharge` (kWh)
- `today_battery_charge` (kWh)

**Additional Sensors** (already exist, keep):
- `total_soc_pct` (%)
- `total_voltage_v` (V)
- `total_current_a` (A)
- `avg_temperature_c` (°C)

**State Topic**: `{base_topic}/battery_arrays/{battery_array_id}/state`

**Device Info**:
- `identifiers`: `["battery_array:{battery_array_id}"]`
- `name`: Battery array name
- `model`: "Battery Array"
- `manufacturer`: "SolarHub"
- `via_device`: `"system:{system_id}"` (if system_id provided)

---

### Phase 3: Inverter-Level Device Discovery

**File**: `solarhub/ha/discovery.py`  
**Method**: `publish_all_for_inverter()` - Already exists, needs enhancement

**Current State**: Already publishes all registers from inverter adapters.

**Required Additions**:

Ensure the following standardized sensors are published (may already exist as registers):

**Real-time Power**:
- `load_power` (W)
- `solar_power` (W) - or `pv_power`
- `grid_power` (W)
- `battery_power` (W)

**Cumulative Energy**:
- `total_load_energy` (kWh)
- `total_grid_import` (kWh)
- `total_grid_export` (kWh)
- `total_solar_energy` (kWh)
- `total_battery_discharge` (kWh)
- `total_battery_charge` (kWh)

**Daily Energy**:
- `today_load_energy` (kWh)
- `today_grid_import` (kWh)
- `today_grid_export` (kWh)
- `today_solar_energy` (kWh)
- `today_battery_discharge` (kWh)
- `today_battery_charge` (kWh)

**State Topic**: `{base_topic}/{inverter_id}/regs` (existing)

**Device Info**:
- `identifiers`: `[inverter_id]`
- `name`: Inverter name
- `model`: From telemetry/config
- `manufacturer`: From telemetry/config
- `via_device`: `"array:{array_id}"` (if array_id available)

**Implementation Notes**:
- If registers don't exist, calculate from hourly/daily energy tables
- Use `_publish_calculated_fields()` method to add missing sensors
- Map existing register names to standardized field names

---

### Phase 4: Battery Pack-Level Device Discovery

**File**: `solarhub/ha/discovery.py`  
**Method**: `publish_pack_entities()` - Exists, needs enhancement

**Required Sensors**:

**Real-time Power**:
- `battery_power` (W) - positive = discharge, negative = charge

**Cumulative Energy**:
- `total_battery_discharge` (kWh)
- `total_battery_charge` (kWh)

**Daily Energy**:
- `today_battery_discharge` (kWh)
- `today_battery_charge` (kWh)

**Additional Sensors** (already exist, keep):
- `soc_pct` (%)
- `voltage_v` (V)
- `current_a` (A)
- `power_w` (W) - same as `battery_power`
- `temperature_c` (°C)

**State Topic**: `{base_topic}/packs/{pack_id}/state`

**Device Info**:
- `identifiers`: `["pack:{pack_id}"]`
- `name`: Pack name
- `model`: From config/telemetry
- `manufacturer`: From config/telemetry
- `via_device`: `"battery_array:{battery_array_id}"` (if available)

---

### Phase 5: Individual Battery-Level Device Discovery

**File**: `solarhub/ha/discovery.py`  
**Method**: `publish_battery_unit_entities()` - Exists, needs enhancement

**Required Sensors**:

**Real-time Power & Basic Telemetry**:
- `battery_power` (W)
- `pack_voltage` (V) - or `voltage`
- `pack_current` (A) - or `current`
- `state_of_charge` (%) - or `soc`
- `temperature` (°C) - if available at battery level

**Cumulative Energy**:
- `total_battery_discharge` (kWh)
- `total_battery_charge` (kWh)

**Daily Energy**:
- `today_battery_discharge` (kWh)
- `today_battery_charge` (kWh)

**State Topic**: `{base_topic}/battery/{bank_id}/{unit_power}/regs` (existing)

**Device Info**:
- `identifiers`: `["battery_unit:{bank_id}:{unit_power}"]`
- `name`: Battery unit name
- `model`: "Battery Unit"
- `manufacturer`: "SolarHub"
- `via_device`: `"pack:{pack_id}"` (if pack_id available, otherwise `"battery_bank:{bank_id}"`)

**Implementation Notes**:
- Map existing field names to standardized names
- Add energy sensors if not already present
- Ensure proper via_device relationship to pack

---

### Phase 6: Cell-Level Discovery (Under Battery Device)

**File**: `solarhub/ha/discovery.py`  
**Method**: `publish_battery_cell_entities()` - Exists, verify implementation

**Current Implementation**: Cells are already published as sensors under the battery unit device (correct).

**Required Sensors** (per cell):
- `cell_{N}_voltage` (V) - Cell N voltage
- `cell_{N}_temperature` (°C) - Cell N temperature (if available)

**State Topic**: `{base_topic}/battery/{bank_id}/{unit_power}/cells/{cell_index}/regs` (existing)

**Device Info**: 
- **MUST use EXACT same device_info as battery unit** (via `_get_battery_unit_device_info()`)
- This ensures cells appear under the battery device, not as separate devices

**Implementation Notes**:
- Current implementation appears correct - cells use same device_info as battery unit
- Verify that all cells are properly grouped under their parent battery device
- Ensure cell sensors are named consistently: `cell_{index}_voltage`, `cell_{index}_temperature`

---

## Data Source Requirements

### Energy Data Sources

For cumulative and daily energy telemetry, we need to query:

1. **System-Level Energy**:
   - Source: `system_hourly_energy` table (aggregated)
   - Calculate cumulative: Sum all hourly values
   - Calculate daily: Sum today's hourly values

2. **Array-Level Energy**:
   - Source: `array_hourly_energy` table
   - Calculate cumulative: Sum all hourly values
   - Calculate daily: Sum today's hourly values

3. **Inverter-Level Energy**:
   - Source: `hourly_energy` table (filtered by `inverter_id`)
   - Calculate cumulative: Sum all hourly values
   - Calculate daily: Sum today's hourly values

4. **Battery Pack-Level Energy**:
   - Source: `battery_bank_hourly` table (filtered by `pack_id`)
   - Calculate cumulative: Sum all hourly values
   - Calculate daily: Sum today's hourly values

5. **Battery Unit-Level Energy**:
   - Source: `battery_unit_samples` table (aggregated to hourly, then summed)
   - Calculate cumulative: Sum all hourly values
   - Calculate daily: Sum today's hourly values

### Implementation Approach

1. **Add Energy Calculation Methods**:
   - Create helper methods in `discovery.py` to query energy data
   - Cache energy values to avoid excessive database queries
   - Update energy values when publishing telemetry

2. **Telemetry Publishing Updates**:
   - Update `_aggregate_and_publish_home_telemetry()` to include energy data
   - Update `_poll_one()` to include energy data in array telemetry
   - Update `_poll_battery()` to include energy data in pack telemetry

3. **State Topic Payload Structure**:
   - Ensure all state topics include both power and energy fields
   - Use consistent field naming across all levels

---

## Field Name Standardization

### Power Fields (W)
- `load_power` - Load power
- `solar_power` or `pv_power` - Solar/PV power
- `grid_power` - Grid power (positive = import, negative = export)
- `battery_power` - Battery power (positive = discharge, negative = charge)

### Energy Fields (kWh)
- `total_load_energy` - Cumulative load energy
- `total_grid_import` - Cumulative grid import
- `total_grid_export` - Cumulative grid export
- `total_solar_energy` - Cumulative solar energy
- `total_battery_discharge` - Cumulative battery discharge
- `total_battery_charge` - Cumulative battery charge
- `today_load_energy` - Today's load energy
- `today_grid_import` - Today's grid import
- `today_grid_export` - Today's grid export
- `today_solar_energy` - Today's solar energy
- `today_battery_discharge` - Today's battery discharge
- `today_battery_charge` - Today's battery charge

### Battery-Specific Fields
- `soc_pct` or `state_of_charge` - State of charge (%)
- `voltage_v` or `pack_voltage` - Voltage (V)
- `current_a` or `pack_current` - Current (A)
- `temperature_c` or `temperature` - Temperature (°C)

---

## Device Hierarchy & via_device Relationships

```
System (top-level, no via_device)
  ├── Inverter Array (via_device: system:{system_id})
  │     ├── Inverter (via_device: array:{array_id})
  │     └── Battery Array (via_device: system:{system_id})
  │           └── Battery Pack (via_device: battery_array:{battery_array_id})
  │                 └── Battery Unit (via_device: pack:{pack_id})
  │                       └── Cell Sensors (same device as Battery Unit)
  └── Meter (via_device: system:{system_id})
```

**Rules**:
1. System has no `via_device` (top-level)
2. Arrays link to system via `via_device: system:{system_id}`
3. Inverters link to their array via `via_device: array:{array_id}`
4. Battery arrays link to system via `via_device: system:{system_id}`
5. Battery packs link to battery array via `via_device: battery_array:{battery_array_id}`
6. Battery units link to pack via `via_device: pack:{pack_id}`
7. Cells use same device_info as battery unit (no separate device)

---

## Implementation Checklist

### Phase 1: System-Level
- [ ] Update `publish_system_entities()` to include all required sensors
- [ ] Add energy calculation methods for system-level
- [ ] Update system telemetry publishing to include energy data
- [ ] Test system-level discovery

### Phase 2: Array-Level
- [ ] Update `publish_array_entities()` to include energy sensors
- [ ] Update `publish_battery_array_entities()` to include energy sensors
- [ ] Add energy calculation methods for array-level
- [ ] Update array telemetry publishing to include energy data
- [ ] Test array-level discovery

### Phase 3: Inverter-Level
- [ ] Verify `publish_all_for_inverter()` publishes all required sensors
- [ ] Add missing energy sensors via `_publish_calculated_fields()`
- [ ] Map register names to standardized field names
- [ ] Add energy calculation methods for inverter-level
- [ ] Test inverter-level discovery

### Phase 4: Battery Pack-Level
- [ ] Update `publish_pack_entities()` to include energy sensors
- [ ] Add energy calculation methods for pack-level
- [ ] Update pack telemetry publishing to include energy data
- [ ] Test pack-level discovery

### Phase 5: Battery Unit-Level
- [ ] Update `publish_battery_unit_entities()` to include energy sensors
- [ ] Add energy calculation methods for unit-level
- [ ] Update unit telemetry publishing to include energy data
- [ ] Test unit-level discovery

### Phase 6: Cell-Level
- [ ] Verify `publish_battery_cell_entities()` uses correct device_info
- [ ] Ensure cells appear under battery device (not separate devices)
- [ ] Test cell-level discovery

### General
- [ ] Add helper methods for energy data queries
- [ ] Update all state topic payloads to include energy fields
- [ ] Standardize field names across all levels
- [ ] Verify via_device relationships are correct
- [ ] Test complete hierarchy in Home Assistant
- [ ] Update documentation

---

## Testing Plan

1. **Unit Tests**:
   - Test each discovery method with mock data
   - Verify sensor configurations are correct
   - Verify device_info and via_device relationships

2. **Integration Tests**:
   - Test complete hierarchy discovery
   - Verify all sensors appear in Home Assistant
   - Verify device relationships in HA UI

3. **Data Flow Tests**:
   - Verify energy data is calculated correctly
   - Verify state topics contain all required fields
   - Verify cumulative and daily energy values update correctly

---

## Migration Notes

- **Backward Compatibility**: Existing sensors will continue to work
- **New Sensors**: New energy sensors will be added alongside existing sensors
- **Field Name Changes**: May need to deprecate old field names gradually
- **State Topics**: Existing state topics will be enhanced with new fields

---

## Estimated Effort

- **Phase 1-2**: 4-6 hours (System and Array levels)
- **Phase 3**: 2-3 hours (Inverter level - mostly verification)
- **Phase 4-5**: 3-4 hours (Battery pack and unit levels)
- **Phase 6**: 1 hour (Cell level - verification)
- **Testing**: 2-3 hours
- **Total**: 12-17 hours

---

## Dependencies

1. **Database Tables**: 
   - `system_hourly_energy` ✅ (exists)
   - `array_hourly_energy` ✅ (exists)
   - `hourly_energy` ✅ (exists)
   - `battery_bank_hourly` ✅ (exists)
   - Need to verify battery unit hourly aggregation

2. **Energy Calculator**:
   - Methods to calculate cumulative and daily energy
   - Methods to query hourly energy tables

3. **Telemetry Publishing**:
   - Update all telemetry publishing methods to include energy data
   - Ensure state topics include all required fields

---

## Success Criteria

1. ✅ All 6 hierarchical levels have complete discovery
2. ✅ All required sensors are published at each level
3. ✅ Energy telemetry (cumulative and daily) is available at all levels
4. ✅ Device hierarchy is correct with proper via_device relationships
5. ✅ Field names are standardized across all levels
6. ✅ Cells appear under battery devices (not separate devices)
7. ✅ All sensors appear correctly in Home Assistant UI
8. ✅ Energy values update correctly in real-time

---

**Last Updated**: 2025-01-XX  
**Status**: Planning Phase  
**Next Steps**: Review and approval, then begin Phase 1 implementation

