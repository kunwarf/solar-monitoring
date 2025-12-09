#!/usr/bin/env python3
"""
Standalone Senergy Register Scanner

A utility class for reading and displaying all registers from Senergy inverters.
This helps discover missing registers and understand available data.
"""

import asyncio
import logging
import struct
import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusException

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

@dataclass
class RegisterInfo:
    """Information about a register."""
    address: int
    size: int
    data_type: str
    value: Any
    raw_value: List[int]
    description: str = ""
    unit: str = ""
    scale: float = 1.0

@dataclass
class CustomRegisterRequest:
    """Custom register reading request with user-specified parameters."""
    address: int
    length: int  # Number of registers to read (1, 2, 3, etc.)
    unit: str = ""  # Unit for display (e.g., "W", "V", "A", "%", "kWh")
    scale: float = 1.0  # Scaling factor to apply to raw value
    data_type: str = "auto"  # "auto", "uint16", "int16", "uint32", "int32", "float32", "ascii"
    description: str = ""  # Optional description

class SenergyRegisterScanner:
    """Standalone class for scanning Senergy inverter registers."""
    
    def __init__(self, port: str = "/dev/ttyUSB2", baudrate: int = 9600, 
                 slave_id: int = 1, timeout: float = 3.0):
        """
        Initialize the register scanner.
        
        Args:
            port: Serial port (e.g., "/dev/ttyUSB0" or "COM3")
            baudrate: Baud rate (default 9600)
            slave_id: Modbus slave ID (default 1)
            timeout: Communication timeout in seconds
        """
        self.port = port
        self.baudrate = baudrate
        self.slave_id = slave_id
        self.timeout = timeout
        self.client: Optional[ModbusSerialClient] = None
        
        # Register type definitions
        self.register_types = {
            'U16': {'size': 1, 'format': 'H', 'signed': False},
            'S16': {'size': 1, 'format': 'h', 'signed': True},
            'U32': {'size': 2, 'format': 'I', 'signed': False},
            'S32': {'size': 2, 'format': 'i', 'signed': True},
        }
        
        # Known register definitions from specification
        self.known_registers = self._load_known_registers()
        
    def _load_known_registers(self) -> Dict[int, Dict[str, Any]]:
        """Load known register definitions from the specification."""
        return {
            # Device Information (0x1A00-0x1A7F)
            0x1A00: {'name': 'Device Model', 'type': 'U16', 'size': 8, 'unit': 'ASCII'},
            0x1A10: {'name': 'Device Serial Number', 'type': 'U16', 'size': 8, 'unit': 'ASCII'},
            0x1A18: {'name': 'Modbus Protocol Version', 'type': 'U16', 'size': 1},
            0x1A1C: {'name': 'Master Software Version', 'type': 'U16', 'size': 3, 'unit': 'ASCII'},
            0x1A1D: {'name': 'Master Software Build Date', 'type': 'U16', 'size': 3, 'unit': 'ASCII'},
            0x1A26: {'name': 'Slave Firmware Version', 'type': 'U16', 'size': 3, 'unit': 'ASCII'},
            0x1A2D: {'name': 'Slave Firmware Build Date', 'type': 'U16', 'size': 3, 'unit': 'ASCII'},
            0x1A3B: {'name': 'MPPT Number', 'type': 'U16', 'size': 1},
            0x1A44: {'name': 'Rated Voltage', 'type': 'U16', 'size': 1, 'unit': 'V', 'scale': 0.1},
            0x1A45: {'name': 'Rated Frequency', 'type': 'U16', 'size': 1, 'unit': 'Hz', 'scale': 0.01},
            0x1A46: {'name': 'Rated Power', 'type': 'U16', 'size': 1, 'unit': 'W'},
            0x1A48: {'name': 'Grid Phase Number', 'type': 'U16', 'size': 1},
            0x1A5A: {'name': 'Production Type', 'type': 'U16', 'size': 1},
            0x1A60: {'name': 'EMS Firmware Version', 'type': 'U16', 'size': 3, 'unit': 'ASCII'},
            0x1A67: {'name': 'EMS Firmware Build Date', 'type': 'U16', 'size': 7, 'unit': 'ASCII'},
            0x1A6F: {'name': 'DCDC Firmware Version', 'type': 'U16', 'size': 3, 'unit': 'ASCII'},
            0x1A76: {'name': 'DCDC Firmware Build Date', 'type': 'U16', 'size': 3, 'unit': 'ASCII'},
            
            # Real-time Data (0x1001-0x2013)
            0x1001: {'name': 'Phase A Voltage', 'type': 'U16', 'size': 1, 'unit': 'V', 'scale': 0.1},
            0x1002: {'name': 'Phase A Current', 'type': 'U16', 'size': 1, 'unit': 'A', 'scale': 0.01},
            0x1003: {'name': 'Phase A Power', 'type': 'S32', 'size': 2, 'unit': 'W', 'scale': 0.1},
            0x1005: {'name': 'Phase A Frequency', 'type': 'U16', 'size': 1, 'unit': 'Hz', 'scale': 0.01},
            0x1006: {'name': 'Phase B Voltage', 'type': 'U16', 'size': 1, 'unit': 'V', 'scale': 0.1},
            0x1007: {'name': 'Phase B Current', 'type': 'U16', 'size': 1, 'unit': 'A', 'scale': 0.01},
            0x1008: {'name': 'Phase B Power', 'type': 'S32', 'size': 2, 'unit': 'W', 'scale': 0.1},
            0x100A: {'name': 'Phase B Frequency', 'type': 'U16', 'size': 1, 'unit': 'Hz', 'scale': 0.01},
            0x100B: {'name': 'Phase C Voltage', 'type': 'U16', 'size': 1, 'unit': 'V', 'scale': 0.1},
            0x100C: {'name': 'Phase C Current', 'type': 'U16', 'size': 1, 'unit': 'A', 'scale': 0.01},
            0x100D: {'name': 'Phase C Power', 'type': 'S32', 'size': 2, 'unit': 'W', 'scale': 0.1},
            0x100F: {'name': 'Phase C Frequency', 'type': 'U16', 'size': 1, 'unit': 'Hz', 'scale': 0.01},
            0x1010: {'name': 'PV1 Voltage', 'type': 'U16', 'size': 1, 'unit': 'V', 'scale': 0.1},
            0x1011: {'name': 'PV1 Current', 'type': 'U16', 'size': 1, 'unit': 'A', 'scale': 0.01},
            0x1012: {'name': 'MPPT1 Power', 'type': 'U32', 'size': 2, 'unit': 'W', 'scale': 0.1},
            0x1014: {'name': 'PV2 Voltage', 'type': 'U16', 'size': 1, 'unit': 'V', 'scale': 0.1},
            0x1015: {'name': 'PV2 Current', 'type': 'U16', 'size': 1, 'unit': 'A', 'scale': 0.01},
            0x1016: {'name': 'MPPT2 Power', 'type': 'U32', 'size': 2, 'unit': 'W', 'scale': 0.1},
            0x1018: {'name': 'PV3 Voltage', 'type': 'U16', 'size': 1, 'unit': 'V', 'scale': 0.1},
            0x1019: {'name': 'PV3 Current', 'type': 'U16', 'size': 1, 'unit': 'A', 'scale': 0.01},
            0x101A: {'name': 'MPPT3 Power', 'type': 'U32', 'size': 2, 'unit': 'W', 'scale': 0.1},
            0x101C: {'name': 'Inner Temperature', 'type': 'S16', 'size': 1, 'unit': '°C'},
            0x101D: {'name': 'Inverter Mode', 'type': 'U16', 'size': 1},
            0x101E: {'name': 'Error Code', 'type': 'U32', 'size': 2},
            0x1021: {'name': 'Total Energy', 'type': 'U32', 'size': 2, 'unit': 'kWh'},
            0x1023: {'name': 'Total Generation Time', 'type': 'U32', 'size': 2, 'unit': 'Hour'},
            0x1027: {'name': 'Today Energy', 'type': 'U32', 'size': 2, 'unit': 'Wh'},
            0x1037: {'name': 'Active Power', 'type': 'S32', 'size': 2, 'unit': 'W', 'scale': 0.1},
            0x1039: {'name': 'Reactive Power', 'type': 'S32', 'size': 2, 'unit': 'Var', 'scale': 0.1},
            0x103B: {'name': 'Today Peak Power', 'type': 'S32', 'size': 2, 'unit': 'W', 'scale': 0.1},
            0x103D: {'name': 'Power Factor', 'type': 'S16', 'size': 1, 'scale': 0.001},
            0x103E: {'name': 'PV4 Voltage', 'type': 'U16', 'size': 1, 'unit': 'V', 'scale': 0.1},
            0x103F: {'name': 'PV4 Current', 'type': 'U16', 'size': 1, 'unit': 'A', 'scale': 0.01},
            0x1040: {'name': 'MPPT4 Power', 'type': 'U32', 'size': 2, 'unit': 'W', 'scale': 0.1},
            0x104C: {'name': 'Decimals of Total Energy', 'type': 'U16', 'size': 1, 'unit': 'Wh'},
            0x1300: {'name': 'Phase R Watt of Grid', 'type': 'S32', 'size': 2, 'unit': 'W', 'scale': 0.1},
            0x1302: {'name': 'Phase S Watt of Grid', 'type': 'S32', 'size': 2, 'unit': 'W', 'scale': 0.1},
            0x1304: {'name': 'Phase T Watt of Grid', 'type': 'S32', 'size': 2, 'unit': 'W', 'scale': 0.1},
            0x1306: {'name': 'Accumulated Energy Positive', 'type': 'U32', 'size': 2, 'unit': 'Wh', 'scale': 10},
            0x1308: {'name': 'Accumulated Energy Negative', 'type': 'U32', 'size': 2, 'unit': 'Wh', 'scale': 10},
            0x130A: {'name': 'Phase R Watt of Load', 'type': 'S32', 'size': 2, 'unit': 'W', 'scale': 0.1},
            0x130C: {'name': 'Phase S Watt of Load', 'type': 'S32', 'size': 2, 'unit': 'W', 'scale': 0.1},
            0x130E: {'name': 'Phase T Watt of Load', 'type': 'S32', 'size': 2, 'unit': 'W', 'scale': 0.1},
            0x1310: {'name': 'Accumulated Energy of Load', 'type': 'U32', 'size': 2, 'unit': 'Wh', 'scale': 10},
            0x131A: {'name': 'L1-N Phase Voltage of Grid', 'type': 'U16', 'size': 1, 'unit': 'V', 'scale': 0.1},
            0x131B: {'name': 'L2-N Phase Voltage of Grid', 'type': 'U16', 'size': 1, 'unit': 'V', 'scale': 0.1},
            0x131C: {'name': 'L3-N Phase Voltage of Grid', 'type': 'U16', 'size': 1, 'unit': 'V', 'scale': 0.1},
            0x131D: {'name': 'L1 Current of Grid', 'type': 'S32', 'size': 2, 'unit': 'A', 'scale': 0.01},
            0x131F: {'name': 'L2 Current of Grid', 'type': 'S32', 'size': 2, 'unit': 'A', 'scale': 0.01},
            0x1321: {'name': 'L3 Current of Grid', 'type': 'S32', 'size': 2, 'unit': 'A', 'scale': 0.01},
            0x1323: {'name': 'L1-N Phase Voltage of Load', 'type': 'U16', 'size': 1, 'unit': 'V', 'scale': 0.1},
            0x1324: {'name': 'L2-N Phase Voltage of Load', 'type': 'U16', 'size': 1, 'unit': 'V', 'scale': 0.1},
            0x1325: {'name': 'L3-N Phase Voltage of Load', 'type': 'U16', 'size': 1, 'unit': 'V', 'scale': 0.1},
            0x1326: {'name': 'L1 Current of Load', 'type': 'S32', 'size': 2, 'unit': 'A', 'scale': 0.01},
            0x1328: {'name': 'L2 Current of Load', 'type': 'S32', 'size': 2, 'unit': 'A', 'scale': 0.01},
            0x132A: {'name': 'L3 Current of Load', 'type': 'S32', 'size': 2, 'unit': 'A', 'scale': 0.01},
            0x1332: {'name': 'Today Import Energy', 'type': 'U32', 'size': 2, 'unit': 'Wh', 'scale': 10},
            0x1334: {'name': 'Today Export Energy', 'type': 'U32', 'size': 2, 'unit': 'Wh', 'scale': 10},
            0x1336: {'name': 'Today Load Energy', 'type': 'U32', 'size': 2, 'unit': 'Wh', 'scale': 10},
            0x1338: {'name': 'Frequency of Grid', 'type': 'U16', 'size': 1, 'unit': 'Hz', 'scale': 0.01},
            0x1350: {'name': 'Phase R Voltage of EPS', 'type': 'U16', 'size': 1, 'unit': 'V', 'scale': 0.1},
            0x1351: {'name': 'Phase R Current of EPS', 'type': 'S32', 'size': 2, 'unit': 'A', 'scale': 0.01},
            0x1353: {'name': 'Phase R Watt of EPS', 'type': 'S32', 'size': 2, 'unit': 'W', 'scale': 0.1},
            0x1355: {'name': 'Frequency of EPS', 'type': 'U16', 'size': 1, 'unit': 'Hz', 'scale': 0.01},
            0x1356: {'name': 'Phase S Voltage of EPS', 'type': 'U16', 'size': 1, 'unit': 'V', 'scale': 0.1},
            0x1357: {'name': 'Phase S Current of EPS', 'type': 'S32', 'size': 2, 'unit': 'A', 'scale': 0.01},
            0x1359: {'name': 'Phase S Watt of EPS', 'type': 'S32', 'size': 2, 'unit': 'W', 'scale': 0.1},
            0x135B: {'name': 'Phase T Voltage of EPS', 'type': 'U16', 'size': 1, 'unit': 'V', 'scale': 0.1},
            0x135C: {'name': 'Phase T Current of EPS', 'type': 'S32', 'size': 2, 'unit': 'A', 'scale': 0.01},
            0x135E: {'name': 'Phase T Watt of EPS', 'type': 'S32', 'size': 2, 'unit': 'W', 'scale': 0.1},
            0x1360: {'name': 'Daily Energy to EPS', 'type': 'U32', 'size': 2, 'unit': 'Wh', 'scale': 10},
            0x1362: {'name': 'Accumulated Energy to EPS', 'type': 'U32', 'size': 2, 'unit': 'Wh', 'scale': 10},
            0x2000: {'name': 'Battery SOC', 'type': 'U16', 'size': 1, 'unit': '%'},
            0x2001: {'name': 'Battery Temperature', 'type': 'S16', 'size': 1, 'unit': '°C'},
            0x2006: {'name': 'Battery Voltage', 'type': 'U16', 'size': 1, 'unit': 'V', 'scale': 0.1},
            0x2007: {'name': 'Battery Current', 'type': 'S32', 'size': 2, 'unit': 'A', 'scale': 0.01},
            0x2009: {'name': 'Battery Power', 'type': 'U32', 'size': 2, 'unit': 'W', 'scale': 0.1},
            0x200B: {'name': 'Battery Daily Charge Energy', 'type': 'U32', 'size': 2, 'unit': 'Wh', 'scale': 10},
            0x200D: {'name': 'Battery Accumulated Charge Energy', 'type': 'U32', 'size': 2, 'unit': 'Wh', 'scale': 10},
            0x200F: {'name': 'Battery Daily Discharge Energy', 'type': 'U32', 'size': 2, 'unit': 'Wh', 'scale': 10},
            0x2011: {'name': 'Battery Accumulated Discharge Energy', 'type': 'U32', 'size': 2, 'unit': 'Wh', 'scale': 10},
            0x2013: {'name': 'Error Message 4', 'type': 'U16', 'size': 1},
            
            # Parameters (0x2100-0x2121)
            0x2100: {'name': 'Hybrid Work Mode', 'type': 'U16', 'size': 1, 'rw': 'RW'},
            0x2101: {'name': 'Once/Everyday', 'type': 'U16', 'size': 1, 'rw': 'RW'},
            0x2102: {'name': 'Charge Start Time 1', 'type': 'U16', 'size': 1, 'rw': 'RW'},
            0x2103: {'name': 'Charge End Time 1', 'type': 'U16', 'size': 1, 'rw': 'RW'},
            0x2104: {'name': 'Discharge Start Time 1', 'type': 'U16', 'size': 1, 'rw': 'RW'},
            0x2105: {'name': 'Discharge End Time 1', 'type': 'U16', 'size': 1, 'rw': 'RW'},
            0x2110: {'name': 'Battery Type Selection', 'type': 'U16', 'size': 1, 'rw': 'RW'},
            0x2111: {'name': 'Comm Address', 'type': 'U16', 'size': 1, 'rw': 'RW'},
            0x2112: {'name': 'Battery Ah', 'type': 'U16', 'size': 1, 'unit': 'Ah', 'rw': 'RW'},
            0x2113: {'name': 'Stop Discharge Voltage', 'type': 'U16', 'size': 1, 'unit': 'V', 'scale': 0.1, 'rw': 'RW'},
            0x2114: {'name': 'Stop Charge Voltage', 'type': 'U16', 'size': 1, 'unit': 'V', 'scale': 0.1, 'rw': 'RW'},
            0x2115: {'name': 'Grid Charge', 'type': 'U16', 'size': 1, 'rw': 'RW'},
            0x2116: {'name': 'Maximum Grid Charger Power', 'type': 'U16', 'size': 1, 'unit': 'W', 'rw': 'RW'},
            0x2117: {'name': 'Capacity of Grid Charger End', 'type': 'U16', 'size': 1, 'unit': '%', 'rw': 'RW'},
            0x2118: {'name': 'Maximum Charger Power', 'type': 'U16', 'size': 1, 'unit': 'W', 'rw': 'RW'},
            0x2119: {'name': 'Capacity of Charger End', 'type': 'U16', 'size': 1, 'unit': '%', 'rw': 'RW'},
            0x211A: {'name': 'Maximum Discharger Power', 'type': 'U16', 'size': 1, 'unit': 'W', 'rw': 'RW'},
            0x211B: {'name': 'Capacity of Discharger End', 'type': 'U16', 'size': 1, 'unit': '%', 'rw': 'RW'},
            0x211C: {'name': 'Off-grid Mode', 'type': 'U16', 'size': 1, 'rw': 'RW'},
            0x211D: {'name': 'Rated Output Voltage', 'type': 'U16', 'size': 1, 'unit': 'V', 'scale': 0.1, 'rw': 'RW'},
            0x211E: {'name': 'Rated Output Frequency', 'type': 'U16', 'size': 1, 'unit': 'Hz', 'scale': 0.01, 'rw': 'RW'},
            0x211F: {'name': 'Off-grid Start-up Battery Capacity', 'type': 'U16', 'size': 1, 'unit': '%', 'rw': 'RW'},
            0x2120: {'name': 'Maximum Discharge Current', 'type': 'U16', 'size': 1, 'unit': 'A', 'scale': 0.01, 'rw': 'RW'},
            0x2121: {'name': 'Maximum Charger Current', 'type': 'U16', 'size': 1, 'unit': 'A', 'scale': 0.01, 'rw': 'RW'},
        }
    
    async def connect(self) -> bool:
        """Connect to the inverter."""
        try:
            self.client = ModbusSerialClient(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                parity='N',
                stopbits=1,
                bytesize=8
            )
            
            if self.client.connect():
                log.info(f"Connected to inverter on {self.port} at {self.baudrate} baud")
                return True
            else:
                log.error(f"Failed to connect to inverter on {self.port}")
                return False
                
        except Exception as e:
            log.error(f"Connection error: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from the inverter."""
        if self.client:
            self.client.close()
            log.info("Disconnected from inverter")
    
    def _convert_register_value(self, raw_values: List[int], data_type: str, 
                              scale: float = 1.0, unit: str = "") -> Any:
        """Convert raw register values to proper format."""
        try:
            if not raw_values:
                return None
            
            # Handle ASCII strings
            if unit == 'ASCII':
                # Convert to ASCII string
                ascii_chars = []
                for val in raw_values:
                    if val == 0:
                        break
                    # Extract two ASCII characters from each 16-bit value
                    char1 = chr((val >> 8) & 0xFF)
                    char2 = chr(val & 0xFF)
                    if char1 != '\x00':
                        ascii_chars.append(char1)
                    if char2 != '\x00':
                        ascii_chars.append(char2)
                return ''.join(ascii_chars).strip()
            
            # Handle numeric values
            if data_type in self.register_types:
                reg_info = self.register_types[data_type]
                size = reg_info['size']
                format_char = reg_info['format']
                
                if len(raw_values) >= size:
                    # Pack the values into bytes (big-endian)
                    if size == 1:
                        # Single 16-bit register
                        packed = struct.pack('>H', raw_values[0])
                        # Unpack as the target type
                        if format_char == 'H':  # U16
                            value = struct.unpack('>H', packed)[0]
                        elif format_char == 'h':  # S16
                            value = struct.unpack('>h', packed)[0]
                    else:
                        # Two 16-bit registers for 32-bit value
                        packed = struct.pack('>HH', raw_values[0], raw_values[1])
                        # Unpack as 32-bit value
                        if format_char == 'I':  # U32
                            value = struct.unpack('>I', packed)[0]
                        elif format_char == 'i':  # S32
                            value = struct.unpack('>i', packed)[0]
                    
                    # Apply scaling
                    if scale != 1.0:
                        value = value * scale
                    
                    return value
            
            return raw_values
            
        except Exception as e:
            log.warning(f"Failed to convert register value: {e}")
            return raw_values
    
    async def read_register(self, address: int, count: int = None) -> Optional[RegisterInfo]:
        """Read a single register or register range."""
        try:
            if not self.client or not self.client.is_socket_open():
                log.error("Not connected to inverter")
                return None
            
            # Get register info if known to determine proper count
            reg_info = self.known_registers.get(address, {})
            if count is None:
                count = reg_info.get('size', 1)
             
            # Read registers
            result = self.client.read_holding_registers(address=address, count=count, device_id=self.slave_id)
            
            if result.isError():
                log.warning(f"Error reading register 0x{address:04X}: {result}")
                return None
            
            raw_values = result.registers
            
            # Get register info if known
            data_type = reg_info.get('type', 'U16')
            size = reg_info.get('size', 1)
            unit = reg_info.get('unit', '')
            scale = reg_info.get('scale', 1.0)
            name = reg_info.get('name', f'Unknown Register 0x{address:04X}')
            
            # Convert value
            value = self._convert_register_value(raw_values, data_type, scale, unit)
            
            return RegisterInfo(
                address=address,
                size=size,
                data_type=data_type,
                value=value,
                raw_value=raw_values,
                description=name,
                unit=unit,
                scale=scale
            )
            
        except Exception as e:
            log.error(f"Exception reading register 0x{address:04X}: {e}")
            return None
    
    async def read_custom_register(self, request: CustomRegisterRequest) -> Optional[RegisterInfo]:
        """
        Read a specific register with custom parameters.
        
        Args:
            request: CustomRegisterRequest with address, length, unit, scale, data_type, description
            
        Returns:
            RegisterInfo object with the read data, or None if failed
        """
        try:
            if not self.client or not self.client.is_socket_open():
                log.error("Not connected to inverter")
                return None
            
            # Read registers
            result = self.client.read_holding_registers(
                address=request.address, 
                count=request.length, 
                device_id=self.slave_id
            )
            
            if result.isError():
                log.warning(f"Error reading register 0x{request.address:04X}: {result}")
                return None
            
            raw_values = result.registers
            
            # Use custom data type or auto-detect
            data_type = request.data_type
            if data_type == "auto":
                data_type = self._auto_detect_data_type(raw_values, request.length)
            
            # Convert value using custom scale and unit
            value = self._convert_register_value(raw_values, data_type, request.scale, request.unit)
            
            return RegisterInfo(
                address=request.address,
                size=request.length,
                data_type=data_type,
                value=value,
                raw_value=raw_values,
                description=request.description or f'Custom Register 0x{request.address:04X}',
                unit=request.unit,
                scale=request.scale
            )
            
        except Exception as e:
            log.error(f"Exception reading custom register 0x{request.address:04X}: {e}")
            return None
    
    def _auto_detect_data_type(self, raw_values: List[int], length: int) -> str:
        """Auto-detect data type based on raw values and length."""
        if length == 1:
            # Single register - check if it's a reasonable value
            val = raw_values[0]
            if 0 <= val <= 65535:
                return "U16"
            else:
                return "U16"  # Default to U16
        elif length == 2:
            # Two registers - could be U32, I32, or Float32
            # For now, default to U32
            return "U32"
        elif length >= 3:
            # Multiple registers - likely ASCII or special format
            # Check if all values are printable ASCII
            try:
                ascii_chars = []
                for val in raw_values:
                    if val == 0:
                        break
                    high_byte = (val >> 8) & 0xFF
                    low_byte = val & 0xFF
                    if 32 <= high_byte <= 126:  # Printable ASCII
                        ascii_chars.append(chr(high_byte))
                    if 32 <= low_byte <= 126:  # Printable ASCII
                        ascii_chars.append(chr(low_byte))
                
                if len(ascii_chars) > 0:
                    return "ASCII"
            except:
                pass
            
            return "U16"  # Default fallback
        
        return "U16"  # Default fallback
    
    async def scan_register_range(self, start_address: int, count: int, 
                                 step: int = 1) -> List[RegisterInfo]:
        """Scan a range of registers sequentially."""
        results = []
        
        log.info(f"Scanning registers from 0x{start_address:04X} to 0x{start_address + count - 1:04X}")
        
        for i in range(0, count, step):
            address = start_address + i
            reg_info = await self.read_register(address)
            
            if reg_info:
                results.append(reg_info)
                self._print_register(reg_info)
            
            # Small delay to avoid overwhelming the inverter
            await asyncio.sleep(0.1)
        
        return results
    
    async def read_multiple_custom_registers(self, requests: List[CustomRegisterRequest]) -> List[RegisterInfo]:
        """
        Read multiple custom registers with different parameters.
        
        Args:
            requests: List of CustomRegisterRequest objects
            
        Returns:
            List of RegisterInfo objects (some may be None if reading failed)
        """
        results = []
        
        log.info(f"Reading {len(requests)} custom registers...")
        
        for i, request in enumerate(requests, 1):
            print(f"\n[{i}/{len(requests)}] Reading register 0x{request.address:04X}...")
            
            reg_info = await self.read_custom_register(request)
            if reg_info:
                results.append(reg_info)
                self._print_register(reg_info)
            else:
                results.append(None)
                print(f"❌ Failed to read register 0x{request.address:04X}")
            
            # Small delay to avoid overwhelming the inverter
            await asyncio.sleep(0.1)
        
        return results
    
    def _print_register(self, reg_info: RegisterInfo):
        """Print register information to console."""
        address_str = f"0x{reg_info.address:04X}"
        raw_str = f"[{', '.join(f'0x{v:04X}' for v in reg_info.raw_value)}]"
        
        # Format value
        if isinstance(reg_info.value, str):
            value_str = f'"{reg_info.value}"'
        elif reg_info.value is None:
            value_str = "None"
        else:
            value_str = str(reg_info.value)
            if reg_info.unit:
                value_str += f" {reg_info.unit}"
        
        # Print formatted output
        print(f"{address_str:6} | {reg_info.data_type:4} | {reg_info.size:2} | {raw_str:20} | {value_str:15} | {reg_info.description}")
    
    def print_header(self):
        """Print table header."""
        print("=" * 120)
        print("SENERGY INVERTER REGISTER SCANNER")
        print("=" * 120)
        print(f"Port: {self.port}, Baudrate: {self.baudrate}, Slave ID: {self.slave_id}")
        print("=" * 120)
        print(f"{'Addr':6} | {'Type':4} | {'Sz':2} | {'Raw Values':20} | {'Value':15} | {'Description'}")
        print("-" * 120)
    
    async def scan_all_known_registers(self) -> List[RegisterInfo]:
        """Scan all known registers from the specification."""
        results = []
        
        self.print_header()
        
        # Sort addresses for better readability
        sorted_addresses = sorted(self.known_registers.keys())
        
        for address in sorted_addresses:
            reg_info = await self.read_register(address)
            if reg_info:
                results.append(reg_info)
                self._print_register(reg_info)
            
            await asyncio.sleep(0.1)
        
        print("-" * 120)
        print(f"Scanned {len(results)} known registers")
        return results
    
    async def discover_unknown_registers(self, start_address: int = 0x0000, 
                                       end_address: int = 0xFFFF, 
                                       step: int = 1) -> List[RegisterInfo]:
        """Discover unknown registers using intelligent analysis of raw values."""
        results = []
        unknown_count = 0
        
        self.print_header()
        print(f"INTELLIGENT DISCOVERY MODE: Scanning 0x{start_address:04X} to 0x{end_address:04X}")
        print("-" * 120)
        
        for address in range(start_address, end_address + 1, step):
            # Skip known registers
            if address in self.known_registers:
                continue
            
            # Read raw register data
            raw_reg_info = await self.read_register(address)
            if raw_reg_info and raw_reg_info.raw_value:
                # Analyze the raw value with different interpretations
                analyzed_regs = self._analyze_unknown_register(address, raw_reg_info.raw_value)
                
                for analyzed_reg in analyzed_regs:
                    if analyzed_reg and self._is_meaningful_value(analyzed_reg):
                        results.append(analyzed_reg)
                        self._print_register(analyzed_reg)
                        unknown_count += 1
            
            # Progress indicator
            if address % 100 == 0:
                print(f"Progress: 0x{address:04X} ({address/0xFFFF*100:.1f}%) - Found {unknown_count} meaningful registers")
            
            await asyncio.sleep(0.05)  # Faster scanning for discovery
        
        print("-" * 120)
        print(f"Intelligent discovery complete: Found {unknown_count} meaningful unknown registers")
        return results
    
    def _analyze_unknown_register(self, address: int, raw_values: List[int]) -> List[RegisterInfo]:
        """Analyze raw register values with different data type interpretations."""
        analyzed_regs = []
        
        # Try different data types and sizes
        interpretations = [
            # Single register interpretations
            {"type": "U16", "size": 1, "description": "Unknown U16"},
            {"type": "S16", "size": 1, "description": "Unknown S16"},
            
            # Two register interpretations
            {"type": "U32", "size": 2, "description": "Unknown U32"},
            {"type": "S32", "size": 2, "description": "Unknown S32"},
        ]
        
        for interp in interpretations:
            if len(raw_values) >= interp["size"]:
                # Try different scaling factors based on learned patterns
                scaling_factors = self._get_learned_scaling_factors(address, raw_values)
                
                for scale in scaling_factors:
                    # Try different units based on learned patterns
                    units = self._get_learned_units(address, raw_values, scale)
                    
                    for unit in units:
                        try:
                            # Convert with this interpretation
                            value = self._convert_register_value(
                                raw_values[:interp["size"]], 
                                interp["type"], 
                                scale, 
                                unit
                            )
                            
                            if value is not None:
                                reg_info = RegisterInfo(
                                    address=address,
                                    size=interp["size"],
                                    data_type=interp["type"],
                                    value=value,
                                    raw_value=raw_values[:interp["size"]],
                                    description=f"{interp['description']} (scale={scale}, unit={unit})",
                                    unit=unit,
                                    scale=scale
                                )
                                analyzed_regs.append(reg_info)
                        except Exception:
                            continue
        
        return analyzed_regs
    
    def _get_learned_scaling_factors(self, address: int, raw_values: List[int]) -> List[float]:
        """Get scaling factors based on learned patterns from known registers."""
        scaling_factors = [1.0]  # Always try unscaled first
        
        # Learn from nearby known registers
        nearby_registers = []
        for known_addr, known_info in self.known_registers.items():
            if abs(known_addr - address) <= 10:  # Within 10 addresses
                nearby_registers.append(known_info)
        
        # Extract unique scaling factors from nearby registers
        for reg_info in nearby_registers:
            if 'scale' in reg_info and reg_info['scale'] not in scaling_factors:
                scaling_factors.append(reg_info['scale'])
        
        # Add common scaling factors based on address patterns
        if 0x1000 <= address <= 0x1FFF:  # Real-time data area
            scaling_factors.extend([0.1, 0.01, 0.001, 10.0, 100.0])
        elif 0x2000 <= address <= 0x2FFF:  # Battery data area
            scaling_factors.extend([0.1, 0.01, 10.0])
        elif 0x3000 <= address <= 0x3FFF:  # Parameters area
            scaling_factors.extend([0.1, 0.01, 0.001])
        elif 0x5000 <= address <= 0x5FFF:  # Advanced parameters
            scaling_factors.extend([0.1, 0.01, 0.001, 10.0])
        
        # Remove duplicates and sort
        return sorted(list(set(scaling_factors)))
    
    def _get_learned_units(self, address: int, raw_values: List[int], scale: float) -> List[str]:
        """Get units based on learned patterns from known registers."""
        units = [""]  # Always try unitless first
        
        # Learn from nearby known registers
        nearby_registers = []
        for known_addr, known_info in self.known_registers.items():
            if abs(known_addr - address) <= 10:  # Within 10 addresses
                nearby_registers.append(known_info)
        
        # Extract unique units from nearby registers
        for reg_info in nearby_registers:
            if 'unit' in reg_info and reg_info['unit'] not in units:
                units.append(reg_info['unit'])
        
        # Add common units based on address patterns and value ranges
        if 0x1000 <= address <= 0x1FFF:  # Real-time data area
            units.extend(["V", "A", "W", "Hz", "°C", "%", "Wh", "kWh"])
        elif 0x2000 <= address <= 0x2FFF:  # Battery data area
            units.extend(["V", "A", "W", "%", "°C", "Wh", "kWh", "Ah"])
        elif 0x3000 <= address <= 0x3FFF:  # Parameters area
            units.extend(["V", "A", "W", "%", "Hz", "s", "min", "h"])
        elif 0x5000 <= address <= 0x5FFF:  # Advanced parameters
            units.extend(["V", "A", "W", "%", "Hz", "s", "ms", "mA"])
        
        # Remove duplicates
        return list(set(units))
    
    def _is_meaningful_value(self, reg_info: RegisterInfo) -> bool:
        """Determine if a register value is meaningful based on learned patterns."""
        if reg_info.value is None:
            return False
        
        # Check for ASCII strings (always meaningful if non-empty)
        if isinstance(reg_info.value, str):
            return len(reg_info.value.strip()) > 0
        
        # Check for numeric values
        if isinstance(reg_info.value, (int, float)):
            # Skip zero values (usually not meaningful)
            if reg_info.value == 0:
                return False
            
            # Check for reasonable ranges based on unit and type
            if reg_info.unit == "V" and 0 < abs(reg_info.value) < 1000:
                return True
            elif reg_info.unit == "A" and 0 < abs(reg_info.value) < 1000:
                return True
            elif reg_info.unit == "W" and 0 < abs(reg_info.value) < 100000:
                return True
            elif reg_info.unit == "Hz" and 0 < reg_info.value < 100:
                return True
            elif reg_info.unit == "°C" and -50 < reg_info.value < 100:
                return True
            elif reg_info.unit == "%" and 0 <= reg_info.value <= 100:
                return True
            elif reg_info.unit == "Wh" and 0 < reg_info.value < 1000000:
                return True
            elif reg_info.unit == "kWh" and 0 < reg_info.value < 10000:
                return True
            elif reg_info.unit == "Ah" and 0 < reg_info.value < 10000:
                return True
            elif reg_info.unit == "s" and 0 < reg_info.value < 86400:  # 24 hours
                return True
            elif reg_info.unit == "min" and 0 < reg_info.value < 1440:  # 24 hours
                return True
            elif reg_info.unit == "h" and 0 < reg_info.value < 8760:  # 1 year
                return True
            elif reg_info.unit == "ms" and 0 < reg_info.value < 100000:
                return True
            elif reg_info.unit == "mA" and 0 < abs(reg_info.value) < 10000:
                return True
            elif reg_info.unit == "" and 0 < abs(reg_info.value) < 65535:  # Unitless
                return True
        
        return False
    
    def _rank_discovered_registers(self, registers: List[RegisterInfo]) -> List[RegisterInfo]:
        """Rank discovered registers by their likelihood of being meaningful."""
        def calculate_score(reg: RegisterInfo) -> float:
            score = 0.0
            
            # Base score for having a value
            if reg.value is not None:
                score += 1.0
            
            # Bonus for reasonable value ranges
            if isinstance(reg.value, (int, float)):
                if reg.unit == "V" and 10 <= abs(reg.value) <= 500:
                    score += 2.0
                elif reg.unit == "A" and 0.1 <= abs(reg.value) <= 100:
                    score += 2.0
                elif reg.unit == "W" and 1 <= abs(reg.value) <= 10000:
                    score += 2.0
                elif reg.unit == "%" and 0 <= reg.value <= 100:
                    score += 2.0
                elif reg.unit == "°C" and -20 <= reg.value <= 80:
                    score += 2.0
                elif reg.unit == "Hz" and 45 <= reg.value <= 65:
                    score += 2.0
                elif reg.unit == "Wh" and 1 <= reg.value <= 100000:
                    score += 1.5
                elif reg.unit == "kWh" and 0.1 <= reg.value <= 1000:
                    score += 1.5
                elif reg.unit == "Ah" and 1 <= reg.value <= 1000:
                    score += 1.5
                elif reg.unit == "s" and 1 <= reg.value <= 3600:
                    score += 1.0
                elif reg.unit == "min" and 1 <= reg.value <= 60:
                    score += 1.0
                elif reg.unit == "h" and 0.1 <= reg.value <= 24:
                    score += 1.0
                elif reg.unit == "ms" and 1 <= reg.value <= 10000:
                    score += 1.0
                elif reg.unit == "mA" and 1 <= abs(reg.value) <= 10000:
                    score += 1.0
                elif reg.unit == "" and 1 <= abs(reg.value) <= 65535:
                    score += 0.5
            
            # Bonus for ASCII strings
            elif isinstance(reg.value, str) and len(reg.value.strip()) > 2:
                score += 3.0
            
            # Bonus for having a unit (more likely to be meaningful)
            if reg.unit:
                score += 0.5
            
            # Bonus for having a scaling factor (indicates precision)
            if reg.scale != 1.0:
                score += 0.3
            
            # Penalty for very large or very small values (less likely to be meaningful)
            if isinstance(reg.value, (int, float)):
                if abs(reg.value) > 1000000 or (reg.value != 0 and abs(reg.value) < 0.001):
                    score -= 1.0
            
            return score
        
        # Sort by score (highest first)
        return sorted(registers, key=calculate_score, reverse=True)
    
    async def intelligent_discovery_analysis(self, start_address: int = 0x0000, 
                                           end_address: int = 0xFFFF, 
                                           step: int = 1) -> Dict[str, List[RegisterInfo]]:
        """Perform intelligent discovery with detailed analysis and ranking."""
        print("🧠 Starting Intelligent Register Discovery Analysis...")
        print("This will analyze raw values with multiple interpretations to find meaningful data.")
        print("=" * 80)
        
        # Perform discovery
        discovered_registers = await self.discover_unknown_registers(start_address, end_address, step)
        
        if not discovered_registers:
            print("No meaningful registers discovered.")
            return {"all": [], "ranked": [], "by_type": {}, "by_unit": {}}
        
        # Rank by likelihood of being meaningful
        ranked_registers = self._rank_discovered_registers(discovered_registers)
        
        # Group by data type
        by_type = {}
        for reg in discovered_registers:
            if reg.data_type not in by_type:
                by_type[reg.data_type] = []
            by_type[reg.data_type].append(reg)
        
        # Group by unit
        by_unit = {}
        for reg in discovered_registers:
            unit = reg.unit or "unitless"
            if unit not in by_unit:
                by_unit[unit] = []
            by_unit[unit].append(reg)
        
        # Print analysis results
        print(f"\n📊 DISCOVERY ANALYSIS RESULTS")
        print("=" * 50)
        print(f"Total meaningful registers found: {len(discovered_registers)}")
        print(f"Top 10 most likely meaningful registers:")
        print("-" * 50)
        
        for i, reg in enumerate(ranked_registers[:10], 1):
            value_str = str(reg.value)
            if len(value_str) > 25:
                value_str = value_str[:22] + "..."
            print(f"{i:2d}. 0x{reg.address:04X}: {value_str} {reg.unit} ({reg.data_type}, scale={reg.scale})")
        
        print(f"\n📋 Breakdown by Data Type:")
        for data_type, regs in by_type.items():
            print(f"  {data_type}: {len(regs)} registers")
        
        print(f"\n📋 Breakdown by Unit:")
        for unit, regs in by_unit.items():
            print(f"  {unit}: {len(regs)} registers")
        
        # Save detailed analysis
        filename = "intelligent_discovery_analysis.txt"
        with open(filename, "w") as f:
            f.write("Senergy Inverter - Intelligent Discovery Analysis\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Scan range: 0x{start_address:04X} to 0x{end_address:04X}\n")
            f.write(f"Total meaningful registers: {len(discovered_registers)}\n\n")
            
            f.write("TOP RANKED REGISTERS (Most Likely Meaningful):\n")
            f.write("-" * 50 + "\n")
            for i, reg in enumerate(ranked_registers, 1):
                f.write(f"{i:3d}. 0x{reg.address:04X} | {reg.data_type} | {reg.size} | {reg.value} {reg.unit} | scale={reg.scale}\n")
            
            f.write(f"\n\nBREAKDOWN BY DATA TYPE:\n")
            f.write("-" * 30 + "\n")
            for data_type, regs in by_type.items():
                f.write(f"\n{data_type} ({len(regs)} registers):\n")
                for reg in regs:
                    f.write(f"  0x{reg.address:04X}: {reg.value} {reg.unit} (scale={reg.scale})\n")
            
            f.write(f"\n\nBREAKDOWN BY UNIT:\n")
            f.write("-" * 30 + "\n")
            for unit, regs in by_unit.items():
                f.write(f"\n{unit} ({len(regs)} registers):\n")
                for reg in regs:
                    f.write(f"  0x{reg.address:04X}: {reg.value} ({reg.data_type}, scale={reg.scale})\n")
        
        print(f"\n💾 Detailed analysis saved to: {filename}")
        
        return {
            "all": discovered_registers,
            "ranked": ranked_registers,
            "by_type": by_type,
            "by_unit": by_unit
        }

async def main():
    """Main function for testing the scanner."""
    # Configuration
    PORT = "/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_AB0OHEJJ-if00-port0"  # Change to your port (e.g., "COM3" on Windows)
    BAUDRATE = 9600
    SLAVE_ID = 1
    
    scanner = SenergyRegisterScanner(port=PORT, baudrate=BAUDRATE, slave_id=SLAVE_ID)
    
    try:
        # Connect to inverter
        if not await scanner.connect():
            print("Failed to connect to inverter. Please check:")
            print(f"1. Port: {PORT}")
            print(f"2. Baudrate: {BAUDRATE}")
            print(f"3. Slave ID: {SLAVE_ID}")
            print("4. Inverter is powered on and connected")
            return
        
        print("\nChoose scanning mode:")
        print("1. Scan all known registers")
        print("2. Scan specific register range")
        print("3. Discover unknown registers")
        print("4. Read single register")
        
        choice = input("Enter choice (1-4): ").strip()
        
        if choice == "1":
            await scanner.scan_all_known_registers()
            
        elif choice == "2":
            start_addr = int(input("Enter start address (hex, e.g., 0x1000): "), 16)
            count = int(input("Enter number of registers to scan: "))
            await scanner.scan_register_range(start_addr, count)
            
        elif choice == "3":
            start_addr = int(input("Enter start address (hex, e.g., 0x0000): "), 16)
            end_addr = int(input("Enter end address (hex, e.g., 0xFFFF): "), 16)
            await scanner.discover_unknown_registers(start_addr, end_addr)
            
        elif choice == "4":
            addr = int(input("Enter register address (hex, e.g., 0x2000): "), 16)
            reg_info = await scanner.read_register(addr)
            if reg_info:
                scanner._print_register(reg_info)
            else:
                print("Failed to read register")
        
        else:
            print("Invalid choice")
    
    except KeyboardInterrupt:
        print("\nScanning interrupted by user")
    
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        await scanner.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
