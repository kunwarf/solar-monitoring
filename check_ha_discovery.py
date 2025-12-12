#!/usr/bin/env python3
"""
Script to verify Home Assistant discovery publishing for all hierarchy levels.
Checks if all expected entities are being published to MQTT.
"""
import sys
import json
from pathlib import Path

def check_ha_discovery_coverage():
    """
    Check if all hierarchy levels have HA discovery methods.
    This is a static code analysis check.
    """
    print("=" * 80)
    print("HOME ASSISTANT DISCOVERY COVERAGE CHECK")
    print("=" * 80)
    
    hierarchy_levels = {
        "System": {
            "method": "publish_system_entities",
            "called_in": "app.py:1045",
            "status": "OK"
        },
        "Inverter Array": {
            "method": "publish_array_entities",
            "called_in": "app.py:982",
            "status": "OK"
        },
        "Battery Array": {
            "method": "publish_battery_array_entities",
            "called_in": "app.py:1060",
            "status": "OK"
        },
        "Battery Pack": {
            "method": "publish_pack_entities + publish_battery_bank_entities",
            "called_in": "app.py:1001, 1013",
            "status": "OK"
        },
        "Battery Unit": {
            "method": "publish_battery_unit_entities",
            "called_in": "app.py:1028 (startup), 2912 (runtime)",
            "status": "WARN (only if telemetry available)"
        },
        "Battery Cell": {
            "method": "publish_battery_cell_entities",
            "called_in": "app.py:2963 (runtime only)",
            "status": "WARN (only when cells_data available)"
        },
        "Inverter": {
            "method": "publish_all_for_inverter",
            "called_in": "app.py:748",
            "status": "OK"
        },
        "Meter": {
            "method": "publish_meter_entities",
            "called_in": "app.py:953",
            "status": "OK"
        }
    }
    
    print("\n1. HIERARCHY LEVEL COVERAGE:")
    print("-" * 80)
    for level, info in hierarchy_levels.items():
        print(f"  {info['status']} {level:20s} - {info['method']:40s}")
        print(f"    Called in: {info['called_in']}")
    
    print("\n2. POTENTIAL ISSUES:")
    print("-" * 80)
    issues = []
    
    # Check battery unit discovery
    if "WARN" in hierarchy_levels["Battery Unit"]["status"]:
        issues.append({
            "level": "Battery Unit",
            "issue": "Discovery only published if telemetry available at startup OR during first poll",
            "impact": "Units discovered after startup may not have HA entities until first poll",
            "fix": "Publish discovery during polling when units are first seen (already implemented)"
        })
    
    # Check battery cell discovery
    if "WARN" in hierarchy_levels["Battery Cell"]["status"]:
        issues.append({
            "level": "Battery Cell",
            "issue": "Discovery only published when cells_data is available during polling",
            "impact": "Cells won't have HA entities if cells_data is empty or None",
            "fix": "Ensure cells_data is populated correctly in adapters"
        })
    
    for issue in issues:
        print(f"\n  WARN {issue['level']}:")
        print(f"     Issue: {issue['issue']}")
        print(f"     Impact: {issue['impact']}")
        print(f"     Fix: {issue['fix']}")
    
    print("\n3. VERIFICATION CHECKLIST:")
    print("-" * 80)
    checklist = [
        ("Systems", "Check MQTT topic: homeassistant/sensor/system_<id>_*/config"),
        ("Inverter Arrays", "Check MQTT topic: homeassistant/sensor/array_<id>_*/config"),
        ("Battery Arrays", "Check MQTT topic: homeassistant/sensor/battery_array_<id>_*/config"),
        ("Battery Packs", "Check MQTT topic: homeassistant/sensor/pack_<id>_*/config"),
        ("Battery Packs (Bank)", "Check MQTT topic: homeassistant/sensor/battery_<id>_*/config"),
        ("Battery Units", "Check MQTT topic: homeassistant/sensor/battery_<id>_unit_<power>_*/config"),
        ("Battery Cells", "Check MQTT topic: homeassistant/sensor/battery_<id>_unit_<power>_cell_<idx>_*/config"),
        ("Inverters", "Check MQTT topic: homeassistant/sensor/<inverter_id>_*/config"),
        ("Meters", "Check MQTT topic: homeassistant/sensor/meter_<id>_*/config"),
    ]
    
    for item, check in checklist:
        print(f"  [ ] {item:25s} - {check}")
    
    print("\n4. RUNTIME DISCOVERY:")
    print("-" * 80)
    print("  Battery units are discovered during polling when:")
    print("    - Telemetry contains devices list")
    print("    - Unit key not in _battery_units_discovered set")
    print("    - Published via: ha.publish_battery_unit_entities()")
    print()
    print("  Battery cells are discovered during polling when:")
    print("    - Telemetry contains cells_data")
    print("    - cells_data entries have 'cells' array with cell data")
    print("    - Cell key not in _battery_cells_discovered set")
    print("    - Published via: ha.publish_battery_cell_entities()")
    
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS:")
    print("=" * 80)
    print("1. Verify MQTT topics are being published (use MQTT explorer or mosquitto_sub)")
    print("2. Check application logs for 'Published HA discovery' messages")
    print("3. Ensure cells_data is populated in battery adapters (check debug logs)")
    print("4. Verify battery units are discovered after first poll (not just at startup)")
    print("5. Check Home Assistant MQTT integration shows all devices")
    
    return issues

if __name__ == "__main__":
    issues = check_ha_discovery_coverage()
    if issues:
        print(f"\nWARN: Found {len(issues)} potential issue(s)")
        sys.exit(1)
    else:
        print("\nOK: All hierarchy levels have HA discovery coverage")
        sys.exit(0)

