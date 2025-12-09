# Senergy Register Scanner

A standalone utility for reading and displaying all registers from Senergy inverters. This tool helps discover missing registers and understand available data beyond the official specification.

## Features

- **Complete Register Scanning**: Read all known registers from the Senergy specification
- **Unknown Register Discovery**: Scan address ranges to find undocumented registers
- **Proper Value Conversion**: Automatic conversion based on register type and scaling
- **ASCII String Support**: Decode ASCII strings from registers
- **Flexible Configuration**: Configurable port, baudrate, and slave ID
- **Console Output**: Formatted display of register values
- **Range Scanning**: Scan specific address ranges sequentially

## Installation

### Prerequisites

```bash
pip install pymodbus pyserial
```

### Files

- `senergy_register_scanner.py` - Main scanner class
- `example_register_scan.py` - Usage examples
- `setup_scanner.py` - Setup and configuration helper

## Quick Start

### 1. Setup

```bash
python setup_scanner.py
```

This will:
- Check dependencies
- Detect available serial ports
- Create configuration file
- Provide usage instructions

### 2. Basic Usage

```bash
python senergy_register_scanner.py
```

Interactive menu options:
1. Scan all known registers
2. Scan specific register range
3. Discover unknown registers
4. Read single register

### 3. Examples

```bash
# Run example scans
python example_register_scan.py

# Discovery mode
python example_register_scan.py discover

# Help
python example_register_scan.py help
```

## Configuration

### Serial Connection

```python
# Default settings
PORT = "/dev/ttyUSB0"  # Linux
# PORT = "COM3"        # Windows
BAUDRATE = 9600
SLAVE_ID = 1
TIMEOUT = 3.0
```

### Scanning Parameters

```python
SCAN_DELAY = 0.1      # Delay between reads (seconds)
VERBOSE = True        # Detailed output
SAVE_TO_FILE = False  # Save results to file
```

## Usage Examples

### 1. Read Single Register

```python
from senergy_register_scanner import SenergyRegisterScanner

scanner = SenergyRegisterScanner(port="/dev/ttyUSB0")
await scanner.connect()

# Read Battery SOC
soc_register = await scanner.read_register(0x2000)
if soc_register:
    print(f"Battery SOC: {soc_register.value}%")

await scanner.disconnect()
```

### 2. Scan Register Range

```python
# Scan battery registers (0x2000-0x2013)
battery_registers = await scanner.scan_register_range(0x2000, 20)
```

### 3. Discover Unknown Registers

```python
# Scan for undocumented registers
unknown_registers = await scanner.discover_unknown_registers(0x0000, 0xFFFF)
```

### 4. Read All Known Registers

```python
# Scan all registers from specification
all_registers = await scanner.scan_all_known_registers()
```

## Register Information

The scanner includes all known registers from the Senergy specification:

### Device Information (0x1A00-0x1A7F)
- Device Model, Serial Number
- Firmware Versions
- Rated Parameters

### Real-time Data (0x1001-0x2013)
- Phase voltages, currents, power
- PV voltages, currents, MPPT power
- Battery SOC, voltage, current, power
- Grid and load measurements

### Parameters (0x2100-0x2121)
- Work modes, time settings
- Battery configuration
- Power limits

### Advanced Parameters (0x3000-0x6001)
- Date/time settings
- Grid protection parameters
- Reactive power control
- Inverter control

## Output Format

```
Addr   | Type | Sz | Raw Values          | Value          | Description
-------|------|----|---------------------|----------------|------------------
0x2000 | U16  |  1 | [0x005A]            | 90 %           | Battery SOC
0x2001 | S16  |  1 | [0x0019]            | 25 °C          | Battery Temperature
0x2006 | U16  |  1 | [0x01E0]            | 48.0 V         | Battery Voltage
0x2007 | S32  |  2 | [0xFFF6, 0x0000]    | -10.0 A        | Battery Current
```

## Register Types

- **U16**: Unsigned 16-bit integer
- **S16**: Signed 16-bit integer  
- **U32**: Unsigned 32-bit integer
- **S32**: Signed 32-bit integer
- **ASCII**: ASCII string (multiple registers)

## Scaling and Units

Registers are automatically scaled according to the specification:
- Voltage: 0.1V (e.g., 480 = 48.0V)
- Current: 0.01A (e.g., 1000 = 10.00A)
- Power: 0.1W (e.g., 5000 = 500.0W)
- Frequency: 0.01Hz (e.g., 5000 = 50.00Hz)

## Troubleshooting

### Connection Issues

1. **Check Port**: Ensure correct serial port
   ```bash
   # Linux
   ls /dev/ttyUSB*
   
   # Windows
   # Check Device Manager > Ports
   ```

2. **Check Baudrate**: Default is 9600, verify with inverter

3. **Check Slave ID**: Default is 1, verify with inverter

4. **Check Cable**: Ensure RS485 cable is properly connected

### Permission Issues (Linux)

```bash
# Add user to dialout group
sudo usermod -a -G dialout $USER

# Or run with sudo (not recommended)
sudo python senergy_register_scanner.py
```

### Common Errors

- **"Failed to connect"**: Check port, baudrate, and cable
- **"ModbusException"**: Check slave ID and inverter status
- **"Permission denied"**: Check serial port permissions

## Advanced Usage

### Custom Register Definitions

Add unknown registers to the `known_registers` dictionary:

```python
scanner.known_registers[0x3000] = {
    'name': 'Custom Register',
    'type': 'U16',
    'size': 1,
    'unit': 'V',
    'scale': 0.1
}
```

### Batch Processing

```python
# Read multiple registers efficiently
addresses = [0x2000, 0x2001, 0x2006, 0x2007]
results = []

for addr in addresses:
    reg_info = await scanner.read_register(addr)
    if reg_info:
        results.append(reg_info)
    await asyncio.sleep(0.1)
```

### Save Results to File

```python
# Save scan results
with open("register_scan.txt", "w") as f:
    for reg_info in results:
        f.write(f"0x{reg_info.address:04X}: {reg_info.value}\n")
```

## Contributing

To add support for new registers:

1. Add register definition to `known_registers` dictionary
2. Include proper type, size, unit, and scale
3. Test with actual inverter
4. Update documentation

## License

This tool is provided as-is for educational and diagnostic purposes. Use at your own risk.

## Support

For issues or questions:
1. Check troubleshooting section
2. Verify inverter connection and settings
3. Test with known working registers first
4. Check inverter documentation for specific model differences
