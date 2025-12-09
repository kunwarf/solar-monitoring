"""
Inverter Metadata Detection and Management

This module provides utilities to detect and manage inverter metadata:
- Single vs multiple inverters
- Single phase vs three phase
- Inverter type from register data
"""

from typing import Dict, Any, Optional, List
import logging

log = logging.getLogger(__name__)


class InverterMetadata:
    """Inverter metadata including phase type and inverter count."""
    
    def __init__(self, phase_type: Optional[str] = None, inverter_count: int = 1):
        """
        Initialize inverter metadata.
        
        Args:
            phase_type: "single" or "three" or None (auto-detect)
            inverter_count: Number of inverters in the system
        """
        self.phase_type = phase_type
        self.inverter_count = inverter_count
    
    @staticmethod
    def detect_phase_type_from_telemetry(telemetry: Dict[str, Any]) -> Optional[str]:
        """
        Detect phase type from telemetry data.
        
        Checks for:
        1. Phase-specific data (load_l1_power_w, grid_l1_power_w, etc.)
        2. inverter_type register value (5 = "3 Phase Hybrid Inverter")
        3. grid_type_setting register value
        
        Args:
            telemetry: Telemetry data dict (from extra field)
            
        Returns:
            "single", "three", or None if cannot be determined
        """
        extra = telemetry.get("extra", {}) or {}
        
        # Check for phase-specific data (most reliable)
        has_phase_data = any(
            extra.get(f"load_l{i}_power_w") is not None or
            extra.get(f"grid_l{i}_power_w") is not None or
            extra.get(f"load_l{i}_voltage_v") is not None or
            extra.get(f"grid_l{i}_voltage_v") is not None
            for i in [1, 2, 3]
        )
        
        if has_phase_data:
            log.debug("Detected three-phase inverter from phase-specific data")
            return "three"
        
        # Check inverter_type register
        inverter_type = extra.get("inverter_type")
        if inverter_type is not None:
            # Powdrive: 5 = "3 Phase Hybrid Inverter"
            if str(inverter_type) == "5" or str(inverter_type).lower() == "3 phase hybrid inverter":
                log.debug(f"Detected three-phase inverter from inverter_type register: {inverter_type}")
                return "three"
            # Other types are typically single phase
            elif str(inverter_type) in ["2", "3", "4"]:
                log.debug(f"Detected single-phase inverter from inverter_type register: {inverter_type}")
                return "single"
        
        # Check grid_type_setting register
        grid_type = extra.get("grid_type_setting")
        if grid_type is not None:
            # 0 = "Three Phase", 1 = "Single-phase"
            if str(grid_type) == "0" or str(grid_type).lower() == "three phase":
                log.debug(f"Detected three-phase inverter from grid_type_setting register: {grid_type}")
                return "three"
            elif str(grid_type) == "1" or str(grid_type).lower() == "single-phase":
                log.debug(f"Detected single-phase inverter from grid_type_setting register: {grid_type}")
                return "single"
        
        log.debug("Could not determine phase type from telemetry data")
        return None
    
    @staticmethod
    def detect_phase_type_from_register(register_value: Any) -> Optional[str]:
        """
        Detect phase type from inverter_type register value.
        
        Args:
            register_value: Value from inverter_type register
            
        Returns:
            "single", "three", or None
        """
        if register_value is None:
            return None
        
        # Powdrive enum: {"2": "Inverter", "3": "Hybrid Inverter", "4": "Micro Inverter", "5": "3 Phase Hybrid Inverter"}
        if str(register_value) == "5" or str(register_value).lower() == "3 phase hybrid inverter":
            return "three"
        elif str(register_value) in ["2", "3", "4"]:
            return "single"
        
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary."""
        return {
            "phase_type": self.phase_type,
            "inverter_count": self.inverter_count,
            "is_three_phase": self.phase_type == "three",
            "is_single_phase": self.phase_type == "single",
            "is_single_inverter": self.inverter_count == 1,
            "is_inverter_array": self.inverter_count > 1,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InverterMetadata":
        """Create metadata from dictionary."""
        return cls(
            phase_type=data.get("phase_type"),
            inverter_count=data.get("inverter_count", 1)
        )


def get_inverter_metadata(
    telemetry: Dict[str, Any],
    config_phase_type: Optional[str] = None,
    inverter_count: int = 1
) -> InverterMetadata:
    """
    Get inverter metadata from telemetry and config.
    
    Priority:
    1. Config phase_type (if specified)
    2. Detected from telemetry data
    3. Default to None (unknown)
    
    Args:
        telemetry: Telemetry data dict
        config_phase_type: Phase type from config (if specified)
        inverter_count: Number of inverters in system
        
    Returns:
        InverterMetadata object
    """
    # Use config phase_type if specified
    if config_phase_type:
        log.debug(f"Using phase_type from config: {config_phase_type}")
        return InverterMetadata(phase_type=config_phase_type, inverter_count=inverter_count)
    
    # Try to detect from telemetry
    detected_phase_type = InverterMetadata.detect_phase_type_from_telemetry(telemetry)
    if detected_phase_type:
        log.debug(f"Detected phase_type from telemetry: {detected_phase_type}")
        return InverterMetadata(phase_type=detected_phase_type, inverter_count=inverter_count)
    
    # Unknown
    log.debug("Phase type unknown (not in config and cannot be detected)")
    return InverterMetadata(phase_type=None, inverter_count=inverter_count)


def should_publish_phase_data(metadata: InverterMetadata) -> bool:
    """
    Determine if phase-specific data should be published.
    
    Args:
        metadata: InverterMetadata object
        
    Returns:
        True if phase-specific data should be published
    """
    return metadata.phase_type == "three"


def get_publishable_fields(
    telemetry: Dict[str, Any],
    metadata: InverterMetadata
) -> Dict[str, Any]:
    """
    Get fields that should be published based on inverter metadata.
    
    For single phase: Only total power, voltage, current
    For three phase: Include phase-specific data (L1, L2, L3)
    
    Args:
        telemetry: Full telemetry data
        metadata: InverterMetadata object
        
    Returns:
        Dictionary with publishable fields
    """
    extra = telemetry.get("extra", {}) or {}
    publishable = {}
    
    # Always include basic fields
    basic_fields = [
        "pv_power_w", "pv1_power_w", "pv2_power_w",
        "load_power_w", "grid_power_w", "batt_power_w",
        "batt_soc_pct", "batt_voltage_v", "batt_current_a",
        "inverter_temp_c", "inverter_mode",
        "today_energy", "today_load_energy", "today_import_energy", "today_export_energy",
    ]
    
    for field in basic_fields:
        if field in telemetry:
            publishable[field] = telemetry[field]
        elif field in extra:
            publishable[field] = extra[field]
    
    # Include phase-specific data for three-phase inverters
    if metadata.phase_type == "three":
        phase_fields = [
            "load_l1_power_w", "load_l2_power_w", "load_l3_power_w",
            "load_l1_voltage_v", "load_l2_voltage_v", "load_l3_voltage_v",
            "load_l1_current_a", "load_l2_current_a", "load_l3_current_a",
            "load_frequency_hz",
            "grid_l1_power_w", "grid_l2_power_w", "grid_l3_power_w",
            "grid_l1_voltage_v", "grid_l2_voltage_v", "grid_l3_voltage_v",
            "grid_l1_current_a", "grid_l2_current_a", "grid_l3_current_a",
            "grid_frequency_hz",
            "grid_line_voltage_ab_v", "grid_line_voltage_bc_v", "grid_line_voltage_ca_v",
        ]
        
        for field in phase_fields:
            if field in extra:
                publishable[field] = extra[field]
    
    # Add metadata
    publishable["_metadata"] = metadata.to_dict()
    
    return publishable

