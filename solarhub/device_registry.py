"""
Device Registry for managing auto-discovered USB devices.

Tracks discovered devices, their ports, serial numbers, and status.
"""

import sqlite3
import json
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime
from dataclasses import dataclass, asdict
from solarhub.timezone_utils import now_configured_iso

log = logging.getLogger(__name__)


@dataclass
class DeviceEntry:
    """Represents a discovered device entry."""
    device_id: str
    device_type: str  # "senergy", "powdrive", "pytes", "iammeter"
    serial_number: str
    port: Optional[str]
    last_known_port: Optional[str]
    port_history: List[str]
    adapter_config: Dict[str, Any]
    status: str  # "active", "recovering", "permanently_disabled"
    failure_count: int
    next_retry_time: Optional[str]
    first_discovered: str
    last_seen: Optional[str]
    discovery_timestamp: str
    is_auto_discovered: bool


class DeviceRegistry:
    """Manages discovered devices in database."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        return sqlite3.connect(self.db_path)
    
    def normalize_serial(self, serial: str) -> str:
        """Normalize serial number: uppercase, alphanumeric only."""
        if not serial:
            return ""
        # Remove special characters, uppercase
        normalized = "".join(c.upper() if c.isalnum() else "" for c in str(serial))
        return normalized
    
    def generate_device_id(self, device_type: str, serial_number: str) -> str:
        """Generate device ID from type and serial: {type}_{serial_last6}."""
        normalized = self.normalize_serial(serial_number)
        if len(normalized) < 6:
            # Pad with zeros if too short
            normalized = normalized.zfill(6)
        last6 = normalized[-6:]
        return f"{device_type}_{last6}"
    
    def find_device_by_serial(self, serial_number: str, device_type: str) -> Optional[DeviceEntry]:
        """Find device by serial number and type."""
        normalized_serial = self.normalize_serial(serial_number)
        con = self._get_connection()
        try:
            cur = con.cursor()
            cur.execute("""
                SELECT device_id, device_type, serial_number, port, last_known_port,
                       port_history, adapter_config, status, failure_count,
                       next_retry_time, first_discovered, last_seen,
                       discovery_timestamp, is_auto_discovered
                FROM device_discovery
                WHERE serial_number = ? AND device_type = ?
            """, (normalized_serial, device_type))
            
            row = cur.fetchone()
            if row:
                return self._row_to_device_entry(row)
            return None
        finally:
            con.close()
    
    def get_device(self, device_id: str) -> Optional[DeviceEntry]:
        """Get device by device_id."""
        con = self._get_connection()
        try:
            cur = con.cursor()
            cur.execute("""
                SELECT device_id, device_type, serial_number, port, last_known_port,
                       port_history, adapter_config, status, failure_count,
                       next_retry_time, first_discovered, last_seen,
                       discovery_timestamp, is_auto_discovered
                FROM device_discovery
                WHERE device_id = ?
            """, (device_id,))
            
            row = cur.fetchone()
            if row:
                return self._row_to_device_entry(row)
            return None
        finally:
            con.close()
    
    def get_all_devices(self, status_filter: Optional[str] = None) -> List[DeviceEntry]:
        """Get all devices, optionally filtered by status."""
        con = self._get_connection()
        try:
            cur = con.cursor()
            if status_filter:
                cur.execute("""
                    SELECT device_id, device_type, serial_number, port, last_known_port,
                           port_history, adapter_config, status, failure_count,
                           next_retry_time, first_discovered, last_seen,
                           discovery_timestamp, is_auto_discovered
                    FROM device_discovery
                    WHERE status = ?
                    ORDER BY device_type, device_id
                """, (status_filter,))
            else:
                cur.execute("""
                    SELECT device_id, device_type, serial_number, port, last_known_port,
                           port_history, adapter_config, status, failure_count,
                           next_retry_time, first_discovered, last_seen,
                           discovery_timestamp, is_auto_discovered
                    FROM device_discovery
                    ORDER BY device_type, device_id
                """)
            
            rows = cur.fetchall()
            return [self._row_to_device_entry(row) for row in rows]
        finally:
            con.close()
    
    def get_devices_by_type(self, device_type: str, status_filter: Optional[str] = None) -> List[DeviceEntry]:
        """Get all devices of a specific type."""
        con = self._get_connection()
        try:
            cur = con.cursor()
            if status_filter:
                cur.execute("""
                    SELECT device_id, device_type, serial_number, port, last_known_port,
                           port_history, adapter_config, status, failure_count,
                           next_retry_time, first_discovered, last_seen,
                           discovery_timestamp, is_auto_discovered
                    FROM device_discovery
                    WHERE device_type = ? AND status = ?
                    ORDER BY device_id
                """, (device_type, status_filter))
            else:
                cur.execute("""
                    SELECT device_id, device_type, serial_number, port, last_known_port,
                           port_history, adapter_config, status, failure_count,
                           next_retry_time, first_discovered, last_seen,
                           discovery_timestamp, is_auto_discovered
                    FROM device_discovery
                    WHERE device_type = ?
                    ORDER BY device_id
                """, (device_type,))
            
            rows = cur.fetchall()
            return [self._row_to_device_entry(row) for row in rows]
        finally:
            con.close()
    
    def register_device(self, device: DeviceEntry) -> None:
        """Register a new device or update existing."""
        con = self._get_connection()
        try:
            cur = con.cursor()
            # Check if device exists
            existing = self.find_device_by_serial(device.serial_number, device.device_type)
            
            if existing:
                # Update existing device
                cur.execute("""
                    UPDATE device_discovery
                    SET port = ?, last_known_port = ?, port_history = ?,
                        adapter_config = ?, status = ?, last_seen = ?,
                        discovery_timestamp = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE device_id = ?
                """, (
                    device.port,
                    device.port,  # Update last_known_port when port changes
                    json.dumps(device.port_history),
                    json.dumps(device.adapter_config),
                    device.status,
                    device.last_seen or now_configured_iso(),
                    device.discovery_timestamp,
                    device.device_id
                ))
                log.info(f"Updated device {device.device_id} in registry")
            else:
                # Insert new device
                cur.execute("""
                    INSERT INTO device_discovery (
                        device_id, device_type, serial_number, port, last_known_port,
                        port_history, adapter_config, status, failure_count,
                        next_retry_time, first_discovered, last_seen,
                        discovery_timestamp, is_auto_discovered
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    device.device_id,
                    device.device_type,
                    self.normalize_serial(device.serial_number),
                    device.port,
                    device.port,
                    json.dumps(device.port_history),
                    json.dumps(device.adapter_config),
                    device.status,
                    device.failure_count,
                    device.next_retry_time,
                    device.first_discovered,
                    device.last_seen,
                    device.discovery_timestamp,
                    1 if device.is_auto_discovered else 0
                ))
                log.info(f"Registered new device {device.device_id} in registry")
            
            con.commit()
        finally:
            con.close()
    
    def update_device_port(self, device_id: str, new_port: str) -> None:
        """Update device port assignment and port history."""
        device = self.get_device(device_id)
        if not device:
            log.warning(f"Device {device_id} not found for port update")
            return
        
        # Update port history
        port_history = device.port_history.copy()
        if device.port and device.port != new_port:
            if device.port not in port_history:
                port_history.append(device.port)
        
        con = self._get_connection()
        try:
            cur = con.cursor()
            cur.execute("""
                UPDATE device_discovery
                SET port = ?, last_known_port = ?, port_history = ?,
                    last_seen = ?, updated_at = CURRENT_TIMESTAMP
                WHERE device_id = ?
            """, (
                new_port,
                new_port,
                json.dumps(port_history),
                now_configured_iso(),
                device_id
            ))
            con.commit()
            log.info(f"Updated port for device {device_id}: {device.port} -> {new_port}")
        finally:
            con.close()
    
    def update_device_status(self, device_id: str, status: str, 
                            failure_count: Optional[int] = None,
                            next_retry_time: Optional[str] = None) -> None:
        """Update device status and related fields."""
        con = self._get_connection()
        try:
            cur = con.cursor()
            updates = ["status = ?", "updated_at = CURRENT_TIMESTAMP"]
            params = [status]
            
            if failure_count is not None:
                updates.append("failure_count = ?")
                params.append(failure_count)
            
            if next_retry_time is not None:
                updates.append("next_retry_time = ?")
                params.append(next_retry_time)
            
            params.append(device_id)
            
            cur.execute(f"""
                UPDATE device_discovery
                SET {', '.join(updates)}
                WHERE device_id = ?
            """, params)
            con.commit()
            log.debug(f"Updated status for device {device_id}: {status}")
        finally:
            con.close()
    
    def mark_device_failed(self, device_id: str, next_retry_time: str) -> None:
        """Mark device as failed and set retry time."""
        device = self.get_device(device_id)
        if device:
            new_failure_count = device.failure_count + 1
            self.update_device_status(
                device_id,
                "recovering",
                failure_count=new_failure_count,
                next_retry_time=next_retry_time
            )
            log.warning(f"Marked device {device_id} as failed (count: {new_failure_count})")
    
    def mark_device_recovered(self, device_id: str) -> None:
        """Mark device as recovered (active)."""
        self.update_device_status(
            device_id,
            "active",
            failure_count=0,
            next_retry_time=None
        )
        # Update last_seen
        con = self._get_connection()
        try:
            cur = con.cursor()
            cur.execute("""
                UPDATE device_discovery
                SET last_seen = ?, updated_at = CURRENT_TIMESTAMP
                WHERE device_id = ?
            """, (now_configured_iso(), device_id))
            con.commit()
        finally:
            con.close()
        log.info(f"Marked device {device_id} as recovered")
    
    def permanently_disable_device(self, device_id: str) -> None:
        """Permanently disable a device."""
        self.update_device_status(device_id, "permanently_disabled")
        log.warning(f"Permanently disabled device {device_id}")
    
    def re_enable_device(self, device_id: str) -> None:
        """Re-enable a permanently disabled device."""
        self.update_device_status(
            device_id,
            "recovering",
            failure_count=0,
            next_retry_time=now_configured_iso()  # Retry immediately
        )
        log.info(f"Re-enabled device {device_id} for discovery")
    
    def get_devices_ready_for_retry(self) -> List[DeviceEntry]:
        """Get devices that are ready for retry (status=recovering, next_retry_time <= now)."""
        now = now_configured_iso()
        con = self._get_connection()
        try:
            cur = con.cursor()
            cur.execute("""
                SELECT device_id, device_type, serial_number, port, last_known_port,
                       port_history, adapter_config, status, failure_count,
                       next_retry_time, first_discovered, last_seen,
                       discovery_timestamp, is_auto_discovered
                FROM device_discovery
                WHERE status = 'recovering' 
                  AND next_retry_time IS NOT NULL
                  AND next_retry_time <= ?
                ORDER BY next_retry_time
            """, (now,))
            
            rows = cur.fetchall()
            return [self._row_to_device_entry(row) for row in rows]
        finally:
            con.close()
    
    def get_used_ports(self) -> List[str]:
        """Get list of ports currently in use by active devices."""
        con = self._get_connection()
        try:
            cur = con.cursor()
            cur.execute("""
                SELECT DISTINCT port
                FROM device_discovery
                WHERE status = 'active' AND port IS NOT NULL
            """)
            rows = cur.fetchall()
            return [row[0] for row in rows if row[0]]
        finally:
            con.close()
    
    def _row_to_device_entry(self, row: tuple) -> DeviceEntry:
        """Convert database row to DeviceEntry."""
        return DeviceEntry(
            device_id=row[0],
            device_type=row[1],
            serial_number=row[2],
            port=row[3],
            last_known_port=row[4],
            port_history=json.loads(row[5]) if row[5] else [],
            adapter_config=json.loads(row[6]) if row[6] else {},
            status=row[7],
            failure_count=row[8] or 0,
            next_retry_time=row[9],
            first_discovered=row[10],
            last_seen=row[11],
            discovery_timestamp=row[12],
            is_auto_discovered=bool(row[13])
        )

