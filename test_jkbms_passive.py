#!/usr/bin/env python3
"""
Standalone JK BMS Passive Listening Test Script

Based on jkbms_monitor project (https://github.com/phillcz/jkbms_monitor).
Passively listens to RS485-2 bus communication and displays battery data.

This script tests the passive listening mode by simulating the real environment:
- Starts continuous background listening task (like the real adapter)
- Simulates periodic polling (like the real app does every 5-10 seconds)
- Shows real-time updates as data arrives
- Displays final results

Usage:
    # Basic listening mode (simulates 60 seconds of operation)
    python test_jkbms_passive.py --port /dev/ttyUSB0
    
    # With custom baudrate
    python test_jkbms_passive.py --port COM3 --baudrate 115200
    
    # Extended listening time (180 seconds)
    python test_jkbms_passive.py --port /dev/ttyUSB0 --timeout 180
    
    # Debug mode (show raw frames)
    python test_jkbms_passive.py --port /dev/serial/by-id/usb-FTDI_FT232R_USB_UART_A10MLU4X-if00-port0 --debug
"""

import asyncio
import argparse
import sys
import time
import json
from typing import Optional, Dict, List, Tuple, Any

try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    print("ERROR: pyserial not installed. Install with: pip install pyserial")
    sys.exit(1)

# Import the adapter
from solarhub.adapters.battery_jkbms_passive import JKBMSPassiveAdapter
from solarhub.config import BatteryBankConfig, BatteryAdapterConfig

import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)


async def simulate_real_environment(port: str, baudrate: int, duration: float, debug: bool):
    """
    Simulate the real environment:
    1. Create adapter instance
    2. Start continuous background listening
    3. Simulate periodic polling (every 5 seconds)
    4. Show real-time updates
    """
    # Create a minimal config for the adapter
    adapter_cfg = BatteryAdapterConfig(
        type="jkbms_passive",
        serial_port=port,
        baudrate=baudrate,
        parity="N",
        stopbits=1,
        bytesize=8,
        bms_broadcasting=True,
        batteries=3,
        cells_per_battery=16,
    )
    
    bank_cfg = BatteryBankConfig(
        id="test_bank",
        name="Test Battery Bank",
        adapter=adapter_cfg,
    )
    
    # Create adapter instance
    adapter = JKBMSPassiveAdapter(bank_cfg)
    
    print(f"\n{'='*60}")
    print(f"SIMULATING REAL ENVIRONMENT")
    print(f"{'='*60}")
    print(f"Port: {port}")
    print(f"Baudrate: {baudrate}")
    print(f"Duration: {duration} seconds")
    print(f"Polling interval: 5 seconds (simulating real app)")
    print(f"{'='*60}\n")
    
    try:
        # Connect to serial port
        print("Connecting to serial port...")
        await adapter.connect()
        print("✓ Connected successfully\n")
        
        # Start continuous background listening task
        print("Starting continuous background listening task...")
        await adapter.start_listening()
        print("✓ Background listening task started\n")
        
        # Wait a bit for initial data
        print("Waiting for initial data (2 seconds)...")
        await asyncio.sleep(2.0)
        print("✓ Initial wait complete\n")
        
        # Simulate periodic polling (like the real app does)
        start_time = time.time()
        poll_count = 0
        last_poll_time = start_time
        poll_interval = 5.0  # Simulate polling every 5 seconds (like real app)
        
        print(f"{'='*60}")
        print("PERIODIC POLLING (simulating real app behavior)")
        print(f"{'='*60}\n")
        
        while time.time() - start_time < duration:
            current_time = time.time()
            
            # Poll if it's time (every 5 seconds)
            if current_time - last_poll_time >= poll_interval:
                poll_count += 1
                elapsed = current_time - start_time
                remaining = duration - elapsed
                
                print(f"\n[Poll #{poll_count} at {elapsed:.1f}s (remaining: {remaining:.1f}s)]")
                print("-" * 60)
                
                try:
                    # Call poll() - this returns cached data from background task
                    tel = await adapter.poll()
                    
                    # Display current state
                    print(f"Battery Bank: {tel.id}")
                    print(f"  Batteries detected: {tel.batteries_count}")
                    print(f"  Cells per battery: {tel.cells_per_battery}")
                    
                    if tel.voltage is not None:
                        print(f"  Bank Voltage: {tel.voltage:.2f} V")
                    if tel.current is not None:
                        print(f"  Bank Current: {tel.current:.2f} A")
                    if tel.temperature is not None:
                        print(f"  Bank Temperature: {tel.temperature:.1f} °C")
                    if tel.soc is not None:
                        print(f"  Bank SOC: {tel.soc:.1f} %")
                    
                    # Show individual batteries
                    if tel.devices:
                        print(f"\n  Individual Batteries:")
                        for dev in tel.devices:
                            battery_id = getattr(dev, 'power', '?')
                            print(f"    Battery #{battery_id}: ", end="")
                            parts = []
                            if dev.voltage is not None:
                                parts.append(f"V={dev.voltage:.2f}V")
                            if dev.current is not None:
                                parts.append(f"I={dev.current:.2f}A")
                            if dev.soc is not None:
                                parts.append(f"SOC={dev.soc:.0f}%")
                            if dev.temperature is not None:
                                parts.append(f"T={dev.temperature:.1f}°C")
                            print(", ".join(parts) if parts else "No data")
                    
                    # Show cache statistics
                    async with adapter._battery_data_lock:
                        cache_size = len(adapter.battery_data)
                        last_update = adapter._last_data_update
                        age = time.time() - last_update if last_update > 0 else 0
                    
                    print(f"\n  Cache: {cache_size} batteries, last update: {age:.1f}s ago")
                    
                except Exception as e:
                    print(f"  ✗ Poll failed: {e}")
                    log.debug(f"Poll error: {e}", exc_info=True)
                
                last_poll_time = current_time
            
            # Sleep a bit to avoid busy waiting
            await asyncio.sleep(0.5)
        
        # Final poll and summary
        print(f"\n\n{'='*60}")
        print("FINAL RESULTS")
        print(f"{'='*60}\n")
        
        try:
            tel = await adapter.poll()
            # Get cache statistics
            async with adapter._battery_data_lock:
                cache_size = len(adapter.battery_data)
                last_update = adapter._last_data_update
            age = time.time() - last_update if last_update > 0 else 0
            print_final_results(tel, poll_count, cache_size, age)
        except Exception as e:
            print(f"✗ Final poll failed: {e}")
            log.debug(f"Final poll error: {e}", exc_info=True)
    
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Stop listening and close connection
        print("\nStopping background listening task...")
        await adapter.stop_listening()
        print("Closing connection...")
        await adapter.close()
        print("✓ Cleanup complete")


def print_final_results(tel, poll_count, cache_size, last_update_age):
    """Print final detailed results."""
    print(f"Total polls executed: {poll_count}")
    print(f"Battery Bank: {tel.id}")
    print(f"Batteries detected: {tel.batteries_count}")
    print(f"Cells per battery: {tel.cells_per_battery}\n")
    
    if tel.devices:
        print(f"{'='*60}")
        print("BATTERY DETAILS")
        print(f"{'='*60}\n")
        
        for dev in tel.devices:
            battery_id = getattr(dev, 'power', '?')
            print(f"Battery #{battery_id}:")
            print(f"  Voltage: {dev.voltage:.2f} V" if dev.voltage is not None else "  Voltage: N/A")
            print(f"  Current: {dev.current:.2f} A" if dev.current is not None else "  Current: N/A")
            print(f"  SOC: {dev.soc:.0f} %" if dev.soc is not None else "  SOC: N/A")
            print(f"  SOH: {dev.soh:.0f} %" if dev.soh is not None else "  SOH: N/A")
            print(f"  Temperature: {dev.temperature:.1f} °C" if dev.temperature is not None else "  Temperature: N/A")
            print(f"  Cycles: {dev.cycles}" if dev.cycles is not None else "  Cycles: N/A")
            print()
    
    # Show cell data if available
    if tel.cells_data:
        print(f"{'='*60}")
        print("CELL DATA")
        print(f"{'='*60}\n")
        
        for entry in tel.cells_data:
            battery_id = entry.get('battery_id', '?')
            cell_count = entry.get('cell_count', 0)
            cell_voltages = entry.get('cell_voltages', [])
            
            print(f"Battery #{battery_id} ({cell_count} cells):")
            if cell_voltages:
                print(f"  Cell Voltages:")
                for i in range(0, len(cell_voltages), 4):
                    cells = cell_voltages[i:i+4]
                    line = "  ".join([f"Cell {i+j+1:2d}: {v:6.3f}V" for j, v in enumerate(cells)])
                    print(f"    {line}")
                
                if len(cell_voltages) > 0:
                    min_v = min(cell_voltages)
                    max_v = max(cell_voltages)
                    avg_v = sum(cell_voltages) / len(cell_voltages)
                    delta_v = max_v - min_v
                    print(f"  Min: {min_v:.3f}V, Max: {max_v:.3f}V, Avg: {avg_v:.3f}V, Delta: {delta_v:.3f}V ({delta_v/avg_v*100:.2f}%)")
            
            # Additional status fields
            if entry.get('balance_current') is not None:
                print(f"  Balance Current: {entry['balance_current']:.3f} A")
            if entry.get('total_runtime') is not None:
                runtime_hours = entry['total_runtime'] / 3600.0
                print(f"  Total Runtime: {entry['total_runtime']}s ({runtime_hours:.1f}h)")
            if entry.get('charge_switch') is not None:
                print(f"  Charge Switch: {'ON' if entry['charge_switch'] else 'OFF'}")
            if entry.get('discharge_switch') is not None:
                print(f"  Discharge Switch: {'ON' if entry['discharge_switch'] else 'OFF'}")
            if entry.get('balance_switch') is not None:
                print(f"  Balance Switch: {'ON' if entry['balance_switch'] else 'OFF'}")
            print()
    
    print(f"{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"Total batteries detected: {tel.batteries_count}")
    print(f"Cache size: {cache_size} batteries")
    print(f"Last data update: {last_update_age:.1f} seconds ago")
    print()
    print("Note: This simulates the real environment:")
    print("  - Continuous background listening task (runs independently)")
    print("  - Periodic polling every 5 seconds (like the real app)")
    print("  - Poll() returns cached data (fast and non-blocking)")
    print("  - Data validation filters out corrupted batteries")
    print(f"{'='*60}\n")


async def main():
    parser = argparse.ArgumentParser(
        description='Test JK BMS passive listening mode (simulates real environment)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic test (60 seconds, simulates real app)
  python test_jkbms_passive.py --port /dev/ttyUSB0
  
  # Extended test (180 seconds)
  python test_jkbms_passive.py --port /dev/ttyUSB0 --timeout 180
  
  # Debug mode (show raw hex)
  python test_jkbms_passive.py --port /dev/ttyUSB0 --debug
  
  # Custom baudrate
  python test_jkbms_passive.py --port COM3 --baudrate 115200
        """
    )
    
    parser.add_argument('--port', '-p', required=True,
                       help='Serial port (e.g., /dev/ttyUSB0 or COM3)')
    parser.add_argument('--baudrate', '-b', type=int, default=115200,
                       help='Baudrate (default: 115200)')
    parser.add_argument('--timeout', '-t', type=float, default=60.0,
                       help='Test duration in seconds (default: 60.0)')
    parser.add_argument('--debug', '-d', action='store_true',
                       help='Enable debug output (show raw hex frames)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    if args.debug:
        logging.getLogger('solarhub.adapters.battery_jkbms_passive').setLevel(logging.DEBUG)
    
    try:
        await simulate_real_environment(
            port=args.port,
            baudrate=args.baudrate,
            duration=args.timeout,
            debug=args.debug
        )
        print("✓ Test completed successfully!")
        return 0
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        return 1
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
