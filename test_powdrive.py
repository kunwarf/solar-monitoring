import asyncio
import argparse
import logging
from typing import Any, Dict, Optional, List

from solarhub.adapters.powdrive import PowdriveAdapter
from solarhub.config import InverterConfig, InverterAdapterConfig, SafetyLimits, SolarArrayParams


def build_config(serial_port: str, unit_id: int, baudrate: int = 9600) -> InverterConfig:
    adapter = InverterAdapterConfig(
        type="powdrive",
        transport="rtu",
        unit_id=unit_id,
        serial_port=serial_port,
        baudrate=baudrate,
        parity="N",
        stopbits=1,
        bytesize=8,
        register_map_file="register_maps/powdrive_registers.json",
    )
    return InverterConfig(
        id="powdrive_test",
        name="Powdrive Test",
        adapter=adapter,
        safety=SafetyLimits(),
        solar=[SolarArrayParams()]
    )


def enum_label(adapter: PowdriveAdapter, ident: str, raw: Any) -> Optional[str]:
    try:
        r = adapter._find_reg_by_id_or_name(ident)  # type: ignore[attr-defined]
        enum = r.get("enum") if isinstance(r, dict) else None
        if isinstance(enum, dict):
            return enum.get(str(raw))
    except Exception:
        pass
    return None


async def run(serial_port: str, unit_id: int, baudrate: int, enable_write_tests: bool = False) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    log = logging.getLogger("powdrive_test")
    
    log.info(f"Starting Powdrive test (enable_write_tests={enable_write_tests})")

    cfg = build_config(serial_port, unit_id, baudrate)
    adapter = PowdriveAdapter(cfg)

    await adapter.connect()
    log.info("Connected to powdrive (port=%s, unit=%s)", serial_port, unit_id)

    # Hardcoded register reads (no JSON dependency)
    async def read_u16(addr: int, count: int = 1) -> List[int]:
        return await adapter._read_u16(addr, count)  # type: ignore[attr-defined]

    def s16(x: int) -> int:
        x &= 0xFFFF
        return x - 0x10000 if x & 0x8000 else x

    # First, test basic connectivity with a simple register (modbus address at 1)
    log.info("Testing basic connectivity with register 1 (Modbus Address)...")
    try:
        addr_reg = (await read_u16(1, 1))[0]
        log.info("✓ Basic connectivity OK: Modbus address register = %s", addr_reg)
        if addr_reg != unit_id:
            log.warning("  Note: Register 1 value (%s) != provided unit_id (%s)", addr_reg, unit_id)
    except Exception as e:
        log.error("✗ Basic connectivity FAILED: %s", e)
        log.error("  Troubleshooting:")
        log.error("   1. Check serial port exists: ls -l %s", serial_port)
        log.error("   2. Verify unit_id (current: %s) matches inverter Modbus address", unit_id)
        log.error("   3. Try different baudrate (current: %s)", baudrate)
        log.error("   4. Check wiring (A/B, ground)")
        log.error("   5. Verify device is powered and online")
        await adapter.close()
        return

    # Serial (3..7)
    try:
        log.info("Reading serial number (registers 3-7)...")
        regs = await read_u16(3, 5)
        buf = bytearray()
        for w in regs:
            buf.append((w >> 8) & 0xFF)
            buf.append(w & 0xFF)
        serial = bytes(buf).split(b"\x00", 1)[0].decode("ascii", errors="ignore").strip()
        log.info("serial_number = %s", serial)
    except Exception as e:
        log.error("Failed to read serial_number: %s", e)

    # Inverter type (0)
    try:
        log.info("Reading inverter type (register 0)...")
        val = (await read_u16(0, 1))[0]
        label_map = {2: "Inverter", 3: "Hybrid Inverter", 4: "Micro Inverter", 5: "3 Phase Hybrid Inverter"}
        label = label_map.get(val)
        if label:
            log.info("inverter_type = %s (%s)", val, label)
        else:
            log.info("inverter_type = %s", val)
    except Exception as e:
        log.error("Failed to read inverter_type: %s", e)

    # Grid power (625, S16)
    try:
        log.info("Reading grid power (register 625)...")
        val = s16((await read_u16(625, 1))[0])
        log.info("grid_power_w = %s", val)
    except Exception as e:
        log.error("Failed to read grid_power_w: %s", e)

    # Battery voltage (587, 0.01)
    try:
        log.info("Reading battery voltage (register 587)...")
        val = (await read_u16(587, 1))[0] * 0.01
        log.info("battery_voltage = %.2f V", val)
    except Exception as e:
        log.error("Failed to read battery_voltage: %s", e)

    # Grid frequency (609, 0.01)
    try:
        log.info("Reading grid frequency (register 609)...")
        val = (await read_u16(609, 1))[0] * 0.01
        log.info("grid_frequency_hz = %.2f Hz", val)
    except Exception as e:
        log.error("Failed to read grid_frequency_hz: %s", e)

    # Inverter temperature (540, 0.1)
    try:
        log.info("Reading inverter temperature (register 540)...")
        val = (await read_u16(540, 1))[0] * 0.1
        log.info("inverter_temp_c = %.1f °C", val)
    except Exception as e:
        log.error("Failed to read inverter_temp_c: %s", e)

    # Run write tests if requested
    if enable_write_tests:
        log.info("=" * 60)
        log.info("Starting write tests...")
        log.info("=" * 60)
        try:
            await test_writes(adapter)
            log.info("Write tests completed successfully")
        except Exception as e:
            log.error(f"Write tests failed with exception: {e}", exc_info=True)
    else:
        log.info("Write tests skipped (use --test-write to enable)")


async def test_writes(adapter: PowdriveAdapter) -> None:
    """Test write operations for TOU windows and related registers."""
    log = logging.getLogger("powdrive_test")
    
    log.info("=" * 60)
    log.info("STARTING TOU REGISTER TESTS")
    log.info("=" * 60)
    
    # Phase 1: Read all TOU registers first
    log.info("\n" + "=" * 60)
    log.info("PHASE 1: READING ALL TOU REGISTERS")
    log.info("=" * 60)
    
    current_tou = 0
    tou_values = {}
    
    # Read TOU enable register (146)
    log.info("\n--- Reading TOU Enable Register (146, tou_selling) ---")
    try:
        await asyncio.sleep(0.5)
        current_tou = await adapter.read_by_ident("tou_selling")
        tou_values["tou_selling"] = current_tou
        log.info(f"✓ tou_selling (register 146): 0x{current_tou:04X} ({current_tou})")
        log.info(f"  Bit 0 (TOU enable): {bool(current_tou & 1)}")
        log.info(f"  Bit 1 (Monday): {bool(current_tou & 2)}")
        log.info(f"  Bit 2 (Tuesday): {bool(current_tou & 4)}")
        log.info(f"  Bit 3 (Wednesday): {bool(current_tou & 8)}")
        log.info(f"  Bit 4 (Thursday): {bool(current_tou & 16)}")
        log.info(f"  Bit 5 (Friday): {bool(current_tou & 32)}")
        log.info(f"  Bit 6 (Saturday): {bool(current_tou & 64)}")
        log.info(f"  Bit 7 (Sunday): {bool(current_tou & 128)}")
        log.info(f"  Bit 8 (Spanish mode): {bool(current_tou & 256)}")
    except Exception as e:
        log.error(f"✗ Failed to read tou_selling: {e}")
        tou_values["tou_selling"] = None
    
    # Read all TOU window time registers (148-153)
    log.info("\n--- Reading TOU Window Time Registers (148-153) ---")
    for idx in range(1, 7):
        try:
            await asyncio.sleep(0.3)
            reg_name = f"prog{idx}_time"
            value = await adapter.read_by_ident(reg_name)
            tou_values[reg_name] = value
            # Decode time (Powdrive format: HHMM decimal)
            hours = value // 100
            minutes = value % 100
            decoded = f"{hours:02d}:{minutes:02d}"
            log.info(f"✓ {reg_name} (register {146+idx}): {value} -> '{decoded}'")
        except Exception as e:
            log.error(f"✗ Failed to read {reg_name}: {e}")
            tou_values[reg_name] = None
    
    # Read all TOU window power registers (154-159)
    log.info("\n--- Reading TOU Window Power Registers (154-159) ---")
    for idx in range(1, 7):
        try:
            await asyncio.sleep(0.3)
            reg_name = f"prog{idx}_power_w"
            value = await adapter.read_by_ident(reg_name)
            tou_values[reg_name] = value
            log.info(f"✓ {reg_name} (register {153+idx}): {value}W")
        except Exception as e:
            log.error(f"✗ Failed to read {reg_name}: {e}")
            tou_values[reg_name] = None
    
    # Read all TOU window capacity registers (166-171)
    log.info("\n--- Reading TOU Window Capacity Registers (166-171) ---")
    for idx in range(1, 7):
        try:
            await asyncio.sleep(0.3)
            reg_name = f"prog{idx}_capacity_pct"
            value = await adapter.read_by_ident(reg_name)
            tou_values[reg_name] = value
            log.info(f"✓ {reg_name} (register {165+idx}): {value}%")
        except Exception as e:
            log.error(f"✗ Failed to read {reg_name}: {e}")
            tou_values[reg_name] = None
    
    # Read all TOU window charge mode registers (172-177)
    log.info("\n--- Reading TOU Window Charge Mode Registers (172-177) ---")
    for idx in range(1, 7):
        try:
            await asyncio.sleep(0.3)
            reg_name = f"prog{idx}_charge_mode"
            value = await adapter.read_by_ident(reg_name)
            tou_values[reg_name] = value
            log.info(f"✓ {reg_name} (register {171+idx}): 0x{value:04X} ({value})")
            log.info(f"    Bit 0 (grid charging): {bool(value & 1)}")
            log.info(f"    Bit 1 (gen charging): {bool(value & 2)}")
        except Exception as e:
            log.error(f"✗ Failed to read {reg_name}: {e}")
            tou_values[reg_name] = None
    
    # Summary
    log.info("\n" + "=" * 60)
    log.info("READ SUMMARY")
    log.info("=" * 60)
    readable = [k for k, v in tou_values.items() if v is not None]
    unreadable = [k for k, v in tou_values.items() if v is None]
    log.info(f"Readable registers: {len(readable)}/{len(tou_values)}")
    if readable:
        log.info(f"  ✓ Readable: {', '.join(readable)}")
    if unreadable:
        log.warning(f"  ✗ Unreadable: {', '.join(unreadable)}")
    
    if not readable:
        log.error("No TOU registers are readable! Cannot proceed with write tests.")
        return
    
    # Phase 2: Write tests (single attempt, no retries)
    log.info("\n" + "=" * 60)
    log.info("PHASE 2: WRITE TESTS (SINGLE ATTEMPT)")
    log.info("=" * 60)
    log.info("Note: Each write will be attempted only once (no retries)")
    log.info("")
    log.info("According to Powdrive spec (matches minimalmodbus library behavior):")
    log.info("  - Registers 60-499 must use function code 16 (0x10) - Write Multiple Holding Registers")
    log.info("  - Registers < 60 use function code 6 (0x06) - Write Single Holding Register")
    log.info("  - All TOU registers (146-177) are in range 60-499, so they use function code 16 (0x10)")
    log.info("  - This matches minimalmodbus library which uses function code 16 for writes")
    log.info("  - The adapter will automatically select the correct function code based on address")
    
    # Test 1: Write TOU enable register (146)
    log.info("\n--- Write Test 1: TOU Enable Register (146) ---")
    log.info("Register 146 is >= 60, so should use function code 16 (0x10) - Write Multiple")
    log.info("This matches minimalmodbus library behavior")
    try:
        # Enable TOU and all days (bits 0-7)
        desired_value = 0
        desired_value |= (1 << 0)  # Bit 0: Enable TOU
        desired_value |= (1 << 1) | (1 << 2) | (1 << 3) | (1 << 4) | (1 << 5) | (1 << 6) | (1 << 7)  # All days
        log.info(f"Writing: 0x{current_tou:04X} -> 0x{desired_value:04X}")
        log.info("Expected: Function code 16 (0x10) - Write Multiple Holding Registers")
        
        await asyncio.sleep(0.5)
        await adapter.write_by_ident("tou_selling", desired_value)
        log.info("✓ Write successful (check logs above for function code used)")
        
        # Verify by reading back
        await asyncio.sleep(0.5)
        verify = await adapter.read_by_ident("tou_selling")
        log.info(f"Read back: 0x{verify:04X} ({verify})")
        if verify == desired_value:
            log.info("✓ Verification successful")
        else:
            log.warning(f"⚠ Mismatch: expected 0x{desired_value:04X}, got 0x{verify:04X}")
    except Exception as e:
        log.error(f"✗ Write failed: {e}")
        log.warning("Continuing with other tests...")
    
    # Test 2: Write time register (prog1_time)
    log.info("\n--- Write Test 2: TOU Window 1 Time (prog1_time, register 148) ---")
    log.info("Register 148 is >= 60, so should use function code 16 (0x10) - Write Multiple")
    log.info("This matches minimalmodbus library behavior")
    try:
        test_time = "00:00"
        log.info(f"Writing time: '{test_time}' (expected encoded: 0)")
        log.info("Expected: Function code 16 (0x10) - Write Multiple Holding Registers")
        log.info("Time format: HHMM decimal (e.g., 2359 = 23:59)")
        
        await asyncio.sleep(0.5)
        await adapter.write_by_ident("prog1_time", test_time)
        log.info("✓ Write successful (check logs above for function code used)")
        
        # Verify by reading back
        await asyncio.sleep(0.5)
        verify_time = await adapter.read_by_ident("prog1_time")
        log.info(f"Read back: {verify_time}")
        
        # Decode time (Powdrive format: HHMM decimal)
        hours = verify_time // 100
        minutes = verify_time % 100
        decoded = f"{hours:02d}:{minutes:02d}"
        log.info(f"Decoded: '{decoded}'")
        if decoded == test_time:
            log.info("✓ Verification successful")
        else:
            log.warning(f"⚠ Mismatch: expected '{test_time}', got '{decoded}'")
    except Exception as e:
        log.error(f"✗ Write failed: {e}")
        log.warning("Continuing with other tests...")
    
    # Test 3: Write power register (prog1_power_w)
    log.info("\n--- Write Test 3: TOU Window 1 Power (prog1_power_w, register 154) ---")
    log.info("Register 154 is >= 60, so should use function code 16 (0x10) - Write Multiple")
    log.info("This matches minimalmodbus library behavior")
    try:
        test_power = 500
        log.info(f"Writing: {test_power}W")
        log.info("Expected: Function code 16 (0x10) - Write Multiple Holding Registers")
        
        await asyncio.sleep(0.5)
        await adapter.write_by_ident("prog1_power_w", test_power)
        log.info("✓ Write successful (check logs above for function code used)")
        
        # Verify by reading back
        await asyncio.sleep(0.5)
        verify_power = await adapter.read_by_ident("prog1_power_w")
        log.info(f"Read back: {verify_power}W")
        if verify_power == test_power:
            log.info("✓ Verification successful")
        else:
            log.warning(f"⚠ Mismatch: expected {test_power}W, got {verify_power}W")
    except Exception as e:
        log.error(f"✗ Write failed: {e}")
        log.warning("Continuing with other tests...")
    
    # Test 4: Write capacity register (prog1_capacity_pct)
    log.info("\n--- Write Test 4: TOU Window 1 Capacity (prog1_capacity_pct, register 166) ---")
    log.info("Register 166 is >= 60, so should use function code 16 (0x10) - Write Multiple")
    log.info("This matches minimalmodbus library behavior")
    try:
        test_capacity = 50
        log.info(f"Writing: {test_capacity}%")
        log.info("Expected: Function code 16 (0x10) - Write Multiple Holding Registers")
        
        await asyncio.sleep(0.5)
        await adapter.write_by_ident("prog1_capacity_pct", test_capacity)
        log.info("✓ Write successful (check logs above for function code used)")
        
        # Verify by reading back
        await asyncio.sleep(0.5)
        verify_capacity = await adapter.read_by_ident("prog1_capacity_pct")
        log.info(f"Read back: {verify_capacity}%")
        if verify_capacity == test_capacity:
            log.info("✓ Verification successful")
        else:
            log.warning(f"⚠ Mismatch: expected {test_capacity}%, got {verify_capacity}%")
    except Exception as e:
        log.error(f"✗ Write failed: {e}")
        log.warning("Continuing with other tests...")
    
    # Test 5: Write charge mode register (prog1_charge_mode)
    log.info("\n--- Write Test 5: TOU Window 1 Charge Mode (prog1_charge_mode, register 172) ---")
    log.info("Register 172 is >= 60, so should use function code 16 (0x10) - Write Multiple")
    log.info("This matches minimalmodbus library behavior")
    try:
        test_charge_mode = 1  # Bit 0 = grid charging enabled
        log.info(f"Writing: 0x{test_charge_mode:04X} (bit 0 = grid charging)")
        log.info("Expected: Function code 16 (0x10) - Write Multiple Holding Registers")
        
        await asyncio.sleep(0.5)
        await adapter.write_by_ident("prog1_charge_mode", test_charge_mode)
        log.info("✓ Write successful (check logs above for function code used)")
        
        # Verify by reading back
        await asyncio.sleep(0.5)
        verify_mode = await adapter.read_by_ident("prog1_charge_mode")
        log.info(f"Read back: 0x{verify_mode:04X} ({verify_mode})")
        log.info(f"  Bit 0 (grid charging): {bool(verify_mode & 1)}")
        log.info(f"  Bit 1 (gen charging): {bool(verify_mode & 2)}")
        if verify_mode == test_charge_mode:
            log.info("✓ Verification successful")
        else:
            log.warning(f"⚠ Mismatch: expected 0x{test_charge_mode:04X}, got 0x{verify_mode:04X}")
    except Exception as e:
        log.error(f"✗ Write failed: {e}")
        log.warning("Continuing with other tests...")
    
    # Test 6: Test full TOU window command
    log.info("\n--- Write Test 6: Full TOU Window Command (set_tou_window1) ---")
    log.info("This will write multiple registers (146, 148, 154, 166, 172)")
    log.info("All registers are >= 60, so all should use function code 16 (0x10) - Write Multiple")
    log.info("This matches minimalmodbus library behavior")
    try:
        cmd = {
            "action": "set_tou_window1",
            "start_time": "00:00",
            "end_time": "06:00",
            "power_w": 500,
            "target_soc_pct": 50,
            "type": "discharge"
        }
        log.info(f"Executing command: {cmd}")
        log.info("Expected: All writes should use function code 16 (0x10) - Write Multiple Holding Registers")
        
        await asyncio.sleep(0.5)
        result = await adapter.handle_command(cmd)
        log.info(f"Command result: {result}")
        if result.get("ok"):
            log.info("✓ Command executed successfully")
        else:
            log.error(f"✗ Command failed: {result.get('reason')}")
    except Exception as e:
        log.error(f"✗ Command execution failed: {e}")
    
    log.info("\n" + "=" * 60)
    log.info("WRITE TESTS COMPLETED")
    log.info("=" * 60)
    
    # Close safely
    try:
        await adapter.close()
    except TypeError:
        # Fallback if close is sync
        try:
            if adapter.client and getattr(adapter.client, "close", None):
                adapter.client.close()
        except Exception:
            pass
    log.info("Done")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Powdrive connectivity and sensor smoke test")
    parser.add_argument("--port", required=True, help="Serial port, e.g. /dev/ttyUSB2 or COM3")
    parser.add_argument("--unit", type=int, default=1, help="Modbus unit id")
    parser.add_argument("--baud", type=int, default=9600, help="Baudrate")
    parser.add_argument("--test-write", action="store_true", 
                       help="Enable write tests (TOU window registers). WARNING: This will modify inverter settings!")
    args = parser.parse_args()

    if args.test_write:
        print("=" * 60)
        print("WARNING: Write tests enabled - this will modify inverter settings!")
        print("=" * 60)
        import time
        time.sleep(2)

    asyncio.run(run(args.port, args.unit, args.baud, enable_write_tests=args.test_write))


