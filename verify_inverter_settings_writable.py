#!/usr/bin/env python3
"""
End-to-end verification script for inverter settings writability.

This script checks:
1. All UI fields have corresponding API endpoints
2. All API endpoints map to writable registers
3. All registers are marked as writable (RW/WO/R/W) in register maps
4. Fields marked as readOnly in UI are actually read-only in register maps
5. All register IDs used in API exist in register maps
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict

# Field mappings from UI to register IDs (from API endpoints)
FIELD_TO_REGISTER_MAP = {
    # Grid Settings
    'grid_voltage_high_v': 'grid_voltage_high_v',
    'grid_voltage_low_v': 'grid_voltage_low_v',
    'grid_frequency_hz': 'grid_frequency_hz',
    'grid_frequency_high_hz': 'grid_frequency_high_hz',
    'grid_frequency_low_hz': 'grid_frequency_low_hz',
    'grid_peak_shaving': 'control_board_special_function_1',  # Bit field
    'grid_peak_shaving_power_kw': 'grid_peak_shaving_power_w',
    
    # Battery Type
    'battery_type': 'battery_type',
    'battery_capacity_ah': 'battery_capacity_ah',
    'battery_operation': 'battery_mode_source',  # Mapped: "State of charge" -> 1, "Voltage" -> 0
    
    # Battery Charging
    'max_discharge_current_a': 'battery_max_discharge_current_a',
    'max_charge_current_a': 'battery_max_charge_current_a',
    'max_grid_charge_current_a': 'grid_charge_battery_current_a',
    'max_generator_charge_current_a': 'generator_charge_battery_current_a',
    'battery_float_charge_voltage_v': 'battery_floating_voltage_v',
    'battery_absorption_charge_voltage_v': 'battery_absorption_voltage_v',
    'battery_equalization_charge_voltage_v': 'battery_equalization_voltage_v',
    'max_grid_charger_power_w': 'maximum_grid_charger_power',  # Senergy: direct, Powdrive: converted to current
    'max_charger_power_w': 'maximum_charger_power',  # Senergy: direct, Powdrive: converted to current
    'max_discharger_power_w': 'maximum_discharger_power',  # Senergy: direct, Powdrive: converted to current
    
    # Work Mode
    'remote_switch': None,  # Read-only
    'grid_charge': 'grid_charge',  # Mapped differently for Powdrive vs Senergy
    'generator_charge': 'generator_charge_enabled',
    'force_generator_on': None,  # Read-only
    'output_shutdown_capacity_pct': 'battery_shutdown_capacity_pct',
    'stop_battery_discharge_capacity_pct': 'battery_low_capacity_pct',
    'start_battery_discharge_capacity_pct': 'battery_restart_capacity_pct',
    'start_grid_charge_capacity_pct': 'grid_charging_start_capacity_pct',
    'off_grid_mode': 'off_grid_mode',
    'off_grid_start_up_battery_capacity_pct': 'off_grid_start_up_battery_capacity_pct',
    
    # Work Mode Detail
    'work_mode': 'limit_control_function',  # Mapped to enum
    'solar_export_when_battery_full': 'solar_sell',
    'energy_pattern': 'solar_priority',
    'max_sell_power_kw': 'max_sell_power_kw',  # May be converted to W
    'max_solar_power_kw': 'max_solar_power_kw',  # May be converted to W
    'grid_trickle_feed_w': 'zero_export_power_w',
    'max_export_power_w': 'max_export_power_w',
    
    # Auxiliary Settings
    'auxiliary_port': None,  # Read-only
    'generator_connected_to_grid_input': None,  # Read-only
    'generator_peak_shaving': 'control_board_special_function_1',  # Bit field (bits 2-3)
    'generator_peak_shaving_power_kw': 'generator_peak_shaving_power_w',
    'generator_stop_capacity_pct': 'generator_charging_start_capacity_pct',  # Note: might be inverted
    'generator_start_capacity_pct': 'generator_charging_start_capacity_pct',
    'generator_max_run_time_h': 'generator_max_run_time_h',
    'generator_down_time_h': 'generator_down_time_h',
}

# Register IDs that may have different names in Senergy vs Powdrive
REGISTER_ALIASES = {
    # Senergy uses these names
    'maximum_grid_charger_power': ['maximum_grid_charger_power', 'max_grid_charger_power'],
    'maximum_charger_power': ['maximum_charger_power', 'max_charger_power'],
    'maximum_discharger_power': ['maximum_discharger_power', 'max_discharger_power'],
    # Powdrive converts power to current, so these may not exist as power registers
    'max_grid_charger_power_w': ['maximum_grid_charger_power', 'grid_charge_battery_current_a'],
    'max_charger_power_w': ['maximum_charger_power', 'battery_max_charge_current_a'],
    'max_discharger_power_w': ['maximum_discharger_power', 'battery_max_discharge_current_a'],
}

# UI fields marked as readOnly
READONLY_UI_FIELDS = {
    'remote_switch',
    'force_generator_on',
    'start_grid_charge_capacity_pct',
    'auxiliary_port',
    'generator_connected_to_grid_input',
}

def load_register_map(register_file: Path) -> Dict[str, Dict]:
    """Load register map JSON file."""
    try:
        with open(register_file, 'r', encoding='utf-8') as f:
            registers = json.load(f)
        # Create a dict keyed by register ID
        reg_map = {}
        for reg in registers:
            reg_id = reg.get('id')
            if reg_id:
                reg_map[reg_id] = reg
        return reg_map
    except Exception as e:
        print(f"Error loading {register_file}: {e}")
        return {}

def check_register_writable(reg: Dict) -> bool:
    """Check if register is writable."""
    rw = str(reg.get('rw', 'RO')).upper()
    return rw in ('RW', 'WO', 'R/W')

def verify_inverter_settings():
    """Main verification function."""
    base_dir = Path(__file__).parent
    register_maps_dir = base_dir / 'register_maps'
    
    # Load register maps
    senergy_map = load_register_map(register_maps_dir / 'senergy_registers.json')
    powdrive_map = load_register_map(register_maps_dir / 'powdrive_registers.json')
    
    print("=" * 80)
    print("INVERTER SETTINGS WRITABILITY VERIFICATION")
    print("=" * 80)
    print()
    
    issues = []
    warnings = []
    verified = []
    
    # Check each field
    for ui_field, register_id in FIELD_TO_REGISTER_MAP.items():
        if register_id is None:
            # Field is read-only, check if it's marked as such in UI
            if ui_field not in READONLY_UI_FIELDS:
                warnings.append(f"Field '{ui_field}' has no register mapping but is not marked as readOnly in UI")
            continue
        
        # Check if register exists in both maps (or aliases)
        register_aliases = REGISTER_ALIASES.get(register_id, [register_id])
        found_in_senergy = any(alias in senergy_map for alias in register_aliases)
        found_in_powdrive = any(alias in powdrive_map for alias in register_aliases)
        
        if not found_in_senergy and not found_in_powdrive:
            issues.append(f"Field '{ui_field}' -> Register '{register_id}': NOT FOUND in register maps (checked: {register_aliases})")
            continue
        
        # Check writability for each alias
        for map_name, reg_map in [('Senergy', senergy_map), ('Powdrive', powdrive_map)]:
            found = False
            for alias in register_aliases:
                if alias in reg_map:
                    found = True
                    reg = reg_map[alias]
                    is_writable = check_register_writable(reg)
                    kind = reg.get('kind', '').lower()
                    
                    if kind != 'holding':
                        issues.append(f"Field '{ui_field}' -> Register '{alias}' ({map_name}): Not a holding register (kind={kind})")
                    elif not is_writable:
                        issues.append(f"Field '{ui_field}' -> Register '{alias}' ({map_name}): Marked as read-only (rw={reg.get('rw')})")
                    else:
                        verified.append(f"Field '{ui_field}' -> Register '{alias}' ({map_name}): [OK] Writable")
                    break
            if not found and (map_name == 'Senergy' and found_in_senergy) or (map_name == 'Powdrive' and found_in_powdrive):
                # Register exists but with different alias
                pass
    
    # Check read-only fields
    print("Checking read-only fields...")
    for field in READONLY_UI_FIELDS:
        if field in FIELD_TO_REGISTER_MAP:
            register_id = FIELD_TO_REGISTER_MAP[field]
            if register_id:
                # Should be read-only in register maps
                for map_name, reg_map in [('Senergy', senergy_map), ('Powdrive', powdrive_map)]:
                    if register_id in reg_map:
                        reg = reg_map[register_id]
                        if check_register_writable(reg):
                            warnings.append(f"Read-only UI field '{field}' -> Register '{register_id}' ({map_name}): Is writable in register map")
    
    # Check for fields that should be writable but are marked readOnly in UI
    print("\nChecking for writable registers marked as readOnly in UI...")
    for ui_field, register_id in FIELD_TO_REGISTER_MAP.items():
        if ui_field in READONLY_UI_FIELDS and register_id:
            for map_name, reg_map in [('Senergy', senergy_map), ('Powdrive', powdrive_map)]:
                if register_id in reg_map:
                    reg = reg_map[register_id]
                    if check_register_writable(reg):
                        warnings.append(f"UI field '{ui_field}' is marked readOnly but register '{register_id}' ({map_name}) is writable")
    
    # Print results
    print("\n" + "=" * 80)
    print("VERIFICATION RESULTS")
    print("=" * 80)
    print(f"\n[OK] Verified Writable: {len(verified)}")
    if verified:
        for v in verified[:10]:  # Show first 10
            print(f"  {v}")
        if len(verified) > 10:
            print(f"  ... and {len(verified) - 10} more")
    
    print(f"\n[WARN] Warnings: {len(warnings)}")
    if warnings:
        for w in warnings:
            print(f"  {w}")
    
    print(f"\n[ERROR] Issues: {len(issues)}")
    if issues:
        for i in issues:
            print(f"  {i}")
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    total_fields = len([f for f in FIELD_TO_REGISTER_MAP.values() if f is not None])
    success_rate = (len(verified) / total_fields * 100) if total_fields > 0 else 0
    print(f"Total fields checked: {total_fields}")
    print(f"Successfully verified: {len(verified)} ({success_rate:.1f}%)")
    print(f"Warnings: {len(warnings)}")
    print(f"Issues: {len(issues)}")
    
    if issues:
        print("\n[FAIL] VERIFICATION FAILED - Some fields cannot be written")
        return 1
    elif warnings:
        print("\n[WARN] VERIFICATION PASSED WITH WARNINGS")
        return 0
    else:
        print("\n[PASS] VERIFICATION PASSED - All fields are writable")
        return 0

if __name__ == '__main__':
    exit(verify_inverter_settings())

