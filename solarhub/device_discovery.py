"""
Device Discovery Service for automatic USB device detection.

Implements the 4-phase discovery process according to USB_Device_Auto_Detection_Design.md:
1. Check known devices from database
2. Search for missing known devices
3. Discover new devices
4. Finalize and cleanup
"""

import asyncio
import logging
import serial.tools.list_ports
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from solarhub.device_registry import DeviceRegistry, DeviceEntry
from solarhub.config import InverterConfig, BatteryBankConfig, InverterAdapterConfig, BatteryAdapterConfig
from solarhub.adapters.base import InverterAdapter, BatteryAdapter
from solarhub.timezone_utils import now_configured_iso
from solarhub.config_manager import ConfigurationManager

log = logging.getLogger(__name__)


class DeviceDiscoveryService:
    """Service for discovering USB devices automatically."""
    
    def __init__(
        self,
        registry: DeviceRegistry,
        adapters: Dict[str, type],
        battery_adapters: Dict[str, type],
        config_manager: ConfigurationManager,
        logger
    ):
        self.registry = registry
        self.adapters = adapters  # Inverter adapters: {"senergy": SenergyAdapter, ...}
        self.battery_adapters = battery_adapters  # Battery adapters: {"pytes": PytesBatteryAdapter}
        self.config_manager = config_manager
        self.logger = logger
        
        # Discovery configuration (from design doc: 2 seconds per step, but battery needs more)
        self.enabled = True
        self.scan_on_startup = True
        self.scan_interval_minutes = 60
        self.priority_order = ["pytes", "senergy", "powdrive", "iammeter"]
        # Timeouts: 5s for battery connection (pwr command can be slow), 3s for others
        self.connection_timeout = 5.0  # Base timeout for connection
        self.operation_timeout = 10.0  # Timeout for connectivity check and serial read (battery needs more)
        self.max_retries = 2
    
    def get_available_ports(self) -> List[str]:
        """Get list of available USB/serial ports (only USB ports: /dev/ttyUSB*)."""
        ports = []
        try:
            for port in serial.tools.list_ports.comports():
                port_name = getattr(port, "device", None) or getattr(port, "name", None)
                if port_name:
                    # Only include USB ports (ttyUSB* on Linux, COM* on Windows)
                    if "/dev/ttyUSB" in port_name or "COM" in port_name:
                        ports.append(port_name)
            log.info(f"Found {len(ports)} available USB ports: {ports}")
        except Exception as e:
            log.error(f"Error scanning USB ports: {e}", exc_info=True)
        return ports
    
    async def identify_device_on_port(
        self,
        port: str,
        device_type: str,
        adapter_class: type,
        adapter_config: Dict[str, Any],
        keep_adapter: bool = False
    ) -> Optional[Tuple[str, Dict[str, Any], Optional[Any]]]:
        """
        Try to identify a device on a port according to design doc.
        
        Steps:
        1. Connect to device (with timeout)
        2. Check connectivity (read test register/command)
        3. Read serial number to verify device identity
        
        Args:
            port: Serial port to check
            device_type: Type of device (senergy, powdrive, pytes, etc.)
            adapter_class: Adapter class to use
            adapter_config: Configuration dict for adapter
            keep_adapter: If True, return adapter instance instead of closing it
        
        Returns:
            (serial_number, adapter_config, adapter) if device identified and keep_adapter=True
            (serial_number, adapter_config, None) if device identified and keep_adapter=False
            None if device not identified
        """
        adapter = None
        try:
            # Check if port exists before attempting connection
            import os
            if not os.path.exists(port):
                log.debug(f"DISCOVERY: Port {port} does not exist for {device_type}")
                return None
            
            # Determine timeout based on device type
            is_battery = device_type in self.battery_adapters
            connect_timeout = self.connection_timeout if is_battery else 3.0
            op_timeout = self.operation_timeout if is_battery else 5.0
            
            log.info(f"DISCOVERY: Attempting to identify {device_type} on {port} (connect_timeout={connect_timeout}s, op_timeout={op_timeout}s)")
            
            # Create temporary config for identification
            if device_type in self.adapters:
                # Inverter adapter
                from solarhub.config import InverterConfig, InverterAdapterConfig
                temp_adapter_cfg = InverterAdapterConfig(**adapter_config)
                temp_inv_cfg = InverterConfig(
                    id=f"temp_{device_type}",
                    adapter=temp_adapter_cfg
                )
                adapter = adapter_class(temp_inv_cfg)
            elif device_type in self.battery_adapters:
                # Battery adapter
                from solarhub.config import BatteryBankConfig, BatteryAdapterConfig
                temp_adapter_cfg = BatteryAdapterConfig(**adapter_config)
                temp_bank_cfg = BatteryBankConfig(
                    id=f"temp_{device_type}",
                    adapter=temp_adapter_cfg
                )
                adapter = self.battery_adapters[device_type](temp_bank_cfg)
            else:
                log.warning(f"Unknown device type: {device_type}")
                return None
            
            # Step 1: Connect to device (with timeout per design doc)
            log.info(f"DISCOVERY: Step 1 - Connecting {device_type} adapter on {port} (timeout={connect_timeout}s)")
            try:
                await asyncio.wait_for(adapter.connect(), timeout=connect_timeout)
                log.info(f"DISCOVERY: Step 1 - Successfully connected {device_type} adapter on {port}")
            except asyncio.TimeoutError:
                log.warning(f"DISCOVERY: Step 1 - Connection timeout for {device_type} on {port} (timeout={connect_timeout}s)")
                try:
                    await adapter.close()
                except:
                    pass
                return None
            except Exception as e:
                error_str = str(e).lower()
                if "could not exclusively lock" in error_str or "resource temporarily unavailable" in error_str:
                    log.warning(f"DISCOVERY: Step 1 - Port {port} is locked (likely in use by runtime) - {device_type}: {e}")
                elif "no such file" in error_str or "no such device" in error_str:
                    log.warning(f"DISCOVERY: Step 1 - Port {port} does not exist - {device_type}: {e}")
                else:
                    log.warning(f"DISCOVERY: Step 1 - Connection failed for {device_type} on {port}: {e}")
                try:
                    await adapter.close()
                except:
                    pass
                return None
            
            # Step 2: Check connectivity (read test register/command per design doc)
            log.info(f"DISCOVERY: Step 2 - Checking connectivity for {device_type} on {port} (timeout={op_timeout}s)")
            try:
                is_connected = await asyncio.wait_for(
                    adapter.check_connectivity(),
                    timeout=op_timeout
                )
                if not is_connected:
                    log.debug(f"DISCOVERY: Step 2 - Connectivity check failed for {device_type} on {port}")
                    try:
                        await adapter.close()
                    except:
                        pass
                    return None
                log.info(f"DISCOVERY: Step 2 - Connectivity check passed for {device_type} on {port}")
            except asyncio.TimeoutError:
                log.warning(f"DISCOVERY: Step 2 - Connectivity check timeout for {device_type} on {port} (timeout={op_timeout}s)")
                try:
                    await adapter.close()
                except:
                    pass
                return None
            except Exception as e:
                log.debug(f"DISCOVERY: Step 2 - Error checking connectivity for {device_type} on {port}: {e}")
                try:
                    await adapter.close()
                except:
                    pass
                return None
            
            # Step 3: Read serial number for identification (per design doc)
            log.info(f"DISCOVERY: Step 3 - Reading serial number for {device_type} on {port} (timeout={op_timeout}s)")
            try:
                serial_number = await asyncio.wait_for(
                    adapter.read_serial_number(),
                    timeout=op_timeout
                )
                if serial_number:
                    # Verify it's a valid serial (not empty, not just whitespace, minimum 3 chars per design doc)
                    serial_number = serial_number.strip()
                    if serial_number and len(serial_number) >= 3:
                        log.info(f"DISCOVERY: Step 3 - Identified {device_type} device on {port}: serial={serial_number}")
                        if keep_adapter:
                            # Keep adapter alive for runtime to reuse
                            log.info(f"DISCOVERY: Keeping adapter connection alive for {device_type} on {port} (runtime will reuse)")
                            return (serial_number, adapter_config, adapter)
                        else:
                            # Close the temporary discovery adapter
                            log.info(f"DISCOVERY: Closing discovery adapter for {device_type} on {port} (runtime will create new adapter)")
                            await adapter.close()
                            # Longer delay to ensure port is fully released by OS before runtime connects
                            await asyncio.sleep(0.5)
                            log.info(f"DISCOVERY: Port {port} released after {device_type} identification")
                            return (serial_number, adapter_config, None)
                    else:
                        log.debug(f"DISCOVERY: Step 3 - Serial number too short or invalid for {device_type} on {port}: '{serial_number}'")
                else:
                    log.debug(f"DISCOVERY: Step 3 - No serial number returned for {device_type} on {port}")
            except asyncio.TimeoutError:
                log.warning(f"DISCOVERY: Step 3 - Serial number read timeout for {device_type} on {port} (timeout={op_timeout}s)")
            except Exception as e:
                log.debug(f"DISCOVERY: Step 3 - Error reading serial number for {device_type} on {port}: {e}")
            
            # Cleanup on failure
            try:
                await adapter.close()
            except:
                pass
            return None
            
        except Exception as e:
            log.warning(f"DISCOVERY: Error identifying {device_type} on {port}: {e}", exc_info=True)
            try:
                if adapter:
                    await adapter.close()
            except:
                pass
            return None
    
    async def discover_devices(self, manual_config_inverters: List[InverterConfig] = None,
                               manual_config_battery: Optional[BatteryBankConfig] = None) -> Tuple[List[DeviceEntry], Dict[str, Any]]:
        """
        Main discovery process - 4 phases as per design doc.
        
        PHASE 1: Check Known Devices from Database
        - Load all known devices from database (with saved ports)
        - For each known device: try to connect to saved port, verify serial matches
        - If not found on saved port, mark for Phase 2 search
        
        PHASE 2: Search for Missing Known Devices
        - For each missing device: scan all available ports (excluding already-used ports)
        - Try to connect and verify serial matches
        - If found: update port assignment, mark as active
        - If not found: set 15-minute retry timer, status = "recovering"
        
        PHASE 3: Discover New Devices
        - Get list of unused ports
        - For each unused port: try each device type in priority order
        - If device found: check if serial exists in database
        - If exists: update port assignment (device moved)
        - If new: create new device entry with device_id = {type}_{serial_last6}
        
        PHASE 4: Finalize and Cleanup
        - Check if all ports are exhausted
        - If all ports scanned and device still missing: permanently disable
        - Save all device configurations to database
        
        Args:
            manual_config_inverters: List of manually configured inverters (from config.yaml)
            manual_config_battery: Manually configured battery bank (from config.yaml)
        
        Returns:
            Tuple of (List of discovered DeviceEntry objects, Dict of adapters by device_id/inverter_id)
            The adapters dict contains connected adapters for manually configured devices that can be reused by runtime.
        """
        if not self.enabled:
            log.info("Device discovery is disabled")
            return [], {}
        
        log.info("Starting device discovery process...")
        discovered_devices: List[DeviceEntry] = []
        used_ports: set = set()
        # Store adapters for manually configured devices to reuse in runtime
        # Discovery only identifies devices - runtime creates fresh connections
        
        # Get manual config ports (to skip during discovery)
        manual_ports = set()
        if manual_config_inverters:
            for inv in manual_config_inverters:
                if inv.adapter.serial_port:
                    manual_ports.add(inv.adapter.serial_port)
        if manual_config_battery and manual_config_battery.adapter.serial_port:
            manual_ports.add(manual_config_battery.adapter.serial_port)
        
        # PHASE 1: Check Known Devices from Database
        log.info("Phase 1: Checking known devices from database...")
        known_devices = self.registry.get_all_devices(status_filter="active")
        missing_devices: List[DeviceEntry] = []
        
        for device in known_devices:
            # Only check devices on USB ports
            if device.port and not ("/dev/ttyUSB" in device.port or "COM" in device.port):
                log.debug(f"Skipping {device.device_id} - port {device.port} is not a USB port")
                continue
            
            if device.port and device.port in manual_ports:
                log.debug(f"Skipping {device.device_id} - port {device.port} is manually configured")
                continue
            
            if device.port:
                # Try to connect to saved port and verify serial matches
                adapter_class = self.adapters.get(device.device_type) or self.battery_adapters.get(device.device_type)
                if not adapter_class:
                    log.warning(f"No adapter class for device type {device.device_type}")
                    missing_devices.append(device)
                    continue
                
                result = await self.identify_device_on_port(
                    device.port,
                    device.device_type,
                    adapter_class,
                    device.adapter_config,
                    keep_adapter=False  # Don't keep adapters for database devices
                )
                
                if result:
                    serial_number, _, _ = result
                    # Verify serial matches (per design doc)
                    if self.registry.normalize_serial(serial_number) == self.registry.normalize_serial(device.serial_number):
                        # Device found on saved port
                        device.last_seen = now_configured_iso()
                        device.status = "active"
                        self.registry.register_device(device)
                        discovered_devices.append(device)
                        used_ports.add(device.port)
                        log.info(f"✓ Found known device {device.device_id} on saved port {device.port}")
                        continue
            
            # Device not found on saved port - mark for Phase 2 search
            missing_devices.append(device)
            log.info(f"Device {device.device_id} not found on saved port {device.port}")
        
        # Also check manually configured devices (from config.yaml)
        log.info("Phase 1: Checking manually configured devices...")
        manually_configured_missing: List[Dict[str, Any]] = []
        
        if manual_config_inverters:
            log.info(f"Checking {len(manual_config_inverters)} manually configured inverters...")
            for inv in manual_config_inverters:
                if not inv.adapter.serial_port:
                    continue
                
                port = inv.adapter.serial_port
                device_type = inv.adapter.type
                
                if not ("/dev/ttyUSB" in port or "COM" in port):
                    log.warning(f"Skipping {inv.id} - port {port} is not a USB port")
                    continue
                
                adapter_class = self.adapters.get(device_type)
                if not adapter_class:
                    log.warning(f"No adapter class for device type {device_type} for {inv.id}")
                    manually_configured_missing.append({
                        "id": inv.id,
                        "type": device_type,
                        "port": port,
                        "adapter_config": {
                            "type": device_type,
                            "transport": getattr(inv.adapter, "transport", "rtu"),
                            "serial_port": port,
                            "unit_id": getattr(inv.adapter, "unit_id", 1),
                            "baudrate": getattr(inv.adapter, "baudrate", 9600),
                            "parity": getattr(inv.adapter, "parity", "N"),
                            "stopbits": getattr(inv.adapter, "stopbits", 1),
                            "bytesize": getattr(inv.adapter, "bytesize", 8),
                            **({"register_map_file": inv.adapter.register_map_file} if hasattr(inv.adapter, "register_map_file") and inv.adapter.register_map_file else {})
                        }
                    })
                    continue
                
                adapter_config = {
                    "type": device_type,
                    "transport": getattr(inv.adapter, "transport", "rtu"),
                    "serial_port": port,
                    "unit_id": getattr(inv.adapter, "unit_id", 1),
                    "baudrate": getattr(inv.adapter, "baudrate", 9600),
                    "parity": getattr(inv.adapter, "parity", "N"),
                    "stopbits": getattr(inv.adapter, "stopbits", 1),
                    "bytesize": getattr(inv.adapter, "bytesize", 8),
                }
                if hasattr(inv.adapter, "register_map_file") and inv.adapter.register_map_file:
                    adapter_config["register_map_file"] = inv.adapter.register_map_file
                
                log.info(f"Checking manually configured device {inv.id} ({device_type}) on port {port}")
                # Identify device and close connection immediately - runtime will create fresh connection
                result = await self.identify_device_on_port(
                    port,
                    device_type,
                    adapter_class,
                    adapter_config,
                    keep_adapter=False  # Close connection immediately - runtime will create fresh one
                )
                
                if result:
                    serial_number, _, _ = result
                    # Don't store adapter - runtime will create fresh connection
                    normalized_serial = self.registry.normalize_serial(serial_number)
                    existing_device = self.registry.find_device_by_serial(normalized_serial, device_type)
                    
                    if existing_device:
                        # Update port if changed
                        if existing_device.port != port:
                            old_port = existing_device.port
                            self.registry.update_device_port(existing_device.device_id, port)
                            existing_device.port = port
                            if old_port and old_port not in existing_device.port_history:
                                existing_device.port_history.append(old_port)
                        existing_device.last_seen = now_configured_iso()
                        existing_device.status = "active"
                        self.registry.register_device(existing_device)
                        discovered_devices.append(existing_device)
                        used_ports.add(port)
                        log.info(f"✓ Found manually configured device {inv.id} ({device_type}) on port {port}")
                    else:
                        # New device - register it
                        device_id = self.registry.generate_device_id(device_type, normalized_serial)
                        new_device = DeviceEntry(
                            device_id=device_id,
                            device_type=device_type,
                            serial_number=normalized_serial,
                            port=port,
                            last_known_port=port,
                            port_history=[],
                            adapter_config=adapter_config,
                            status="active",
                            failure_count=0,
                            next_retry_time=None,
                            first_discovered=now_configured_iso(),
                            last_seen=now_configured_iso(),
                            discovery_timestamp=now_configured_iso(),
                            is_auto_discovered=False
                        )
                        self.registry.register_device(new_device)
                        discovered_devices.append(new_device)
                        used_ports.add(port)
                        log.info(f"✓ Registered manually configured device {inv.id} ({device_id}) on port {port}")
                else:
                    log.warning(f"Manually configured device {inv.id} ({device_type}) not found on configured port {port} - will search other ports in Phase 2")
                    manually_configured_missing.append({
                        "id": inv.id,
                        "type": device_type,
                        "port": port,
                        "adapter_config": adapter_config
                    })
        
        # Check manually configured battery bank
        if manual_config_battery and manual_config_battery.adapter.serial_port:
            bank = manual_config_battery
            port = bank.adapter.serial_port
            device_type = bank.adapter.type
            
            if not ("/dev/ttyUSB" in port or "COM" in port):
                log.warning(f"Skipping {bank.id} - port {port} is not a USB port")
            else:
                adapter_class = self.battery_adapters.get(device_type)
                if not adapter_class:
                    log.warning(f"No adapter class for battery type {device_type} for {bank.id}")
                    manually_configured_missing.append({
                        "id": bank.id,
                        "type": device_type,
                        "port": port,
                        "adapter_config": {
                            "type": device_type,
                            "serial_port": port,
                            "baudrate": getattr(bank.adapter, "baudrate", 115200),
                            "parity": getattr(bank.adapter, "parity", "N"),
                            "stopbits": getattr(bank.adapter, "stopbits", 1),
                            "bytesize": getattr(bank.adapter, "bytesize", 8),
                            "batteries": getattr(bank.adapter, "batteries", 1),
                            "cells_per_battery": getattr(bank.adapter, "cells_per_battery", 16),
                            **({"dev_name": bank.adapter.dev_name} if hasattr(bank.adapter, "dev_name") else {})
                        }
                    })
                else:
                    adapter_config = {
                        "type": device_type,
                        "serial_port": port,
                        "baudrate": getattr(bank.adapter, "baudrate", 115200),
                        "parity": getattr(bank.adapter, "parity", "N"),
                        "stopbits": getattr(bank.adapter, "stopbits", 1),
                        "bytesize": getattr(bank.adapter, "bytesize", 8),
                        "batteries": getattr(bank.adapter, "batteries", 1),
                        "cells_per_battery": getattr(bank.adapter, "cells_per_battery", 16),
                    }
                    if hasattr(bank.adapter, "dev_name"):
                        adapter_config["dev_name"] = bank.adapter.dev_name
                    
                    log.info(f"Checking manually configured battery bank {bank.id} ({device_type}) on port {port}")
                    # Identify device and close connection immediately - runtime will create fresh connection
                    result = await self.identify_device_on_port(
                        port,
                        device_type,
                        adapter_class,
                        adapter_config,
                        keep_adapter=False  # Close connection immediately - runtime will create fresh one
                    )
                    
                    if result:
                        serial_number, _, _ = result
                        # Don't store adapter - runtime will create fresh connection
                        normalized_serial = self.registry.normalize_serial(serial_number)
                        existing_device = self.registry.find_device_by_serial(normalized_serial, device_type)
                        
                        if existing_device:
                            if existing_device.port != port:
                                old_port = existing_device.port
                                self.registry.update_device_port(existing_device.device_id, port)
                                existing_device.port = port
                                if old_port and old_port not in existing_device.port_history:
                                    existing_device.port_history.append(old_port)
                            existing_device.last_seen = now_configured_iso()
                            existing_device.status = "active"
                            self.registry.register_device(existing_device)
                            discovered_devices.append(existing_device)
                            used_ports.add(port)
                            log.info(f"✓ Found manually configured battery {bank.id} ({device_type}) on port {port}")
                        else:
                            device_id = self.registry.generate_device_id(device_type, normalized_serial)
                            new_device = DeviceEntry(
                                device_id=device_id,
                                device_type=device_type,
                                serial_number=normalized_serial,
                                port=port,
                                last_known_port=port,
                                port_history=[],
                                adapter_config=adapter_config,
                                status="active",
                                failure_count=0,
                                next_retry_time=None,
                                first_discovered=now_configured_iso(),
                                last_seen=now_configured_iso(),
                                discovery_timestamp=now_configured_iso(),
                                is_auto_discovered=False
                            )
                            self.registry.register_device(new_device)
                            discovered_devices.append(new_device)
                            used_ports.add(port)
                            log.info(f"✓ Registered manually configured battery {bank.id} ({device_id}) on port {port}")
                    else:
                        log.warning(f"Manually configured battery {bank.id} ({device_type}) not found on configured port {port} - will search other ports in Phase 2")
                        manually_configured_missing.append({
                            "id": bank.id,
                            "type": device_type,
                            "port": port,
                            "adapter_config": adapter_config
                        })
        
        # PHASE 2: Search for Missing Known Devices
        log.info(f"Phase 2: Searching for {len(missing_devices)} missing devices from database...")
        all_ports = self.get_available_ports()
        available_ports = [p for p in all_ports if p not in used_ports]
        
        for device in missing_devices:
            found = False
            adapter_class = self.adapters.get(device.device_type) or self.battery_adapters.get(device.device_type)
            if not adapter_class:
                continue
            
            # Search all available ports (excluding already-used ports)
            for port in available_ports:
                if port in used_ports:
                    continue
                
                result = await self.identify_device_on_port(
                    port,
                    device.device_type,
                    adapter_class,
                    device.adapter_config,
                    keep_adapter=False
                )
                
                if result:
                    serial_number, _, _ = result
                    # Verify serial matches (per design doc)
                    if self.registry.normalize_serial(serial_number) == self.registry.normalize_serial(device.serial_number):
                        # Device found on new port - update port assignment
                        old_port = device.port
                        self.registry.update_device_port(device.device_id, port)
                        device.port = port
                        if old_port and old_port != port:
                            if old_port not in device.port_history:
                                device.port_history.append(old_port)
                        device.last_seen = now_configured_iso()
                        device.status = "active"
                        self.registry.register_device(device)
                        discovered_devices.append(device)
                        used_ports.add(port)
                        log.info(f"✓ Found missing device {device.device_id} on new port {port}")
                        found = True
                        break
            
            if not found:
                # Device not found on any port - set 15-minute retry timer (per design doc)
                retry_time = (datetime.now() + timedelta(minutes=15)).isoformat()
                self.registry.update_device_status(
                    device.device_id,
                    "recovering",
                    failure_count=device.failure_count + 1,
                    next_retry_time=retry_time
                )
                log.warning(f"Device {device.device_id} not found on any port - will retry in 15 minutes")
        
        # Also search for manually configured missing devices
        log.info(f"Phase 2: Searching for {len(manually_configured_missing)} missing manually configured devices...")
        found_manual_devices = []
        for manual_dev in manually_configured_missing:
            found = False
            device_type = manual_dev["type"]
            device_id = manual_dev["id"]
            adapter_class = self.adapters.get(device_type) or self.battery_adapters.get(device_type)
            if not adapter_class:
                continue
            
            log.info(f"Searching for manually configured device {device_id} ({device_type}) originally on {manual_dev['port']}")
            
            # Search all ports (skip only ports already used by discovered devices)
            for port in all_ports:
                if port in used_ports:
                    continue
                
                test_adapter_config = manual_dev["adapter_config"].copy()
                test_adapter_config["serial_port"] = port
                
                # Identify device and close connection immediately - runtime will create fresh connection
                result = await self.identify_device_on_port(
                    port,
                    device_type,
                    adapter_class,
                    test_adapter_config,
                    keep_adapter=False  # Close connection immediately - runtime will create fresh one
                )
                
                if result:
                    serial_number, _, _ = result
                    # Don't store adapter - runtime will create fresh connection
                    normalized_serial = self.registry.normalize_serial(serial_number)
                    existing_device = self.registry.find_device_by_serial(normalized_serial, device_type)
                    
                    if existing_device:
                        old_port = existing_device.port
                        self.registry.update_device_port(existing_device.device_id, port)
                        existing_device.port = port
                        if old_port and old_port != port:
                            if old_port not in existing_device.port_history:
                                existing_device.port_history.append(old_port)
                        existing_device.last_seen = now_configured_iso()
                        existing_device.status = "active"
                        self.registry.register_device(existing_device)
                        discovered_devices.append(existing_device)
                        used_ports.add(port)
                        log.info(f"✓ Found manually configured device {device_id} on new port {port}")
                        found = True
                        found_manual_devices.append(device_id)
                        break
                    else:
                        # New device - register it
                        new_device_id = self.registry.generate_device_id(device_type, normalized_serial)
                        new_device = DeviceEntry(
                            device_id=new_device_id,
                            device_type=device_type,
                            serial_number=normalized_serial,
                            port=port,
                            last_known_port=port,
                            port_history=[],
                            adapter_config=test_adapter_config,
                            status="active",
                            failure_count=0,
                            next_retry_time=None,
                            first_discovered=now_configured_iso(),
                            last_seen=now_configured_iso(),
                            discovery_timestamp=now_configured_iso(),
                            is_auto_discovered=False
                        )
                        self.registry.register_device(new_device)
                        discovered_devices.append(new_device)
                        used_ports.add(port)
                        log.info(f"✓ Found manually configured device {device_id} on port {port} (registered as {new_device_id})")
                        found = True
                        found_manual_devices.append(device_id)
                        break
            
            if not found:
                log.warning(f"Manually configured device {device_id} ({device_type}) not found on any port after checking: {all_ports}")
        
        # Remove found devices from manually_configured_missing for Phase 4 check
        manually_configured_missing = [
            d for d in manually_configured_missing 
            if d['id'] not in found_manual_devices
        ]
        
        # PHASE 3: Discover New Devices (if ports available)
        log.info("Phase 3: Discovering new devices on unused ports...")
        unused_ports = [p for p in all_ports if p not in used_ports]
        
        for port in unused_ports:
            device_found = False
            # Try each device type in priority order (per design doc)
            for device_type in self.priority_order:
                if device_found:
                    break
                
                adapter_class = self.adapters.get(device_type) or self.battery_adapters.get(device_type)
                if not adapter_class:
                    continue
                
                # Create default config for this device type
                if device_type in self.adapters:
                    default_config = {
                        "type": device_type,
                        "transport": "rtu",
                        "serial_port": port,
                        "unit_id": 1,
                        "baudrate": 9600,
                        "parity": "N",
                        "stopbits": 1,
                        "bytesize": 8,
                    }
                elif device_type in self.battery_adapters:
                    default_config = {
                        "type": device_type,
                        "serial_port": port,
                        "baudrate": 115200,
                        "parity": "N",
                        "stopbits": 1,
                        "bytesize": 8,
                        "batteries": 1,
                        "cells_per_battery": 16,
                    }
                else:
                    continue
                
                result = await self.identify_device_on_port(
                    port,
                    device_type,
                    adapter_class,
                    default_config,
                    keep_adapter=False
                )
                
                if result:
                    serial_number, adapter_config, _ = result
                    normalized_serial = self.registry.normalize_serial(serial_number)
                    
                    # Check if this serial already exists (per design doc)
                    existing_device = self.registry.find_device_by_serial(normalized_serial, device_type)
                    
                    if existing_device:
                        # Device moved to new port - update port assignment
                        old_port = existing_device.port
                        self.registry.update_device_port(existing_device.device_id, port)
                        existing_device.port = port
                        if old_port and old_port != port:
                            if old_port not in existing_device.port_history:
                                existing_device.port_history.append(old_port)
                        existing_device.last_seen = now_configured_iso()
                        existing_device.status = "active"
                        self.registry.register_device(existing_device)
                        discovered_devices.append(existing_device)
                        log.info(f"✓ Device {existing_device.device_id} moved to port {port}")
                    else:
                        # New device - create new device entry with device_id = {type}_{serial_last6} (per design doc)
                        device_id = self.registry.generate_device_id(device_type, normalized_serial)
                        new_device = DeviceEntry(
                            device_id=device_id,
                            device_type=device_type,
                            serial_number=normalized_serial,
                            port=port,
                            last_known_port=port,
                            port_history=[],
                            adapter_config=adapter_config,
                            status="active",
                            failure_count=0,
                            next_retry_time=None,
                            first_discovered=now_configured_iso(),
                            last_seen=now_configured_iso(),
                            discovery_timestamp=now_configured_iso(),
                            is_auto_discovered=True
                        )
                        self.registry.register_device(new_device)
                        discovered_devices.append(new_device)
                        log.info(f"✓ Discovered new device {device_id} on port {port}")
                    
                    used_ports.add(port)
                    device_found = True
                    break
        
        # PHASE 4: Finalize and Cleanup
        log.info("Phase 4: Finalizing discovery...")
        
        # Check if all ports are exhausted (per design doc)
        all_ports_scanned = len(unused_ports) == 0 or all(p in used_ports for p in all_ports)
        
        if all_ports_scanned:
            # All ports scanned - check for still-missing devices from database
            still_missing = [
                d for d in missing_devices
                if d.device_id not in [dd.device_id for dd in discovered_devices]
            ]
            
            for device in still_missing:
                # Device not found anywhere - likely decommissioned (per design doc)
                log.warning(
                    f"Device {device.device_id} not found on any port after full scan - "
                    f"permanently disabling (likely decommissioned)"
                )
                self.registry.permanently_disable_device(device.device_id)
            
            # Check for still-missing manually configured devices
            for manual_dev in manually_configured_missing:
                log.warning(
                    f"Manually configured device {manual_dev['id']} ({manual_dev['type']}) "
                    f"not found on any port after full scan - device may be decommissioned. "
                    f"Consider removing it from config.yaml if no longer in use."
                )
        
        log.info(f"Discovery complete: {len(discovered_devices)} devices found")
        return discovered_devices, {}  # Return empty dict - runtime creates fresh connections
