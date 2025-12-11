"""
Telemetry management for hierarchy objects.
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from collections import defaultdict


class TelemetryManager:
    """
    Centralized telemetry storage and retrieval for hierarchy objects.
    
    This class maintains telemetry caches for all devices, arrays, and systems,
    allowing efficient access to current and historical telemetry data.
    """
    
    def __init__(self):
        # Device telemetry: {device_id: {timestamp: telemetry_dict}}
        self._device_telemetry: Dict[str, Dict[datetime, Dict[str, Any]]] = defaultdict(dict)
        
        # Array telemetry: {array_id: {timestamp: telemetry_dict}}
        self._array_telemetry: Dict[str, Dict[datetime, Dict[str, Any]]] = defaultdict(dict)
        
        # System telemetry: {system_id: {timestamp: telemetry_dict}}
        self._system_telemetry: Dict[str, Dict[datetime, Dict[str, Any]]] = defaultdict(dict)
        
        # Latest telemetry timestamps
        self._latest_device_telemetry: Dict[str, datetime] = {}
        self._latest_array_telemetry: Dict[str, datetime] = {}
        self._latest_system_telemetry: Dict[str, datetime] = {}
    
    def update_device_telemetry(self, device_id: str, telemetry: Dict[str, Any], timestamp: Optional[datetime] = None):
        """Update telemetry for a device."""
        ts = timestamp or datetime.now()
        self._device_telemetry[device_id][ts] = telemetry
        self._latest_device_telemetry[device_id] = ts
        
        # Keep only last N entries per device (e.g., last 100)
        if len(self._device_telemetry[device_id]) > 100:
            # Remove oldest entries
            sorted_timestamps = sorted(self._device_telemetry[device_id].keys())
            for old_ts in sorted_timestamps[:-100]:
                del self._device_telemetry[device_id][old_ts]
    
    def update_array_telemetry(self, array_id: str, telemetry: Dict[str, Any], timestamp: Optional[datetime] = None):
        """Update aggregated telemetry for an array."""
        ts = timestamp or datetime.now()
        self._array_telemetry[array_id][ts] = telemetry
        self._latest_array_telemetry[array_id] = ts
        
        # Keep only last N entries per array
        if len(self._array_telemetry[array_id]) > 100:
            sorted_timestamps = sorted(self._array_telemetry[array_id].keys())
            for old_ts in sorted_timestamps[:-100]:
                del self._array_telemetry[array_id][old_ts]
    
    def update_system_telemetry(self, system_id: str, telemetry: Dict[str, Any], timestamp: Optional[datetime] = None):
        """Update aggregated telemetry for a system."""
        ts = timestamp or datetime.now()
        self._system_telemetry[system_id][ts] = telemetry
        self._latest_system_telemetry[system_id] = ts
        
        # Keep only last N entries per system
        if len(self._system_telemetry[system_id]) > 100:
            sorted_timestamps = sorted(self._system_telemetry[system_id].keys())
            for old_ts in sorted_timestamps[:-100]:
                del self._system_telemetry[system_id][old_ts]
    
    def get_device_telemetry(self, device_id: str, timestamp: Optional[datetime] = None) -> Optional[Dict[str, Any]]:
        """Get telemetry for a device at a specific timestamp (or latest if None)."""
        if device_id not in self._device_telemetry:
            return None
        
        if timestamp is None:
            # Return latest
            latest_ts = self._latest_device_telemetry.get(device_id)
            if latest_ts:
                return self._device_telemetry[device_id].get(latest_ts)
            return None
        
        # Return at specific timestamp (or closest before)
        timestamps = sorted(self._device_telemetry[device_id].keys(), reverse=True)
        for ts in timestamps:
            if ts <= timestamp:
                return self._device_telemetry[device_id][ts]
        return None
    
    def get_array_telemetry(self, array_id: str, timestamp: Optional[datetime] = None) -> Optional[Dict[str, Any]]:
        """Get aggregated telemetry for an array at a specific timestamp (or latest if None)."""
        if array_id not in self._array_telemetry:
            return None
        
        if timestamp is None:
            latest_ts = self._latest_array_telemetry.get(array_id)
            if latest_ts:
                return self._array_telemetry[array_id].get(latest_ts)
            return None
        
        timestamps = sorted(self._array_telemetry[array_id].keys(), reverse=True)
        for ts in timestamps:
            if ts <= timestamp:
                return self._array_telemetry[array_id][ts]
        return None
    
    def get_system_telemetry(self, system_id: str, timestamp: Optional[datetime] = None) -> Optional[Dict[str, Any]]:
        """Get aggregated telemetry for a system at a specific timestamp (or latest if None)."""
        if system_id not in self._system_telemetry:
            return None
        
        if timestamp is None:
            latest_ts = self._latest_system_telemetry.get(system_id)
            if latest_ts:
                return self._system_telemetry[system_id].get(latest_ts)
            return None
        
        timestamps = sorted(self._system_telemetry[system_id].keys(), reverse=True)
        for ts in timestamps:
            if ts <= timestamp:
                return self._system_telemetry[system_id][ts]
        return None
    
    def get_device_telemetry_history(self, device_id: str, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get telemetry history for a device within a time range."""
        if device_id not in self._device_telemetry:
            return []
        
        timestamps = sorted(self._device_telemetry[device_id].keys())
        result = []
        
        for ts in timestamps:
            if start_time and ts < start_time:
                continue
            if end_time and ts > end_time:
                continue
            result.append({
                'timestamp': ts.isoformat(),
                'telemetry': self._device_telemetry[device_id][ts]
            })
        
        return result
    
    def clear_device_telemetry(self, device_id: str):
        """Clear all telemetry for a device."""
        if device_id in self._device_telemetry:
            del self._device_telemetry[device_id]
        if device_id in self._latest_device_telemetry:
            del self._latest_device_telemetry[device_id]
    
    def clear_array_telemetry(self, array_id: str):
        """Clear all telemetry for an array."""
        if array_id in self._array_telemetry:
            del self._array_telemetry[array_id]
        if array_id in self._latest_array_telemetry:
            del self._latest_array_telemetry[array_id]
    
    def clear_system_telemetry(self, system_id: str):
        """Clear all telemetry for a system."""
        if system_id in self._system_telemetry:
            del self._system_telemetry[system_id]
        if system_id in self._latest_system_telemetry:
            del self._latest_system_telemetry[system_id]
    
    def clear_all(self):
        """Clear all telemetry."""
        self._device_telemetry.clear()
        self._array_telemetry.clear()
        self._system_telemetry.clear()
        self._latest_device_telemetry.clear()
        self._latest_array_telemetry.clear()
        self._latest_system_telemetry.clear()
    
    def __repr__(self) -> str:
        return f"TelemetryManager(devices={len(self._device_telemetry)}, arrays={len(self._array_telemetry)}, systems={len(self._system_telemetry)})"

