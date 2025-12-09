#!/usr/bin/env python3
"""
Standalone JK BMS RS485 TCP/IP Gateway Test Script

Based on jkbms-rs485-addon (https://github.com/jean-luc1203/jkbms-rs485-addon).
Tests JK-BMS connectivity via RS485-to-TCP/IP gateway (Ethernet or WiFi).

This script tests the TCP/IP gateway connection by:
- Connecting to RS485 gateway via TCP/IP socket
- Listening to RS485-2 bus communication (passive mode)
- Parsing Modbus RTU frames and 55AAEB90 data frames
- Displaying battery status and configuration data

The RS485 gateway works in transparent mode - it forwards RS485 data over TCP/IP.
This means the protocol is the same as serial, just over a network connection.

Usage:
    # Basic listening mode (passive - listens to broadcasts)
    python test_jkbms_tcpip.py --host 192.168.1.100 --port 8899
    
    # With custom timeout
    python test_jkbms_tcpip.py --host 192.168.1.100 --port 8899 --timeout 180
    
    # Debug mode (show raw frames)
    python test_jkbms_tcpip.py --host 192.168.1.100 --port 8899 --debug
    
    # Extended listening time
    python test_jkbms_tcpip.py --host 192.168.1.100 --port 8899 --timeout 300
"""

import asyncio
import argparse
import sys
import time
import json
import socket
from typing import Optional, Dict, List, Tuple, Any

import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)

# Import the adapter (for configuration structure)
try:
    from solarhub.config import BatteryBankConfig, BatteryAdapterConfig
except ImportError:
    # Fallback if not available
    BatteryBankConfig = None
    BatteryAdapterConfig = None

# ---- JK RS485-2 Modbus protocol constants -----------------------------------

MODBUS_PATTERN = bytes([0x10, 0x16])
DATA_FRAME_START = bytes([0x55, 0xAA, 0xEB, 0x90])

FRAME_TYPE_CONFIG = 0x01
FRAME_TYPE_STATUS = 0x02
MODBUS_REQUEST = 0x20

RECV_BUFFER_SIZE = 4096
READ_TIMEOUT = 1.0
MAX_MODBUS_FRAME_LENGTH = 512

# ---- System / pack assumptions ----------------------------------------------

# Default configuration
CELLS_PER_BATTERY = 16
CELL_NOMINAL_VOLTAGE = 3.2  # V
BATTERIES_EXPECTED = 3

DEFAULT_GATEWAY_HOST = "192.168.1.100"
DEFAULT_GATEWAY_PORT = 8899

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


# ---- low-level helpers ------------------------------------------------------

def read_int_le(data: bytes, offset: int, length: int,
                signed: bool = False, scale: float = 1.0) -> Optional[float]:
    if offset + length > len(data):
        return None
    value = int.from_bytes(data[offset:offset + length], "little", signed=signed)
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
    for b in data:
        crc ^= b
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


# ---- Modbus frame parsing (RS485-2) ----------------------------------------

def parse_modbus_frame(data: bytes) -> Optional[Tuple[int, int, bytes, bool, int]]:
    """
    Try to parse a Modbus frame starting at byte 0 of `data`.

    Returns:
        (battery_id, frame_type, payload, crc_valid, frame_length)
    or None if no valid frame starting at data[0].
    """
    if len(data) < 6:
        return None

    battery_id = data[0]
    if data[1:3] != MODBUS_PATTERN:
        return None

    frame_type = data[3]
    max_check = min(len(data), MAX_MODBUS_FRAME_LENGTH)

    for end_pos in range(6, max_check + 1):
        frame_without_crc = data[:end_pos - 2]
        received_crc = (data[end_pos - 1] << 8) | data[end_pos - 2]
        calculated_crc = modbus_crc16(frame_without_crc)

        if received_crc == calculated_crc:
            payload = data[4:end_pos - 2]
            return battery_id, frame_type, payload, True, end_pos

    return None


# ---- JK "data frames" (55 AA EB 90) parsing --------------------------------

def parse_frame_type_01(frame_data: bytes, cells_per_battery: int = CELLS_PER_BATTERY) -> dict:
    """Configuration frame."""
    result = {"type": "configuration"}

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
        result["display_always_on"] = read_bit_flag(frame_data, 282, 4)
        result["smart_sleep_switch"] = read_bit_flag(frame_data, 282, 7)
        result["disable_pcl_module"] = read_bit_flag(frame_data, 282, 8)
        result["timed_stored_data"] = read_bit_flag(frame_data, 283, 1)

    # derived: what we *expect* from JK, given your pack
    result["expected_cells"] = cells_per_battery
    result["nominal_cell_voltage"] = CELL_NOMINAL_VOLTAGE
    result["nominal_pack_voltage"] = cells_per_battery * CELL_NOMINAL_VOLTAGE
    return result


def parse_frame_type_02(frame_data: bytes, cells_per_battery: int = CELLS_PER_BATTERY) -> dict:
    """Status frame: voltages, temps, SOC, etc."""
    result = {"type": "status", "cell_voltages": []}

    # Parse cells
    for cell in range(cells_per_battery):
        offset = 6 + cell * 2
        voltage = read_int_le(frame_data, offset, 2, signed=False, scale=1000.0)
        if voltage is not None:
            result["cell_voltages"].append(round(voltage, 3))
        else:
            result["cell_voltages"].append(None)

    if len(frame_data) < 236:
        # still return partial result
        return result

    cell_resistances: List[float] = []
    for cell in range(cells_per_battery):
        offset = 80 + cell * 2
        resistance = read_int_le(frame_data, offset, 2, signed=True, scale=1000.0)
        if resistance is not None:
            cell_resistances.append(resistance)
    result["cell_resistances"] = cell_resistances

    result["mos_temp"] = read_int_le(frame_data, 144, 2, signed=True, scale=10.0)
    result["power"] = read_int_le(frame_data, 154, 4, signed=False, scale=1000.0)
    result["current"] = read_int_le(frame_data, 158, 4, signed=True, scale=1000.0)
    result["temp1"] = read_int_le(frame_data, 162, 2, signed=True, scale=10.0)
    result["temp2"] = read_int_le(frame_data, 164, 2, signed=True, scale=10.0)
    result["temp3"] = read_int_le(frame_data, 254, 2, signed=True, scale=10.0)
    result["temp4"] = read_int_le(frame_data, 258, 2, signed=True, scale=10.0)
    result["balance_current"] = read_int_le(frame_data, 170, 2, signed=True, scale=1000.0)
    result["balance_action"] = read_bool(frame_data, 172)
    if len(frame_data) > 173:
        result["soc"] = frame_data[173]
    result["remaining_capacity"] = read_int_le(frame_data, 174, 4, signed=True, scale=1000.0)
    result["total_capacity"] = read_int_le(frame_data, 178, 4, signed=True, scale=1000.0)
    result["cycle_count"] = read_int_le(frame_data, 182, 4, signed=True, scale=1.0)
    result["cycle_capacity"] = read_int_le(frame_data, 186, 4, signed=True, scale=100.0)
    if len(frame_data) > 190:
        result["soh"] = frame_data[190]
    result["total_runtime"] = read_int_le(frame_data, 194, 4, signed=False, scale=1.0)
    result["charge_switch"] = read_bool(frame_data, 198)
    result["discharge_switch"] = read_bool(frame_data, 199)
    result["balance_switch"] = read_bool(frame_data, 200)
    result["pack_voltage"] = read_int_le(frame_data, 234, 2, signed=False, scale=100.0)

    # Derived stats from your assumptions
    result["nominal_pack_voltage"] = cells_per_battery * CELL_NOMINAL_VOLTAGE
    if result["cell_voltages"]:
        valid_cells = [v for v in result["cell_voltages"] if v is not None]
        if valid_cells:
            result["avg_cell_voltage"] = round(sum(valid_cells) / len(valid_cells), 4)

    return result


def parse_data_frame(data: bytes, cells_per_battery: int = CELLS_PER_BATTERY) -> Optional[dict]:
    """Parse JK data frame that starts with 55 AA EB 90."""
    if len(data) < 5 or data[:4] != DATA_FRAME_START:
        return None

    frame_type = data[4]
    payload = data  # we already start at 0

    if frame_type == FRAME_TYPE_CONFIG:
        return parse_frame_type_01(payload, cells_per_battery)
    elif frame_type == FRAME_TYPE_STATUS:
        return parse_frame_type_02(payload, cells_per_battery)
    else:
        return {"type": frame_type, "unknown_type": True}


# ---- Connection wrapper for TCP/IP ------------------------------------------

class TcpConnectionWrapper:
    """Wrapper for TCP/IP socket connection (RS485 gateway)."""
    
    def __init__(self, sock: socket.socket):
        self.sock = sock
        self.sock.settimeout(READ_TIMEOUT)
    
    def recv(self, size: int) -> bytes:
        """Receive data from TCP socket."""
        try:
            return self.sock.recv(size)
        except socket.timeout:
            return b''
        except Exception as e:
            log.debug(f"Socket recv error: {e}")
            return b''
    
    def close(self) -> None:
        """Close TCP socket."""
        try:
            self.sock.close()
        except Exception:
            pass
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc, tb):
        self.close()


def open_tcp_connection(host: str, port: int) -> TcpConnectionWrapper:
    """Open TCP/IP connection to RS485 gateway."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5.0)  # Connection timeout
    try:
        sock.connect((host, port))
        log.info(f"Connected to RS485 gateway at {host}:{port}")
        return TcpConnectionWrapper(sock)
    except Exception as e:
        sock.close()
        raise ConnectionError(f"Failed to connect to {host}:{port}: {e}")


# ---- frame detection & processing --------------------------------------------

def find_next_frame_start(data: bytes, start_pos: int = 0):
    """
    Scan buffer for either JK data frame start (55 AA EB 90)
    or Modbus pattern (xx 10 16 ...) and return earliest one.
    """
    data_pos = find_pattern(data, DATA_FRAME_START, start_pos)

    modbus_pos = -1
    for i in range(start_pos, len(data) - 2):
        if data[i + 1:i + 3] == MODBUS_PATTERN:
            modbus_pos = i
            break

    if data_pos >= 0 and (modbus_pos < 0 or data_pos < modbus_pos):
        return data_pos, "data"
    elif modbus_pos >= 0:
        return modbus_pos, "modbus"
    else:
        return -1, None


def format_battery_line(battery_id: int, data: Dict) -> str:
    """Format a single battery's telemetry as a compact one-line string."""
    status = data.get('status', {})
    config = data.get('configuration', {})
    
    # Extract key values
    voltage = status.get('pack_voltage')
    current = status.get('current')
    soc = status.get('soc')
    temp = None
    temps = []
    for temp_key in ['temp1', 'temp2', 'temp3', 'temp4', 'mos_temp']:
        t = status.get(temp_key)
        if t is not None:
            temps.append(t)
    if temps:
        temp = sum(temps) / len(temps)
    
    power = status.get('power')
    cells_count = len([v for v in status.get('cell_voltages', []) if v is not None])
    
    # Format the line
    parts = [f"Battery {battery_id}:"]
    
    if voltage is not None:
        parts.append(f"V={voltage:.2f}V")
    if current is not None:
        parts.append(f"I={current:.2f}A")
    if power is not None:
        parts.append(f"P={power:.1f}W")
    if soc is not None:
        parts.append(f"SOC={soc}%")
    if temp is not None:
        parts.append(f"T={temp:.1f}°C")
    if cells_count > 0:
        parts.append(f"Cells={cells_count}")
    
    return " | ".join(parts)


def display_batteries(batteries: Dict[int, Dict], last_count: int = 0):
    """Display all discovered batteries in a compact format, updating in place."""
    current_count = len(batteries)
    
    if not batteries:
        if last_count == 0:
            print("No batteries discovered yet...")
        return current_count
    
    # Try to move cursor up to overwrite previous lines (if not first display)
    # This works in most modern terminals (Linux, macOS, Windows Terminal)
    if last_count > 0:
        try:
            # Move up: header (2 lines) + battery lines
            lines_to_move = 2 + last_count  # Header + separator + battery lines
            print(f"\033[{lines_to_move}A", end="", flush=True)  # Move up
        except:
            # Fallback: just print new section if ANSI codes don't work
            pass
    
    # Print header
    print(f"\nDiscovered Batteries ({current_count}):")
    print("-" * 80)
    
    # Print each battery line
    for battery_id in sorted(batteries.keys()):
        line = format_battery_line(battery_id, batteries[battery_id])
        print(f"{line:<80}")
    
    sys.stdout.flush()
    return current_count


def process_stream(conn: TcpConnectionWrapper, debug: bool, pretty: bool, duration: float,
                   batteries_expected: int = BATTERIES_EXPECTED, cells_per_battery: int = CELLS_PER_BATTERY) -> None:
    """
    Main parser:
    - Reads from TCP connection
    - Prints RAW + HEX when debug is enabled
    - Tracks per-battery status/config
    - Displays real-time battery telemetry (one line per battery)
    - Logs undecoded frames
    """
    buffer = b""
    # Latest data per battery_id
    batteries: Dict[int, Dict] = {}
    current_battery_id: Optional[int] = None
    start_time = time.time()
    last_display_time = 0.0
    display_interval = 0.5  # Update display every 0.5 seconds
    last_battery_count = 0  # Track number of batteries for display updates
    
    print(f"\n{'='*60}")
    print(f"LISTENING TO RS485 GATEWAY (TCP/IP)")
    print(f"{'='*60}")
    print(f"Duration: {duration} seconds")
    print(f"Mode: Passive listening (broadcasting)")
    print(f"{'='*60}")
    print("\nWaiting for battery data...")

    while time.time() - start_time < duration:
        try:
            chunk = conn.recv(RECV_BUFFER_SIZE)
            if not chunk:
                # No data received (timeout) - continue waiting
                time.sleep(0.1)
                continue

            if debug and chunk:
                # RAW chunk
                print(f"RAW: {chunk.hex()}", file=sys.stderr)
                # Also spaced HEX format:
                spaced_hex = " ".join(f"{b:02X}" for b in chunk)
                print(f"HEX: {spaced_hex}", file=sys.stderr)

            buffer += chunk
            pos = 0

            while pos < len(buffer):
                next_pos, kind = find_next_frame_start(buffer, pos)
                if next_pos < 0:
                    # no more full frames; keep tail in buffer
                    break

                if kind == "modbus":
                    data_slice = buffer[next_pos:]
                    parsed = parse_modbus_frame(data_slice)
                    if parsed:
                        battery_id, frame_type_byte, payload, crc_valid, frame_len = parsed
                        raw_frame = data_slice[:frame_len]

                        # Normalise battery_id if JK does the 15 -> 0 wrap hack
                        if battery_id == 15:
                            battery_id = 0

                        # Limit to our expected batteries
                        if battery_id >= batteries_expected:
                            if debug:
                                print(
                                    f"DEBUG: ignoring battery_id {battery_id} (>={batteries_expected}) "
                                    f"frame={raw_frame.hex()}",
                                    file=sys.stderr,
                                )
                        else:
                            if debug:
                                if frame_type_byte == MODBUS_REQUEST:
                                    print(
                                        f"DEBUG: Modbus request (id={battery_id}) "
                                        f"raw={raw_frame.hex()} payload={payload.hex()}",
                                        file=sys.stderr,
                                    )
                                else:
                                    print(
                                        f"DEBUG: Modbus response (id={battery_id}) "
                                        f"raw={raw_frame.hex()} crc_valid={crc_valid}",
                                        file=sys.stderr,
                                    )

                            # We use Modbus requests to detect that master is now talking to another BMS.
                            if frame_type_byte == MODBUS_REQUEST:
                                current_battery_id = battery_id

                        pos = next_pos + frame_len
                    else:
                        # unparsed Modbus-ish frame, log minimal info
                        if debug:
                            print(
                                f"DEBUG: Unparsed Modbus-like chunk from pos={next_pos}, "
                                f"data={buffer[next_pos:next_pos+40].hex()}...",
                                file=sys.stderr,
                            )
                        pos = next_pos + 1

                elif kind == "data":
                    # JK data frame (55 AA EB 90 ...)
                    slice_data = buffer[next_pos:]
                    end_pos = len(slice_data)
                    next_frame_pos, _ = find_next_frame_start(slice_data, 1)
                    if next_frame_pos > 0:
                        end_pos = next_frame_pos

                    frame_bytes = slice_data[:end_pos]
                    parsed = parse_data_frame(frame_bytes, cells_per_battery)
                    if not parsed:
                        # we saw 55 AA EB 90 but couldn't parse; log raw
                        print(
                            f"UNKNOWN_DATA_FRAME: raw={frame_bytes.hex()}",
                            file=sys.stderr,
                        )
                        # Update position to skip this frame
                        pos = next_pos + end_pos
                    else:
                        frame_type = parsed.get("type", "unknown")
                        # make sure we know which battery this belongs to
                        # Fallback: if we don't have current_battery_id yet, treat as 0
                        b_id = current_battery_id if current_battery_id is not None else 0

                        if b_id >= batteries_expected:
                            # ignore extra IDs
                            if debug:
                                print(
                                    f"DEBUG: ignoring data frame for battery_id {b_id} >= {batteries_expected}",
                                    file=sys.stderr,
                                )
                            # Update position to skip this frame
                            pos = next_pos + end_pos
                        else:
                            if b_id not in batteries:
                                batteries[b_id] = {
                                    "battery_id": b_id,
                                    "battery_index": b_id + 1,  # 1..3 for convenience
                                    "cells_per_battery": cells_per_battery,
                                    "nominal_cell_voltage": CELL_NOMINAL_VOLTAGE,
                                    "nominal_pack_voltage": cells_per_battery * CELL_NOMINAL_VOLTAGE,
                                }

                            # merge frame
                            entry = batteries[b_id]
                            entry["timestamp"] = int(time.time())

                            # drop meta keys
                            frame_copy = {
                                k: v
                                for k, v in parsed.items()
                                if k not in ("type", "battery_id", "timestamp")
                            }

                            if frame_type == "configuration":
                                entry.setdefault("configuration", {}).update(frame_copy)
                            elif frame_type == "status":
                                entry.setdefault("status", {}).update(frame_copy)
                            else:
                                entry.setdefault("other_frames", []).append(
                                    {"frame_type": frame_type, "data": frame_copy}
                                )

                            if debug:
                                print(
                                    f"DEBUG: Parsed {frame_type} frame for battery {b_id} "
                                    f"len={len(frame_bytes)} raw={frame_bytes.hex()}",
                                    file=sys.stderr,
                                )
                            
                            # Update position after processing frame
                            pos = next_pos + end_pos
                            
                            # Trigger display update after processing data frame
                            current_time = time.time()
                            if current_time - last_display_time >= display_interval:
                                last_battery_count = display_batteries(batteries, last_battery_count)
                                last_display_time = current_time

            # keep unprocessed tail
            buffer = buffer[pos:]
            
            # Periodic display update (even if no new frames)
            current_time = time.time()
            if current_time - last_display_time >= display_interval:
                last_battery_count = display_batteries(batteries, last_battery_count)
                last_display_time = current_time
            
        except KeyboardInterrupt:
            print("\n\n\nInterrupted by user", file=sys.stderr)
            break
        except Exception as e:
            log.error(f"Error processing stream: {e}", exc_info=True)
            time.sleep(0.1)
    
    # Final display
    print("\n")
    print(f"{'='*60}")
    print("FINAL RESULTS")
    print(f"{'='*60}\n")
    
    if batteries:
        print(f"Discovered Batteries ({len(batteries)}):")
        print("-" * 80)
        for battery_id in sorted(batteries.keys()):
            line = format_battery_line(battery_id, batteries[battery_id])
            print(line)
        
        # Optionally show detailed JSON if requested
        if pretty:
            print("\n" + "-" * 80)
            print("\nDetailed Data:")
            for battery_id in sorted(batteries.keys()):
                json_str = json.dumps(
                    batteries[battery_id],
                    indent=2,
                )
                print(f"\nBattery {battery_id}:")
                print(json_str)
    else:
        print("No batteries discovered during the test period.")
    
    sys.stdout.flush()


async def main():
    parser = argparse.ArgumentParser(
        description='Test JK BMS via RS485 TCP/IP Gateway (passive listening mode)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic test (60 seconds, passive listening)
  python test_jkbms_tcpip.py --host 192.168.1.100 --port 8899
  
  # Extended test (180 seconds)
  python test_jkbms_tcpip.py --host 192.168.1.100 --port 8899 --timeout 180
  
  # Debug mode (show raw hex)
  python test_jkbms_tcpip.py --host 192.168.1.100 --port 8899 --debug
  
  # Custom gateway port
  python test_jkbms_tcpip.py --host 192.168.1.100 --port 502
        """
    )
    
    parser.add_argument('--host', '-H', required=True,
                       help='RS485 gateway IP address or hostname')
    parser.add_argument('--port', '-p', type=int, default=DEFAULT_GATEWAY_PORT,
                       help=f'RS485 gateway TCP port (default: {DEFAULT_GATEWAY_PORT})')
    parser.add_argument('--timeout', '-t', type=float, default=60.0,
                       help='Test duration in seconds (default: 60.0)')
    parser.add_argument('--debug', '-d', action='store_true',
                       help='Enable debug output (show raw hex frames)')
    parser.add_argument('--pretty', action='store_true',
                       help='Pretty-print JSON output')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    parser.add_argument('--batteries', '-b', type=int, default=BATTERIES_EXPECTED,
                       help=f'Number of batteries expected (default: {BATTERIES_EXPECTED})')
    parser.add_argument('--cells', '-c', type=int, default=CELLS_PER_BATTERY,
                       help=f'Cells per battery (default: {CELLS_PER_BATTERY})')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        print(f"Connecting to RS485 gateway at {args.host}:{args.port}...")
        with open_tcp_connection(args.host, args.port) as conn:
            # Run synchronous process_stream in thread pool to avoid blocking
            await asyncio.to_thread(
                process_stream, 
                conn, 
                args.debug, 
                args.pretty, 
                args.timeout,
                args.batteries,
                args.cells
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

