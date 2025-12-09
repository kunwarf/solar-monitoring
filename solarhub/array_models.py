"""
Domain models for Array, BatteryPack, and related concepts.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class BatteryUnitConfig(BaseModel):
    """Configuration for a single battery unit within a pack."""
    id: str
    serial: Optional[str] = None


class BatteryPackConfig(BaseModel):
    """Configuration for a battery pack."""
    id: str
    name: Optional[str] = None
    chemistry: str = "LFP"  # LFP, NMC, etc.
    nominal_kwh: float = Field(ge=0.1, description="Nominal capacity in kWh")
    max_charge_kw: float = Field(ge=0.1, description="Maximum charge power in kW")
    max_discharge_kw: float = Field(ge=0.1, description="Maximum discharge power in kW")
    units: List[BatteryUnitConfig] = Field(default_factory=list, description="Battery units in this pack")


class BatteryPackAttachment(BaseModel):
    """Time-bounded attachment of a battery pack to an array."""
    pack_id: str
    array_id: str
    attached_since: str  # ISO 8601 timestamp
    detached_at: Optional[str] = None  # ISO 8601 timestamp, None = active


class ArraySchedulerConfig(BaseModel):
    """Per-array scheduler configuration (overrides global if provided)."""
    enabled: Optional[bool] = None  # None = inherit from global
    policy: Optional[Dict[str, Any]] = None  # Per-array policy overrides
    tou_windows: Optional[List[Dict[str, Any]]] = None  # Per-array TOU windows


class ArrayConfig(BaseModel):
    """Configuration for a solar array (logical group of inverters)."""
    id: str
    name: Optional[str] = None
    inverter_ids: List[str] = Field(default_factory=list, description="Inverter IDs in this array")
    scheduler: Optional[ArraySchedulerConfig] = None  # Optional per-array scheduler config


class Array(BaseModel):
    """Runtime representation of an array."""
    id: str
    name: Optional[str] = None
    inverter_ids: List[str] = []
    attached_pack_ids: List[str] = []  # Currently attached battery packs
    scheduler_config: Optional[ArraySchedulerConfig] = None


class BatteryPack(BaseModel):
    """Runtime representation of a battery pack."""
    id: str
    name: Optional[str] = None
    chemistry: str
    nominal_kwh: float
    max_charge_kw: float
    max_discharge_kw: float
    unit_ids: List[str] = []
    attached_array_id: Optional[str] = None  # Currently attached array (if any)


class ArrayTelemetry(BaseModel):
    """Aggregated telemetry for an array."""
    array_id: str
    ts: str
    pv_power_w: Optional[int] = None
    load_power_w: Optional[int] = None
    grid_power_w: Optional[int] = None
    batt_power_w: Optional[int] = None
    batt_soc_pct: Optional[float] = None  # Energy-weighted mean across attached packs
    batt_voltage_v: Optional[float] = None
    batt_current_a: Optional[float] = None
    # Per-inverter breakdown
    inverters: List[Dict[str, Any]] = Field(default_factory=list)
    # Per-pack breakdown
    packs: List[Dict[str, Any]] = Field(default_factory=list)
    # Metadata (aliased to _metadata in JSON output for backward compatibility)
    metadata: Dict[str, Any] = Field(default_factory=dict, alias="_metadata", serialization_alias="_metadata")
    
    model_config = {
        "populate_by_name": True,  # Allow both 'metadata' and '_metadata' in input
    }


class BatteryPackTelemetry(BaseModel):
    """Telemetry for a battery pack."""
    pack_id: str
    array_id: Optional[str] = None  # Attached array
    ts: str
    soc_pct: Optional[float] = None
    voltage_v: Optional[float] = None
    current_a: Optional[float] = None
    power_w: Optional[float] = None
    temperature_c: Optional[float] = None
    # Per-unit breakdown
    units: List[Dict[str, Any]] = Field(default_factory=list)
    # Metadata (aliased to _metadata in JSON output for backward compatibility)
    metadata: Dict[str, Any] = Field(default_factory=dict, alias="_metadata", serialization_alias="_metadata")
    
    model_config = {
        "populate_by_name": True,  # Allow both 'metadata' and '_metadata' in input
    }


class BatteryBankArray(BaseModel):
    """Runtime representation of a battery bank array (groups multiple battery banks)."""
    id: str
    name: Optional[str] = None
    battery_bank_ids: List[str] = []  # Battery bank IDs in this array
    attached_inverter_array_id: Optional[str] = None  # Currently attached inverter array (1:1 relationship)


class HomeTelemetry(BaseModel):
    """Aggregated telemetry for the home (top-level aggregation)."""
    home_id: str = "home"
    ts: str
    # Aggregated array data
    total_pv_power_w: Optional[int] = None
    total_load_power_w: Optional[int] = None
    total_grid_power_w: Optional[int] = None
    total_batt_power_w: Optional[int] = None
    avg_batt_soc_pct: Optional[float] = None  # Energy-weighted mean across all arrays
    # Per-array breakdown
    arrays: List[Dict[str, Any]] = Field(default_factory=list)
    # Home-level meters (attached to "home")
    meters: List[Dict[str, Any]] = Field(default_factory=list)
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, alias="_metadata", serialization_alias="_metadata")
    
    model_config = {
        "populate_by_name": True,
    }
