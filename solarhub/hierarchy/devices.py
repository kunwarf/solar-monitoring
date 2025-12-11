"""
Device classes for inverters, battery packs, and meters.
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from solarhub.hierarchy.base import BaseDevice
from solarhub.hierarchy.adapters import AdapterInstance
from solarhub.hierarchy.batteries import Battery


class Inverter(BaseDevice):
    """Represents an individual inverter."""
    
    def __init__(
        self,
        inverter_id: str,
        name: str,
        array_id: str,
        system_id: str,
        adapter_id: Optional[str] = None,
        model: Optional[str] = None,
        serial_number: Optional[str] = None,
        vendor: Optional[str] = None,
        phase_type: Optional[str] = None,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None
    ):
        super().__init__(inverter_id, name, system_id, model, serial_number, created_at, updated_at)
        self.inverter_id = inverter_id  # Explicit field for clarity
        self.array_id = array_id
        self.adapter_id = adapter_id
        self.vendor = vendor
        self.phase_type = phase_type
        
        # Adapter instance (loaded separately)
        self.adapter: Optional[AdapterInstance] = None
    
    @property
    def id(self) -> str:
        """Alias for inverter_id for convenience."""
        return self.inverter_id
    
    def set_adapter(self, adapter: AdapterInstance):
        """Set the adapter instance for this inverter."""
        if adapter.device_id != self.inverter_id:
            raise ValueError(f"Adapter device_id {adapter.device_id} does not match inverter_id {self.inverter_id}")
        if adapter.device_type != 'inverter':
            raise ValueError(f"Adapter device_type {adapter.device_type} is not 'inverter'")
        self.adapter = adapter
        self.adapter_id = adapter.adapter_id
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert inverter to dictionary representation."""
        return {
            'inverter_id': self.inverter_id,
            'name': self.name,
            'array_id': self.array_id,
            'system_id': self.system_id,
            'adapter_id': self.adapter_id,
            'model': self.model,
            'serial_number': self.serial_number,
            'vendor': self.vendor,
            'phase_type': self.phase_type,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }
    
    def __repr__(self) -> str:
        return f"Inverter(id={self.inverter_id}, name={self.name}, array_id={self.array_id}, adapter_id={self.adapter_id})"


class BatteryPack(BaseDevice):
    """Represents a battery pack (group of battery units)."""
    
    def __init__(
        self,
        pack_id: str,
        name: str,
        battery_array_id: str,
        system_id: str,
        chemistry: Optional[str] = None,
        nominal_kwh: Optional[float] = None,
        max_charge_kw: Optional[float] = None,
        max_discharge_kw: Optional[float] = None,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None
    ):
        super().__init__(pack_id, name, system_id, None, None, created_at, updated_at)
        self.pack_id = pack_id  # Explicit field for clarity
        self.battery_array_id = battery_array_id
        self.chemistry = chemistry
        self.nominal_kwh = nominal_kwh
        self.max_charge_kw = max_charge_kw
        self.max_discharge_kw = max_discharge_kw
        
        # Child batteries
        self.batteries: List[Battery] = []
        
        # Adapter instances (can have multiple for failover)
        self.adapters: List[AdapterInstance] = []
    
    @property
    def id(self) -> str:
        """Alias for pack_id for convenience."""
        return self.pack_id
    
    def add_battery(self, battery: Battery):
        """Add a battery unit to this pack."""
        if battery.pack_id != self.pack_id:
            raise ValueError(f"Battery {battery.battery_id} belongs to pack {battery.pack_id}, not {self.pack_id}")
        if battery not in self.batteries:
            self.batteries.append(battery)
    
    def get_battery(self, battery_id: str) -> Optional[Battery]:
        """Get battery unit by ID."""
        for battery in self.batteries:
            if battery.battery_id == battery_id:
                return battery
        return None
    
    def add_adapter(self, adapter: AdapterInstance):
        """Add an adapter instance to this battery pack (for failover support)."""
        if adapter.device_id != self.pack_id:
            raise ValueError(f"Adapter device_id {adapter.device_id} does not match pack_id {self.pack_id}")
        if adapter.device_type != 'battery_pack':
            raise ValueError(f"Adapter device_type {adapter.device_type} is not 'battery_pack'")
        if adapter not in self.adapters:
            self.adapters.append(adapter)
            # Sort by priority (lower number = higher priority)
            self.adapters.sort(key=lambda a: a.priority or 1)
    
    def get_primary_adapter(self) -> Optional[AdapterInstance]:
        """Get the primary adapter (highest priority, enabled)."""
        for adapter in self.adapters:
            if adapter.enabled:
                return adapter
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert battery pack to dictionary representation."""
        return {
            'pack_id': self.pack_id,
            'name': self.name,
            'battery_array_id': self.battery_array_id,
            'system_id': self.system_id,
            'chemistry': self.chemistry,
            'nominal_kwh': self.nominal_kwh,
            'max_charge_kw': self.max_charge_kw,
            'max_discharge_kw': self.max_discharge_kw,
            'batteries_count': len(self.batteries),
            'adapters_count': len(self.adapters),
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }
    
    def __repr__(self) -> str:
        return f"BatteryPack(id={self.pack_id}, name={self.name}, battery_array_id={self.battery_array_id}, batteries={len(self.batteries)}, adapters={len(self.adapters)})"


class Meter(BaseDevice):
    """Represents an energy meter."""
    
    def __init__(
        self,
        meter_id: str,
        name: str,
        system_id: str,
        array_id: Optional[str] = None,
        adapter_id: Optional[str] = None,
        model: Optional[str] = None,
        meter_type: Optional[str] = None,
        attachment_target: Optional[str] = None,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None
    ):
        super().__init__(meter_id, name, system_id, model, None, created_at, updated_at)
        self.meter_id = meter_id  # Explicit field for clarity
        self.array_id = array_id  # None = system-level meter
        self.adapter_id = adapter_id
        self.meter_type = meter_type  # 'grid', 'consumption', etc.
        self.attachment_target = attachment_target  # 'system' or array_id
        
        # Adapter instance (loaded separately)
        self.adapter: Optional[AdapterInstance] = None
    
    @property
    def id(self) -> str:
        """Alias for meter_id for convenience."""
        return self.meter_id
    
    def set_adapter(self, adapter: AdapterInstance):
        """Set the adapter instance for this meter."""
        if adapter.device_id != self.meter_id:
            raise ValueError(f"Adapter device_id {adapter.device_id} does not match meter_id {self.meter_id}")
        if adapter.device_type != 'meter':
            raise ValueError(f"Adapter device_type {adapter.device_type} is not 'meter'")
        self.adapter = adapter
        self.adapter_id = adapter.adapter_id
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert meter to dictionary representation."""
        return {
            'meter_id': self.meter_id,
            'name': self.name,
            'system_id': self.system_id,
            'array_id': self.array_id,
            'adapter_id': self.adapter_id,
            'model': self.model,
            'type': self.meter_type,
            'attachment_target': self.attachment_target,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }
    
    def __repr__(self) -> str:
        return f"Meter(id={self.meter_id}, name={self.name}, system_id={self.system_id}, array_id={self.array_id}, adapter_id={self.adapter_id})"

