# Telemetry Mapping System Audit

This document tracks the implementation status of the standardized telemetry mapping system across all components.

## ✅ Completed

### Core Infrastructure
- [x] `TelemetryMapper` class created (`solarhub/telemetry_mapper.py`)
- [x] `StandardFields` class with all standardized field names
- [x] `read_all_registers()` method added to `JsonRegisterMixin`
- [x] Documentation created (`TELEMETRY_MAPPING_SYSTEM.md`, `STANDARD_FIELD_NAMES.md`)

### Device Adapters
- [x] **PowdriveAdapter**: 
  - Uses `TelemetryMapper` to convert device-specific names to standardized names
  - Reads all registers from register map using `read_all_registers()`
  - Maps all data to standardized format before creating Telemetry object
  
- [x] **SenergyAdapter**:
  - Uses `TelemetryMapper` to convert device-specific names to standardized names
  - Maps all register values to standardized format in `extra` field

### MQTT Publishing
- [x] **app.py** (`_poll_one` method):
  - Ensures all standardized register data is included in MQTT payload
  - Includes both standardized and device-specific keys for backward compatibility
  - Publishes to `<base_topic>/<inverter_id>/regs` topic

### Home Assistant Discovery
- [x] **discovery.py**:
  - Uses `standard_id` from register JSON when available (priority: standard_id > ha_key > reg_id > name)
  - Falls back to `ha_key` or `reg_id` for backward compatibility
  - All registers are published as HA entities

### Smart Scheduler
- [x] Already uses standardized field names:
  - `pv_power_w`, `load_power_w`, `grid_power_w`
  - `batt_soc_pct`, `batt_voltage_v`, `batt_current_a`
  - `inverter_temp_c`, `inverter_mode`

### API Server
- [x] Already normalizes field names in `/api/now` endpoint
- [x] Maps device-specific names to standardized names

## 📋 Pending Tasks

### Register JSON Files
- [ ] Add `standard_id` mappings to `register_maps/powdrive_registers.json`
  - Run: `python scripts/add_standard_id_mappings.py register_maps/powdrive_registers.json`
- [ ] Add `standard_id` mappings to `register_maps/senergy_registers.json` (if exists)
- [ ] Verify all registers have appropriate `standard_id` values

### Testing
- [ ] Test that all registers are read from devices
- [ ] Test that all registers are published to MQTT
- [ ] Test that all registers appear in Home Assistant
- [ ] Test that smart scheduler can access all required fields
- [ ] Test backward compatibility with existing integrations

### Documentation
- [ ] Update adapter development guide to include mapping system
- [ ] Add examples of adding new devices with mapping system

## 🔍 Verification Checklist

### For Each Device Adapter:
- [ ] Register map JSON file exists
- [ ] `TelemetryMapper` is created in `__init__`
- [ ] `poll()` method uses mapper to convert device data
- [ ] All registers are read (using `read_all_registers()` or equivalent)
- [ ] Standardized field names are used in `extra` dict

### For MQTT Publishing:
- [ ] All standardized fields are in payload
- [ ] All device-specific fields are in payload (for backward compatibility)
- [ ] Payload is published to correct topic: `<base_topic>/<inverter_id>/regs`

### For Home Assistant:
- [ ] All registers have discovery configs published
- [ ] Discovery uses `standard_id` when available
- [ ] All entities are accessible via MQTT state topic

### For Smart Scheduler:
- [ ] Can access all required telemetry fields using standardized names
- [ ] No hardcoded device-specific field names

## 🎯 Usage Examples

### Reading Telemetry in Smart Scheduler
```python
# Use standardized field names
pv_power = telemetry.extra.get("pv_power_w")
load_power = telemetry.extra.get("load_power_w")
batt_soc = telemetry.extra.get("batt_soc_pct")
```

### Accessing in Home Assistant
All registers are available as entities:
- State topic: `<base_topic>/<inverter_id>/regs`
- Value template: `{{ value_json.<standard_id> }}`

### Adding New Device
1. Create register JSON file with all registers
2. Add `standard_id` field to each register
3. Adapter automatically uses mapper to convert to standardized format
4. All registers automatically published to MQTT and HA

## 📊 Current Status

**Overall Progress: 85%**

- ✅ Core infrastructure: 100%
- ✅ Powdrive adapter: 100%
- ✅ Senergy adapter: 100%
- ✅ MQTT publishing: 100%
- ✅ HA discovery: 100%
- ✅ Smart scheduler: 100% (already using standardized names)
- ⏳ Register JSON files: 50% (need to add standard_id mappings)
- ⏳ Testing: 0% (needs verification)

## 🚀 Next Steps

1. **Add standard_id mappings to register JSON files**
   ```bash
   python scripts/add_standard_id_mappings.py register_maps/powdrive_registers.json
   ```

2. **Test end-to-end flow**
   - Verify all registers are read
   - Verify all registers are published to MQTT
   - Verify all registers appear in Home Assistant

3. **Update documentation**
   - Add examples for new device integration
   - Document migration path for existing devices

