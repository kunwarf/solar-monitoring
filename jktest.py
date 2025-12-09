#!/usr/bin/env python3
import sys
sys.stdout.reconfigure(line_buffering=True)

import time
import json
import argparse
from typing import Optional, Tuple, Dict, Union, List

import socket  # only for type hints in case you ever extend to TCP

try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False

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

# Your setup:
CELLS_PER_BATTERY = 16
CELL_NOMINAL_VOLTAGE = 3.2  # V
BATTERIES_EXPECTED = 3

DEFAULT_SERIAL_DEVICE = "/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_A10MLU4X-if00-port0"
DEFAULT_BAUDRATE = 115200

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


# ---- Modbus frame parsing (RS485-2) -----------------------------------------

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


# ---- JK "data frames" (55 AA EB 90) parsing ---------------------------------

def parse_frame_type_01(frame_data: bytes) -> dict:
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
    result["expected_cells"] = CELLS_PER_BATTERY
    result["nominal_cell_voltage"] = CELL_NOMINAL_VOLTAGE
    result["nominal_pack_voltage"] = CELLS_PER_BATTERY * CELL_NOMINAL_VOLTAGE
    return result


def parse_frame_type_02(frame_data: bytes) -> dict:
    """Status frame: voltages, temps, SOC, etc."""
    result = {"type": "status", "cell_voltages": []}

    # 16 cells
    for cell in range(CELLS_PER_BATTERY):
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
    for cell in range(CELLS_PER_BATTERY):
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
    result["nominal_pack_voltage"] = CELLS_PER_BATTERY * CELL_NOMINAL_VOLTAGE
    if result["cell_voltages"]:
        valid_cells = [v for v in result["cell_voltages"] if v is not None]
        if valid_cells:
            result["avg_cell_voltage"] = round(sum(valid_cells) / len(valid_cells), 4)

    return result


def parse_data_frame(data: bytes) -> Optional[dict]:
    """Parse JK data frame that starts with 55 AA EB 90."""
    if len(data) < 5 or data[:4] != DATA_FRAME_START:
        return None

    frame_type = data[4]
    payload = data  # we already start at 0

    if frame_type == FRAME_TYPE_CONFIG:
        return parse_frame_type_01(payload)
    elif frame_type == FRAME_TYPE_STATUS:
        return parse_frame_type_02(payload)
    else:
        return {"type": frame_type, "unknown_type": True}


# ---- Connection wrapper (serial only right now) -----------------------------

class ConnectionWrapper:
    """Unified interface so we can swap serial/TCP if ever needed."""
    def __init__(self, conn: Union["serial.Serial", socket.socket]):
        self.conn = conn
        self.is_socket = isinstance(conn, socket.socket)

    def recv(self, size: int) -> bytes:
        if self.is_socket:
            return self.conn.recv(size)
        else:
            return self.conn.read(size)

    def close(self) -> None:
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()


def open_serial(device: str, baudrate: int) -> ConnectionWrapper:
    if not SERIAL_AVAILABLE:
        raise ImportError("pyserial required. Install with: pip install pyserial")

    ser = serial.Serial(
        port=device,
        baudrate=baudrate,
        timeout=READ_TIMEOUT,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
    )
    return ConnectionWrapper(ser)


# ---- frame detection & processing -------------------------------------------

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


def process_stream(conn: ConnectionWrapper, debug: bool, pretty: bool) -> None:
    """
    Main parser:
    - Reads from connection
    - Prints RAW + HEX when debug is enabled (no truncation)
    - Tracks per-battery status/config
    - Prints JSON per battery when we see complete frames
    - Logs undecoded frames
    """
    buffer = b""
    # Latest data per battery_id
    batteries: Dict[int, Dict] = {}
    current_battery_id: Optional[int] = None

    while True:
        chunk = conn.recv(RECV_BUFFER_SIZE)
        if not chunk:
            # connection closed / timeout
            break

        if debug and chunk:
            # RAW chunk (as you had in your logs)
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

                    # Limit to our 3 expected batteries
                    if battery_id >= BATTERIES_EXPECTED:
                        if debug:
                            print(
                                f"DEBUG: ignoring battery_id {battery_id} (>={BATTERIES_EXPECTED}) "
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
                            if current_battery_id is not None and battery_id != current_battery_id:
                                # When master moves to next battery, flush current battery JSON
                                if current_battery_id in batteries:
                                    out = batteries[current_battery_id]
                                    json_str = json.dumps(
                                        out,
                                        indent=2 if pretty else None,
                                        separators=(",", ":") if not pretty else None,
                                    )
                                    print(json_str)
                                    sys.stdout.flush()
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
                parsed = parse_data_frame(frame_bytes)
                if not parsed:
                    # we saw 55 AA EB 90 but couldn't parse; log raw
                    print(
                        f"UNKNOWN_DATA_FRAME: raw={frame_bytes.hex()}",
                        file=sys.stderr,
                    )
                else:
                    frame_type = parsed.get("type", "unknown")
                    # make sure we know which battery this belongs to
                    # Fallback: if we don't have current_battery_id yet, treat as 0
                    b_id = current_battery_id if current_battery_id is not None else 0

                    if b_id >= BATTERIES_EXPECTED:
                        # ignore extra IDs
                        if debug:
                            print(
                                f"DEBUG: ignoring data frame for battery_id {b_id} >= {BATTERIES_EXPECTED}",
                                file=sys.stderr,
                            )
                    else:
                        if b_id not in batteries:
                            batteries[b_id] = {
                                "battery_id": b_id,
                                "battery_index": b_id + 1,  # 1..3 for convenience
                                "cells_per_battery": CELLS_PER_BATTERY,
                                "nominal_cell_voltage": CELL_NOMINAL_VOLTAGE,
                                "nominal_pack_voltage": CELLS_PER_BATTERY * CELL_NOMINAL_VOLTAGE,
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

                        # Optional: when we have both status & configuration, we could
                        # flush immediately. For now, just keep them; the flush is
                        # handled when Modbus request jumps to next battery.

                pos = next_pos + end_pos
            else:
                # Shouldn't happen
                pos += 1

        # keep unprocessed tail
        buffer = buffer[pos:]


# ---- CLI / main -------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="JK BMS RS485-2 monitor (3x 16-cell batteries, serial only)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  %(prog)s                      # use default serial device + 115200
  %(prog)s --device /dev/ttyUSB0 --baud 115200 --debug
        """,
    )
    parser.add_argument(
        "--device",
        default=DEFAULT_SERIAL_DEVICE,
        help=f"Serial device (default: {DEFAULT_SERIAL_DEVICE})",
    )
    parser.add_argument(
        "--baud",
        type=int,
        default=DEFAULT_BAUDRATE,
        help=f"Baudrate (default: {DEFAULT_BAUDRATE})",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable verbose debug output (RAW/HEX + parser logs to stderr)",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )

    args = parser.parse_args()

    print(
        f"Listening on {args.device} @ {args.baud} baud "
        f"for JK RS485-2 frames ({BATTERIES_EXPECTED} batteries, {CELLS_PER_BATTERY} cells each)...",
        file=sys.stderr,
    )

    try:
        with open_serial(args.device, args.baud) as conn:
            process_stream(conn, debug=args.debug, pretty=args.pretty)
    except KeyboardInterrupt:
        print("\nInterrupted by user.", file=sys.stderr)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
