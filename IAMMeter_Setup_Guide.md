# IAMMeter Modbus/TCP Integration Setup Guide

## Overview

The IAMMeter adapter has been integrated into the solar monitoring system to monitor grid connection and provide import/export data via Modbus/TCP protocol.

## Features

- **Real-time Grid Monitoring**: Monitors voltage, current, power, and energy
- **Bidirectional Energy Tracking**: Tracks both grid import and export
- **Daily Energy Reset**: Automatically resets daily energy counters at midnight
- **Flexible Register Mapping**: Supports custom register addresses for different IAMMeter models

## Configuration

### Basic Configuration

Add an IAMMeter device to your `config.yaml`:

```yaml
inverters:
  - id: grid_meter_1
    name: Main Grid Connection Meter
    adapter:
      type: iammeter
      transport: tcp
      host: 192.168.1.100  # IAMMeter device IP address
      port: 502            # Modbus TCP port (default: 502)
      unit_id: 1          # Modbus unit ID (default: 1)
    solar:
      - pv_dc_kw: 0  # IAMMeter doesn't have solar, set to 0
```

### Advanced Configuration (Custom Register Addresses)

If your IAMMeter model uses different register addresses, you can override the defaults:

```yaml
inverters:
  - id: grid_meter_1
    name: Main Grid Connection Meter
    adapter:
      type: iammeter
      transport: tcp
      host: 192.168.1.100
      port: 502
      unit_id: 1
      # Custom register addresses (if different from defaults)
      voltage_register: 0x0000
      voltage_scale: 10
      current_register: 0x0001
      current_scale: 100
      power_register: 0x0002
      energy_register: 0x0004
      energy_scale: 1000
      frequency_register: 0x0006
      frequency_scale: 100
      power_factor_register: 0x0007
      power_factor_scale: 1000
    solar:
      - pv_dc_kw: 0
```

## Default Register Map

The adapter uses the following default register addresses (0-based):

| Parameter | Register | Scale | Description |
|-----------|----------|-------|-------------|
| Voltage | 0x0000 | 10 | Voltage in volts (register value / 10) |
| Current | 0x0001 | 100 | Current in amperes (register value / 100) |
| Active Power | 0x0002-0x0003 | 1 | Power in watts (signed 32-bit, 2 registers) |
| Active Energy | 0x0004-0x0005 | 1000 | Energy in kWh (unsigned 32-bit, 2 registers) |
| Frequency | 0x0006 | 100 | Frequency in Hz (register value / 100) |
| Power Factor | 0x0007 | 1000 | Power factor (register value / 1000) |

**Note**: These addresses are typical for IAMMeter devices. Verify with your device's documentation as register maps may vary by model.

## Data Provided

The IAMMeter adapter provides the following telemetry data:

- **grid_power_w**: Grid power in watts (positive = import, negative = export)
- **grid_voltage_v**: Grid voltage in volts
- **grid_current_a**: Grid current in amperes
- **grid_frequency_hz**: Grid frequency in hertz
- **grid_import_wh**: Daily grid import energy in watt-hours
- **grid_export_wh**: Daily grid export energy in watt-hours
- **power_factor**: Power factor (0.0 to 1.0)

Additional metadata is stored in the `extra` field:
- `power_factor`: Power factor value
- `energy_kwh`: Cumulative energy in kWh
- `device_type`: "iammeter"
- `host`: Device IP address
- `port`: Modbus TCP port

## Integration with Energy Calculator

IAMMeter data automatically integrates with the existing energy calculation system:

1. **Real-time Monitoring**: Grid power is available in the `/api/now` endpoint
2. **Daily Aggregation**: Daily import/export energy is tracked and aggregated
3. **Billing Integration**: Grid import/export data feeds into billing calculations
4. **Dashboard Display**: Data appears in the dashboard alongside inverter data

## Troubleshooting

### Connection Issues

1. **Verify Network Connectivity**:
   ```bash
   ping 192.168.1.100  # Replace with your IAMMeter IP
   ```

2. **Check Modbus Port**:
   ```bash
   telnet 192.168.1.100 502  # Should connect if port is open
   ```

3. **Verify Modbus Unit ID**: Check your IAMMeter configuration for the correct unit ID (typically 1)

### Register Address Issues

If data values are incorrect or zero:

1. **Check Device Documentation**: Verify register addresses for your specific IAMMeter model
2. **Use Modbus Scanner**: Use a Modbus client tool to scan registers and find correct addresses
3. **Override in Config**: Update register addresses in `config.yaml` as shown in Advanced Configuration

### Daily Energy Reset

The adapter automatically tracks daily energy by:
- Detecting midnight crossover
- Calculating energy deltas between readings
- Resetting counters at the start of each day

If daily energy seems incorrect:
- Check that the device's energy register is cumulative (not resetting)
- Verify the energy_scale is correct for your device

## Testing

After configuration, verify the integration:

1. **Check Logs**: Look for connection messages:
   ```
   Connected to IAMMeter grid_meter_1 at 192.168.1.100:502
   ```

2. **Query API**: Check `/api/now?inverter_id=grid_meter_1` for telemetry data

3. **Monitor Dashboard**: IAMMeter data should appear in the dashboard grid section

## Device Setup

Before using the adapter, ensure your IAMMeter device is:

1. **Connected to Network**: Device must be on the same network as the solar hub
2. **Modbus/TCP Enabled**: Enable Modbus/TCP in the device's web interface
3. **IP Address Configured**: Note the device's IP address for configuration
4. **Port Configured**: Default Modbus TCP port is 502, verify if different

## Support

For IAMMeter-specific issues:
- Refer to IAMMeter device documentation for register maps
- Check device web interface for Modbus/TCP settings
- Verify device firmware version and compatibility

For integration issues:
- Check application logs for error messages
- Verify network connectivity and firewall settings
- Test with Modbus client tools to isolate issues

