"""
Telemetry Mapper - Standardized Field Name Mapping Layer

This module provides a mapping layer between device-specific register names
and standardized field names used throughout the system (smart scheduler,
API server, Home Assistant publishing).

All device adapters should use this mapper to convert their device-specific
telemetry data to standardized field names.
"""

from typing import Dict, Any, Optional, List
import logging

log = logging.getLogger(__name__)


# Standardized field names used throughout the system
class StandardFields:
    """Standardized field names for telemetry data."""
    
    # Timestamp
    TS = "ts"
    
    # Power flows (watts)
    PV_POWER_W = "pv_power_w"
    PV1_POWER_W = "pv1_power_w"
    PV2_POWER_W = "pv2_power_w"
    PV3_POWER_W = "pv3_power_w"
    PV4_POWER_W = "pv4_power_w"
    LOAD_POWER_W = "load_power_w"
    GRID_POWER_W = "grid_power_w"
    BATT_POWER_W = "batt_power_w"
    
    # Three-phase Load data
    LOAD_L1_POWER_W = "load_l1_power_w"
    LOAD_L2_POWER_W = "load_l2_power_w"
    LOAD_L3_POWER_W = "load_l3_power_w"
    LOAD_L1_VOLTAGE_V = "load_l1_voltage_v"
    LOAD_L2_VOLTAGE_V = "load_l2_voltage_v"
    LOAD_L3_VOLTAGE_V = "load_l3_voltage_v"
    LOAD_L1_CURRENT_A = "load_l1_current_a"
    LOAD_L2_CURRENT_A = "load_l2_current_a"
    LOAD_L3_CURRENT_A = "load_l3_current_a"
    LOAD_FREQUENCY_HZ = "load_frequency_hz"
    
    # Three-phase Grid data
    GRID_L1_POWER_W = "grid_l1_power_w"
    GRID_L2_POWER_W = "grid_l2_power_w"
    GRID_L3_POWER_W = "grid_l3_power_w"
    GRID_L1_VOLTAGE_V = "grid_l1_voltage_v"
    GRID_L2_VOLTAGE_V = "grid_l2_voltage_v"
    GRID_L3_VOLTAGE_V = "grid_l3_voltage_v"
    GRID_L1_CURRENT_A = "grid_l1_current_a"
    GRID_L2_CURRENT_A = "grid_l2_current_a"
    GRID_L3_CURRENT_A = "grid_l3_current_a"
    GRID_FREQUENCY_HZ = "grid_frequency_hz"
    GRID_LINE_VOLTAGE_AB_V = "grid_line_voltage_ab_v"
    GRID_LINE_VOLTAGE_BC_V = "grid_line_voltage_bc_v"
    GRID_LINE_VOLTAGE_CA_V = "grid_line_voltage_ca_v"
    
    # Battery data
    BATT_SOC_PCT = "batt_soc_pct"
    BATT_VOLTAGE_V = "batt_voltage_v"
    BATT_CURRENT_A = "batt_current_a"
    BATT_TEMP_C = "batt_temp_c"
    
    # Inverter data
    INVERTER_MODE = "inverter_mode"
    INVERTER_TEMP_C = "inverter_temp_c"
    ERROR_CODE = "error_code"
    
    # Device info
    DEVICE_MODEL = "device_model"
    DEVICE_SERIAL_NUMBER = "device_serial_number"
    RATED_POWER_W = "rated_power_w"
    
    # Energy totals (kWh)
    TODAY_ENERGY = "today_energy"
    TOTAL_ENERGY = "total_energy"
    TODAY_LOAD_ENERGY = "today_load_energy"
    TODAY_IMPORT_ENERGY = "today_import_energy"
    TODAY_EXPORT_ENERGY = "today_export_energy"
    TODAY_BATTERY_CHARGE_ENERGY = "today_battery_charge_energy"
    TODAY_BATTERY_DISCHARGE_ENERGY = "today_battery_discharge_energy"
    TODAY_PEAK_POWER = "today_peak_power"
    
    # Configuration
    OFF_GRID_MODE = "off_grid_mode"
    
    # All standard fields as a set for validation
    ALL_FIELDS = {
        TS, PV_POWER_W, PV1_POWER_W, PV2_POWER_W, PV3_POWER_W, PV4_POWER_W,
        LOAD_POWER_W, GRID_POWER_W, BATT_POWER_W,
        LOAD_L1_POWER_W, LOAD_L2_POWER_W, LOAD_L3_POWER_W,
        LOAD_L1_VOLTAGE_V, LOAD_L2_VOLTAGE_V, LOAD_L3_VOLTAGE_V,
        LOAD_L1_CURRENT_A, LOAD_L2_CURRENT_A, LOAD_L3_CURRENT_A,
        LOAD_FREQUENCY_HZ,
        GRID_L1_POWER_W, GRID_L2_POWER_W, GRID_L3_POWER_W,
        GRID_L1_VOLTAGE_V, GRID_L2_VOLTAGE_V, GRID_L3_VOLTAGE_V,
        GRID_L1_CURRENT_A, GRID_L2_CURRENT_A, GRID_L3_CURRENT_A,
        GRID_FREQUENCY_HZ,
        GRID_LINE_VOLTAGE_AB_V, GRID_LINE_VOLTAGE_BC_V, GRID_LINE_VOLTAGE_CA_V,
        BATT_SOC_PCT, BATT_VOLTAGE_V, BATT_CURRENT_A, BATT_TEMP_C,
        INVERTER_MODE, INVERTER_TEMP_C, ERROR_CODE,
        DEVICE_MODEL, DEVICE_SERIAL_NUMBER, RATED_POWER_W,
        TODAY_ENERGY, TOTAL_ENERGY, TODAY_LOAD_ENERGY,
        TODAY_IMPORT_ENERGY, TODAY_EXPORT_ENERGY,
        TODAY_BATTERY_CHARGE_ENERGY, TODAY_BATTERY_DISCHARGE_ENERGY,
        TODAY_PEAK_POWER, OFF_GRID_MODE
    }


class TelemetryMapper:
    """
    Maps device-specific register names to standardized field names.
    
    Uses register map JSON files to determine mappings. Each register in the
    JSON can have a "standard_id" field that maps to a standardized field name.
    If "standard_id" is not provided, the register "id" is used as-is.
    
    This ensures consistent field names across all devices for:
    - Smart scheduler
    - API server
    - Home Assistant publishing
    """
    
    def __init__(self, register_map: List[Dict[str, Any]]):
        """
        Initialize mapper with a register map.
        
        Args:
            register_map: List of register definitions from JSON file
        """
        self.register_map = register_map
        self.device_to_standard: Dict[str, str] = {}
        self.standard_to_device: Dict[str, List[str]] = {}
        
        # Build mapping dictionaries
        self._build_mappings()
    
    def _build_mappings(self):
        """Build bidirectional mapping dictionaries from register map."""
        for reg in self.register_map:
            device_id = reg.get("id")
            if not device_id:
                continue
            
            # Get standard field name (use standard_id if provided, otherwise use id)
            standard_id = reg.get("standard_id") or device_id
            
            # Map device-specific ID to standard ID
            self.device_to_standard[device_id] = standard_id
            
            # Build reverse mapping (standard -> list of device IDs)
            if standard_id not in self.standard_to_device:
                self.standard_to_device[standard_id] = []
            if device_id not in self.standard_to_device[standard_id]:
                self.standard_to_device[standard_id].append(device_id)
        
        log.debug(f"Built telemetry mappings: {len(self.device_to_standard)} device fields -> {len(self.standard_to_device)} standard fields")
    
    def map_to_standard(self, device_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert device-specific telemetry data to standardized format.
        
        Args:
            device_data: Dictionary with device-specific field names
            
        Returns:
            Dictionary with standardized field names
        """
        standardized: Dict[str, Any] = {}
        
        # Map all device-specific fields to standard fields
        for device_key, value in device_data.items():
            standard_key = self.device_to_standard.get(device_key, device_key)
            standardized[standard_key] = value
        
        # Also preserve original device data in 'extra' for backward compatibility
        if "extra" not in standardized:
            standardized["extra"] = {}
        standardized["extra"].update(device_data)
        
        return standardized
    
    def get_standard_field(self, device_field: str) -> str:
        """
        Get standardized field name for a device-specific field.
        
        Args:
            device_field: Device-specific field name
            
        Returns:
            Standardized field name
        """
        return self.device_to_standard.get(device_field, device_field)
    
    def get_device_fields(self, standard_field: str) -> List[str]:
        """
        Get all device-specific field names that map to a standard field.
        
        Args:
            standard_field: Standardized field name
            
        Returns:
            List of device-specific field names
        """
        return self.standard_to_device.get(standard_field, [])
    
    def get_all_standard_fields(self) -> List[str]:
        """Get list of all standardized field names."""
        return list(self.standard_to_device.keys())
    
    def validate_mapping(self, standard_field: str) -> bool:
        """
        Validate that a standard field name is recognized.
        
        Args:
            standard_field: Standardized field name to validate
            
        Returns:
            True if field is recognized, False otherwise
        """
        return standard_field in StandardFields.ALL_FIELDS or standard_field in self.standard_to_device


def create_mapper_from_registers(register_map: List[Dict[str, Any]]) -> TelemetryMapper:
    """
    Create a TelemetryMapper from a register map.
    
    Args:
        register_map: List of register definitions
        
    Returns:
        TelemetryMapper instance
    """
    return TelemetryMapper(register_map)


def map_telemetry_to_standard(
    device_data: Dict[str, Any],
    register_map: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Convenience function to map device telemetry to standard format.
    
    Args:
        device_data: Device-specific telemetry data
        register_map: Register map JSON data
        
    Returns:
        Standardized telemetry data
    """
    mapper = TelemetryMapper(register_map)
    return mapper.map_to_standard(device_data)

