from typing import Optional, Dict, Any, List
from pydantic import BaseModel

class Telemetry(BaseModel):
    ts: str
    grid_power_w: Optional[int] = None
    pv_power_w: Optional[int] = None
    load_power_w: Optional[int] = None
    batt_soc_pct: Optional[float] = None
    batt_voltage_v: Optional[float] = None
    batt_current_a: Optional[float] = None
    batt_power_w: Optional[float] = None  # Calculated as voltage * current
    inverter_temp_c: Optional[float] = None
    grid_import_wh: Optional[int] = None
    grid_export_wh: Optional[int] = None
    # Additional energy fields
    battery_daily_charge_energy: Optional[float] = None  # kWh
    battery_daily_discharge_energy: Optional[float] = None  # kWh
    daily_energy_to_eps: Optional[float] = None  # kWh
    # Array support
    array_id: Optional[str] = None  # Array this inverter belongs to
    extra: Optional[Dict[str, Any]] = None


class BatteryCell(BaseModel):
    power: int  # battery index (1..N)
    cell: int   # cell index (1..M)
    voltage: Optional[float] = None
    current: Optional[float] = None
    temperature: Optional[float] = None
    basic_st: Optional[str] = None
    volt_st: Optional[str] = None
    curr_st: Optional[str] = None
    temp_st: Optional[str] = None
    soc: Optional[float] = None
    coulomb: Optional[float] = None  # Ah

class BatteryUnit(BaseModel):
    power: int
    voltage: Optional[float] = None
    current: Optional[float] = None
    temperature: Optional[float] = None
    soc: Optional[float] = None
    soh: Optional[float] = None  # State of Health percentage
    cycles: Optional[int] = None  # Cycle count
    basic_st: Optional[str] = None
    volt_st: Optional[str] = None
    current_st: Optional[str] = None
    temp_st: Optional[str] = None
    soh_st: Optional[str] = None
    coul_st: Optional[str] = None
    heater_st: Optional[str] = None
    bat_events: Optional[int] = None
    power_events: Optional[int] = None
    sys_events: Optional[int] = None

class BatteryBankTelemetry(BaseModel):
    ts: str
    id: str
    batteries_count: int
    cells_per_battery: int
    voltage: Optional[float] = None
    current: Optional[float] = None
    temperature: Optional[float] = None
    soc: Optional[float] = None
    devices: List[BatteryUnit] = []
    cells_data: Optional[List[Dict[str, Any]]] = None  # per-battery stats + cells
    extra: Optional[Dict[str, Any]] = None


class MeterTelemetry(BaseModel):
    """Telemetry model for energy meters (grid meters, consumption meters, etc.)"""
    ts: str
    id: str
    # Grid/Energy meter data
    grid_power_w: Optional[int] = None  # Positive = import, negative = export
    grid_voltage_v: Optional[float] = None
    grid_current_a: Optional[float] = None
    grid_frequency_hz: Optional[float] = None
    grid_import_wh: Optional[int] = None  # Daily import energy
    grid_export_wh: Optional[int] = None  # Daily export energy
    energy_kwh: Optional[float] = None  # Total cumulative energy
    power_factor: Optional[float] = None
    # Phase-specific data (for three-phase meters)
    voltage_phase_a: Optional[float] = None
    voltage_phase_b: Optional[float] = None
    voltage_phase_c: Optional[float] = None
    current_phase_a: Optional[float] = None
    current_phase_b: Optional[float] = None
    current_phase_c: Optional[float] = None
    power_phase_a: Optional[int] = None
    power_phase_b: Optional[int] = None
    power_phase_c: Optional[int] = None
    # Array support
    array_id: Optional[str] = None  # Array this meter is associated with
    extra: Optional[Dict[str, Any]] = None
