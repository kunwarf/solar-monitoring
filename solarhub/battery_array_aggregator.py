"""
Battery Array Aggregator: Aggregates battery pack telemetry into battery array-level data.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
from solarhub.array_models import BatteryPackTelemetry

log = logging.getLogger(__name__)


class BatteryArrayTelemetry:
    """Aggregated telemetry for a battery array."""
    def __init__(
        self,
        battery_array_id: str,
        system_id: str,
        ts: str,
        total_soc_pct: Optional[float] = None,
        total_voltage_v: Optional[float] = None,
        total_current_a: Optional[float] = None,
        total_power_w: Optional[float] = None,
        avg_temperature_c: Optional[float] = None,
        packs: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.battery_array_id = battery_array_id
        self.system_id = system_id
        self.ts = ts
        self.total_soc_pct = total_soc_pct
        self.total_voltage_v = total_voltage_v
        self.total_current_a = total_current_a
        self.total_power_w = total_power_w
        self.avg_temperature_c = avg_temperature_c
        self.packs = packs or []
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "battery_array_id": self.battery_array_id,
            "system_id": self.system_id,
            "ts": self.ts,
            "total_soc_pct": self.total_soc_pct,
            "total_voltage_v": self.total_voltage_v,
            "total_current_a": self.total_current_a,
            "total_power_w": self.total_power_w,
            "avg_temperature_c": self.avg_temperature_c,
            "packs": self.packs,
            "metadata": self.metadata
        }


class BatteryArrayAggregator:
    """
    Aggregates per-pack telemetry into per-battery-array consolidated data.
    
    Handles:
    - Energy-weighted SOC across packs
    - Summing currents/powers across packs
    - Averaging voltages/temperatures
    - Per-pack breakdowns
    """
    
    def __init__(self):
        """Initialize the battery array aggregator."""
        pass
    
    def aggregate_battery_array_telemetry(
        self,
        battery_array_id: str,
        system_id: str,
        pack_telemetry: Dict[str, BatteryPackTelemetry],
        pack_configs: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> BatteryArrayTelemetry:
        """
        Aggregate battery pack telemetry into battery array-level data.
        
        Args:
            battery_array_id: Battery array identifier
            system_id: System identifier
            pack_telemetry: Dict mapping pack_id -> BatteryPackTelemetry
            pack_configs: Optional dict mapping pack_id -> config (for nominal_kwh)
            
        Returns:
            BatteryArrayTelemetry with aggregated data
        """
        if not pack_telemetry:
            log.warning(f"No pack telemetry provided for battery array {battery_array_id}")
            return BatteryArrayTelemetry(
                battery_array_id=battery_array_id,
                system_id=system_id,
                ts=datetime.utcnow().isoformat(),
                metadata={"pack_count": 0}
            )
        
        # Get most recent timestamp
        timestamps = [pack.ts for pack in pack_telemetry.values() if pack.ts]
        latest_ts = max(timestamps) if timestamps else datetime.utcnow().isoformat()
        
        # Energy-weighted SOC calculation across packs
        total_soc_pct = self._calculate_energy_weighted_soc(
            pack_telemetry,
            pack_configs or {}
        )
        
        # Sum currents and powers across packs
        total_current_a = sum(
            pack.current_a for pack in pack_telemetry.values()
            if pack.current_a is not None
        ) or None
        
        total_power_w = sum(
            pack.power_w for pack in pack_telemetry.values()
            if pack.power_w is not None
        ) or None
        
        # Average voltage (packs in parallel typically have same voltage)
        voltages = [pack.voltage_v for pack in pack_telemetry.values() if pack.voltage_v is not None]
        total_voltage_v = sum(voltages) / len(voltages) if voltages else None
        
        # Average temperature
        temperatures = [pack.temperature_c for pack in pack_telemetry.values() if pack.temperature_c is not None]
        avg_temperature_c = sum(temperatures) / len(temperatures) if temperatures else None
        
        # Per-pack breakdown
        pack_breakdown = []
        for pack_id, pack_tel in pack_telemetry.items():
            pack_data = {
                "pack_id": pack_id,
                "soc_pct": pack_tel.soc_pct,
                "voltage_v": pack_tel.voltage_v,
                "current_a": pack_tel.current_a,
                "power_w": pack_tel.power_w,
                "temperature_c": pack_tel.temperature_c,
            }
            pack_breakdown.append(pack_data)
        
        # Metadata
        metadata = {
            "pack_count": len(pack_telemetry),
        }
        
        return BatteryArrayTelemetry(
            battery_array_id=battery_array_id,
            system_id=system_id,
            ts=latest_ts,
            total_soc_pct=total_soc_pct,
            total_voltage_v=total_voltage_v,
            total_current_a=total_current_a,
            total_power_w=total_power_w,
            avg_temperature_c=avg_temperature_c,
            packs=pack_breakdown,
            metadata=metadata
        )
    
    def _calculate_energy_weighted_soc(
        self,
        pack_telemetry: Dict[str, BatteryPackTelemetry],
        pack_configs: Dict[str, Dict[str, Any]]
    ) -> Optional[float]:
        """
        Calculate energy-weighted SOC across packs.
        
        Formula: sum(pack_soc * pack_nominal_kwh) / sum(pack_nominal_kwh)
        
        Args:
            pack_telemetry: Dict mapping pack_id -> BatteryPackTelemetry
            pack_configs: Dict mapping pack_id -> config with nominal_kwh
            
        Returns:
            Energy-weighted SOC percentage, or None if no data
        """
        if not pack_telemetry:
            return None
        
        total_energy = 0.0
        weighted_soc = 0.0
        
        for pack_id, pack_tel in pack_telemetry.items():
            if pack_tel.soc_pct is None:
                continue
            
            # Get nominal capacity from config
            nominal_kwh = pack_configs.get(pack_id, {}).get("nominal_kwh", 0.0)
            if nominal_kwh <= 0:
                # Fallback: use equal weighting if no config
                nominal_kwh = 1.0
            
            total_energy += nominal_kwh
            weighted_soc += pack_tel.soc_pct * nominal_kwh
        
        if total_energy <= 0:
            return None
        
        return weighted_soc / total_energy

