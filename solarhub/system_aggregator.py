"""
System Aggregator: Aggregates array telemetry into system-level data.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
from solarhub.array_models import ArrayTelemetry, HomeTelemetry
from solarhub.array_aggregator import ArrayAggregator

log = logging.getLogger(__name__)


class SystemAggregator:
    """
    Aggregates array telemetry into system-level data.
    
    This is essentially a wrapper around ArrayAggregator.aggregate_home_telemetry
    but with explicit system_id awareness and proper hierarchy structure.
    """
    
    def __init__(self):
        """Initialize the system aggregator."""
        self.array_aggregator = ArrayAggregator()
    
    def aggregate_system_telemetry(
        self,
        system_id: str,
        array_telemetry: Dict[str, ArrayTelemetry],
        meter_telemetry: Optional[Dict[str, Any]] = None,
        battery_bank_telemetry: Optional[Dict[str, Any]] = None,
        meter_configs: Optional[Dict[str, Any]] = None,
        meter_energy_data: Optional[Dict[str, Dict[str, float]]] = None
    ) -> HomeTelemetry:
        """
        Aggregate array telemetry into system-level data.
        
        Args:
            system_id: System identifier
            array_telemetry: Dict mapping array_id -> ArrayTelemetry
            meter_telemetry: Optional dict mapping meter_id -> MeterTelemetry (for system-attached meters)
            battery_bank_telemetry: Optional dict mapping bank_id -> BatteryBankTelemetry (for aggregation)
            meter_configs: Optional dict mapping meter_id -> meter config
            meter_energy_data: Optional dict mapping meter_id -> energy data
            
        Returns:
            HomeTelemetry with aggregated data from all arrays in the system
        """
        # Use existing aggregate_home_telemetry but ensure system_id is included
        home_tel = self.array_aggregator.aggregate_home_telemetry(
            array_telemetry, meter_telemetry, battery_bank_telemetry,
            meter_configs=meter_configs, meter_energy_data=meter_energy_data
        )
        
        # Update home_id to system_id for proper hierarchy
        home_tel.home_id = system_id
        
        # Ensure all arrays in breakdown include system_id
        if home_tel.arrays:
            for array_data in home_tel.arrays:
                array_data["system_id"] = system_id
        
        # Ensure all meters in breakdown include system_id
        if home_tel.meters:
            for meter_data in home_tel.meters:
                meter_data["system_id"] = system_id
        
        return home_tel

