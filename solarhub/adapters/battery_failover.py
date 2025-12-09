"""
Battery Adapter Failover Wrapper

Provides automatic failover between multiple battery adapters.
If the primary adapter fails, automatically switches to secondary adapters.

Configuration:
    adapters:
      - adapter:
          type: jkbms_tcpip
          connection_type: rtu
          serial_port: /dev/ttyUSB0
          ...
        priority: 1  # Primary
      - adapter:
          type: jkbms_ble
          bt_addresses: [...]
          ...
        priority: 2  # Secondary (failover)
"""

import asyncio
import logging
from typing import Optional, List, Dict, Any

from solarhub.adapters.base import BatteryAdapter
from solarhub.config import BatteryBankConfig, BatteryAdapterConfigWithPriority
from solarhub.schedulers.models import BatteryBankTelemetry

log = logging.getLogger(__name__)


class FailoverBatteryAdapter(BatteryAdapter):
    """
    Battery adapter wrapper that provides automatic failover between multiple adapters.
    
    Tries adapters in priority order (lower priority number = higher priority).
    If primary adapter fails, automatically switches to secondary adapters.
    """
    
    def __init__(self, bank_cfg: BatteryBankConfig, adapter_factory: Dict[str, type]):
        super().__init__(bank_cfg)
        
        self.adapter_factory = adapter_factory
        self.adapters: List[BatteryAdapter] = []
        self.current_adapter: Optional[BatteryAdapter] = None
        self.current_adapter_index: int = -1
        self.failover_count: int = 0
        self.last_tel: Optional[BatteryBankTelemetry] = None
        
        # Sort adapters by priority (lower number = higher priority)
        if not bank_cfg.adapters:
            raise ValueError("adapters list is required for FailoverBatteryAdapter")
        
        sorted_adapters = sorted(
            [a for a in bank_cfg.adapters if a.enabled],
            key=lambda x: x.priority
        )
        
        if not sorted_adapters:
            raise ValueError("No enabled adapters found in adapters list")
        
        # Create adapter instances
        for adapter_cfg_with_priority in sorted_adapters:
            adapter_cfg = adapter_cfg_with_priority.adapter
            if adapter_cfg.type not in adapter_factory:
                log.warning(f"Skipping adapter type '{adapter_cfg.type}' - not found in factory")
                continue
            
            # Create a temporary BatteryBankConfig for this adapter
            temp_bank_cfg = BatteryBankConfig(
                id=bank_cfg.id,
                name=bank_cfg.name,
                adapter=adapter_cfg
            )
            
            try:
                adapter = adapter_factory[adapter_cfg.type](temp_bank_cfg)
                self.adapters.append(adapter)
                log.info(f"Created failover adapter: {adapter_cfg.type} (priority: {adapter_cfg_with_priority.priority})")
            except Exception as e:
                log.error(f"Failed to create adapter {adapter_cfg.type}: {e}")
        
        if not self.adapters:
            raise ValueError("No valid adapters could be created")
        
        log.info(f"FailoverBatteryAdapter initialized with {len(self.adapters)} adapter(s)")
    
    async def connect(self):
        """Connect to the primary adapter, with automatic failover to secondary if needed."""
        # Try to connect to adapters in priority order
        for idx, adapter in enumerate(self.adapters):
            try:
                log.info(f"Attempting to connect to adapter {idx+1}/{len(self.adapters)} (type: {adapter.bank_cfg.adapter.type})...")
                await adapter.connect()
                self.current_adapter = adapter
                self.current_adapter_index = idx
                log.info(f"✓ Connected to primary adapter: {adapter.bank_cfg.adapter.type}")
                return
            except Exception as e:
                log.warning(f"Failed to connect to adapter {idx+1} ({adapter.bank_cfg.adapter.type}): {e}")
                if idx < len(self.adapters) - 1:
                    log.info(f"Trying next adapter in failover chain...")
                else:
                    log.error(f"All adapters failed to connect. Last error: {e}")
                    raise RuntimeError(f"All {len(self.adapters)} adapter(s) failed to connect. Last error: {e}")
    
    async def close(self):
        """Close all adapter connections."""
        for idx, adapter in enumerate(self.adapters):
            try:
                await adapter.close()
            except Exception as e:
                log.warning(f"Error closing adapter {idx+1}: {e}")
        
        self.current_adapter = None
        self.current_adapter_index = -1
        log.debug("Closed all failover adapters")
    
    async def _try_failover(self) -> bool:
        """Try to failover to next available adapter. Returns True if successful."""
        if self.current_adapter_index >= len(self.adapters) - 1:
            # Already tried all adapters
            return False
        
        # Close current adapter
        if self.current_adapter:
            try:
                await self.current_adapter.close()
            except Exception:
                pass
        
        # Try next adapter
        for idx in range(self.current_adapter_index + 1, len(self.adapters)):
            adapter = self.adapters[idx]
            try:
                log.info(f"Attempting failover to adapter {idx+1}/{len(self.adapters)} (type: {adapter.bank_cfg.adapter.type})...")
                await adapter.connect()
                self.current_adapter = adapter
                self.current_adapter_index = idx
                self.failover_count += 1
                log.info(f"✓ Failover successful to adapter: {adapter.bank_cfg.adapter.type}")
                return True
            except Exception as e:
                log.warning(f"Failover to adapter {idx+1} ({adapter.bank_cfg.adapter.type}) failed: {e}")
                if idx < len(self.adapters) - 1:
                    continue
                else:
                    log.error(f"All adapters exhausted during failover")
                    return False
        
        return False
    
    async def poll(self) -> BatteryBankTelemetry:
        """Poll the current adapter, with automatic failover on failure."""
        if not self.current_adapter:
            # Try to connect if not connected
            await self.connect()
        
        # Try to poll current adapter
        try:
            result = await self.current_adapter.poll()
            self.last_tel = result
            return result
        except Exception as e:
            log.warning(f"Poll failed on current adapter ({self.current_adapter.bank_cfg.adapter.type}): {e}")
            
            # Try failover
            if await self._try_failover():
                # Retry poll with new adapter
                try:
                    result = await self.current_adapter.poll()
                    self.last_tel = result
                    log.info(f"Poll successful after failover to {self.current_adapter.bank_cfg.adapter.type}")
                    return result
                except Exception as retry_e:
                    log.error(f"Poll failed even after failover: {retry_e}")
                    # Return last known telemetry if available
                    if self.last_tel:
                        log.warning("Returning last known telemetry due to adapter failure")
                        return self.last_tel
                    raise
            else:
                # All adapters failed
                log.error("All adapters failed. Returning last known telemetry if available.")
                if self.last_tel:
                    return self.last_tel
                raise RuntimeError(f"All adapters failed and no cached telemetry available. Last error: {e}")
    
    async def check_connectivity(self) -> bool:
        """Check if current adapter is connected and responding."""
        if not self.current_adapter:
            return False
        
        try:
            if hasattr(self.current_adapter, 'check_connectivity'):
                return await self.current_adapter.check_connectivity()
            else:
                # Fallback: try to poll
                await self.current_adapter.poll()
                return True
        except Exception:
            # Try failover
            if await self._try_failover():
                return await self.check_connectivity()
            return False
    
    def get_current_adapter_info(self) -> Dict[str, Any]:
        """Get information about the currently active adapter."""
        if not self.current_adapter:
            return {"status": "no_adapter", "adapter_type": None}
        
        return {
            "status": "active",
            "adapter_type": self.current_adapter.bank_cfg.adapter.type,
            "adapter_index": self.current_adapter_index,
            "failover_count": self.failover_count,
            "total_adapters": len(self.adapters),
        }

