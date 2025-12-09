# IAMMeter Register Map Implementation Status

## Summary

**Current Status**: ⚠️ **PARTIALLY IMPLEMENTED**

**Serial Number Support**: ✅ **IMPLEMENTED** (Address 0x38, 8 registers)

The current IAMMeter adapter (`solarhub/adapters/iammeter.py`) only implements a **basic subset** of registers (approximately 6-7 registers), while the full IAMMeter specification includes **46 registers** starting at address 0x0048 (72 decimal).

## Current Implementation

The current adapter only reads:
- Basic voltage (register 0x0000) - **NOT in specification**
- Basic current (register 0x0001) - **NOT in specification**
- Basic power (register 0x0002) - **NOT in specification**
- Basic energy (register 0x0004) - **NOT in specification**
- Frequency (register 0x0006) - **NOT in specification**
- Power Factor (register 0x0007) - **NOT in specification**

**Note**: The current implementation uses registers 0x0000-0x0007, which are **NOT** part of the specification you provided (which starts at 0x0048).

## Required Implementation (46 Registers)

Based on the specification provided, the following registers need to be implemented:

### Phase A Registers (0x0048-0x0050)
- ✅ Register 0x0048: Voltage of Phase A
- ✅ Register 0x0049: Current of Phase A
- ✅ Register 0x004A: Active Power of Phase A
- ✅ Register 0x004B-0x004C: Active Energy (Forward) Phase A
- ✅ Register 0x004D: Power Factor of Phase A
- ✅ Register 0x004E-0x004F: Active Energy (Reverse) Phase A
- ✅ Register 0x0050: Power Direction Indicator Phase A

### Phase B Registers (0x0051-0x0059)
- ✅ Register 0x0051: Voltage of Phase B
- ✅ Register 0x0052: Current of Phase B
- ✅ Register 0x0053: Active Power of Phase B
- ✅ Register 0x0054-0x0055: Active Energy (Forward) Phase B
- ✅ Register 0x0056: Power Factor of Phase B
- ✅ Register 0x0057-0x0058: Active Energy (Reverse) Phase B
- ✅ Register 0x0059: Power Direction Indicator Phase B

### Phase C Registers (0x005A-0x0062)
- ✅ Register 0x005A: Voltage of Phase C
- ✅ Register 0x005B: Current of Phase C
- ✅ Register 0x005C: Active Power of Phase C
- ✅ Register 0x005D-0x005E: Active Energy (Forward) Phase C
- ✅ Register 0x005F: Power Factor of Phase C
- ✅ Register 0x0060-0x0061: Active Energy (Reverse) Phase C
- ✅ Register 0x0062: Power Direction Indicator Phase C

### Total/System Registers
- ✅ Register 0x0063-0x0064: Total Active Energy (Forward)
- ✅ Register 0x0065: Frequency
- ✅ Register 0x0066-0x0067: Total Active Energy (Reverse)

### Alternative Energy Registers (0x0068-0x0077)
- ✅ Register 0x0068-0x0069: Active Energy Phase A (Forward) Alternative
- ✅ Register 0x006A-0x006B: Active Energy Phase A (Reverse) Alternative
- ✅ Register 0x006C-0x006D: Active Energy Phase B (Forward) Alternative
- ✅ Register 0x006E-0x006F: Active Energy Phase B (Reverse) Alternative
- ✅ Register 0x0070-0x0071: Active Energy Phase C (Forward) Alternative
- ✅ Register 0x0072-0x0073: Active Energy Phase C (Reverse) Alternative
- ✅ Register 0x0074-0x0075: Total Active Energy (Forward) Alternative
- ✅ Register 0x0076-0x0077: Total Active Energy (Reverse) Alternative

### Power Registers (0x0078-0x007F)
- ✅ Register 0x0078-0x0079: Total Power (Signed)
- ✅ Register 0x007A-0x007B: Active Power Phase A (Signed)
- ✅ Register 0x007C-0x007D: Active Power Phase B (Signed)
- ✅ Register 0x007E-0x007F: Active Power Phase C (Signed)

### Reactive Power Registers (0x0080-0x0085)
- ✅ Register 0x0080-0x0081: Reactive Power Phase A
- ✅ Register 0x0082-0x0083: Reactive Power Phase B
- ✅ Register 0x0084-0x0085: Reactive Power Phase C

### Reactive Energy Registers (0x0086-0x0091)
- ✅ Register 0x0086-0x0087: Forward Reactive Energy (Inductive) Phase A
- ✅ Register 0x0088-0x0089: Reverse Reactive Energy (Capacitive) Phase A
- ✅ Register 0x008A-0x008B: Forward Reactive Energy (Inductive) Phase B
- ✅ Register 0x008C-0x008D: Reverse Reactive Energy (Capacitive) Phase B
- ✅ Register 0x008E-0x008F: Forward Reactive Energy (Inductive) Phase C
- ✅ Register 0x0090-0x0091: Reverse Reactive Energy (Capacitive) Phase C

## Register Map JSON File Created

✅ **Created**: `register_maps/iammeter_registers.json`

This file contains all 46 registers from the specification PLUS serial number register with:
- ✅ Serial Number register (Address 0x38, 8 registers, ASCII encoded)
- Correct addresses (0x0048-0x0091 for measurement registers)
- Proper data types (U16, U32, S32, string)
- Correct scaling factors
- Model-specific notes (WEM3080T vs WEM3046T)

## Serial Number Implementation

✅ **Implemented**: Serial number reading from Modbus register 0x38 (56 decimal)
- Address: 0x38 (hexadecimal) / 56 (decimal)
- Size: 8 registers (16 bytes)
- Format: ASCII encoded string
- Function Code: 03 (Read Holding Registers)
- Implementation: `read_serial_number()` method in `IAMMeterAdapter`
- Connectivity Check: Updated `check_connectivity()` to use serial number register as primary check

## Next Steps

To fully implement all registers, the IAMMeter adapter needs to be refactored to:

1. **Use JsonRegisterMixin** (like SenergyAdapter and PowdriveAdapter)
   - Load register map from JSON file
   - Use `read_all_registers()` method to read all registers
   - Map device-specific fields to standardized telemetry fields

2. **Support Modbus/TCP** (current implementation already uses TCP)
   - Ensure ModbusClientMixin supports TCP or implement TCP-specific methods
   - Use `_read_holding_regs()` method for register reading

3. **Update poll() method**
   - Read all registers from the JSON map
   - Parse three-phase data (Phase A, B, C)
   - Include reactive power and energy
   - Map to Telemetry model fields

4. **Update Telemetry model** (if needed)
   - Ensure support for three-phase voltages, currents, powers
   - Support reactive power and energy fields
   - Support per-phase energy tracking

## Recommendation

The register map JSON file has been created with all 46 registers. The adapter should be refactored to use `JsonRegisterMixin` pattern similar to `SenergyAdapter` to automatically read and parse all registers from the JSON file.

