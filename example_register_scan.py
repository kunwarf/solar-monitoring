#!/usr/bin/env python3
"""
Example usage of the Senergy Register Scanner

This script demonstrates how to use the SenergyRegisterScanner class
to read and display inverter register values.
"""

import asyncio
import sys
from senergy_register_scanner import SenergyRegisterScanner, CustomRegisterRequest

async def example_usage():
    """Example usage of the register scanner."""
    
    # Configuration - adjust these for your setup
    PORT = "/dev/ttyUSB0"  # Change to your port (e.g., "COM3" on Windows)
    BAUDRATE = 9600
    SLAVE_ID = 1
    
    # Create scanner instance
    scanner = SenergyRegisterScanner(port=PORT, baudrate=BAUDRATE, slave_id=SLAVE_ID)
    
    try:
        # Connect to inverter
        print("Connecting to inverter...")
        if not await scanner.connect():
            print("❌ Failed to connect to inverter")
            print("Please check your connection settings:")
            print(f"  Port: {PORT}")
            print(f"  Baudrate: {BAUDRATE}")
            print(f"  Slave ID: {SLAVE_ID}")
            return
        
        print("✅ Connected to inverter successfully!")
        
        # Example 1: Read a single register (Battery SOC)
        print("\n" + "="*60)
        print("EXAMPLE 1: Reading Battery SOC (0x2000)")
        print("="*60)
        soc_register = await scanner.read_register(0x2000)
        if soc_register:
            scanner._print_register(soc_register)
        else:
            print("Failed to read Battery SOC register")
        
        # Example 2: Read battery-related registers
        print("\n" + "="*60)
        print("EXAMPLE 2: Reading Battery Registers (0x2000-0x2013)")
        print("="*60)
        battery_registers = [0x2000, 0x2001, 0x2006, 0x2007, 0x2009, 0x200B, 0x200D, 0x200F, 0x2011]
        for addr in battery_registers:
            reg_info = await scanner.read_register(addr)
            if reg_info:
                scanner._print_register(reg_info)
            await asyncio.sleep(0.1)
        
        # Example 3: Scan a range of registers
        print("\n" + "="*60)
        print("EXAMPLE 3: Scanning PV Registers (0x1010-0x101F)")
        print("="*60)
        pv_registers = await scanner.scan_register_range(0x1010, 16)
        print(f"Found {len(pv_registers)} PV-related registers")
        
        # Example 4: Read device information
        print("\n" + "="*60)
        print("EXAMPLE 4: Device Information Registers")
        print("="*60)
        device_registers = [0x1A00, 0x1A10, 0x1A18, 0x1A44, 0x1A45, 0x1A46, 0x1A48]
        for addr in device_registers:
            reg_info = await scanner.read_register(addr)
            if reg_info:
                scanner._print_register(reg_info)
            await asyncio.sleep(0.1)
        
        # Example 5: Read real-time power data
        print("\n" + "="*60)
        print("EXAMPLE 5: Real-time Power Data")
        print("="*60)
        power_registers = [0x1037, 0x1039, 0x1300, 0x1302, 0x1304, 0x130A, 0x130C, 0x130E]
        for addr in power_registers:
            reg_info = await scanner.read_register(addr)
            if reg_info:
                scanner._print_register(reg_info)
            await asyncio.sleep(0.1)
        
        print("\n" + "="*60)
        print("✅ All examples completed successfully!")
        print("="*60)
        
    except KeyboardInterrupt:
        print("\n⚠️  Scanning interrupted by user")
    
    except Exception as e:
        print(f"❌ Error: {e}")
    
    finally:
        await scanner.disconnect()
        print("🔌 Disconnected from inverter")

async def scan_all_known_registers():
    """Scan all known registers from the specification."""
    
    PORT = "/dev/ttyUSB0"  # Change to your port
    BAUDRATE = 9600
    SLAVE_ID = 1
    
    scanner = SenergyRegisterScanner(port=PORT, baudrate=BAUDRATE, slave_id=SLAVE_ID)
    
    try:
        if not await scanner.connect():
            print("❌ Failed to connect to inverter")
            return
        
        print("📊 Starting comprehensive scan of all known registers...")
        print("This will scan all registers documented in the Senergy specification.")
        print("It may take a few minutes to complete.")
        
        # Scan all known registers
        all_registers = await scanner.scan_all_known_registers()
        
        print(f"\n🎯 Scan complete! Successfully read {len(all_registers)} known registers")
        
        # Group registers by category for summary
        categories = {
            "Device Information": [],
            "Real-time Data": [],
            "Battery Data": [],
            "PV Data": [],
            "Grid Data": [],
            "Load Data": [],
            "Parameters": [],
            "Advanced Parameters": [],
            "Other": []
        }
        
        for reg in all_registers:
            addr = reg.address
            if 0x1A00 <= addr <= 0x1A7F:
                categories["Device Information"].append(reg)
            elif 0x1001 <= addr <= 0x2013:
                if 0x2000 <= addr <= 0x2013:
                    categories["Battery Data"].append(reg)
                elif 0x1010 <= addr <= 0x1040:
                    categories["PV Data"].append(reg)
                elif 0x1300 <= addr <= 0x1338:
                    categories["Grid Data"].append(reg)
                elif 0x1350 <= addr <= 0x1362:
                    categories["Load Data"].append(reg)
                else:
                    categories["Real-time Data"].append(reg)
            elif 0x2100 <= addr <= 0x2121:
                categories["Parameters"].append(reg)
            elif 0x3000 <= addr <= 0x6001:
                categories["Advanced Parameters"].append(reg)
            else:
                categories["Other"].append(reg)
        
        # Print summary by category
        print("\n📋 Register Summary by Category:")
        print("-" * 50)
        for category, registers in categories.items():
            if registers:
                print(f"\n{category} ({len(registers)} registers):")
                for reg in registers[:5]:  # Show first 5 registers
                    value_str = str(reg.value)
                    if len(value_str) > 20:
                        value_str = value_str[:17] + "..."
                    print(f"  0x{reg.address:04X}: {value_str} {reg.unit}")
                if len(registers) > 5:
                    print(f"  ... and {len(registers) - 5} more registers")
        
        # Save results to file
        filename = "all_registers_scan_results.txt"
        with open(filename, "w") as f:
            f.write("Senergy Inverter - All Known Registers Scan Results\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Scan completed: {len(all_registers)} registers read\n\n")
            
            for category, registers in categories.items():
                if registers:
                    f.write(f"\n{category} ({len(registers)} registers):\n")
                    f.write("-" * 40 + "\n")
                    for reg in registers:
                        f.write(f"0x{reg.address:04X} | {reg.data_type} | {reg.size} | {reg.value} {reg.unit} | {reg.description}\n")
        
        print(f"\n💾 Results saved to: {filename}")
    
    except Exception as e:
        print(f"❌ Error during scan: {e}")
    
    finally:
        await scanner.disconnect()

async def discover_unknown_registers():
    """Example of discovering unknown registers."""
    
    PORT = "/dev/ttyUSB0"  # Change to your port
    BAUDRATE = 9600
    SLAVE_ID = 1
    
    scanner = SenergyRegisterScanner(port=PORT, baudrate=BAUDRATE, slave_id=SLAVE_ID)
    
    try:
        if not await scanner.connect():
            print("❌ Failed to connect to inverter")
            return
        
        print("🔍 Starting unknown register discovery...")
        print("This will scan for registers not in the specification.")
        print("It may take several minutes to complete.")
        
        # Ask user for scan range
        print("\nSelect discovery range:")
        print("1. Quick scan (0x3000-0x3FFF) - ~5 minutes")
        print("2. Medium scan (0x0000-0x7FFF) - ~15 minutes")
        print("3. Full scan (0x0000-0xFFFF) - ~30 minutes")
        print("4. Custom range")
        
        try:
            choice = input("Enter choice (1-4): ").strip()
            
            if choice == "1":
                start_addr, end_addr = 0x3000, 0x3FFF
            elif choice == "2":
                start_addr, end_addr = 0x0000, 0x7FFF
            elif choice == "3":
                start_addr, end_addr = 0x0000, 0xFFFF
            elif choice == "4":
                start_addr = int(input("Enter start address (hex, e.g., 0x0000): "), 16)
                end_addr = int(input("Enter end address (hex, e.g., 0xFFFF): "), 16)
            else:
                print("Invalid choice, using quick scan")
                start_addr, end_addr = 0x3000, 0x3FFF
        except (ValueError, KeyboardInterrupt):
            print("Invalid input, using quick scan")
            start_addr, end_addr = 0x3000, 0x3FFF
        
        print(f"\n🔍 Scanning range: 0x{start_addr:04X} to 0x{end_addr:04X}")
        
        unknown_registers = await scanner.discover_unknown_registers(start_addr, end_addr)
        
        print(f"\n🎯 Discovery complete! Found {len(unknown_registers)} unknown registers with data")
        
        if unknown_registers:
            print("\n📋 Summary of unknown registers:")
            for reg in unknown_registers:
                value_str = str(reg.value)
                if len(value_str) > 30:
                    value_str = value_str[:27] + "..."
                print(f"  0x{reg.address:04X}: {value_str} ({reg.data_type})")
            
            # Save unknown registers to file
            filename = "unknown_registers_discovery.txt"
            with open(filename, "w") as f:
                f.write("Senergy Inverter - Unknown Registers Discovery\n")
                f.write("=" * 50 + "\n\n")
                f.write(f"Scan range: 0x{start_addr:04X} to 0x{end_addr:04X}\n")
                f.write(f"Found: {len(unknown_registers)} unknown registers with data\n\n")
                
                for reg in unknown_registers:
                    f.write(f"0x{reg.address:04X} | {reg.data_type} | {reg.size} | {reg.raw_value} | {reg.value}\n")
            
            print(f"\n💾 Unknown registers saved to: {filename}")
        else:
            print("No unknown registers with data found in the specified range.")
    
    except Exception as e:
        print(f"❌ Error during discovery: {e}")
    
    finally:
        await scanner.disconnect()

async def comprehensive_scan():
    """Perform a comprehensive scan of all registers."""
    
    PORT = "/dev/ttyUSB0"  # Change to your port
    BAUDRATE = 9600
    SLAVE_ID = 1
    
    scanner = SenergyRegisterScanner(port=PORT, baudrate=BAUDRATE, slave_id=SLAVE_ID)
    
    try:
        if not await scanner.connect():
            print("❌ Failed to connect to inverter")
            return
        
        print("🚀 Starting comprehensive register scan...")
        print("This will perform both known and unknown register discovery.")
        print("It may take 30-45 minutes to complete.")
        
        # Step 1: Scan all known registers
        print("\n📊 Step 1: Scanning all known registers...")
        known_registers = await scanner.scan_all_known_registers()
        print(f"✅ Found {len(known_registers)} known registers")
        
        # Step 2: Discover unknown registers
        print("\n🔍 Step 2: Discovering unknown registers...")
        print("Scanning full address space (0x0000-0xFFFF)...")
        unknown_registers = await scanner.discover_unknown_registers(0x0000, 0xFFFF)
        print(f"✅ Found {len(unknown_registers)} unknown registers")
        
        # Step 3: Generate comprehensive report
        print("\n📋 Step 3: Generating comprehensive report...")
        
        total_registers = len(known_registers) + len(unknown_registers)
        print(f"\n🎯 Comprehensive scan complete!")
        print(f"   Known registers: {len(known_registers)}")
        print(f"   Unknown registers: {len(unknown_registers)}")
        print(f"   Total registers with data: {total_registers}")
        
        # Save comprehensive results
        filename = "comprehensive_register_scan.txt"
        with open(filename, "w") as f:
            f.write("Senergy Inverter - Comprehensive Register Scan\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Scan completed: {total_registers} total registers found\n")
            f.write(f"Known registers: {len(known_registers)}\n")
            f.write(f"Unknown registers: {len(unknown_registers)}\n\n")
            
            f.write("KNOWN REGISTERS:\n")
            f.write("-" * 40 + "\n")
            for reg in known_registers:
                f.write(f"0x{reg.address:04X} | {reg.data_type} | {reg.size} | {reg.value} {reg.unit} | {reg.description}\n")
            
            f.write("\n\nUNKNOWN REGISTERS:\n")
            f.write("-" * 40 + "\n")
            for reg in unknown_registers:
                f.write(f"0x{reg.address:04X} | {reg.data_type} | {reg.size} | {reg.raw_value} | {reg.value}\n")
        
        print(f"\n💾 Comprehensive results saved to: {filename}")
        
        # Print top unknown registers by value
        if unknown_registers:
            print("\n🔍 Top 10 unknown registers with interesting values:")
            sorted_unknown = sorted(unknown_registers, key=lambda x: abs(x.value) if isinstance(x.value, (int, float)) else 0, reverse=True)
            for i, reg in enumerate(sorted_unknown[:10], 1):
                print(f"  {i:2d}. 0x{reg.address:04X}: {reg.value} ({reg.data_type})")
    
    except Exception as e:
        print(f"❌ Error during comprehensive scan: {e}")
    
    finally:
        await scanner.disconnect()

async def intelligent_discovery():
    """Perform intelligent discovery with AI-like analysis."""
    
    PORT = "/dev/ttyUSB0"  # Change to your port
    BAUDRATE = 9600
    SLAVE_ID = 1
    
    scanner = SenergyRegisterScanner(port=PORT, baudrate=BAUDRATE, slave_id=SLAVE_ID)
    
    try:
        if not await scanner.connect():
            print("❌ Failed to connect to inverter")
            return
        
        print("🧠 Starting intelligent register discovery...")
        print("This uses AI-like analysis to find meaningful registers.")
        print("It will try multiple data types, scaling factors, and units.")
        
        # Ask user for scan range
        print("\nSelect intelligent discovery range:")
        print("1. Quick analysis (0x3000-0x3FFF) - ~10 minutes")
        print("2. Medium analysis (0x0000-0x7FFF) - ~25 minutes")
        print("3. Full analysis (0x0000-0xFFFF) - ~45 minutes")
        print("4. Custom range")
        
        try:
            choice = input("Enter choice (1-4): ").strip()
            
            if choice == "1":
                start_addr, end_addr = 0x3000, 0x3FFF
            elif choice == "2":
                start_addr, end_addr = 0x0000, 0x7FFF
            elif choice == "3":
                start_addr, end_addr = 0x0000, 0xFFFF
            elif choice == "4":
                start_addr = int(input("Enter start address (hex, e.g., 0x0000): "), 16)
                end_addr = int(input("Enter end address (hex, e.g., 0xFFFF): "), 16)
            else:
                print("Invalid choice, using quick analysis")
                start_addr, end_addr = 0x3000, 0x3FFF
        except (ValueError, KeyboardInterrupt):
            print("Invalid input, using quick analysis")
            start_addr, end_addr = 0x3000, 0x3FFF
        
        print(f"\n🧠 Performing intelligent analysis on range: 0x{start_addr:04X} to 0x{end_addr:04X}")
        
        # Perform intelligent discovery analysis
        results = await scanner.intelligent_discovery_analysis(start_addr, end_addr)
        
        print(f"\n🎯 Intelligent discovery complete!")
        print(f"   Total meaningful registers: {len(results['all'])}")
        print(f"   Top ranked registers: {len(results['ranked'])}")
        
        if results['ranked']:
            print(f"\n🏆 Top 5 most likely meaningful registers:")
            for i, reg in enumerate(results['ranked'][:5], 1):
                value_str = str(reg.value)
                if len(value_str) > 30:
                    value_str = value_str[:27] + "..."
                print(f"  {i}. 0x{reg.address:04X}: {value_str} {reg.unit} ({reg.data_type})")
        
        print(f"\n💡 These registers are most likely to contain meaningful data")
        print(f"   based on value ranges, units, and scaling factors.")
    
    except Exception as e:
        print(f"❌ Error during intelligent discovery: {e}")
    
    finally:
        await scanner.disconnect()

def print_usage():
    """Print usage instructions."""
    print("Senergy Register Scanner - Enhanced Usage Examples")
    print("=" * 60)
    print()
    print("Available scanning modes:")
    print()
    print("1. Basic examples (default):")
    print("   python example_register_scan.py")
    print("   - Shows individual register reading examples")
    print("   - Battery, PV, device info, and power data")
    print()
    print("2. Scan all known registers:")
    print("   python example_register_scan.py all")
    print("   - Scans all registers from the specification")
    print("   - Categorizes results by function")
    print("   - Saves results to file")
    print()
    print("3. Discover unknown registers:")
    print("   python example_register_scan.py discover")
    print("   - Scans for undocumented registers")
    print("   - Interactive range selection")
    print("   - Saves discovery results to file")
    print()
    print("4. Comprehensive scan:")
    print("   python example_register_scan.py comprehensive")
    print("   - Scans both known and unknown registers")
    print("   - Full address space discovery (0x0000-0xFFFF)")
    print("   - Complete report with all findings")
    print()
    print("5. Intelligent discovery:")
    print("   python example_register_scan.py intelligent")
    print("   - Uses AI-like analysis to find meaningful registers")
    print("   - Tries multiple data types, scaling factors, and units")
    print("   - Ranks results by likelihood of being meaningful")
    print()
    print("6. Interactive mode:")
    print("   python senergy_register_scanner.py")
    print("   - Interactive menu with all options")
    print()
    print("Configuration:")
    print("  - Edit the PORT variable in the script")
    print("  - Default: /dev/ttyUSB0 (Linux) or COM3 (Windows)")
    print("  - Baudrate: 9600")
    print("  - Slave ID: 1")
    print()
    print("Output files:")
    print("  - all_registers_scan_results.txt (known registers)")
    print("  - unknown_registers_discovery.txt (unknown registers)")
    print("  - comprehensive_register_scan.txt (complete scan)")
    print("  - intelligent_discovery_analysis.txt (AI-analyzed results)")
    print()
    print("7. Custom register reading:")
    print("   python example_register_scan.py custom")
    print("   - Read specific registers with custom parameters")
    print()

async def custom_register_examples():
    """Example of reading specific registers with custom parameters."""
    
    # Configuration - adjust these for your setup
    PORT = "/dev/ttyUSB0"  # Change to your port (e.g., "COM3" on Windows)
    BAUDRATE = 9600
    SLAVE_ID = 1
    
    # Create scanner instance
    scanner = SenergyRegisterScanner(port=PORT, baudrate=BAUDRATE, slave_id=SLAVE_ID)
    
    try:
        # Connect to inverter
        print("Connecting to inverter...")
        if not await scanner.connect():
            print("❌ Failed to connect to inverter")
            print("Please check your connection settings:")
            print(f"  Port: {PORT}")
            print(f"  Baudrate: {BAUDRATE}")
            print(f"  Slave ID: {SLAVE_ID}")
            return
        
        print("✅ Connected to inverter successfully!")
        
        # Example 1: Read Battery SOC with custom parameters
        print("\n" + "="*60)
        print("EXAMPLE 1: Reading Battery SOC (0x2000) with custom parameters")
        print("="*60)
        
        soc_request = CustomRegisterRequest(
            address=0x2000,
            length=1,
            unit="%",
            scale=0.1,
            data_type="U16",
            description="Battery State of Charge"
        )
        
        soc_register = await scanner.read_custom_register(soc_request)
        if soc_register:
            scanner._print_register(soc_register)
        else:
            print("Failed to read Battery SOC register")
        
        # Example 2: Read Battery Voltage with custom parameters
        print("\n" + "="*60)
        print("EXAMPLE 2: Reading Battery Voltage (0x2001) with custom parameters")
        print("="*60)
        
        voltage_request = CustomRegisterRequest(
            address=0x2001,
            length=1,
            unit="V",
            scale=0.1,
            data_type="U16",
            description="Battery Voltage"
        )
        
        voltage_register = await scanner.read_custom_register(voltage_request)
        if voltage_register:
            scanner._print_register(voltage_register)
        else:
            print("Failed to read Battery Voltage register")
        
        # Example 3: Read multiple custom registers
        print("\n" + "="*60)
        print("EXAMPLE 3: Reading multiple custom registers")
        print("="*60)
        
        custom_requests = [
            CustomRegisterRequest(
                address=0x2002,
                length=1,
                unit="A",
                scale=0.01,
                data_type="U16",
                description="Battery Current"
            ),
            CustomRegisterRequest(
                address=0x2003,
                length=1,
                unit="W",
                scale=1.0,
                data_type="U16",
                description="Battery Power"
            ),
            CustomRegisterRequest(
                address=0x2004,
                length=1,
                unit="°C",
                scale=0.1,
                data_type="U16",
                description="Battery Temperature"
            ),
            CustomRegisterRequest(
                address=0x2005,
                length=2,
                unit="kWh",
                scale=0.01,
                data_type="U32",
                description="Battery Daily Charge Energy"
            )
        ]
        
        results = await scanner.read_multiple_custom_registers(custom_requests)
        
        # Example 4: Read unknown register with auto-detection
        print("\n" + "="*60)
        print("EXAMPLE 4: Reading unknown register with auto-detection")
        print("="*60)
        
        unknown_request = CustomRegisterRequest(
            address=0x3000,  # Example unknown address
            length=1,
            unit="",
            scale=1.0,
            data_type="auto",  # Auto-detect data type
            description="Unknown Register (Auto-detect)"
        )
        
        unknown_register = await scanner.read_custom_register(unknown_request)
        if unknown_register:
            scanner._print_register(unknown_register)
        else:
            print("Failed to read unknown register (this is normal for non-existent addresses)")
        
        # Example 5: Interactive custom register reading
        print("\n" + "="*60)
        print("EXAMPLE 5: Interactive custom register reading")
        print("="*60)
        
        await interactive_custom_reading(scanner)
        
    except KeyboardInterrupt:
        print("\n⚠️  Scan interrupted by user")
    except Exception as e:
        print(f"❌ Error during custom register reading: {e}")
    finally:
        await scanner.disconnect()
        print("\n✅ Disconnected from inverter")

async def interactive_custom_reading(scanner):
    """Interactive mode for reading custom registers."""
    print("🔧 Interactive Custom Register Reading")
    print("Enter register details (or 'quit' to exit):")
    
    while True:
        try:
            print("\n" + "-"*40)
            address_input = input("Register address (hex, e.g., 0x2000): ").strip()
            
            if address_input.lower() in ['quit', 'exit', 'q']:
                break
            
            # Parse address
            if address_input.startswith('0x') or address_input.startswith('0X'):
                address = int(address_input, 16)
            else:
                address = int(address_input)
            
            # Get other parameters
            length = int(input("Number of registers to read (1, 2, 3, etc.): ") or "1")
            unit = input("Unit (e.g., V, A, W, %, °C, kWh): ").strip()
            scale = float(input("Scale factor (e.g., 0.1, 1.0, 0.01): ") or "1.0")
            data_type = input("Data type (auto, uint16, int16, uint32, int32, float32, ascii): ").strip() or "auto"
            description = input("Description (optional): ").strip()
            
            # Create request
            request = CustomRegisterRequest(
                address=address,
                length=length,
                unit=unit,
                scale=scale,
                data_type=data_type,
                description=description
            )
            
            # Read register
            print(f"\n📖 Reading register 0x{address:04X}...")
            reg_info = await scanner.read_custom_register(request)
            
            if reg_info:
                scanner._print_register(reg_info)
            else:
                print(f"❌ Failed to read register 0x{address:04X}")
            
        except ValueError as e:
            print(f"❌ Invalid input: {e}")
        except KeyboardInterrupt:
            print("\n⚠️  Interrupted by user")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        
        if mode == "all":
            print("📊 Starting comprehensive scan of all known registers...")
            asyncio.run(scan_all_known_registers())
        elif mode == "discover":
            print("🔍 Starting register discovery mode...")
            asyncio.run(discover_unknown_registers())
        elif mode == "comprehensive":
            print("🚀 Starting comprehensive register scan...")
            asyncio.run(comprehensive_scan())
        elif mode == "intelligent":
            print("🧠 Starting intelligent register discovery...")
            asyncio.run(intelligent_discovery())
        elif mode == "custom":
            print("🔧 Starting custom register reading examples...")
            asyncio.run(custom_register_examples())
        elif mode == "help":
            print_usage()
        else:
            print(f"❌ Unknown mode: {mode}")
            print("Use 'python example_register_scan.py help' for usage information")
    else:
        print("🚀 Starting Senergy Register Scanner examples...")
        print("Use 'python example_register_scan.py help' for usage information")
        print()
        asyncio.run(example_usage())
