"""
Array Aggregator: Aggregates inverter telemetry into array-level data.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
from solarhub.array_models import ArrayTelemetry, BatteryPackTelemetry, HomeTelemetry
from solarhub.models import Telemetry

log = logging.getLogger(__name__)


class ArrayAggregator:
    """
    Aggregates per-inverter telemetry into per-array consolidated data.
    
    Handles:
    - Summing powers/energies across inverters
    - Energy-weighted means for SOC/temps
    - Per-inverter and per-pack breakdowns
    """
    
    def __init__(self):
        """Initialize the aggregator."""
        pass
    
    def aggregate_array_telemetry(
        self,
        array_id: str,
        inverter_telemetry: Dict[str, Telemetry],
        pack_telemetry: Optional[Dict[str, BatteryPackTelemetry]] = None,
        pack_configs: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> ArrayTelemetry:
        """
        Aggregate inverter telemetry into array-level data.
        
        Args:
            array_id: Array identifier
            inverter_telemetry: Dict mapping inverter_id -> Telemetry
            pack_telemetry: Optional dict mapping pack_id -> BatteryPackTelemetry
            pack_configs: Optional dict mapping pack_id -> config (for nominal_kwh)
            
        Returns:
            ArrayTelemetry with aggregated data
        """
        if not inverter_telemetry:
            log.warning(f"No inverter telemetry provided for array {array_id}")
            return ArrayTelemetry(
                array_id=array_id,
                ts=datetime.utcnow().isoformat(),
                metadata={"inverter_count": 0}  # Will be serialized as _metadata in JSON
            )
        
        # Get most recent timestamp
        timestamps = [tel.ts for tel in inverter_telemetry.values() if tel.ts]
        latest_ts = max(timestamps) if timestamps else datetime.utcnow().isoformat()
        
        # Sum powers across all inverters
        pv_power_w = sum(
            tel.pv_power_w for tel in inverter_telemetry.values()
            if tel.pv_power_w is not None
        ) or None
        
        load_power_w = sum(
            tel.load_power_w for tel in inverter_telemetry.values()
            if tel.load_power_w is not None
        ) or None
        
        grid_power_w = sum(
            tel.grid_power_w for tel in inverter_telemetry.values()
            if tel.grid_power_w is not None
        ) or None
        
        # Battery power: sum from inverters (if available) or from packs
        batt_power_w = None
        if any(tel.batt_power_w is not None for tel in inverter_telemetry.values()):
            batt_power_w = sum(
                tel.batt_power_w for tel in inverter_telemetry.values()
                if tel.batt_power_w is not None
            )
        elif pack_telemetry:
            batt_power_w = sum(
                pack.power_w for pack in pack_telemetry.values()
                if pack.power_w is not None
            ) or None
        
        # Energy-weighted SOC calculation across attached packs
        batt_soc_pct = self._calculate_energy_weighted_soc(
            pack_telemetry or {},
            pack_configs or {}
        )
        
        # If no pack SOC, use inverter battery SOC (fallback)
        if batt_soc_pct is None:
            soc_values = [
                tel.batt_soc_pct for tel in inverter_telemetry.values()
                if tel.batt_soc_pct is not None
            ]
            if soc_values:
                batt_soc_pct = sum(soc_values) / len(soc_values)
        
        # Battery voltage/current: average or sum depending on topology
        batt_voltage_v = None
        batt_current_a = None
        
        if pack_telemetry:
            # From packs: voltage is typically same (parallel), current is sum
            voltages = [p.voltage_v for p in pack_telemetry.values() if p.voltage_v is not None]
            if voltages:
                batt_voltage_v = sum(voltages) / len(voltages)  # Average for parallel packs
            
            currents = [p.current_a for p in pack_telemetry.values() if p.current_a is not None]
            if currents:
                batt_current_a = sum(currents)  # Sum for parallel packs
        else:
            # From inverters: average voltage, sum current
            voltages = [tel.batt_voltage_v for tel in inverter_telemetry.values() if tel.batt_voltage_v is not None]
            if voltages:
                batt_voltage_v = sum(voltages) / len(voltages)
            
            currents = [tel.batt_current_a for tel in inverter_telemetry.values() if tel.batt_current_a is not None]
            if currents:
                batt_current_a = sum(currents)
        
        # Per-inverter breakdown
        inverter_breakdown = []
        for inv_id, tel in inverter_telemetry.items():
            inv_data = {
                "inverter_id": inv_id,
                "pv_power_w": tel.pv_power_w,
                "load_power_w": tel.load_power_w,
                "grid_power_w": tel.grid_power_w,
                "batt_power_w": tel.batt_power_w,
            }
            # Add phase type if available
            if tel.extra and "phase_type" in tel.extra:
                inv_data["phase_type"] = tel.extra["phase_type"]
            inverter_breakdown.append(inv_data)
        
        # Per-pack breakdown
        pack_breakdown = []
        if pack_telemetry:
            for pack_id, pack_tel in pack_telemetry.items():
                pack_data = {
                    "pack_id": pack_id,
                    "soc_pct": pack_tel.soc_pct,
                    "voltage_v": pack_tel.voltage_v,
                    "current_a": pack_tel.current_a,
                    "power_w": pack_tel.power_w,
                }
                pack_breakdown.append(pack_data)
        
        # Metadata
        metadata = {
            "inverter_count": len(inverter_telemetry),
            "attached_pack_ids": list(pack_telemetry.keys()) if pack_telemetry else [],
        }
        
        # Add phase mix and vendor mix if available
        phase_types = []
        vendor_types = []
        for tel in inverter_telemetry.values():
            if tel.extra:
                if "phase_type" in tel.extra:
                    phase_types.append(tel.extra["phase_type"])
                if "vendor" in tel.extra:
                    vendor_types.append(tel.extra["vendor"])
                elif "device_model" in tel.extra:
                    # Try to infer vendor from model name
                    model = tel.extra.get("device_model", "").lower()
                    if "senergy" in model:
                        vendor_types.append("senergy")
                    elif "powdrive" in model:
                        vendor_types.append("powdrive")
        
        if phase_types:
            metadata["phase_mix"] = phase_types
        if vendor_types:
            metadata["vendor_mix"] = list(set(vendor_types))  # Unique vendors
        
        return ArrayTelemetry(
            array_id=array_id,
            ts=latest_ts,
            pv_power_w=int(round(pv_power_w)) if pv_power_w is not None else None,
            load_power_w=int(round(load_power_w)) if load_power_w is not None else None,
            grid_power_w=int(round(grid_power_w)) if grid_power_w is not None else None,
            batt_power_w=int(round(batt_power_w)) if batt_power_w is not None else None,
            batt_soc_pct=batt_soc_pct,
            batt_voltage_v=batt_voltage_v,
            batt_current_a=batt_current_a,
            inverters=inverter_breakdown,
            packs=pack_breakdown,
            metadata=metadata  # Will be serialized as _metadata in JSON due to alias
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
    
    def aggregate_home_telemetry(
        self,
        array_telemetry: Dict[str, ArrayTelemetry],
        meter_telemetry: Optional[Dict[str, Any]] = None,
        battery_bank_telemetry: Optional[Dict[str, Any]] = None
    ) -> HomeTelemetry:
        """
        Aggregate array telemetry into home-level data.
        
        Args:
            array_telemetry: Dict mapping array_id -> ArrayTelemetry
            meter_telemetry: Optional dict mapping meter_id -> MeterTelemetry (for home-attached meters)
            battery_bank_telemetry: Optional dict mapping bank_id -> BatteryBankTelemetry (for aggregation)
            
        Returns:
            HomeTelemetry with aggregated data from all arrays
        """
        from solarhub.timezone_utils import now_configured_iso
        
        if not array_telemetry:
            log.warning("No array telemetry provided for home aggregation")
            return HomeTelemetry(
                home_id="home",
                ts=now_configured_iso(),
                metadata={"array_count": 0}
            )
        
        # Get most recent timestamp
        timestamps = [arr_tel.ts for arr_tel in array_telemetry.values() if arr_tel.ts]
        latest_ts = max(timestamps) if timestamps else now_configured_iso()
        
        # Sum powers across all arrays
        total_pv_power_w = sum(
            arr_tel.pv_power_w for arr_tel in array_telemetry.values()
            if arr_tel.pv_power_w is not None
        ) or None
        
        total_load_power_w = sum(
            arr_tel.load_power_w for arr_tel in array_telemetry.values()
            if arr_tel.load_power_w is not None
        ) or None
        
        total_grid_power_w = sum(
            arr_tel.grid_power_w for arr_tel in array_telemetry.values()
            if arr_tel.grid_power_w is not None
        ) or None
        
        # Battery power: prefer battery bank telemetry (more accurate) over inverter telemetry
        total_batt_power_w = None
        
        # First, try to get battery power from battery bank telemetry (sum all battery banks)
        # This is the most accurate source as it comes directly from battery BMS
        if battery_bank_telemetry:
            battery_powers = []
            for bank_id, bank_tel in battery_bank_telemetry.items():
                # Try to get power from extra field first (stored by adapters)
                bank_power = None
                if hasattr(bank_tel, 'extra') and bank_tel.extra:
                    bank_power = bank_tel.extra.get('power')
                
                # If not in extra, calculate from voltage * current
                # Note: current sign convention: positive = charging, negative = discharging
                if bank_power is None and bank_tel.voltage is not None and bank_tel.current is not None:
                    bank_power = bank_tel.voltage * bank_tel.current
                    log.debug(f"Calculated battery power for {bank_id}: {bank_tel.voltage}V × {bank_tel.current}A = {bank_power:.1f}W")
                
                if bank_power is not None:
                    battery_powers.append(bank_power)
                    log.debug(f"Battery bank {bank_id} power: {bank_power:.1f}W (from {'extra' if hasattr(bank_tel, 'extra') and bank_tel.extra and bank_tel.extra.get('power') else 'calculated'})")
            
            if battery_powers:
                total_batt_power_w = sum(battery_powers)
                log.info(f"Aggregated battery power from {len(battery_powers)} battery bank(s): {total_batt_power_w:.1f}W (banks: {list(battery_bank_telemetry.keys())})")
        
        # Fallback to array-level battery power if no battery bank data
        if total_batt_power_w is None:
            total_batt_power_w = sum(
                arr_tel.batt_power_w for arr_tel in array_telemetry.values()
                if arr_tel.batt_power_w is not None
            ) or None
            if total_batt_power_w is not None:
                log.debug(f"Using battery power from inverter arrays: {total_batt_power_w:.1f}W")
        
        # Calculate energy-weighted average SOC across all arrays
        # Use battery bank telemetry if available, otherwise use array battery SOC
        avg_batt_soc_pct = None
        
        if battery_bank_telemetry:
            # Calculate energy-weighted SOC from battery banks
            total_capacity = 0.0
            weighted_soc = 0.0
            
            for bank_id, bank_tel in battery_bank_telemetry.items():
                if bank_tel.soc is None:
                    continue
                
                # Estimate capacity from voltage and current if available
                # For now, use equal weighting or try to get from extra
                capacity_kwh = 1.0  # Default equal weighting
                if hasattr(bank_tel, 'extra') and bank_tel.extra:
                    # Try to get capacity from extra
                    capacity_kwh = bank_tel.extra.get('nominal_capacity_kwh', 1.0)
                
                total_capacity += capacity_kwh
                weighted_soc += bank_tel.soc * capacity_kwh
            
            if total_capacity > 0:
                avg_batt_soc_pct = weighted_soc / total_capacity
        
        # Fallback to array-level SOC if no battery bank data
        if avg_batt_soc_pct is None:
            soc_values = [
                arr_tel.batt_soc_pct for arr_tel in array_telemetry.values()
                if arr_tel.batt_soc_pct is not None
            ]
            if soc_values:
                avg_batt_soc_pct = sum(soc_values) / len(soc_values)
        
        # Per-array breakdown
        array_breakdown = []
        for array_id, arr_tel in array_telemetry.items():
            array_data = {
                "array_id": array_id,
                "pv_power_w": arr_tel.pv_power_w,
                "load_power_w": arr_tel.load_power_w,
                "grid_power_w": arr_tel.grid_power_w,
                "batt_power_w": arr_tel.batt_power_w,
                "batt_soc_pct": arr_tel.batt_soc_pct,
                "inverter_count": arr_tel.metadata.get("inverter_count", 0) if arr_tel.metadata else 0,
            }
            array_breakdown.append(array_data)
        
        # Home-level meters (attached to "home")
        meter_breakdown = []
        if meter_telemetry:
            for meter_id, meter_tel in meter_telemetry.items():
                # Handle both MeterTelemetry objects and dicts
                if hasattr(meter_tel, 'grid_power_w'):
                    # It's a MeterTelemetry object
                    meter_data = {
                        "meter_id": meter_id,
                        "power_w": meter_tel.grid_power_w,
                        "voltage_v": meter_tel.grid_voltage_v,
                        "current_a": meter_tel.grid_current_a,
                        "frequency_hz": meter_tel.grid_frequency_hz,
                    }
                elif isinstance(meter_tel, dict):
                    # It's already a dict
                    meter_data = {
                        "meter_id": meter_id,
                        "power_w": meter_tel.get('grid_power_w') or meter_tel.get('power_w'),
                        "voltage_v": meter_tel.get('grid_voltage_v') or meter_tel.get('voltage_v'),
                        "current_a": meter_tel.get('grid_current_a') or meter_tel.get('current_a'),
                        "frequency_hz": meter_tel.get('grid_frequency_hz') or meter_tel.get('frequency_hz'),
                    }
                else:
                    # Fallback to getattr
                    meter_data = {
                        "meter_id": meter_id,
                        "power_w": getattr(meter_tel, 'grid_power_w', None) or getattr(meter_tel, 'power_w', None),
                        "voltage_v": getattr(meter_tel, 'grid_voltage_v', None) or getattr(meter_tel, 'voltage_v', None),
                        "current_a": getattr(meter_tel, 'grid_current_a', None) or getattr(meter_tel, 'current_a', None),
                        "frequency_hz": getattr(meter_tel, 'grid_frequency_hz', None) or getattr(meter_tel, 'frequency_hz', None),
                    }
                meter_breakdown.append(meter_data)
        
        # Metadata
        metadata = {
            "array_count": len(array_telemetry),
            "total_inverters": sum(
                arr_tel.metadata.get("inverter_count", 0) if arr_tel.metadata else 0
                for arr_tel in array_telemetry.values()
            ),
            "meter_count": len(meter_breakdown),
        }
        
        return HomeTelemetry(
            home_id="home",
            ts=latest_ts,
            total_pv_power_w=int(round(total_pv_power_w)) if total_pv_power_w is not None else None,
            total_load_power_w=int(round(total_load_power_w)) if total_load_power_w is not None else None,
            total_grid_power_w=int(round(total_grid_power_w)) if total_grid_power_w is not None else None,
            total_batt_power_w=int(round(total_batt_power_w)) if total_batt_power_w is not None else None,
            avg_batt_soc_pct=avg_batt_soc_pct,
            arrays=array_breakdown,
            meters=meter_breakdown,
            metadata=metadata
        )

