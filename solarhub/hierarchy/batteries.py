"""
Battery classes for individual battery units and cells.
"""
from typing import Optional, Dict, Any, List
from datetime import datetime


class Battery:
    """Represents an individual battery unit within a pack."""
    
    def __init__(
        self,
        battery_id: str,
        pack_id: str,
        battery_array_id: str,
        system_id: str,
        battery_index: int,
        serial_number: Optional[str] = None,
        model: Optional[str] = None,
        created_at: Optional[str] = None
    ):
        self.battery_id = battery_id
        self.pack_id = pack_id
        self.battery_array_id = battery_array_id
        self.system_id = system_id
        self.battery_index = battery_index
        self.serial_number = serial_number
        self.model = model
        self.created_at = created_at or datetime.now().isoformat()
        
        # Child cells
        self.cells: List['BatteryCell'] = []
        
        # Telemetry cache
        self._telemetry: Optional[Dict[str, Any]] = None
        self._telemetry_timestamp: Optional[datetime] = None
    
    @property
    def id(self) -> str:
        """Alias for battery_id for convenience."""
        return self.battery_id
    
    def add_cell(self, cell: 'BatteryCell'):
        """Add a cell to this battery."""
        if cell.battery_id != self.battery_id:
            raise ValueError(f"Cell {cell.cell_id} belongs to battery {cell.battery_id}, not {self.battery_id}")
        if cell not in self.cells:
            self.cells.append(cell)
    
    def get_cell(self, cell_id: str) -> Optional['BatteryCell']:
        """Get cell by ID."""
        for cell in self.cells:
            if cell.cell_id == cell_id:
                return cell
        return None
    
    def update_telemetry(self, telemetry: Dict[str, Any], timestamp: Optional[datetime] = None):
        """Update battery telemetry cache."""
        self._telemetry = telemetry
        self._telemetry_timestamp = timestamp or datetime.now()
    
    def get_telemetry(self) -> Optional[Dict[str, Any]]:
        """Get cached telemetry."""
        return self._telemetry
    
    def clear_telemetry(self):
        """Clear telemetry cache."""
        self._telemetry = None
        self._telemetry_timestamp = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert battery to dictionary representation."""
        return {
            'battery_id': self.battery_id,
            'pack_id': self.pack_id,
            'battery_array_id': self.battery_array_id,
            'system_id': self.system_id,
            'battery_index': self.battery_index,
            'serial_number': self.serial_number,
            'model': self.model,
            'cells_count': len(self.cells),
            'created_at': self.created_at,
        }
    
    def __repr__(self) -> str:
        return f"Battery(id={self.battery_id}, pack_id={self.pack_id}, battery_index={self.battery_index}, cells={len(self.cells)})"


class BatteryCell:
    """Represents a battery cell within a battery unit."""
    
    def __init__(
        self,
        cell_id: str,
        battery_id: str,
        pack_id: str,
        battery_array_id: str,
        system_id: str,
        cell_index: int,
        nominal_voltage: Optional[float] = None,
        created_at: Optional[str] = None
    ):
        self.cell_id = cell_id
        self.battery_id = battery_id
        self.pack_id = pack_id
        self.battery_array_id = battery_array_id
        self.system_id = system_id
        self.cell_index = cell_index
        self.nominal_voltage = nominal_voltage
        self.created_at = created_at or datetime.now().isoformat()
        
        # Telemetry cache
        self._telemetry: Optional[Dict[str, Any]] = None
        self._telemetry_timestamp: Optional[datetime] = None
    
    @property
    def id(self) -> str:
        """Alias for cell_id for convenience."""
        return self.cell_id
    
    def update_telemetry(self, telemetry: Dict[str, Any], timestamp: Optional[datetime] = None):
        """Update cell telemetry cache."""
        self._telemetry = telemetry
        self._telemetry_timestamp = timestamp or datetime.now()
    
    def get_telemetry(self) -> Optional[Dict[str, Any]]:
        """Get cached telemetry."""
        return self._telemetry
    
    def clear_telemetry(self):
        """Clear telemetry cache."""
        self._telemetry = None
        self._telemetry_timestamp = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert cell to dictionary representation."""
        return {
            'cell_id': self.cell_id,
            'battery_id': self.battery_id,
            'pack_id': self.pack_id,
            'battery_array_id': self.battery_array_id,
            'system_id': self.system_id,
            'cell_index': self.cell_index,
            'nominal_voltage': self.nominal_voltage,
            'created_at': self.created_at,
        }
    
    def __repr__(self) -> str:
        return f"BatteryCell(id={self.cell_id}, battery_id={self.battery_id}, cell_index={self.cell_index})"

