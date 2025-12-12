"""
Array classes for inverter and battery arrays.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from solarhub.hierarchy.base import BaseArray
from solarhub.hierarchy.devices import Inverter, BatteryPack


class InverterArray(BaseArray):
    """Represents an inverter array (logical group of inverters)."""
    
    def __init__(
        self,
        array_id: str,
        name: str,
        system_id: str,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None
    ):
        super().__init__(array_id, name, system_id, created_at, updated_at)
        
        # Child devices
        self.inverters: List[Inverter] = []
        
        # Attached battery array (1:1 relationship)
        self.attached_battery_array: Optional['BatteryArray'] = None
    
    def add_inverter(self, inverter: Inverter):
        """Add an inverter to this array."""
        if inverter.array_id != self.array_id:
            raise ValueError(f"Inverter {inverter.inverter_id} belongs to array {inverter.array_id}, not {self.array_id}")
        if inverter.system_id != self.system_id:
            raise ValueError(f"Inverter {inverter.inverter_id} belongs to system {inverter.system_id}, not {self.system_id}")
        if inverter not in self.inverters:
            self.inverters.append(inverter)
    
    def get_inverter(self, inverter_id: str) -> Optional[Inverter]:
        """Get inverter by ID."""
        for inverter in self.inverters:
            if inverter.inverter_id == inverter_id:
                return inverter
        return None
    
    def attach_battery_array(self, battery_array: 'BatteryArray'):
        """Attach a battery array to this inverter array."""
        if battery_array.system_id != self.system_id:
            raise ValueError(f"Battery array {battery_array.battery_array_id} belongs to system {battery_array.system_id}, not {self.system_id}")
        self.attached_battery_array = battery_array
    
    def detach_battery_array(self):
        """Detach the battery array from this inverter array."""
        self.attached_battery_array = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert array to dictionary representation."""
        return {
            'array_id': self.array_id,
            'name': self.name,
            'system_id': self.system_id,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'inverters': [inv.to_dict() for inv in self.inverters],
            'attached_battery_array_id': self.attached_battery_array.battery_array_id if self.attached_battery_array else None,
        }
    
    def __repr__(self) -> str:
        return f"InverterArray(id={self.array_id}, name={self.name}, inverters={len(self.inverters)}, attached_battery_array={self.attached_battery_array.battery_array_id if self.attached_battery_array else None})"


class BatteryArray(BaseArray):
    """Represents a battery array (logical group of battery packs)."""
    
    def __init__(
        self,
        battery_array_id: str,
        name: str,
        system_id: str,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None
    ):
        # Call parent with battery_array_id as array_id
        # This will set self.array_id in the parent class
        super().__init__(battery_array_id, name, system_id, created_at, updated_at)
        # battery_array_id is the same as array_id, just store it for clarity
        self.battery_array_id = self.array_id
        
        # Child devices
        self.battery_packs: List[BatteryPack] = []
        
        # Attached inverter array (1:1 relationship)
        self.attached_inverter_array: Optional[InverterArray] = None
    
    @property
    def array_id(self) -> str:
        """Alias for battery_array_id for BaseArray compatibility."""
        # Return the parent's array_id (which is set by BaseArray.__init__)
        return super().__getattribute__('array_id')
    
    @array_id.setter
    def array_id(self, value: str):
        """Setter for array_id (also updates battery_array_id)."""
        # Set the parent's array_id attribute directly
        super().__setattr__('array_id', value)
        # Keep battery_array_id in sync
        self.battery_array_id = value
    
    def add_battery_pack(self, pack: BatteryPack):
        """Add a battery pack to this array."""
        if pack.battery_array_id != self.battery_array_id:
            raise ValueError(f"Battery pack {pack.pack_id} belongs to array {pack.battery_array_id}, not {self.battery_array_id}")
        if pack.system_id != self.system_id:
            raise ValueError(f"Battery pack {pack.pack_id} belongs to system {pack.system_id}, not {self.system_id}")
        if pack not in self.battery_packs:
            self.battery_packs.append(pack)
    
    def get_battery_pack(self, pack_id: str) -> Optional[BatteryPack]:
        """Get battery pack by ID."""
        for pack in self.battery_packs:
            if pack.pack_id == pack_id:
                return pack
        return None
    
    def attach_inverter_array(self, inverter_array: InverterArray):
        """Attach this battery array to an inverter array."""
        if inverter_array.system_id != self.system_id:
            raise ValueError(f"Inverter array {inverter_array.array_id} belongs to system {inverter_array.system_id}, not {self.system_id}")
        self.attached_inverter_array = inverter_array
        # Also update the inverter array's reference
        inverter_array.attach_battery_array(self)
    
    def detach_inverter_array(self):
        """Detach from the inverter array."""
        if self.attached_inverter_array:
            self.attached_inverter_array.detach_battery_array()
        self.attached_inverter_array = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert array to dictionary representation."""
        return {
            'battery_array_id': self.battery_array_id,
            'name': self.name,
            'system_id': self.system_id,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'battery_packs': [pack.to_dict() for pack in self.battery_packs],
            'attached_inverter_array_id': self.attached_inverter_array.array_id if self.attached_inverter_array else None,
        }
    
    def __repr__(self) -> str:
        return f"BatteryArray(id={self.battery_array_id}, name={self.name}, battery_packs={len(self.battery_packs)}, attached_inverter_array={self.attached_inverter_array.array_id if self.attached_inverter_array else None})"

