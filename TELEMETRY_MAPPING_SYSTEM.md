# Telemetry Mapping System

This document describes the standardized telemetry mapping system that ensures consistent field names across all devices, smart scheduler, API server, and Home Assistant publishing.

## Overview

The telemetry mapping system provides a layer of abstraction between device-specific register names and standardized field names used throughout the system. This ensures:

1. **Consistency**: All devices use the same field names internally
2. **Maintainability**: Changes to device adapters don't affect higher layers
3. **Extensibility**: Easy to add new devices without changing smart scheduler or API
4. **Clarity**: Clear separation between device-specific and standardized data

## Architecture

### Components

1. **StandardFields** (`solarhub/telemetry_mapper.py`): Defines all standardized field names
2. **TelemetryMapper**: Maps device-specific field names to standardized names
3. **Register JSON Files**: Define device-specific registers with optional `standard_id` mappings
4. **Device Adapters**: Use the mapper to convert device data to standardized format

### Data Flow

```
Device Register → Device-Specific Name → TelemetryMapper → Standardized Name → Smart Scheduler/API/HA
```

## Standard Field Names

All standardized field names are defined in `solarhub/telemetry_mapper.py` in the `StandardFields` class. See `register_maps/STANDARD_FIELD_NAMES.md` for the complete list.

### Naming Convention

- **Power**: `*_power_w` (watts)
- **Voltage**: `*_voltage_v` (volts)
- **Current**: `*_current_a` (amperes)
- **Temperature**: `*_temp_c` (celsius)
- **Percentage**: `*_pct` (percent)
- **Frequency**: `*_frequency_hz` (hertz)
- **Energy**: `today_*_energy` or `total_*_energy` (kWh)
- **Time**: `*_time` (ISO 8601 format)

## Register JSON Format

Each register in the JSON file can include a `standard_id` field that maps to a standardized field name:

```json
{
  "id": "device_specific_name",
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

### Mapping Rules

1. If `standard_id` is provided, it is used as the standardized field name
2. If `standard_id` is not provided, the register `id` is used as-is (for backward compatibility)
3. The mapper automatically handles common device-specific name variations

## Usage

### In Device Adapters

```python
from solarhub.telemetry_mapper import TelemetryMapper

class MyAdapter(InverterAdapter, JsonRegisterMixin):
    def __init__(self, inv):
        super().__init__(inv)
        # Load register map
        self.load_register_map("register_maps/my_device.json")
        
        # Create mapper
        self.mapper = TelemetryMapper(self.regs)
    
    async def poll(self) -> Telemetry:
        # Read all registers
        device_data = await self.read_all_registers()
        
        # Map to standardized names
        standardized_data = self.mapper.map_to_standard(device_data)
        
        # Use standardized_data for Telemetry object
        # ...
```

### Reading All Registers

The `JsonRegisterMixin` now includes a `read_all_registers()` method that reads all registers from the register map:

```python
# Read all registers from register map
device_data = await self.read_all_registers()
```

This ensures all registers defined in the JSON file are read from the device.

## Adding Standard ID Mappings

### Manual Method

Edit the register JSON file and add `standard_id` fields:

```json
{
  "id": "battery_voltage",
  "standard_id": "batt_voltage_v",
  ...
}
```

### Automated Method

Use the provided script to add standard_id mappings:

```bash
python scripts/add_standard_id_mappings.py register_maps/powdrive_registers.json
```

This script:
1. Loads the register JSON file
2. Attempts to map each register `id` to a standard field name
3. Adds `standard_id` fields where mappings are found
4. Saves the updated JSON file

## Benefits

### For Smart Scheduler

The smart scheduler can now use standardized field names without knowing device-specific details:

```python
# Works for all devices
pv_power = telemetry.extra.get("pv_power_w")
load_power = telemetry.extra.get("load_power_w")
batt_soc = telemetry.extra.get("batt_soc_pct")
```

### For API Server

The API server can use standardized field names when normalizing telemetry data:

```python
# Normalize using standardized names
normalized = {
    "pv_power_w": tel.get("pv_power_w") or extra.get("pv_power_w"),
    "load_power_w": tel.get("load_power_w") or extra.get("load_power_w"),
    # ...
}
```

### For Home Assistant

Home Assistant publishing can use standardized field names for consistent entity names:

```python
# Publish with standardized names
ha_payload = {
    "pv_power_w": telemetry.extra.get("pv_power_w"),
    "load_power_w": telemetry.extra.get("load_power_w"),
    # ...
}
```

## Migration Guide

### For Existing Adapters

1. Update register JSON files to include `standard_id` mappings (use the script)
2. Update adapter `__init__` to create a `TelemetryMapper` instance
3. Update `poll()` method to:
   - Read all registers using `read_all_registers()`
   - Map device data to standardized format using `mapper.map_to_standard()`
   - Use standardized field names when creating Telemetry object

### For New Adapters

1. Create register JSON file with all device registers
2. Add `standard_id` fields to map to standard field names
3. Use `TelemetryMapper` in adapter to convert device data
4. Use `read_all_registers()` to read all registers from device

## Example: Powdrive Adapter

The Powdrive adapter has been updated to use the mapping system:

1. **Register Map**: `register_maps/powdrive_registers.json` includes all registers
2. **Mapper**: Created in `__init__` using `TelemetryMapper(self.regs)`
3. **Poll Method**: 
   - Reads all registers using `read_all_registers()`
   - Maps to standardized format using `mapper.map_to_standard()`
   - Uses standardized field names throughout

## Future Enhancements

1. **Automatic Mapping**: Enhance the mapping script to better detect standard field names
2. **Validation**: Add validation to ensure all required standard fields are present
3. **Documentation**: Auto-generate documentation from register JSON files
4. **Testing**: Add unit tests for mapping functionality

## See Also

- `register_maps/STANDARD_FIELD_NAMES.md`: Complete list of standard field names
- `solarhub/telemetry_mapper.py`: Implementation of mapping system
- `scripts/add_standard_id_mappings.py`: Script to add standard_id mappings

