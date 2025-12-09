#!/usr/bin/env python3
"""
Demo script for Senergy Register Scanner

This script demonstrates the scanner functionality without requiring
a physical inverter connection.
"""

import asyncio
import sys
from senergy_register_scanner import SenergyRegisterScanner, RegisterInfo

class MockModbusClient:
    """Mock Modbus client for demonstration purposes."""
    
    def __init__(self):
        self.is_open = True
        # Mock register data
        self.mock_data = {
            0x2000: [90],      # Battery SOC: 90%
            0x2001: [25],      # Battery Temperature: 25°C
            0x2006: [480],     # Battery Voltage: 48.0V
            0x2007: [0xFFFF, 0xFFF6],   # Battery Current: -10.0A (discharging) - S32
            0x2009: [0x12C0, 0x0000],   # Battery Power: 4800 (480.0W) - U32
            0x1010: [450],     # PV1 Voltage: 45.0V
            0x1011: [800],     # PV1 Current: 8.0A
            0x1012: [0x0E10, 0x0000],   # MPPT1 Power: 3600 (360.0W) - U32
            0x1037: [0x1388, 0x0000],   # Active Power: 5000 (500.0W) - S32
            0x1A00: [0x5056, 0x2D33, 0x302D, 0x4F4E, 0x5958, 0x2D55, 0x4C2D, 0x364B, 0x0057],  # "PV-ONYX-UL-6KW"
            0x1A10: [0x3132, 0x3334, 0x2D31, 0x3233, 0x3435, 0x3637, 0x3839, 0x5048],  # "1234-123456789PH"
        }
    
    def connect(self):
        return True
    
    def is_socket_open(self):
        return self.is_open
    
    def read_holding_registers(self, address, count, slave=None):
        """Mock read holding registers."""
        class MockResult:
            def __init__(self, registers):
                self.registers = registers
                self.isError = lambda: False
        
        # Return mock data if available, otherwise zeros
        if address in self.mock_data:
            return MockResult(self.mock_data[address][:count])
        else:
            return MockResult([0] * count)
    
    def close(self):
        self.is_open = False

class DemoScanner(SenergyRegisterScanner):
    """Demo scanner with mock client."""
    
    def __init__(self):
        super().__init__()
        self.client = MockModbusClient()
    
    async def connect(self):
        """Mock connection."""
        print("🔌 [DEMO] Connected to mock inverter")
        return True
    
    async def disconnect(self):
        """Mock disconnection."""
        print("🔌 [DEMO] Disconnected from mock inverter")

async def demo_basic_scanning():
    """Demonstrate basic register scanning."""
    print("🚀 Senergy Register Scanner - DEMO MODE")
    print("=" * 50)
    
    scanner = DemoScanner()
    
    try:
        await scanner.connect()
        
        print("\n📊 DEMO 1: Reading Battery Registers")
        print("-" * 40)
        scanner.print_header()
        
        # Read battery-related registers
        battery_registers = [0x2000, 0x2001, 0x2006, 0x2007, 0x2009]
        for addr in battery_registers:
            reg_info = await scanner.read_register(addr)
            if reg_info:
                scanner._print_register(reg_info)
            await asyncio.sleep(0.1)
        
        print("\n📊 DEMO 2: Reading PV Registers")
        print("-" * 40)
        
        pv_registers = [0x1010, 0x1011, 0x1012]
        for addr in pv_registers:
            reg_info = await scanner.read_register(addr)
            if reg_info:
                scanner._print_register(reg_info)
            await asyncio.sleep(0.1)
        
        print("\n📊 DEMO 3: Reading Device Information")
        print("-" * 40)
        
        device_registers = [0x1A00, 0x1A10]
        for addr in device_registers:
            reg_info = await scanner.read_register(addr)
            if reg_info:
                scanner._print_register(reg_info)
            await asyncio.sleep(0.1)
        
        print("\n📊 DEMO 4: Reading Power Data")
        print("-" * 40)
        
        power_register = await scanner.read_register(0x1037)
        if power_register:
            scanner._print_register(power_register)
        
        print("\n✅ Demo completed successfully!")
        print("\n💡 To use with a real inverter:")
        print("   1. Connect your inverter via RS485")
        print("   2. Run: python senergy_register_scanner.py")
        print("   3. Or run: python example_register_scan.py")
        
    except Exception as e:
        print(f"❌ Demo error: {e}")
    
    finally:
        await scanner.disconnect()

async def demo_register_range_scanning():
    """Demonstrate register range scanning."""
    print("\n🔍 DEMO: Register Range Scanning")
    print("=" * 40)
    
    scanner = DemoScanner()
    
    try:
        await scanner.connect()
        
        # Scan a range of registers
        print("Scanning battery register range (0x2000-0x2009)...")
        results = await scanner.scan_register_range(0x2000, 10)
        
        print(f"\nFound {len(results)} registers with data")
        
        # Show summary
        print("\n📋 Summary:")
        for reg in results:
            if reg.value is not None:
                print(f"  0x{reg.address:04X}: {reg.value} {reg.unit}")
    
    except Exception as e:
        print(f"❌ Demo error: {e}")
    
    finally:
        await scanner.disconnect()

def demo_register_conversion():
    """Demonstrate register value conversion."""
    print("\n🔧 DEMO: Register Value Conversion")
    print("=" * 40)
    
    scanner = DemoScanner()
    
    # Test different data types
    test_cases = [
        ([90], 'U16', 1.0, '', 'Battery SOC'),
        ([480], 'U16', 0.1, 'V', 'Battery Voltage'),
        ([0xFFFF, 0xFFF6], 'S32', 0.01, 'A', 'Battery Current'),
        ([0x5056, 0x2D33], 'U16', 1.0, 'ASCII', 'Device Model'),
    ]
    
    print("Testing value conversion:")
    for raw_values, data_type, scale, unit, description in test_cases:
        value = scanner._convert_register_value(raw_values, data_type, scale, unit)
        print(f"  {description}: {raw_values} -> {value} {unit}")
    
    print("\n✅ Conversion demo completed!")

def print_usage_info():
    """Print usage information."""
    print("\n📖 USAGE INFORMATION")
    print("=" * 30)
    print()
    print("Real Usage:")
    print("  python senergy_register_scanner.py")
    print("  python example_register_scan.py")
    print("  python setup_scanner.py")
    print()
    print("Demo Mode:")
    print("  python test_scanner_demo.py")
    print("  python test_scanner_demo.py range")
    print("  python test_scanner_demo.py conversion")
    print()
    print("Configuration:")
    print("  - Edit PORT in the script for your setup")
    print("  - Default: /dev/ttyUSB0 (Linux) or COM3 (Windows)")
    print("  - Baudrate: 9600, Slave ID: 1")
    print()

async def main():
    """Main demo function."""
    if len(sys.argv) > 1:
        if sys.argv[1] == "range":
            await demo_register_range_scanning()
        elif sys.argv[1] == "conversion":
            demo_register_conversion()
        elif sys.argv[1] == "help":
            print_usage_info()
        else:
            print("Unknown option. Use 'help' for usage information.")
    else:
        await demo_basic_scanning()
        demo_register_conversion()
        print_usage_info()

if __name__ == "__main__":
    asyncio.run(main())
