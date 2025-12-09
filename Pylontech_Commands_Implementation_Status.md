# Pylontech Console Commands Implementation Status

Based on the [ioBroker.pylontech repository](https://github.com/PLCHome/ioBroker.pylontech/tree/master/src), here's the status of console command implementations:

## ✅ Implemented Commands

1. **`pwr N`** - Power/Status command for battery unit N
   - Returns voltage, current, temperature, SOC, status flags
   - Used in `poll()` method for regular telemetry collection
   - Status: ✅ Fully implemented

2. **`bat N`** - Detailed battery information for unit N
   - Returns per-cell data (voltage, current, temperature, SOC per cell)
   - Used in `poll()` method for cell-level telemetry
   - Status: ✅ Fully implemented

3. **`info`** - Device information command
   - Returns device details including serial number (Barcode), firmware versions, specifications
   - Used in `read_serial_number()` method
   - Status: ✅ Just implemented

## ❌ Missing Commands

### High Priority (Useful for Monitoring)

1. **`soh N`** - State of Health command
   - Purpose: Returns State of Health percentage for battery unit N
   - Use case: Battery health monitoring, degradation tracking
   - Implementation: Should return SOH percentage (0-100%)

2. **`stat`** or **`status`** - System status command
   - Purpose: Returns overall system status, alarms, warnings
   - Use case: System health monitoring, fault detection
   - Implementation: Should parse status flags and alarm conditions

3. **`log`** - Event log command
   - Purpose: Retrieves event/fault logs from battery
   - Use case: Troubleshooting, historical fault analysis
   - Implementation: Should parse log entries with timestamps

### Medium Priority (Configuration/System)

4. **`unit N`** - Unit-specific information
   - Purpose: May return unit-specific configuration or status
   - Use case: Unit identification, configuration verification
   - Implementation: May overlap with `info` command

5. **`sysinfo`** - System information
   - Purpose: System-level information (may differ from `info`)
   - Use case: System configuration, network settings
   - Implementation: Should parse system-level parameters

### Low Priority (Time Synchronization)

6. **`time`** - Time synchronization command
   - Purpose: Set/get device time
   - Use case: Time synchronization for log timestamps
   - Implementation: Read/write time commands

## Implementation Recommendations

### Priority 1: `soh` Command
- **Why**: State of Health is critical for battery monitoring
- **Usage**: Can be called periodically (less frequent than `pwr`)
- **Integration**: Add to `BatteryUnit` model and telemetry

### Priority 2: `stat`/`status` Command
- **Why**: System status helps with fault detection
- **Usage**: Can be called during `poll()` or separately
- **Integration**: Add to telemetry `extra` field or separate status endpoint

### Priority 3: `log` Command
- **Why**: Event logs help with troubleshooting
- **Usage**: Can be called on-demand or periodically
- **Integration**: Store in separate log storage, expose via API

## Command Format Reference

Based on Pylontech console protocol:
- Commands are sent as ASCII strings with newline (`\n`)
- Responses are line-oriented text
- Commands end with "Command completed successfully" marker
- Typical timeout: 1-2 seconds per command

## Next Steps

1. Implement `soh` command for State of Health monitoring
2. Implement `stat` command for system status
3. Add optional `log` command support for troubleshooting
4. Test all commands with actual Pylontech hardware

