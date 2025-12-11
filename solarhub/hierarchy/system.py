"""
System class representing the top-level system.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from solarhub.hierarchy.arrays import InverterArray, BatteryArray
from solarhub.hierarchy.devices import Meter


class System:
    """Represents a system (top-level container)."""
    
    def __init__(
        self,
        system_id: str,
        name: str,
        description: Optional[str] = None,
        timezone: str = "Asia/Karachi",
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None
    ):
        self.system_id = system_id
        self.name = name
        self.description = description
        self.timezone = timezone
        self.created_at = created_at or datetime.now().isoformat()
        self.updated_at = updated_at or datetime.now().isoformat()
        
        # Child collections
        self.inverter_arrays: List[InverterArray] = []
        self.battery_arrays: List[BatteryArray] = []
        self.meters: List[Meter] = []  # System-level meters
        
        # Aggregated telemetry cache
        self._telemetry: Optional[Dict[str, Any]] = None
        self._telemetry_timestamp: Optional[datetime] = None
    
    @property
    def id(self) -> str:
        """Alias for system_id for convenience."""
        return self.system_id
    
    def add_inverter_array(self, array: InverterArray):
        """Add an inverter array to this system."""
        if array.system_id != self.system_id:
            raise ValueError(f"Array {array.array_id} belongs to system {array.system_id}, not {self.system_id}")
        if array not in self.inverter_arrays:
            self.inverter_arrays.append(array)
    
    def add_battery_array(self, array: BatteryArray):
        """Add a battery array to this system."""
        if array.system_id != self.system_id:
            raise ValueError(f"Array {array.array_id} belongs to system {array.system_id}, not {self.system_id}")
        if array not in self.battery_arrays:
            self.battery_arrays.append(array)
    
    def add_meter(self, meter: Meter):
        """Add a system-level meter to this system."""
        if meter.system_id != self.system_id:
            raise ValueError(f"Meter {meter.meter_id} belongs to system {meter.system_id}, not {self.system_id}")
        if meter.array_id is not None:
            raise ValueError(f"Meter {meter.meter_id} is array-level, not system-level")
        if meter not in self.meters:
            self.meters.append(meter)
    
    def get_inverter_array(self, array_id: str) -> Optional[InverterArray]:
        """Get inverter array by ID."""
        for array in self.inverter_arrays:
            if array.array_id == array_id:
                return array
        return None
    
    def get_battery_array(self, array_id: str) -> Optional[BatteryArray]:
        """Get battery array by ID."""
        for array in self.battery_arrays:
            if array.battery_array_id == array_id:
                return array
        return None
    
    def get_meter(self, meter_id: str) -> Optional[Meter]:
        """Get system-level meter by ID."""
        for meter in self.meters:
            if meter.meter_id == meter_id:
                return meter
        return None
    
    def get_all_inverters(self) -> List:
        """Get all inverters from all arrays in this system."""
        inverters = []
        for array in self.inverter_arrays:
            inverters.extend(array.inverters)
        return inverters
    
    def get_all_battery_packs(self) -> List:
        """Get all battery packs from all arrays in this system."""
        packs = []
        for array in self.battery_arrays:
            packs.extend(array.battery_packs)
        return packs
    
    def update_telemetry(self, telemetry: Dict[str, Any], timestamp: Optional[datetime] = None):
        """Update system-level aggregated telemetry cache."""
        self._telemetry = telemetry
        self._telemetry_timestamp = timestamp or datetime.now()
    
    def get_telemetry(self) -> Optional[Dict[str, Any]]:
        """Get cached system-level aggregated telemetry."""
        return self._telemetry
    
    def clear_telemetry(self):
        """Clear telemetry cache."""
        self._telemetry = None
        self._telemetry_timestamp = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert system to dictionary representation."""
        return {
            'system_id': self.system_id,
            'name': self.name,
            'description': self.description,
            'timezone': self.timezone,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'inverter_arrays': [array.to_dict() for array in self.inverter_arrays],
            'battery_arrays': [array.to_dict() for array in self.battery_arrays],
            'meters': [meter.to_dict() for meter in self.meters],
        }
    
    def __repr__(self) -> str:
        return f"System(id={self.system_id}, name={self.name}, inverter_arrays={len(self.inverter_arrays)}, battery_arrays={len(self.battery_arrays)}, meters={len(self.meters)})"

