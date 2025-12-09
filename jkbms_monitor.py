#!/usr/bin/env python3
import sys
sys.stdout.reconfigure(line_buffering=True)

import socket
import time
import json
import argparse
from typing import Optional, Tuple, List, Dict, Union

try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False

MODBUS_PATTERN = bytes([0x10, 0x16])
DATA_FRAME_START = bytes([0x55, 0xAA, 0xEB, 0x90])
MODBUS_REQUEST = 0x20
FRAME_TYPE_CONFIG = 0x01
FRAME_TYPE_STATUS = 0x02

RECONNECT_DELAY = 2.0
READ_TIMEOUT = 1.0
RECV_BUFFER_SIZE = 4096
MAX_MODBUS_FRAME_LENGTH = 512


# (field_name, offset, length, scale, is_numeric)
CONFIG_FIELDS = [
    ('smart_sleep_voltage', 6, 4, 1000.0, True),
    ('cell_undervoltage_protection', 10, 4, 1000.0, True),
    ('cell_undervoltage_recovery', 14, 4, 1000.0, True),
    ('cell_overvoltage_protection', 18, 4, 1000.0, True),
    ('cell_overvoltage_recovery', 22, 4, 1000.0, True),
    ('balance_trigger_voltage', 26, 4, 1000.0, True),
    ('cell_soc100_voltage', 30, 4, 1000.0, True),
    ('cell_soc0_voltage', 34, 4, 1000.0, True),
    ('cell_request_charge_voltage', 38, 4, 1000.0, True),
    ('cell_request_float_voltage', 42, 4, 1000.0, True),
    ('power_off_voltage', 46, 4, 1000.0, True),
    ('max_charge_current', 50, 4, 1000.0, True),
    ('charge_overcurrent_delay', 54, 4, 1.0, True),
    ('charge_overcurrent_recovery', 58, 4, 1.0, True),
    ('max_discharge_current', 62, 4, 1000.0, True),
    ('discharge_overcurrent_delay', 66, 4, 1.0, True),
    ('discharge_overcurrent_recovery', 70, 4, 1.0, True),
    ('short_circuit_recovery', 74, 4, 1.0, True),
    ('max_balance_current', 78, 4, 1000.0, True),
    ('charge_overtemp_protection', 82, 4, 10.0, True),
    ('charge_overtemp_recovery', 86, 4, 10.0, True),
    ('discharge_overtemp_protection', 90, 4, 10.0, True),
    ('discharge_overtemp_recovery', 94, 4, 10.0, True),
    ('charge_undertemp_protection', 98, 4, 10.0, True),
    ('charge_undertemp_recovery', 102, 4, 10.0, True),
    ('power_tube_overtemp_protection', 106, 4, 10.0, True),
    ('power_tube_overtemp_recovery', 110, 4, 10.0, True),
    ('cell_count', 114, 4, 1.0, True),
    ('charging_switch', 118, 1, None, False),
    ('discharging_switch', 122, 1, None, False),
    ('balance_switch', 126, 1, None, False),
    ('total_battery_capacity', 130, 4, 1000.0, True),
    ('short_circuit_delay', 134, 4, 1.0, True),
    ('balance_starting_voltage', 138, 4, 1000.0, True),
    ('wire_resistance_1', 158, 4, 1000.0, True),
    ('device_address', 270, 4, 1.0, True),
]


def read_int_le(data: bytes, offset: int, length: int, signed: bool = False, scale: float = 1.0) -> Optional[float]:
    if offset + length > len(data):
        return None
    value = int.from_bytes(data[offset:offset+length], 'little', signed=signed)
    return value / scale if scale != 1.0 else float(value)


def read_bool(data: bytes, offset: int) -> Optional[bool]:
    if offset >= len(data):
        return None
    return bool(data[offset])


def read_bit_flag(data: bytes, offset: int, bit: int) -> Optional[bool]:
    if offset >= len(data):
        return None
    return bool((data[offset] >> bit) & 1)


def modbus_crc16(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc


def find_pattern(data: bytes, pattern: bytes, start_pos: int = 0) -> int:
    try:
        return data.index(pattern, start_pos)
    except ValueError:
        return -1


def parse_modbus_frame(data: bytes) -> Optional[Tuple[int, int, bytes, bool, int]]:
    if len(data) < 6:
        return None
    
    battery_id = data[0]
    if data[1:3] != MODBUS_PATTERN:
        return None
    
    frame_type = data[3]
    max_check = min(len(data), MAX_MODBUS_FRAME_LENGTH)
    
    for end_pos in range(6, max_check + 1):
        frame_without_crc = data[:end_pos-2]
        received_crc = (data[end_pos-1] << 8) | data[end_pos-2]
        calculated_crc = modbus_crc16(frame_without_crc)
        
        if received_crc == calculated_crc:
            payload = data[4:end_pos-2]
            return (battery_id, frame_type, payload, True, end_pos)
    
    return None


def parse_frame_type_01(frame_data: bytes) -> dict:
    result = {'type': 'configuration'}
    
    if len(frame_data) < 286:
        return result
    
    for field_name, offset, length, scale, is_numeric in CONFIG_FIELDS:
        if is_numeric:
            value = read_int_le(frame_data, offset, length, signed=True, scale=scale)
            if value is not None:
                result[field_name] = int(value) if scale == 1.0 else value
        else:
            value = read_bool(frame_data, offset)
            if value is not None:
                result[field_name] = value
    
    if len(frame_data) >= 284:
        result['display_always_on'] = read_bit_flag(frame_data, 282, 4)
        result['smart_sleep_switch'] = read_bit_flag(frame_data, 282, 7)
        result['disable_pcl_module'] = read_bit_flag(frame_data, 282, 8)
        result['timed_stored_data'] = read_bit_flag(frame_data, 283, 1)
    
    return result


def parse_frame_type_02(frame_data: bytes) -> dict:
    result = {'type': 'status', 'cell_voltages': []}
    
    for cell in range(16):
        offset = 6 + (cell * 2)
        voltage = read_int_le(frame_data, offset, 2, signed=False, scale=1000.0)
        if voltage is not None:
            result['cell_voltages'].append(round(voltage, 3))
        else:
            result['cell_voltages'].append(None)
    
    if len(frame_data) < 236:
        return result
    
    cell_resistances = []
    for cell in range(16):
        offset = 80 + (cell * 2)
        resistance = read_int_le(frame_data, offset, 2, signed=True, scale=1000.0)
        if resistance is not None:
            cell_resistances.append(resistance)
    result['cell_resistances'] = cell_resistances
    
    result['mos_temp'] = read_int_le(frame_data, 144, 2, signed=True, scale=10.0)
    result['power'] = read_int_le(frame_data, 154, 4, signed=False, scale=1000.0)
    result['current'] = read_int_le(frame_data, 158, 4, signed=True, scale=1000.0)
    result['temp1'] = read_int_le(frame_data, 162, 2, signed=True, scale=10.0)
    result['temp2'] = read_int_le(frame_data, 164, 2, signed=True, scale=10.0)
    result['temp3'] = read_int_le(frame_data, 254, 2, signed=True, scale=10.0)
    result['temp4'] = read_int_le(frame_data, 258, 2, signed=True, scale=10.0)
    result['balance_current'] = read_int_le(frame_data, 170, 2, signed=True, scale=1000.0)
    result['balance_action'] = read_bool(frame_data, 172)
    if len(frame_data) > 173:
        result['soc'] = frame_data[173]
    result['remaining_capacity'] = read_int_le(frame_data, 174, 4, signed=True, scale=1000.0)
    result['total_capacity'] = read_int_le(frame_data, 178, 4, signed=True, scale=1000.0)
    result['cycle_count'] = read_int_le(frame_data, 182, 4, signed=True, scale=1.0)
    result['cycle_capacity'] = read_int_le(frame_data, 186, 4, signed=True, scale=100.0)
    if len(frame_data) > 190:
        result['soh'] = frame_data[190]
    result['total_runtime'] = read_int_le(frame_data, 194, 4, signed=False, scale=1.0)
    result['charge_switch'] = read_bool(frame_data, 198)
    result['discharge_switch'] = read_bool(frame_data, 199)
    result['balance_switch'] = read_bool(frame_data, 200)
    result['pack_voltage'] = read_int_le(frame_data, 234, 2, signed=False, scale=100.0)
    
    return result


def parse_data_frame(data: bytes) -> Optional[dict]:
    if len(data) < 5 or data[:4] != DATA_FRAME_START:
        return None
    
    frame_type = data[4]
    if frame_type == FRAME_TYPE_CONFIG:
        return parse_frame_type_01(data)
    elif frame_type == FRAME_TYPE_STATUS:
        return parse_frame_type_02(data)
    else:
        return {'type': frame_type, 'unknown_type': True}


def parse_connection_string(conn_str: str) -> Tuple[str, ...]:
    """Parse connection string format: tcp:host:port or serial:/dev/ttyUSB0:115200"""
    parts = conn_str.split(':')
    
    if len(parts) < 2:
        raise ValueError(f"Invalid connection string format: {conn_str}. Expected 'tcp:host:port' or 'serial:/dev/ttyUSB0:115200'")
    
    conn_type = parts[0].lower()
    
    if conn_type == 'tcp':
        if len(parts) != 3:
            raise ValueError(f"Invalid TCP connection string: {conn_str}. Expected 'tcp:host:port'")
        try:
            port = int(parts[2])
        except ValueError:
            raise ValueError(f"Invalid port number: {parts[2]}")
        return ('tcp', parts[1], port)
    
    elif conn_type == 'serial':
        if len(parts) < 2:
            raise ValueError(f"Invalid serial connection string: {conn_str}. Expected 'serial:/dev/ttyUSB0:115200'")
        device = parts[1]
        baudrate = 115200  # default
        if len(parts) >= 3:
            try:
                baudrate = int(parts[2])
            except ValueError:
                raise ValueError(f"Invalid baudrate: {parts[2]}")
        return ('serial', device, baudrate)
    
    else:
        raise ValueError(f"Unknown connection type: {conn_type}. Supported types: 'tcp', 'serial'")


def create_connection(conn_type: str, **kwargs) -> Union[socket.socket, 'serial.Serial']:
    """Create and return a connection object based on connection type."""
    if conn_type == 'tcp':
        host = kwargs['host']
        port = kwargs['port']
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(READ_TIMEOUT)
        sock.connect((host, port))
        return sock
    
    elif conn_type == 'serial':
        if not SERIAL_AVAILABLE:
            raise ImportError("pyserial package is required for serial port support. Install it with: pip install pyserial")
        device = kwargs['device']
        baudrate = kwargs['baudrate']
        ser = serial.Serial(
            port=device,
            baudrate=baudrate,
            timeout=READ_TIMEOUT,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE
        )
        return ser
    
    else:
        raise ValueError(f"Unknown connection type: {conn_type}")


class ConnectionWrapper:
    """Wrapper to provide unified interface for socket and serial connections."""
    def __init__(self, conn: Union[socket.socket, 'serial.Serial']):
        self.conn = conn
        self.is_socket = isinstance(conn, socket.socket)
    
    def recv(self, size: int) -> bytes:
        """Read data from connection."""
        if self.is_socket:
            return self.conn.recv(size)
        else:
            return self.conn.read(size)
    
    def close(self) -> None:
        """Close connection."""
        if self.is_socket:
            self.conn.close()
        else:
            self.conn.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def find_next_frame_start(data: bytes, start_pos: int = 0) -> Tuple[int, Optional[str]]:
    data_pos = find_pattern(data, DATA_FRAME_START, start_pos)
    
    modbus_pos = -1
    for i in range(start_pos, len(data) - 2):
        if data[i+1:i+3] == MODBUS_PATTERN:
            modbus_pos = i
            break
    
    if data_pos >= 0 and (modbus_pos < 0 or data_pos < modbus_pos):
        return (data_pos, 'data')
    elif modbus_pos >= 0:
        return (modbus_pos, 'modbus')
    else:
        return (-1, None)


def process_and_output_frames(conn_wrapper: ConnectionWrapper, debug: bool, pretty: bool) -> bool:
    """Process frames from connection and output when battery changes. Returns False if connection closed."""
    buffer = b''
    current_battery_id: Optional[int] = None
    current_battery_data: Dict = {}
    
    try:
        while True:
            try:
                data = conn_wrapper.recv(RECV_BUFFER_SIZE)
                if not data:
                    # Output remaining data before closing
                    if current_battery_data:
                        json_str = json.dumps(current_battery_data, indent=2 if pretty else None, separators=(',', ':') if not pretty else None)
                        print(json_str, file=sys.stdout)
                        sys.stdout.flush()
                    return False
                
                buffer += data
                pos = 0
                
                while pos < len(buffer):
                    next_pos, frame_type = find_next_frame_start(buffer, pos)
                    
                    if next_pos < 0:
                        break
                    
                    if frame_type == 'modbus':
                        modbus_data = buffer[next_pos:]
                        result = parse_modbus_frame(modbus_data)
                        
                        if result:
                            battery_id, frame_type_byte, payload, crc_valid, frame_length = result
                            raw_frame = buffer[next_pos:next_pos + frame_length]
                            
                            if debug:
                                if frame_type_byte == MODBUS_REQUEST:
                                    print(f"DEBUG: Modbus request - raw={raw_frame.hex()}, battery_id={battery_id}, payload={payload.hex()}", file=sys.stderr)
                                else:
                                    print(f"DEBUG: Modbus response - raw={raw_frame.hex()}, battery_id={battery_id}, payload={payload.hex()}, crc_valid={crc_valid}", file=sys.stderr)
                            
                            # Hack alert: battery ID 0 does not send requests.
                            # Convert battery ID 15 to 0 (battery 15 wraps around to battery 0)
                            if battery_id == 15:
                                battery_id = 0
                            
                            # Check for battery transition
                            if frame_type_byte == MODBUS_REQUEST:
                                if current_battery_id is not None and battery_id != current_battery_id:
                                    # Output current battery data before switching
                                    if current_battery_data:
                                        json_str = json.dumps(current_battery_data, indent=2 if pretty else None, separators=(',', ':') if not pretty else None)
                                        print(json_str, file=sys.stdout)
                                        sys.stdout.flush()
                                    # Start new battery data
                                    current_battery_data = {}
                            
                            current_battery_id = battery_id
                            
                            pos = next_pos + frame_length
                        else:
                            pos = next_pos + 1
                    
                    elif frame_type == 'data':
                        data_buffer = buffer[next_pos:]
                        end_pos = len(data_buffer)
                        next_frame_pos, _ = find_next_frame_start(data_buffer, 1)
                        if next_frame_pos > 0:
                            end_pos = next_frame_pos
                        
                        frame_data = data_buffer[:end_pos]
                        parsed = parse_data_frame(frame_data)
                        
                        if parsed:
                            frame_type_name = parsed.get('type', 'unknown')
                            
                            if debug:
                                print(f"DEBUG: Parsed {frame_type_name} response - raw={frame_data.hex()}, battery_id={current_battery_id}", file=sys.stderr)
                            
                            if not current_battery_data:
                                current_battery_data = {
                                    'battery_id': current_battery_id if current_battery_id is not None else 0,
                                    'timestamp': int(time.time())
                                }
                            
                            # Merge parsed data into current_battery_data
                            frame_copy = {k: v for k, v in parsed.items() 
                                         if k not in ('type', 'battery_id', 'timestamp')}
                            
                            if frame_type_name == 'configuration':
                                current_battery_data['configuration'] = frame_copy
                            elif frame_type_name == 'status':
                                current_battery_data['status'] = frame_copy
                            
                            # Update timestamp
                            current_battery_data['timestamp'] = int(time.time())

                        pos = next_pos + end_pos
                
                buffer = buffer[pos:] if pos < len(buffer) else b''
            
            except (socket.timeout, OSError):
                # socket.timeout for TCP, OSError for serial timeout
                continue
            except ConnectionError:
                raise
    
    except Exception:
        # Output remaining data on any error
        if current_battery_data:
            json_str = json.dumps(current_battery_data, indent=2 if pretty else None, separators=(',', ':') if not pretty else None)
            print(json_str, file=sys.stdout)
            sys.stdout.flush()
        raise
    
    return True


def run_connection_loop(conn_str: str, debug: bool, pretty: bool) -> None:
    """Run connection loop with automatic reconnection."""
    # Parse connection string once
    conn_type, *conn_params = parse_connection_string(conn_str)
    
    while True:
        conn_wrapper = None
        try:
            # Create connection based on type
            if conn_type == 'tcp':
                host, port = conn_params
                print(f"Connecting to {host}:{port}...", file=sys.stderr)
                conn = create_connection('tcp', host=host, port=port)
                conn_wrapper = ConnectionWrapper(conn)
                print(f"Connected. Receiving data...", file=sys.stderr)
            elif conn_type == 'serial':
                device, baudrate = conn_params
                print(f"Opening serial port {device} at {baudrate} baud...", file=sys.stderr)
                conn = create_connection('serial', device=device, baudrate=baudrate)
                conn_wrapper = ConnectionWrapper(conn)
                print(f"Connected. Receiving data...", file=sys.stderr)
            
            process_and_output_frames(conn_wrapper, debug, pretty)
        
        except KeyboardInterrupt:
            print("\nInterrupted by user", file=sys.stderr)
            break
        except Exception as e:
            print(f"Connection error: {e}", file=sys.stderr)
            print(f"Reconnecting in {RECONNECT_DELAY} seconds...", file=sys.stderr)
            time.sleep(RECONNECT_DELAY)
        finally:
            if conn_wrapper is not None:
                try:
                    conn_wrapper.close()
                except (OSError, socket.error):
                    pass


def main():
    parser = argparse.ArgumentParser(
        description='JKBMS RS485-2 Monitor - Passively monitor JKBMS battery communication',
        epilog='''
Examples:
  %(prog)s tcp:192.168.1.20:505
  %(prog)s serial:/dev/ttyUSB0:115200
  %(prog)s serial:/dev/ttyUSB0
  %(prog)s tcp:192.168.1.20:505 --debug --pretty
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('connection',
                        metavar='CONNECTION',
                        help='Connection string: tcp:host:port or serial:/dev/ttyUSB0:115200')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    parser.add_argument('--pretty', action='store_true', help='Pretty print JSON output')
    
    # Check if no arguments provided and show helpful message
    if len(sys.argv) == 1:
        parser.print_help()
        print('\nError: Connection string is required.', file=sys.stderr)
        sys.exit(1)
    
    args = parser.parse_args()
    
    run_connection_loop(args.connection, args.debug, args.pretty)


if __name__ == '__main__':
    main()

