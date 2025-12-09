#!/usr/bin/env python3
"""
Standalone Senergy Inverter Test Script (TCP Modbus)

This script tests connectivity and register reading from Senergy inverters via Modbus/TCP.
It can be run independently to validate hardware connections and register values.

Senergy inverters provide:
- PV power, voltage, current
- Grid power, voltage, current, frequency
- Battery power, voltage, current, SOC
- Load power
- Device information (model, serial number)
- Various status and configuration registers

Usage:
    python test_senergy_tcp.py --host 192.168.1.100
    python test_senergy_tcp.py --host 192.168.1.100 --port 502 --unit-id 1
    python test_senergy_tcp.py --host 192.168.1.100 --test-register 0x1A0A
    python test_senergy_tcp.py --host 192.168.1.100 --read-all
"""

import asyncio
import argparse
import sys
import json
import os
from typing import List, Optional, Dict, Any
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)

try:
    from pymodbus.client import AsyncModbusTcpClient
    from pymodbus.exceptions import ModbusException
except ImportError:
    print("ERROR: pymodbus not installed. Install with: pip install pymodbus")
    sys.exit(1)


class SenergyTcpTester:
    """
    Standalone tester for Senergy inverters via Modbus/TCP.
    
    Supports reading from Senergy inverters over network (Ethernet/Wi-Fi).
    """
    
    # Default register map path
    DEFAULT_REGISTER_MAP = os.path.join(
        os.path.dirname(__file__), "register_maps", "senergy_registers.json"
    )
    
    def __init__(self, host: str, port: int = 502, unit_id: int = 1, timeout: float = 3.0,
                 register_map_file: Optional[str] = None):
        self.host = host
        self.port = port
        self.unit_id = unit_id
        self.timeout = timeout
        self.client: Optional[AsyncModbusTcpClient] = None
        self.register_map: List[Dict[str, Any]] = []
        self.register_map_file = register_map_file or self.DEFAULT_REGISTER_MAP
        
        # Load register map if available
        if os.path.exists(self.register_map_file):
            try:
                with open(self.register_map_file, 'r') as f:
                    self.register_map = json.load(f)
                log.info(f"Loaded Senergy register map: {self.register_map_file} ({len(self.register_map)} registers)")
            except Exception as e:
                log.error(f"Error loading register map {self.register_map_file}: {e}")
                self.register_map = []
        else:
            log.warning(f"Register map file not found: {self.register_map_file}. Will use hardcoded registers.")
    
    async def connect(self) -> bool:
        """Connect to Senergy inverter via Modbus/TCP."""
        try:
            log.info(f"Connecting to Senergy inverter at {self.host}:{self.port} (unit ID: {self.unit_id})...")
            self.client = AsyncModbusTcpClient(
                host=self.host,
                port=self.port,
                timeout=self.timeout,
            )
            ok = await self.client.connect()
            if ok and self.client.connected:
                log.info(f"✓ Connected successfully to {self.host}:{self.port}")
                return True
            else:
                log.error(f"✗ Connection failed: client.connect() returned {ok}")
                return False
        except Exception as e:
            log.error(f"✗ Connection error: {e}")
            return False
    
    async def close(self):
        """Close Modbus/TCP connection."""
        if self.client:
            try:
                if hasattr(self.client, 'close'):
                    import inspect
                    if inspect.iscoroutinefunction(self.client.close):
                        await self.client.close()
                    else:
                        self.client.close()
                self.client = None
                log.info("Connection closed")
            except Exception as e:
                log.warning(f"Error closing connection: {e}")
    
    async def test_connectivity(self) -> bool:
        """Test basic connectivity by reading a known register."""
        try:
            # Try reading device model (address 6656, holding register)
            result = await self.client.read_holding_registers(
                address=6656,
                count=8,
                device_id=self.unit_id
            )
            if result.isError():
                log.error(f"Connectivity test failed: {result}")
                return False
            log.info("✓ Inverter is responding (device model register)")
            return True
        except Exception as e:
            log.error(f"Connectivity test error: {e}")
            return False
    
    def _decode_ascii(self, registers: List[int]) -> str:
        """Decode ASCII string from register values."""
        buf = bytearray()
        for w in registers:
            w = int(w) & 0xFFFF
            buf.append((w >> 8) & 0xFF)
            buf.append(w & 0xFF)
        s = bytes(buf).split(b"\x00", 1)[0].decode("ascii", errors="ignore").strip()
        return s
    
    def _decode_value(self, reg: Dict[str, Any], raw_value: Any) -> Any:
        """Decode register value based on type and scale."""
        reg_type = reg.get("type", "U16")
        scale = reg.get("scale", 1.0)
        size = reg.get("size", 1)
        
        if size == 1:
            if reg_type in ["S16", "I16"]:
                # Signed 16-bit
                val = int(raw_value)
                if val > 32767:
                    val = val - 65536
            else:
                val = int(raw_value)
        elif size == 2:
            # 32-bit value (two registers)
            if isinstance(raw_value, list) and len(raw_value) >= 2:
                val = (int(raw_value[0]) << 16) | int(raw_value[1])
                if reg_type in ["S32", "I32"]:
                    if val > 2147483647:
                        val = val - 4294967296
            else:
                val = int(raw_value) if isinstance(raw_value, (int, float)) else 0
        else:
            val = raw_value
        
        # Apply scale
        if isinstance(scale, (int, float)) and scale != 1.0:
            val = float(val) * scale
        
        return val
    
    async def read_register(self, address: int, size: int = 1, kind: str = "holding") -> Optional[List[int]]:
        """Read a register or register range."""
        try:
            if kind == "holding":
                result = await self.client.read_holding_registers(
                    address=address,
                    count=size,
                    device_id=self.unit_id
                )
            elif kind == "input":
                result = await self.client.read_input_registers(
                    address=address,
                    count=size,
                    device_id=self.unit_id
                )
            else:
                log.error(f"Unknown register kind: {kind}")
                return None
            
            if result.isError():
                log.error(f"Error reading register 0x{address:04X}: {result}")
                return None
            
            return list(result.registers) if result.registers else None
        except Exception as e:
            log.error(f"Exception reading register 0x{address:04X}: {e}")
            return None
    
    async def read_device_info(self):
        """Read device model and serial number."""
        log.info("Reading device information...")
        
        # Device Model (address 6656, 8 registers, holding)
        model_regs = await self.read_register(6656, 8, "holding")
        if model_regs:
            model = self._decode_ascii(model_regs)
            log.info(f"✓ Device Model: {model}")
        else:
            log.warning("✗ Could not read device model")
        
        # Serial Number (address 6672, 8 registers, holding)
        serial_regs = await self.read_register(6672, 8, "holding")
        if serial_regs:
            serial = self._decode_ascii(serial_regs)
            log.info(f"✓ Serial Number: {serial}")
        else:
            log.warning("✗ Could not read serial number")
    
    async def read_basic_data(self):
        """Read basic inverter telemetry data."""
        log.info("Reading basic inverter data...")
        
        # Find key registers from register map
        key_registers = {
            "pv_power_w": None,
            "pv_voltage_v": None,
            "pv_current_a": None,
            "grid_power_w": None,
            "grid_voltage_v": None,
            "grid_current_a": None,
            "grid_frequency_hz": None,
            "batt_power_w": None,
            "batt_voltage_v": None,
            "batt_current_a": None,
            "batt_soc_pct": None,
            "load_power_w": None,
        }
        
        # Map register IDs to addresses from register map
        for reg in self.register_map:
            reg_id = reg.get("id", "")
            if reg_id in key_registers:
                key_registers[reg_id] = {
                    "addr": reg.get("addr"),
                    "size": reg.get("size", 1),
                    "kind": reg.get("kind", "holding"),
                    "type": reg.get("type", "U16"),
                    "scale": reg.get("scale", 1.0),
                    "unit": reg.get("unit", ""),
                    "name": reg.get("name", reg_id)
                }
        
        print("\n" + "=" * 80)
        print("Senergy Inverter - Basic Data")
        print("=" * 80)
        
        for reg_id, reg_info in key_registers.items():
            if reg_info is None:
                continue
            
            addr = reg_info["addr"]
            size = reg_info["size"]
            kind = reg_info["kind"]
            name = reg_info["name"]
            unit = reg_info.get("unit", "")
            
            raw_value = await self.read_register(addr, size, kind)
            if raw_value is not None:
                decoded_value = self._decode_value(reg_info, raw_value)
                if unit:
                    print(f"{name:40s}: {decoded_value:12.3f} {unit}")
                else:
                    print(f"{name:40s}: {decoded_value}")
            else:
                print(f"{name:40s}: N/A")
        
        print("=" * 80)
    
    async def read_all_registers(self):
        """Read all registers from the register map."""
        if not self.register_map:
            log.error("No register map loaded. Cannot read all registers.")
            return
        
        log.info("Reading all registers from JSON map...")
        
        print("\n" + "=" * 80)
        print("Senergy Inverter - All Registers from JSON Map")
        print("=" * 80)
        
        successful = 0
        failed = 0
        
        for reg in self.register_map:
            reg_id = reg.get("id", "unknown")
            name = reg.get("name", reg_id)
            addr = reg.get("addr")
            size = reg.get("size", 1)
            kind = reg.get("kind", "holding")
            reg_type = reg.get("type", "U16")
            scale = reg.get("scale", 1.0)
            unit = reg.get("unit", "")
            
            if addr is None:
                continue
            
            raw_value = await self.read_register(addr, size, kind)
            if raw_value is not None:
                try:
                    if unit == "ascii":
                        decoded_value = self._decode_ascii(raw_value)
                        print(f"{reg_id:30s} 0x{addr:04X} {decoded_value:30s} {name}")
                    else:
                        decoded_value = self._decode_value(reg, raw_value)
                        if unit:
                            print(f"{reg_id:30s} 0x{addr:04X} {decoded_value:12.3f} {unit:8s} {name}")
                        else:
                            print(f"{reg_id:30s} 0x{addr:04X} {decoded_value:12} {name}")
                    successful += 1
                except Exception as e:
                    print(f"{reg_id:30s} 0x{addr:04X} ERROR: {e} {name}")
                    failed += 1
            else:
                failed += 1
        
        print("=" * 80)
        print(f"Total registers read: {successful}")
        if failed > 0:
            print(f"Failed reads: {failed}")
    
    async def test_single_register(self, address: int, size: int = 1, kind: str = "holding"):
        """Test reading a single register."""
        log.info(f"Testing register 0x{address:04X} (size={size}, kind={kind})...")
        
        raw_value = await self.read_register(address, size, kind)
        if raw_value is not None:
            print(f"\nRegister 0x{address:04X}:")
            if size == 1:
                print(f"  Raw value: {raw_value[0]} (0x{raw_value[0]:04X})")
            else:
                print(f"  Raw values: {raw_value}")
                # Try to decode as 32-bit
                if size == 2:
                    combined = (int(raw_value[0]) << 16) | int(raw_value[1])
                    print(f"  Combined (32-bit): {combined} (0x{combined:08X})")
        else:
            print(f"✗ Failed to read register 0x{address:04X}")


async def main():
    parser = argparse.ArgumentParser(
        description="Test Senergy inverter via Modbus/TCP",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_senergy_tcp.py --host 192.168.1.100
  python test_senergy_tcp.py --host 192.168.1.100 --port 502 --unit-id 1
  python test_senergy_tcp.py --host 192.168.1.100 --test-register 0x1A0A
  python test_senergy_tcp.py --host 192.168.1.100 --read-all
        """
    )
    
    parser.add_argument("--host", required=True, help="IP address of the inverter")
    parser.add_argument("--port", type=int, default=502, help="Modbus TCP port (default: 502)")
    parser.add_argument("--unit-id", type=int, default=1, help="Modbus unit ID (default: 1)")
    parser.add_argument("--timeout", type=float, default=3.0, help="Connection timeout in seconds (default: 3.0)")
    parser.add_argument("--register-map", help="Path to register map JSON file")
    parser.add_argument("--test-register", help="Test a specific register (hex format, e.g., 0x1A0A)")
    parser.add_argument("--read-all", action="store_true", help="Read all registers from register map")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Parse test register if provided
    test_addr = None
    if args.test_register:
        try:
            test_addr = int(args.test_register, 16) if args.test_register.startswith("0x") else int(args.test_register)
        except ValueError:
            log.error(f"Invalid register address: {args.test_register}")
            sys.exit(1)
    
    tester = SenergyTcpTester(
        host=args.host,
        port=args.port,
        unit_id=args.unit_id,
        timeout=args.timeout,
        register_map_file=args.register_map
    )
    
    try:
        # Connect
        if not await tester.connect():
            log.error("Failed to connect to inverter")
            sys.exit(1)
        
        # Test connectivity
        if not await tester.test_connectivity():
            log.error("Connectivity test failed")
            sys.exit(1)
        
        # Read device info
        await tester.read_device_info()
        
        # Execute requested action
        if test_addr is not None:
            await tester.test_single_register(test_addr)
        elif args.read_all:
            await tester.read_all_registers()
        else:
            # Default: read basic data
            await tester.read_basic_data()
        
        print("\n" + "=" * 80)
        print("✓ Test completed successfully!")
        print("=" * 80)
        
    except KeyboardInterrupt:
        log.info("\nTest interrupted by user")
    except Exception as e:
        log.error(f"Test failed: {e}", exc_info=True)
        sys.exit(1)
    finally:
        await tester.close()


if __name__ == "__main__":
    asyncio.run(main())

