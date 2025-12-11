"""
Hierarchy module for representing the complete system structure.

This module provides object-oriented classes representing the hierarchy:
- System (top-level)
- InverterArray, BatteryArray (arrays)
- Inverter, BatteryPack, Meter (devices)
- Battery, BatteryCell (battery units)
- AdapterBase, AdapterInstance (adapters)
"""

from solarhub.hierarchy.base import BaseDevice, BaseArray
from solarhub.hierarchy.system import System
from solarhub.hierarchy.arrays import InverterArray, BatteryArray
from solarhub.hierarchy.devices import Inverter, BatteryPack, Meter
from solarhub.hierarchy.batteries import Battery, BatteryCell
from solarhub.hierarchy.adapters import AdapterBase, AdapterInstance
from solarhub.hierarchy.telemetry import TelemetryManager

__all__ = [
    'BaseDevice',
    'BaseArray',
    'System',
    'InverterArray',
    'BatteryArray',
    'Inverter',
    'BatteryPack',
    'Meter',
    'Battery',
    'BatteryCell',
    'AdapterBase',
    'AdapterInstance',
    'TelemetryManager',
]

