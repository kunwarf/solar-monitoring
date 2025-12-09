"""
Auto-Recovery Manager for handling device failures and retries.

Implements exponential backoff retry strategy and permanent disable logic.
"""

import asyncio
import logging
from typing import Optional
from datetime import datetime, timedelta
from solarhub.device_registry import DeviceRegistry, DeviceEntry
from solarhub.timezone_utils import now_configured_iso

log = logging.getLogger(__name__)


class AutoRecoveryManager:
    """Manages automatic recovery of failed devices."""
    
    def __init__(
        self,
        registry: DeviceRegistry,
        discovery_service,
        initial_retry_minutes: int = 15,
        max_retry_minutes: int = 120,
        backoff_multiplier: float = 1.5,
        max_failures: int = 10
    ):
        self.registry = registry
        self.discovery_service = discovery_service
        self.initial_retry_minutes = initial_retry_minutes
        self.max_retry_minutes = max_retry_minutes
        self.backoff_multiplier = backoff_multiplier
        self.max_failures = max_failures
    
    def calculate_retry_delay(self, failure_count: int) -> int:
        """
        Calculate retry delay in minutes using exponential backoff.
        
        Args:
            failure_count: Number of consecutive failures
        
        Returns:
            Retry delay in minutes
        """
        delay = self.initial_retry_minutes * (self.backoff_multiplier ** (failure_count - 1))
        delay = min(delay, self.max_retry_minutes)
        return int(delay)
    
    async def handle_device_failure(self, device_id: str) -> None:
        """Handle a device failure during polling."""
        device = self.registry.get_device(device_id)
        if not device:
            log.warning(f"Device {device_id} not found in registry")
            return
        
        if device.status == "permanently_disabled":
            # Device is permanently disabled, don't retry
            return
        
        # Calculate next retry time
        new_failure_count = device.failure_count + 1
        retry_delay_minutes = self.calculate_retry_delay(new_failure_count)
        next_retry_time = (datetime.now() + timedelta(minutes=retry_delay_minutes)).isoformat()
        
        # Check if we should permanently disable
        if new_failure_count >= self.max_failures:
            log.error(
                f"Device {device_id} has failed {new_failure_count} times - "
                f"permanently disabling"
            )
            self.registry.permanently_disable_device(device_id)
            return
        
        # Mark device as recovering
        self.registry.mark_device_failed(device_id, next_retry_time)
        log.warning(
            f"Device {device_id} failed (count: {new_failure_count}) - "
            f"will retry in {retry_delay_minutes} minutes"
        )
    
    async def process_recovery_retries(self) -> int:
        """
        Process devices that are ready for retry.
        
        Returns:
            Number of devices processed
        """
        devices_ready = self.registry.get_devices_ready_for_retry()
        if not devices_ready:
            return 0
        
        log.info(f"Processing {len(devices_ready)} devices ready for recovery retry...")
        processed = 0
        
        for device in devices_ready:
            if device.status != "recovering":
                continue
            
            # Try to find device on all available ports
            found = False
            all_ports = self.discovery_service.get_available_ports()
            
            # First try last known port
            if device.last_known_port and device.last_known_port in all_ports:
                result = await self.discovery_service.identify_device_on_port(
                    device.last_known_port,
                    device.device_type,
                    self.discovery_service.adapters.get(device.device_type) or 
                    self.discovery_service.battery_adapters.get(device.device_type),
                    device.adapter_config
                )
                
                if result:
                    serial_number, _ = result
                    if (self.registry.normalize_serial(serial_number) == 
                        self.registry.normalize_serial(device.serial_number)):
                        # Device found on last known port
                        self.registry.update_device_port(device.device_id, device.last_known_port)
                        self.registry.mark_device_recovered(device.device_id)
                        log.info(f"✓ Recovered device {device.device_id} on last known port {device.last_known_port}")
                        found = True
                        processed += 1
                        continue
            
            # If not found, scan all ports
            if not found:
                adapter_class = (self.discovery_service.adapters.get(device.device_type) or
                                self.discovery_service.battery_adapters.get(device.device_type))
                if adapter_class:
                    for port in all_ports:
                        result = await self.discovery_service.identify_device_on_port(
                            port,
                            device.device_type,
                            adapter_class,
                            device.adapter_config
                        )
                        
                        if result:
                            serial_number, _ = result
                            if (self.registry.normalize_serial(serial_number) == 
                                self.registry.normalize_serial(device.serial_number)):
                                # Device found on new port
                                self.registry.update_device_port(device.device_id, port)
                                self.registry.mark_device_recovered(device.device_id)
                                log.info(f"✓ Recovered device {device.device_id} on new port {port}")
                                found = True
                                processed += 1
                                break
            
            # If still not found, schedule next retry
            if not found:
                retry_delay_minutes = self.calculate_retry_delay(device.failure_count + 1)
                next_retry_time = (datetime.now() + timedelta(minutes=retry_delay_minutes)).isoformat()
                self.registry.mark_device_failed(device.device_id, next_retry_time)
                log.debug(
                    f"Device {device.device_id} still not found - "
                    f"next retry in {retry_delay_minutes} minutes"
                )
        
        return processed

