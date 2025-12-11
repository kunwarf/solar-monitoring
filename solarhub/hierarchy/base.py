"""
Base classes for hierarchy objects.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from datetime import datetime


class BaseDevice(ABC):
    """Abstract base class for all devices (inverters, battery packs, meters)."""
    
    def __init__(
        self,
        device_id: str,
        name: str,
        system_id: str,
        model: Optional[str] = None,
        serial_number: Optional[str] = None,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None
    ):
        self.device_id = device_id
        self.name = name
        self.system_id = system_id
        self.model = model
        self.serial_number = serial_number
        self.created_at = created_at or datetime.now().isoformat()
        self.updated_at = updated_at or datetime.now().isoformat()
        
        # Telemetry cache
        self._telemetry: Optional[Dict[str, Any]] = None
        self._telemetry_timestamp: Optional[datetime] = None
    
    @property
    def id(self) -> str:
        """Alias for device_id for convenience."""
        return self.device_id
    
    def update_telemetry(self, telemetry: Dict[str, Any], timestamp: Optional[datetime] = None):
        """Update device telemetry cache."""
        self._telemetry = telemetry
        self._telemetry_timestamp = timestamp or datetime.now()
    
    def get_telemetry(self) -> Optional[Dict[str, Any]]:
        """Get cached telemetry."""
        return self._telemetry
    
    def clear_telemetry(self):
        """Clear telemetry cache."""
        self._telemetry = None
        self._telemetry_timestamp = None
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Convert device to dictionary representation."""
        pass
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.device_id}, name={self.name}, system_id={self.system_id})"


class BaseArray(ABC):
    """Abstract base class for arrays (inverter arrays, battery arrays)."""
    
    def __init__(
        self,
        array_id: str,
        name: str,
        system_id: str,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None
    ):
        self.array_id = array_id
        self.name = name
        self.system_id = system_id
        self.created_at = created_at or datetime.now().isoformat()
        self.updated_at = updated_at or datetime.now().isoformat()
        
        # Aggregated telemetry cache
        self._telemetry: Optional[Dict[str, Any]] = None
        self._telemetry_timestamp: Optional[datetime] = None
    
    @property
    def id(self) -> str:
        """Alias for array_id for convenience."""
        return self.array_id
    
    def update_telemetry(self, telemetry: Dict[str, Any], timestamp: Optional[datetime] = None):
        """Update array aggregated telemetry cache."""
        self._telemetry = telemetry
        self._telemetry_timestamp = timestamp or datetime.now()
    
    def get_telemetry(self) -> Optional[Dict[str, Any]]:
        """Get cached aggregated telemetry."""
        return self._telemetry
    
    def clear_telemetry(self):
        """Clear telemetry cache."""
        self._telemetry = None
        self._telemetry_timestamp = None
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Convert array to dictionary representation."""
        pass
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.array_id}, name={self.name}, system_id={self.system_id})"

