#!/usr/bin/env python3
"""
Standalone IAMMeter Test Script

This script tests connectivity and register reading from IAMMeter devices.
It can be run independently to validate hardware connections and register values.

IAMMeter devices (WEM3080, WEM3080T, etc.) provide:
- Voltage, Current, Active Power (W) - positive = import, negative = export
- Active Energy (kWh) - cumulative
- Frequency (Hz)
- Power Factor
- Three-phase data (Phase A, B, C)
- Reactive power and energy

Usage:
    python test_iammeter.py --host 192.168.1.100
    python test_iammeter.py --host 192.168.1.100 --port 502 --unit-id 1
    python test_iammeter.py --host 192.168.1.100 --test-register 0x48
    python test_iammeter.py --host 192.168.1.100 --read-all
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
except ImportError:
    print("ERROR: pymodbus not installed. Install with: pip install pymodbus")
    sys.exit(1)


class IAMMeterStandaloneTester:
    """
    Standalone tester for IAMMeter devices via Modbus/TCP.
    
    Supports reading from IAMMeter Wi-Fi energy meters (WEM3080, WEM3080T, etc.).
    """
    
    # Common register addresses (may vary by model)
    # Serial number (address 0x38, 8 registers)
    REG_SERIAL_NUMBER = 0x38
    
    # Phase A registers (standard addresses from register map)
    REG_VOLTAGE_A = 72      # 0x48, scale 0.01 (divide by 100)
    REG_CURRENT_A = 73      # 0x49, scale 0.01 (divide by 100)
    REG_POWER_A = 74        # 0x4A, scale 1.0 (U16, not S32!)
    REG_ENERGY_FORWARD_A = 75  # 0x4B, 2 registers (U32), scale 0.00125
    REG_POWER_FACTOR_A = 77    # 0x4D, scale 0.001 (divide by 1000)
    REG_ENERGY_REVERSE_A = 78  # 0x4E, 2 registers (U32), scale 0.00125
    
    # Phase B registers
    REG_VOLTAGE_B = 81      # 0x51
    REG_CURRENT_B = 82      # 0x52
    REG_POWER_B = 83        # 0x53
    REG_POWER_FACTOR_B = 86  # 0x56
    
    # Phase C registers
    REG_VOLTAGE_C = 90      # 0x5A
    REG_CURRENT_C = 91      # 0x5B
    REG_POWER_C = 92        # 0x5C
    REG_POWER_FACTOR_C = 95  # 0x5F
    
    # Total/System registers
    REG_FREQUENCY = 101     # 0x65, scale 0.01 (divide by 100)
    REG_TOTAL_POWER = 120   # 0x78, 2 registers (signed 32-bit)
    REG_TOTAL_ENERGY_FORWARD = 99   # 0x63, 2 registers (unsigned 32-bit), scale 0.00125 (divide by 800)
    
    # Legacy registers (fallback, may not be in all models)
    REG_VOLTAGE_LEGACY = 0x0000
    REG_CURRENT_LEGACY = 0x0001
    REG_POWER_LEGACY = 0x0002  # 2 registers
    REG_ENERGY_LEGACY = 0x0004  # 2 registers
    REG_FREQUENCY_LEGACY = 0x0006
    REG_POWER_FACTOR_LEGACY = 0x0007
    
    # Default register map path
    DEFAULT_REGISTER_MAP = os.path.join(
        os.path.dirname(__file__), "register_maps", "iammeter_registers.json"
    )
    
    def __init__(self, host: str, port: int = 502, unit_id: int = 1, timeout: float = 3.0,
                 register_map_file: Optional[str] = None, prefer_legacy_registers: bool = False):
        self.host = host
        self.port = port
        self.unit_id = unit_id
        self.timeout = timeout
        self.client: Optional[AsyncModbusTcpClient] = None
        self.register_map: List[Dict[str, Any]] = []
        self.register_map_file = register_map_file or self.DEFAULT_REGISTER_MAP
        self.prefer_legacy_registers = prefer_legacy_registers
        
        # Load register map if available
        if os.path.exists(self.register_map_file):
            try:
                with open(self.register_map_file, 'r') as f:
                    self.register_map = json.load(f)
                log.info(f"Loaded IAMMeter register map: {self.register_map_file} ({len(self.register_map)} registers)")
            except Exception as e:
                log.error(f"Error loading register map {self.register_map_file}: {e}")
                self.register_map = []
        else:
            log.warning(f"Register map file not found: {self.register_map_file}. Will use hardcoded registers.")
    
    async def connect(self) -> bool:
        """Connect to IAMMeter via Modbus/TCP."""
        try:
            log.info(f"Connecting to IAMMeter at {self.host}:{self.port} (unit ID: {self.unit_id})...")
            self.client = AsyncModbusTcpClient(
                host=self.host,
                port=self.port,
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
    
    async def read_registers(self, start_addr: int, count: int) -> Optional[List[int]]:
        """
        Read holding registers from IAMMeter.
        
        Args:
            start_addr: Starting register address
            count: Number of registers to read
            
        Returns:
            List of register values or None on error
        """
        if not self.client or not self.client.connected:
            log.error("Client not connected")
            return None
        
        try:
            rr = await self.client.read_holding_registers(
                address=start_addr,
                count=count,
                device_id=self.unit_id
            )
            if rr.isError():
                log.error(f"Modbus read error at 0x{start_addr:04X}: {rr}")
                return None
            return list(rr.registers) if rr.registers else None
        except Exception as e:
            log.error(f"Exception reading registers 0x{start_addr:04X}: {e}")
            return None
    
    def decode_signed_32bit(self, regs: List[int]) -> int:
        """Decode signed 32-bit integer from two 16-bit registers (big-endian)."""
        if not regs or len(regs) < 2:
            return 0
        value = (regs[0] << 16) | regs[1]
        if value & 0x80000000:
            value = value - 0x100000000
        return value
    
    def decode_unsigned_32bit(self, regs: List[int]) -> int:
        """Decode unsigned 32-bit integer from two 16-bit registers (big-endian)."""
        if not regs or len(regs) < 2:
            return 0
        return (regs[0] << 16) | regs[1]
    
    async def test_connectivity(self) -> bool:
        """Test basic connectivity by reading serial number register."""
        log.info("Testing connectivity...")
        # Try serial number register first (more reliable)
        regs = await self.read_registers(self.REG_SERIAL_NUMBER, 8)
        if regs:
            log.info("✓ IAMMeter is responding (serial number register)")
            return True
        
        # Fallback: try voltage register
        regs = await self.read_registers(self.REG_VOLTAGE_A, 1)
        if regs:
            log.info("✓ IAMMeter is responding (voltage register)")
            return True
        
        log.error("✗ IAMMeter is not responding")
        return False
    
    async def read_serial_number(self) -> Optional[str]:
        """Read device serial number."""
        log.info("Reading serial number...")
        regs = await self.read_registers(self.REG_SERIAL_NUMBER, 8)
        if not regs:
            return None
        
        # Decode ASCII from registers
        serial_bytes = bytearray()
        for reg in regs:
            serial_bytes.append((reg >> 8) & 0xFF)
            serial_bytes.append(reg & 0xFF)
        
        serial_number = serial_bytes.split(b'\x00')[0].decode('ascii', errors='ignore').strip()
        return serial_number if serial_number and len(serial_number) >= 3 else None
    
    async def read_basic_data(self) -> Optional[Dict[str, Any]]:
        """Read basic meter data (voltage, current, power, energy, frequency)."""
        log.info("Reading basic meter data...")
        
        data: Dict[str, Any] = {}
        
        # Try Phase A registers - order depends on prefer_legacy_registers flag
        async def try_read_voltage(standard_addr: int, legacy_addr: int) -> Optional[float]:
            if self.prefer_legacy_registers:
                # Legacy first
                regs = await self.read_registers(legacy_addr, 1)
                if regs and regs[0] != 0:
                    return regs[0] / 100.0
                regs = await self.read_registers(standard_addr, 1)
                if regs and regs[0] != 0:
                    return regs[0] / 100.0
            else:
                # Extended first (default)
                regs = await self.read_registers(standard_addr, 1)
                if regs and regs[0] != 0:
                    return regs[0] / 100.0
                regs = await self.read_registers(legacy_addr, 1)
                if regs and regs[0] != 0:
                    return regs[0] / 100.0
            return None
        
        async def try_read_current(standard_addr: int, legacy_addr: int) -> Optional[float]:
            if self.prefer_legacy_registers:
                # Legacy first
                regs = await self.read_registers(legacy_addr, 1)
                if regs and regs[0] != 0:
                    return regs[0] / 100.0
                regs = await self.read_registers(standard_addr, 1)
                if regs and regs[0] != 0:
                    return regs[0] / 100.0
            else:
                # Extended first (default)
                regs = await self.read_registers(standard_addr, 1)
                if regs and regs[0] != 0:
                    return regs[0] / 100.0
                regs = await self.read_registers(legacy_addr, 1)
                if regs and regs[0] != 0:
                    return regs[0] / 100.0
            return None
        
        # Try Phase A voltage (extended first, then legacy)
        voltage = await try_read_voltage(self.REG_VOLTAGE_A, self.REG_VOLTAGE_LEGACY)
        if voltage is not None:
            data['voltage_v'] = voltage
        
        # Try Phase A current (extended first, then legacy)
        current = await try_read_current(self.REG_CURRENT_A, self.REG_CURRENT_LEGACY)
        if current is not None:
            data['current_a'] = current
        
        # Try total power - order depends on prefer_legacy_registers flag
        async def try_read_power() -> Optional[int]:
            if self.prefer_legacy_registers:
                # Legacy first
                # Try sum power legacy (address 32, 2 registers, signed 32-bit)
                power_regs = await self.read_registers(32, 2)
                if power_regs and (power_regs[0] != 0 or power_regs[1] != 0):
                    return self.decode_signed_32bit(power_regs)
                
                # Try legacy Phase A power (2 registers, signed 32-bit)
                power_regs = await self.read_registers(self.REG_POWER_LEGACY, 2)
                if power_regs and (power_regs[0] != 0 or power_regs[1] != 0):
                    return self.decode_signed_32bit(power_regs)
                
                # Try total power (address 120, 2 registers, signed 32-bit)
                power_regs = await self.read_registers(self.REG_TOTAL_POWER, 2)
                if power_regs and (power_regs[0] != 0 or power_regs[1] != 0):
                    return self.decode_signed_32bit(power_regs)
                
                # Try Phase A power (U16, not S32)
                power_regs = await self.read_registers(self.REG_POWER_A, 1)
                if power_regs and power_regs[0] != 0:
                    power_val = power_regs[0]
                    if power_val & 0x8000:
                        return power_val - 0x10000
                    return power_val
            else:
                # Extended first (default)
                # Try total power (address 120, 2 registers, signed 32-bit)
                power_regs = await self.read_registers(self.REG_TOTAL_POWER, 2)
                if power_regs and (power_regs[0] != 0 or power_regs[1] != 0):
                    return self.decode_signed_32bit(power_regs)
                
                # Try Phase A power (U16, not S32)
                power_regs = await self.read_registers(self.REG_POWER_A, 1)
                if power_regs and power_regs[0] != 0:
                    power_val = power_regs[0]
                    if power_val & 0x8000:
                        return power_val - 0x10000
                    return power_val
                
                # Try sum power legacy (address 32, 2 registers, signed 32-bit)
                power_regs = await self.read_registers(32, 2)
                if power_regs and (power_regs[0] != 0 or power_regs[1] != 0):
                    return self.decode_signed_32bit(power_regs)
                
                # Fallback to legacy Phase A power (2 registers, signed 32-bit)
                power_regs = await self.read_registers(self.REG_POWER_LEGACY, 2)
                if power_regs and (power_regs[0] != 0 or power_regs[1] != 0):
                    return self.decode_signed_32bit(power_regs)
            
            return None
        
        power = await try_read_power()
        if power is not None:
            data['power_w'] = power
        
        # Try total active energy forward - order depends on prefer_legacy_registers flag
        async def try_read_energy() -> Optional[float]:
            if self.prefer_legacy_registers:
                # Legacy first
                # Try sum forward energy legacy (address 34, scale 0.00125 = divide by 800)
                energy_regs = await self.read_registers(34, 2)
                if energy_regs and (energy_regs[0] != 0 or energy_regs[1] != 0):
                    energy_raw = self.decode_unsigned_32bit(energy_regs)
                    return energy_raw / 800.0
                
                # Try legacy Phase A forward energy (address 4, scale 0.00125 = divide by 800)
                energy_regs = await self.read_registers(self.REG_ENERGY_LEGACY, 2)
                if energy_regs and (energy_regs[0] != 0 or energy_regs[1] != 0):
                    energy_raw = self.decode_unsigned_32bit(energy_regs)
                    return energy_raw / 800.0  # Legacy also uses scale 0.00125
                
                # Try total active energy forward (address 99, scale 0.00125 = divide by 800)
                energy_regs = await self.read_registers(self.REG_TOTAL_ENERGY_FORWARD, 2)
                if energy_regs and (energy_regs[0] != 0 or energy_regs[1] != 0):
                    energy_raw = self.decode_unsigned_32bit(energy_regs)
                    return energy_raw / 800.0  # Scale 0.00125 = divide by 800
                
                # Try alternative energy register (address 104, scale 0.001 = divide by 1000)
                energy_regs = await self.read_registers(104, 2)
                if energy_regs and (energy_regs[0] != 0 or energy_regs[1] != 0):
                    energy_raw = self.decode_unsigned_32bit(energy_regs)
                    return energy_raw / 1000.0
            else:
                # Extended first (default)
                # Try total active energy forward (address 99, scale 0.00125 = divide by 800)
                energy_regs = await self.read_registers(self.REG_TOTAL_ENERGY_FORWARD, 2)
                if energy_regs and (energy_regs[0] != 0 or energy_regs[1] != 0):
                    energy_raw = self.decode_unsigned_32bit(energy_regs)
                    return energy_raw / 800.0  # Scale 0.00125 = divide by 800
                
                # Try alternative energy register (address 104, scale 0.001 = divide by 1000)
                energy_regs = await self.read_registers(104, 2)
                if energy_regs and (energy_regs[0] != 0 or energy_regs[1] != 0):
                    energy_raw = self.decode_unsigned_32bit(energy_regs)
                    return energy_raw / 1000.0
                
                # Try sum forward energy legacy (address 34, scale 0.00125 = divide by 800)
                energy_regs = await self.read_registers(34, 2)
                if energy_regs and (energy_regs[0] != 0 or energy_regs[1] != 0):
                    energy_raw = self.decode_unsigned_32bit(energy_regs)
                    return energy_raw / 800.0
                
                # Fallback to legacy Phase A forward energy (address 4, scale 0.00125 = divide by 800)
                energy_regs = await self.read_registers(self.REG_ENERGY_LEGACY, 2)
                if energy_regs and (energy_regs[0] != 0 or energy_regs[1] != 0):
                    energy_raw = self.decode_unsigned_32bit(energy_regs)
                    return energy_raw / 800.0  # Legacy also uses scale 0.00125
            
            return None
        
        energy = await try_read_energy()
        if energy is not None:
            data['energy_kwh'] = energy
        
        # Try frequency - order depends on prefer_legacy_registers flag
        async def try_read_frequency() -> Optional[float]:
            if self.prefer_legacy_registers:
                # Legacy first
                freq_regs = await self.read_registers(self.REG_FREQUENCY_LEGACY, 1)
                if freq_regs and freq_regs[0] != 0:
                    return freq_regs[0] / 100.0  # Scale 0.01
                freq_regs = await self.read_registers(self.REG_FREQUENCY, 1)
                if freq_regs and freq_regs[0] != 0:
                    return freq_regs[0] / 100.0  # Scale 0.01
            else:
                # Extended first (default)
                freq_regs = await self.read_registers(self.REG_FREQUENCY, 1)
                if freq_regs and freq_regs[0] != 0:
                    return freq_regs[0] / 100.0  # Scale 0.01
                freq_regs = await self.read_registers(self.REG_FREQUENCY_LEGACY, 1)
                if freq_regs and freq_regs[0] != 0:
                    return freq_regs[0] / 100.0
            return None
        
        frequency = await try_read_frequency()
        if frequency is not None:
            data['frequency_hz'] = frequency
        
        # Try power factor - order depends on prefer_legacy_registers flag
        async def try_read_power_factor() -> Optional[float]:
            if self.prefer_legacy_registers:
                # Legacy first
                pf_regs = await self.read_registers(self.REG_POWER_FACTOR_LEGACY, 1)
                if pf_regs and pf_regs[0] != 0:
                    return pf_regs[0] / 1000.0
                pf_regs = await self.read_registers(self.REG_POWER_FACTOR_A, 1)
                if pf_regs and pf_regs[0] != 0:
                    return pf_regs[0] / 1000.0
            else:
                # Extended first (default)
                pf_regs = await self.read_registers(self.REG_POWER_FACTOR_A, 1)
                if pf_regs and pf_regs[0] != 0:
                    return pf_regs[0] / 1000.0
                pf_regs = await self.read_registers(self.REG_POWER_FACTOR_LEGACY, 1)
                if pf_regs and pf_regs[0] != 0:
                    return pf_regs[0] / 1000.0
            return None
        
        pf = await try_read_power_factor()
        if pf is not None:
            data['power_factor'] = pf
        
        return data if data else None
    
    async def read_phase_data(self) -> Optional[Dict[str, Any]]:
        """Read three-phase data (Phase A, B, C)."""
        log.info("Reading three-phase data...")
        
        phase_data: Dict[str, Dict[str, Any]] = {}
        
        # Try addresses - order depends on prefer_legacy_registers flag
        async def try_read_voltage(standard_addr: int, legacy_addr: int) -> Optional[float]:
            if self.prefer_legacy_registers:
                # Legacy first
                regs = await self.read_registers(legacy_addr, 1)
                if regs and regs[0] != 0:
                    return regs[0] / 100.0
                regs = await self.read_registers(standard_addr, 1)
                if regs and regs[0] != 0:
                    return regs[0] / 100.0
            else:
                # Extended first (default)
                regs = await self.read_registers(standard_addr, 1)
                if regs and regs[0] != 0:
                    return regs[0] / 100.0
                regs = await self.read_registers(legacy_addr, 1)
                if regs and regs[0] != 0:
                    return regs[0] / 100.0
            return None
        
        async def try_read_current(standard_addr: int, legacy_addr: int) -> Optional[float]:
            if self.prefer_legacy_registers:
                # Legacy first
                regs = await self.read_registers(legacy_addr, 1)
                if regs and regs[0] != 0:
                    return regs[0] / 100.0
                regs = await self.read_registers(standard_addr, 1)
                if regs and regs[0] != 0:
                    return regs[0] / 100.0
            else:
                # Extended first (default)
                regs = await self.read_registers(standard_addr, 1)
                if regs and regs[0] != 0:
                    return regs[0] / 100.0
                regs = await self.read_registers(legacy_addr, 1)
                if regs and regs[0] != 0:
                    return regs[0] / 100.0
            return None
        
        async def try_read_power(standard_addr: int, legacy_addr: int) -> Optional[int]:
            if self.prefer_legacy_registers:
                # Legacy first (2 registers, S32)
                regs = await self.read_registers(legacy_addr, 2)
                if regs and (regs[0] != 0 or regs[1] != 0):
                    return self.decode_signed_32bit(regs)
                # Try standard (U16)
                regs = await self.read_registers(standard_addr, 1)
                if regs and regs[0] != 0:
                    power_val = regs[0]
                    if power_val & 0x8000:
                        return power_val - 0x10000
                    return power_val
            else:
                # Extended first (default)
                # Try standard (U16)
                regs = await self.read_registers(standard_addr, 1)
                if regs and regs[0] != 0:
                    power_val = regs[0]
                    if power_val & 0x8000:
                        return power_val - 0x10000
                    return power_val
                # Try legacy (2 registers, S32)
                regs = await self.read_registers(legacy_addr, 2)
                if regs and (regs[0] != 0 or regs[1] != 0):
                    return self.decode_signed_32bit(regs)
            return None
        
        async def try_read_power_factor(standard_addr: int, legacy_addr: int) -> Optional[float]:
            if self.prefer_legacy_registers:
                # Legacy first
                regs = await self.read_registers(legacy_addr, 1)
                if regs and regs[0] != 0:
                    return regs[0] / 1000.0
                regs = await self.read_registers(standard_addr, 1)
                if regs and regs[0] != 0:
                    return regs[0] / 1000.0
            else:
                # Extended first (default)
                regs = await self.read_registers(standard_addr, 1)
                if regs and regs[0] != 0:
                    return regs[0] / 1000.0
                regs = await self.read_registers(legacy_addr, 1)
                if regs and regs[0] != 0:
                    return regs[0] / 1000.0
            return None
        
        # Phase A
        phase_a: Dict[str, Any] = {}
        voltage = await try_read_voltage(self.REG_VOLTAGE_A, self.REG_VOLTAGE_LEGACY)
        if voltage is not None:
            phase_a['voltage_v'] = voltage
        
        current = await try_read_current(self.REG_CURRENT_A, self.REG_CURRENT_LEGACY)
        if current is not None:
            phase_a['current_a'] = current
        
        power = await try_read_power(self.REG_POWER_A, self.REG_POWER_LEGACY)
        if power is not None:
            phase_a['power_w'] = power
        
        pf = await try_read_power_factor(self.REG_POWER_FACTOR_A, self.REG_POWER_FACTOR_LEGACY)
        if pf is not None:
            phase_a['power_factor'] = pf
        
        if phase_a:
            phase_data['phase_a'] = phase_a
        
        # Phase B (legacy addresses: 10, 11, 12, 18)
        phase_b: Dict[str, Any] = {}
        voltage = await try_read_voltage(self.REG_VOLTAGE_B, 10)
        if voltage is not None:
            phase_b['voltage_v'] = voltage
        
        current = await try_read_current(self.REG_CURRENT_B, 11)
        if current is not None:
            phase_b['current_a'] = current
        
        power = await try_read_power(self.REG_POWER_B, 12)
        if power is not None:
            phase_b['power_w'] = power
        
        pf = await try_read_power_factor(self.REG_POWER_FACTOR_B, 18)
        if pf is not None:
            phase_b['power_factor'] = pf
        
        if phase_b:
            phase_data['phase_b'] = phase_b
        
        # Phase C (legacy addresses: 20, 21, 22, 28)
        phase_c: Dict[str, Any] = {}
        voltage = await try_read_voltage(self.REG_VOLTAGE_C, 20)
        if voltage is not None:
            phase_c['voltage_v'] = voltage
        
        current = await try_read_current(self.REG_CURRENT_C, 21)
        if current is not None:
            phase_c['current_a'] = current
        
        power = await try_read_power(self.REG_POWER_C, 22)
        if power is not None:
            phase_c['power_w'] = power
        
        pf = await try_read_power_factor(self.REG_POWER_FACTOR_C, 28)
        if pf is not None:
            phase_c['power_factor'] = pf
        
        if phase_c:
            phase_data['phase_c'] = phase_c
        
        return phase_data if phase_data else None
    
    def print_basic_data(self, data: Dict[str, Any]):
        """Print basic meter data in a formatted way."""
        print(f"\n{'='*60}")
        print("IAMMeter - Basic Data")
        print(f"{'='*60}")
        print(f"Voltage:        {data.get('voltage_v', 'N/A'):>8} V")
        print(f"Current:        {data.get('current_a', 'N/A'):>8} A")
        power = data.get('power_w', 0)
        power_str = f"{power:>8} W"
        if power > 0:
            power_str += " (Import)"
        elif power < 0:
            power_str += " (Export)"
        print(f"Power:          {power_str}")
        print(f"Energy:         {data.get('energy_kwh', 'N/A'):>8} kWh")
        print(f"Frequency:      {data.get('frequency_hz', 'N/A'):>8} Hz")
        print(f"Power Factor:   {data.get('power_factor', 'N/A'):>8}")
    
    def print_phase_data(self, phase_data: Dict[str, Dict[str, Any]]):
        """Print three-phase data in a formatted way."""
        print(f"\n{'='*60}")
        print("IAMMeter - Three-Phase Data")
        print(f"{'='*60}")
        
        for phase_key, phase_info in phase_data.items():
            phase_name = phase_key.replace('phase_', '').upper()
            print(f"\n{phase_name}:")
            print(f"  Voltage:      {phase_info.get('voltage_v', 'N/A'):>8} V")
            print(f"  Current:      {phase_info.get('current_a', 'N/A'):>8} A")
            power = phase_info.get('power_w', 0)
            power_str = f"{power:>8} W"
            if power > 0:
                power_str += " (Import)"
            elif power < 0:
                power_str += " (Export)"
            print(f"  Power:        {power_str}")
            print(f"  Power Factor: {phase_info.get('power_factor', 'N/A'):>8}")
    
    async def test_single_register(self, addr: int, count: int = 1):
        """Test reading a single register or register range."""
        print(f"\n{'='*60}")
        print(f"Testing Register Read")
        print(f"{'='*60}")
        print(f"Address: 0x{addr:04X} ({addr})")
        print(f"Count: {count}")
        print(f"Unit ID: {self.unit_id}")
        
        regs = await self.read_registers(addr, count)
        if regs:
            print(f"\n✓ Success! Read {len(regs)} register(s):")
            for i, val in enumerate(regs):
                current_addr = addr + i
                print(f"  0x{current_addr:04X} ({current_addr:5d}): 0x{val:04X} ({val:5d})")
        else:
            print(f"\n✗ Failed to read registers")
    
    def _decode_register_value(self, reg_info: Dict[str, Any], raw_values: List[int]) -> Any:
        """Decode register value based on register info from JSON map."""
        reg_type = (reg_info.get("type") or "").upper()
        size = max(1, int(reg_info.get("size", 1)))
        scale = reg_info.get("scale")
        
        if size == 1 and raw_values:
            val = int(raw_values[0])
            if "S16" in reg_type and val >= 0x8000:
                val = val - 0x10000
        elif size == 2 and raw_values and len(raw_values) >= 2:
            hi, lo = raw_values[0], raw_values[1]
            val = (hi << 16) | lo
            if "S32" in reg_type and val & 0x80000000:
                val = -((~val & 0xFFFFFFFF) + 1)
        else:
            val = 0
        
        if scale and isinstance(val, (int, float)):
            val = val * scale
        
        return val
    
    async def read_all_registers_from_map(self) -> Dict[str, Any]:
        """Read all registers defined in the JSON register map."""
        if not self.register_map:
            log.warning("No register map loaded")
            return {}
        
        results: Dict[str, Any] = {}
        
        for reg_info in self.register_map:
            reg_id = reg_info.get("id")
            if not reg_id:
                continue
            
            # Skip write-only registers
            if str(reg_info.get("rw", "RO")).upper() in ("WO", "Write-Only"):
                continue
            
            # Only read holding/input registers
            kind = (reg_info.get("kind") or "").lower()
            if kind not in ("holding", "input"):
                continue
            
            addr = int(reg_info.get("addr", 0))
            size = max(1, int(reg_info.get("size", 1)))
            
            try:
                raw_values = await self.read_registers(addr, size)
                if raw_values:
                    decoded_value = self._decode_register_value(reg_info, raw_values)
                    results[reg_id] = {
                        "value": decoded_value,
                        "raw": raw_values,
                        "address": addr,
                        "name": reg_info.get("name", ""),
                        "unit": reg_info.get("unit", ""),
                        "scale": reg_info.get("scale")
                    }
                else:
                    results[reg_id] = None
            except Exception as e:
                log.debug(f"Failed to read register {reg_id} at address {addr}: {e}")
                results[reg_id] = None
        
        return results
    
    def print_all_registers(self, all_registers: Dict[str, Any]):
        """Print all register values in a formatted table."""
        print(f"\n{'='*80}")
        print("IAMMeter - All Registers from JSON Map")
        print(f"{'='*80}\n")
        
        # Group registers by category
        legacy_regs = []
        extended_regs = []
        other_regs = []
        
        for reg_id, reg_data in sorted(all_registers.items()):
            if reg_data is None:
                continue
            
            addr = reg_data.get("address", 0)
            if addr < 72:
                legacy_regs.append((reg_id, reg_data))
            elif addr >= 72:
                extended_regs.append((reg_id, reg_data))
            else:
                other_regs.append((reg_id, reg_data))
        
        def print_register_group(title: str, regs: List[tuple]):
            if not regs:
                return
            print(f"\n{title}")
            print("-" * 80)
            print(f"{'ID':<40} {'Addr':<8} {'Value':<15} {'Unit':<8} {'Name'}")
            print("-" * 80)
            for reg_id, reg_data in regs:
                value = reg_data.get("value")
                addr = reg_data.get("address", 0)
                unit = reg_data.get("unit", "")
                name = reg_data.get("name", "")
                
                # Format value
                if isinstance(value, float):
                    value_str = f"{value:.3f}"
                elif isinstance(value, int):
                    value_str = f"{value}"
                elif value is None:
                    value_str = "None"
                else:
                    value_str = str(value)
                
                print(f"{reg_id:<40} 0x{addr:04X}   {value_str:<15} {unit:<8} {name}")
        
        print_register_group("Legacy Registers (0-71)", legacy_regs)
        print_register_group("Extended Registers (72+)", extended_regs)
        if other_regs:
            print_register_group("Other Registers", other_regs)
        
        print(f"\n{'='*80}")
        print(f"Total registers read: {len([r for r in all_registers.values() if r is not None])}")
        print(f"{'='*80}")


async def main():
    parser = argparse.ArgumentParser(
        description='Test IAMMeter connectivity and register reading',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test basic connectivity
  python test_iammeter.py --host 192.168.1.100
  
  # Test with custom port and unit ID
  python test_iammeter.py --host 192.168.1.100 --port 502 --unit-id 1
  
  # Read all data (basic + three-phase)
  python test_iammeter.py --host 192.168.1.100 --read-all
  
  # Test specific register
  python test_iammeter.py --host 192.168.1.100 --test-register 0x48
  
  # Read three-phase data only
  python test_iammeter.py --host 192.168.1.100 --read-phases
        """
    )
    
    parser.add_argument('--host', '-H', required=True,
                       help='IAMMeter device IP address (e.g., 192.168.1.100)')
    parser.add_argument('--port', '-p', type=int, default=502,
                       help='Modbus TCP port (default: 502)')
    parser.add_argument('--unit-id', '-u', type=int, default=1,
                       help='Modbus unit ID (default: 1)')
    parser.add_argument('--timeout', type=float, default=3.0,
                       help='Timeout in seconds (default: 3.0)')
    parser.add_argument('--read-all', action='store_true',
                       help='Read all data (basic + three-phase + serial number)')
    parser.add_argument('--read-phases', action='store_true',
                       help='Read three-phase data only')
    parser.add_argument('--test-register', type=str,
                       help='Test reading a specific register (hex format, e.g., 0x48)')
    parser.add_argument('--test-register-count', type=int, default=1,
                       help='Number of registers to read when testing (default: 1)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    parser.add_argument('--scan-registers', action='store_true',
                       help='Scan common register addresses to find non-zero values')
    parser.add_argument('--scan-start', type=int, default=0,
                       help='Start address for register scan (default: 0)')
    parser.add_argument('--scan-end', type=int, default=150,
                       help='End address for register scan (default: 150)')
    parser.add_argument('--read-all-registers', action='store_true',
                       help='Read and print all registers from JSON register map')
    parser.add_argument('--register-map', type=str,
                       help='Path to register map JSON file (default: register_maps/iammeter_registers.json)')
    parser.add_argument('--prefer-legacy', action='store_true',
                       help='Prefer legacy registers (0-36) over extended registers (72-120). Reads legacy first, then falls back to extended if legacy values are zero.')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create tester
    tester = IAMMeterStandaloneTester(
        host=args.host,
        port=args.port,
        unit_id=args.unit_id,
        timeout=args.timeout,
        register_map_file=args.register_map,
        prefer_legacy_registers=args.prefer_legacy
    )
    
    try:
        # Connect
        if not await tester.connect():
            print("\n✗ Failed to connect. Check:")
            print("  - IP address is correct")
            print("  - Device is powered on and connected to network")
            print("  - Port 502 is not blocked by firewall")
            print("  - Device supports Modbus/TCP")
            return 1
        
        # Scan registers if requested
        if args.scan_registers:
            print(f"\n{'='*60}")
            print(f"Scanning Registers {args.scan_start} to {args.scan_end}")
            print(f"{'='*60}\n")
            found_any = False
            for addr in range(args.scan_start, args.scan_end + 1):
                regs = await tester.read_registers(addr, 1)
                if regs and regs[0] != 0:
                    print(f"  0x{addr:04X} ({addr:5d}): 0x{regs[0]:04X} ({regs[0]:5d})")
                    found_any = True
            if not found_any:
                print("  No non-zero registers found in scan range")
            print(f"\n{'='*60}")
            return 0
        
        # Test specific register if requested
        if args.test_register:
            try:
                if args.test_register.startswith('0x') or args.test_register.startswith('0X'):
                    reg_addr = int(args.test_register, 16)
                else:
                    reg_addr = int(args.test_register)
                await tester.test_single_register(reg_addr, args.test_register_count)
                return 0
            except ValueError:
                print(f"✗ Invalid register address: {args.test_register}")
                return 1
        
        # Test connectivity
        if not await tester.test_connectivity():
            print(f"\n✗ IAMMeter at {args.host} is not responding")
            print("\nTroubleshooting:")
            print(f"  - Check if IP address {args.host} is correct")
            print("  - Verify device is powered on")
            print("  - Check network connectivity (ping the device)")
            print("  - Verify Modbus/TCP is enabled on the device")
            print("  - Try different unit ID: --unit-id 1, 2, or 255")
            return 1
        
        # Read serial number
        serial = await tester.read_serial_number()
        if serial:
            print(f"\n✓ Serial Number: {serial}")
        
        # Read all registers from JSON map if requested
        if args.read_all_registers:
            print(f"\nReading all registers from JSON map...")
            all_registers = await tester.read_all_registers_from_map()
            tester.print_all_registers(all_registers)
            return 0
        
        # Read all data if requested
        if args.read_all:
            # Basic data
            basic_data = await tester.read_basic_data()
            if basic_data:
                tester.print_basic_data(basic_data)
            
            # Three-phase data
            phase_data = await tester.read_phase_data()
            if phase_data:
                tester.print_phase_data(phase_data)
            
            # All registers from JSON map
            if tester.register_map:
                print(f"\nReading all registers from JSON map...")
                all_registers = await tester.read_all_registers_from_map()
                tester.print_all_registers(all_registers)
            
            print(f"\n{'='*60}")
            print("✓ Test completed successfully!")
            print(f"{'='*60}")
            return 0
        
        # Read three-phase data only if requested
        if args.read_phases:
            phase_data = await tester.read_phase_data()
            if phase_data:
                tester.print_phase_data(phase_data)
            else:
                print(f"\n✗ Failed to read three-phase data")
                return 1
            return 0
        
        # Default: read basic data
        basic_data = await tester.read_basic_data()
        if basic_data:
            tester.print_basic_data(basic_data)
        else:
            print(f"\n✗ Failed to read basic data from IAMMeter")
            return 1
        
        print(f"\n{'='*60}")
        print("✓ Test completed successfully!")
        print(f"{'='*60}")
        return 0
        
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        return 1
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        await tester.close()


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))

