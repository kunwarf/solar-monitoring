#!/usr/bin/env python3
"""
Script to add standard_id mappings to register JSON files.

This script adds standard_id fields to register definitions based on
the register id. If a register id already matches a standard field name,
it sets standard_id to the same value. Otherwise, it attempts to map
common device-specific names to standard names.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any

# Mapping from common device-specific names to standard names
STANDARD_MAPPINGS = {
    # Power flows
    "pv_power": "pv_power_w",
    "pv1_power": "pv1_power_w",
    "pv2_power": "pv2_power_w",
    "pv3_power": "pv3_power_w",
    "pv4_power": "pv4_power_w",
    "load_power": "load_power_w",
    "grid_power": "grid_power_w",
    "battery_power": "batt_power_w",
    "batt_power": "batt_power_w",
    
    # Battery data
    "battery_voltage": "batt_voltage_v",
    "battery_current": "batt_current_a",
    "battery_soc": "batt_soc_pct",
    "battery_temp": "batt_temp_c",
    "batt_voltage": "batt_voltage_v",
    "batt_current": "batt_current_a",
    "batt_soc": "batt_soc_pct",
    "batt_temp": "batt_temp_c",
    
    # Inverter data
    "inverter_temp": "inverter_temp_c",
    "inner_temperature": "inverter_temp_c",
    "inverter_mode": "inverter_mode",
    "hybrid_work_mode": "inverter_mode",
    "working_mode": "inverter_mode",
    
    # Energy fields
    "pv_energy_today": "today_energy",
    "pv_energy_today_kwh": "today_energy",
    "day_gen_energy": "today_energy",
    "day_gen_energy_kwh": "today_energy",
    "load_energy_today": "today_load_energy",
    "load_energy_today_kwh": "today_load_energy",
    "daily_energy_to_eps": "today_load_energy",
    "grid_import_energy_today": "today_import_energy",
    "grid_import_energy_today_kwh": "today_import_energy",
    "grid_export_energy_today": "today_export_energy",
    "grid_export_energy_today_kwh": "today_export_energy",
    "battery_charge_energy_today": "today_battery_charge_energy",
    "battery_charge_energy_today_kwh": "today_battery_charge_energy",
    "battery_discharge_energy_today": "today_battery_discharge_energy",
    "battery_discharge_energy_today_kwh": "today_battery_discharge_energy",
    "total_energy": "total_energy",
    "pv_energy_total": "total_energy",
    "pv_energy_total_kwh": "total_energy",
    
    # Device info
    "device_model": "device_model",
    "device_serial_number": "device_serial_number",
    "rated_power": "rated_power_w",
    "rated_power_w": "rated_power_w",
    
    # Three-phase load
    "load_l1_power": "load_l1_power_w",
    "load_l2_power": "load_l2_power_w",
    "load_l3_power": "load_l3_power_w",
    "load_l1_voltage": "load_l1_voltage_v",
    "load_l2_voltage": "load_l2_voltage_v",
    "load_l3_voltage": "load_l3_voltage_v",
    "load_l1_current": "load_l1_current_a",
    "load_l2_current": "load_l2_current_a",
    "load_l3_current": "load_l3_current_a",
    "load_frequency": "load_frequency_hz",
    
    # Three-phase grid
    "grid_l1_power": "grid_l1_power_w",
    "grid_l2_power": "grid_l2_power_w",
    "grid_l3_power": "grid_l3_power_w",
    "grid_l1_voltage": "grid_l1_voltage_v",
    "grid_l2_voltage": "grid_l2_voltage_v",
    "grid_l3_voltage": "grid_l3_voltage_v",
    "grid_l1_current": "grid_l1_current_a",
    "grid_l2_current": "grid_l2_current_a",
    "grid_l3_current": "grid_l3_current_a",
    "grid_frequency": "grid_frequency_hz",
    "grid_voltage": "grid_l1_voltage_v",
}


def normalize_key(key: str) -> str:
    """Normalize a key for matching."""
    return key.lower().replace("_", "").replace("-", "")


def find_standard_mapping(reg_id: str) -> str:
    """
    Find standard field name for a register id.
    
    Args:
        reg_id: Device-specific register id
        
    Returns:
        Standard field name, or reg_id if no mapping found
    """
    # Check exact match first
    if reg_id in STANDARD_MAPPINGS:
        return STANDARD_MAPPINGS[reg_id]
    
    # Check normalized match
    reg_normalized = normalize_key(reg_id)
    for device_key, standard_key in STANDARD_MAPPINGS.items():
        if normalize_key(device_key) == reg_normalized:
            return standard_key
    
    # Check if reg_id already matches a standard name (ends with _w, _v, _a, etc.)
    if any(reg_id.endswith(suffix) for suffix in ["_w", "_v", "_a", "_c", "_pct", "_hz", "_kwh"]):
        return reg_id
    
    # No mapping found, return as-is
    return reg_id


def add_standard_ids(registers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Add standard_id fields to register definitions.
    
    Args:
        registers: List of register definitions
        
    Returns:
        Updated list of register definitions with standard_id fields
    """
    updated = []
    for reg in registers:
        reg = reg.copy()  # Don't modify original
        reg_id = reg.get("id")
        
        if reg_id:
            # Only add standard_id if not already present
            if "standard_id" not in reg:
                standard_id = find_standard_mapping(reg_id)
                if standard_id != reg_id:
                    reg["standard_id"] = standard_id
                    print(f"Mapped {reg_id} -> {standard_id}")
        
        updated.append(reg)
    
    return updated


def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python add_standard_id_mappings.py <register_json_file> [output_file]")
        print("  If output_file is not provided, updates file in-place")
        sys.exit(1)
    
    input_file = Path(sys.argv[1])
    if not input_file.exists():
        print(f"Error: File not found: {input_file}")
        sys.exit(1)
    
    output_file = Path(sys.argv[2]) if len(sys.argv) > 2 else input_file
    
    # Load register JSON
    print(f"Loading register map from: {input_file}")
    with open(input_file, 'r', encoding='utf-8') as f:
        registers = json.load(f)
    
    if not isinstance(registers, list):
        print(f"Error: Expected JSON array, got {type(registers)}")
        sys.exit(1)
    
    print(f"Found {len(registers)} registers")
    
    # Add standard_id mappings
    updated_registers = add_standard_ids(registers)
    
    # Count how many got mappings
    mapped_count = sum(1 for r in updated_registers if "standard_id" in r and r["standard_id"] != r.get("id"))
    print(f"\nAdded {mapped_count} standard_id mappings")
    
    # Save updated JSON
    print(f"Saving updated register map to: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(updated_registers, f, indent=2, ensure_ascii=False)
    
    print("Done!")


if __name__ == "__main__":
    main()

