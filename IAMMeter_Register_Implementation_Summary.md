# IAMMeter Register Implementation Summary

## Status: ✅ FULLY IMPLEMENTED

All 47 registers from the IAMMeter register map JSON file are now being read and published.

## Implementation Details

### 1. Register Map Loading
- ✅ Adapter now uses `JsonRegisterMixin` to load register map from JSON
- ✅ Automatically loads `register_maps/iammeter_registers.json` if available
- ✅ Supports custom register map file via `register_map_file` config option
- ✅ Falls back to legacy hardcoded registers if JSON not available

### 2. Register Reading
- ✅ Implements `_read_holding_regs()` method for Modbus/TCP
- ✅ Uses `read_all_registers()` from JsonRegisterMixin to read all registers
- ✅ Reads all 47 registers from JSON map:
  - Serial number (address 0x38)
  - Phase A, B, C voltages, currents, powers
  - Forward/reverse energy for each phase
  - Power factors
  - Power direction indicators
  - Total energy
  - Reactive power and energy
  - Frequency

### 3. Data Publication
- ✅ All register values are included in telemetry `extra["registers"]` field
- ✅ Key values (voltage, current, power, energy, frequency, power factor) are extracted for Telemetry object fields
- ✅ Three-phase data is available in the registers dictionary
- ✅ Reactive power and energy data is available in the registers dictionary

### 4. Backward Compatibility
- ✅ Falls back to legacy register reading if JSON map not loaded
- ✅ Maintains compatibility with existing configurations
- ✅ Legacy register addresses still supported

## Register Map Contents

The JSON register map (`register_maps/iammeter_registers.json`) contains:

1. **Serial Number** (Address 0x38, 8 registers)
2. **Phase A Registers** (Addresses 0x48-0x50):
   - Voltage, Current, Active Power
   - Active Energy Forward/Reverse
   - Power Factor
   - Power Direction Indicator
3. **Phase B Registers** (Addresses 0x51-0x59)
4. **Phase C Registers** (Addresses 0x5A-0x62)
5. **Total/System Registers** (Addresses 0x63-0x67):
   - Total Active Energy Forward/Reverse
   - Frequency
6. **Alternative Energy Registers** (Addresses 0x68-0x77)
7. **Power Registers** (Addresses 0x78-0x7F):
   - Total Power (Signed)
   - Phase A/B/C Power (Signed)
8. **Reactive Power Registers** (Addresses 0x80-0x85)
9. **Reactive Energy Registers** (Addresses 0x86-0x91)

## Usage

### Configuration

To use the full register map, configure the adapter with:

```yaml
inverters:
  - id: grid_meter_1
    name: Main Grid Meter
    adapter:
      type: iammeter
      host: 192.168.1.100
      port: 502
      unit_id: 1
      register_map_file: register_maps/iammeter_registers.json  # Optional, auto-loaded if not specified
```

### Accessing Register Data

All register values are available in the telemetry `extra["registers"]` field:

```python
telemetry = await adapter.poll()
all_registers = telemetry.extra.get("registers", {})
voltage_phase_a = all_registers.get("voltage_phase_a")
current_phase_b = all_registers.get("current_phase_b")
reactive_power_phase_c = all_registers.get("reactive_power_phase_c")
# ... etc
```

### Key Telemetry Fields

The adapter extracts key values for standard Telemetry fields:
- `grid_voltage_v`: Phase A voltage (or legacy voltage)
- `grid_current_a`: Phase A current (or legacy current)
- `grid_power_w`: Total power (or legacy power)
- `grid_frequency_hz`: Frequency
- `grid_import_wh`: Daily import energy
- `grid_export_wh`: Daily export energy

All other register values are available in `extra["registers"]`.

## Testing

To verify all registers are being read:

1. Check logs for: `"Read X registers from JSON map"`
2. Check telemetry `extra["registers"]` field contains all register IDs
3. Verify register values match expected ranges

## Notes

- Register reading uses proper scaling factors from JSON map
- Model-specific scaling (WEM3080T vs WEM3046T) is documented in register comments
- Failed register reads are logged but don't stop other registers from being read
- All registers are read in a single `read_all_registers()` call for efficiency

