from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, model_validator
from datetime import time

class MqttConfig(BaseModel):
    host: str
    port: int = 1883
    username: Optional[str] = None
    password: Optional[str] = None
    base_topic: str = "solar/fleet"
    client_id: str = "solar-hub"
    ha_discovery: bool = False

class PollingConfig(BaseModel):
    interval_secs: float = Field(ge=0.5, default=2.0)
    timeout_ms: int = 1500
    concurrent: int = 5

class SafetyLimits(BaseModel):
    max_batt_voltage_v: float = 60.0
    min_batt_voltage_v: float = 44.0
    max_charge_a: int = 120
    max_discharge_a: int = 120
    max_inverter_temp_c: float = 85.0

class InverterAdapterConfig(BaseModel):
    type: str  # "senergy" | "powdrive" | "iammeter"
    unit_id: int = 1
    transport: str = "rtu"  # "tcp" | "rtu"
    host: Optional[str] = None
    port: int = 502
    serial_port: Optional[str] = None
    baudrate: int = 9600
    parity: str = "N"
    stopbits: int = 1
    bytesize: int = 8
    register_map_file: Optional[str] = None
    # IAMMeter-specific register addresses (optional, defaults provided)
    voltage_register: Optional[int] = None
    voltage_scale: Optional[int] = None
    current_register: Optional[int] = None
    current_scale: Optional[int] = None
    power_register: Optional[int] = None
    energy_register: Optional[int] = None
    energy_scale: Optional[int] = None
    frequency_register: Optional[int] = None
    frequency_scale: Optional[int] = None
    power_factor_register: Optional[int] = None
    power_factor_scale: Optional[int] = None
    # IAMMeter-specific: Prefer legacy registers (0-36) over extended registers (72-120)
    # If True, reads legacy registers first, then falls back to extended if legacy values are zero
    # If False (default), reads extended registers first, then falls back to legacy if extended values are zero
    prefer_legacy_registers: bool = False

class BatteryAdapterConfig(BaseModel):
    type: str  # "pytes", "jkbms_passive", "jkbms_ble", etc.
    serial_port: Optional[str] = None
    baudrate: int = 115200
    parity: str = "N"
    stopbits: int = 1
    bytesize: int = 8
    transport: Optional[str] = None  # "rtu" for Modbus RTU (JKBMS), None for serial console (Pytes)
    timeout: Optional[float] = None  # Communication timeout in seconds
    # JKBMS protocol selection: "modbus" (Modbus RTU) or "custom" (0x4E 0x57 protocol) or None (auto-detect)
    jkbms_protocol: Optional[str] = None  # "modbus" | "custom" | None (auto-detect)
    # JKBMS custom protocol: terminal ID (4 bytes, default 0x00000001)
    jkbms_terminal_id: Optional[int] = None  # Default: 0x00000001
    # Bank topology
    batteries: int = 1  # number of batteries in the bank (aka powers)
    cells_per_battery: int = 16
    dev_name: str = "battery_bank"
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    # JKBMS-specific: Modbus addresses for each battery pack (1-15)
    battery_addresses: Optional[List[int]] = None  # If None, defaults to [1, 2, ..., batteries]
    # JKBMS listening mode: If True, listens to broadcasts from master BMS (address 0) instead of querying individually
    bms_broadcasting: bool = False  # True = listening mode, False = master mode (default)
    # JKBMS fast polling: If True, reduces delays for high-frequency polling (5-10 Hz, ~0.03s per read)
    jkbms_fast_polling: bool = False  # True = optimized for speed, False = standard delays (default)
    # Bluetooth configuration (for jkbms_ble type)
    bt_address: Optional[str] = None  # Single Bluetooth MAC address (e.g., "CC:44:8C:F7:AD:BB") - for single battery
    bt_addresses: Optional[List[str]] = None  # List of Bluetooth MAC addresses for multiple batteries
    bt_adapter: Optional[str] = None  # Bluetooth adapter name (e.g., "hci0", "hci1")
    bt_pin: Optional[str] = None  # Bluetooth pairing PIN (if required, applies to all batteries)
    bt_keep_alive: bool = True  # Keep Bluetooth connection alive (don't disconnect between reads)
    bt_timeout: float = 8.0  # Bluetooth connection timeout in seconds
    # TCP/IP configuration (for jkbms_tcpip type)
    host: Optional[str] = None  # RS485 gateway IP address or hostname (e.g., "192.168.1.100")
    port: Optional[int] = None  # RS485 gateway TCP port (e.g., 8899)
    # Connection type for jkbms_tcpip: "tcpip" (TCP/IP gateway) or "rtu" (Modbus RTU serial)
    connection_type: Optional[str] = None  # "tcpip" | "rtu" | None (auto-detect: tcpip if host/port set, rtu if serial_port set)
    poll_timeout: Optional[float] = None  # How long to listen per poll in seconds (default: 2.0)

class BatteryAdapterConfigWithPriority(BaseModel):
    """Battery adapter configuration with priority for failover support."""
    adapter: BatteryAdapterConfig
    priority: int = 1  # Lower number = higher priority (1 = primary, 2 = secondary, etc.)
    enabled: bool = True  # Whether this adapter is enabled

class BatteryBankConfig(BaseModel):
    id: str = "battery"
    name: Optional[str] = None
    adapter: Optional[BatteryAdapterConfig] = None  # Single adapter (backward compatibility)
    adapters: Optional[List[BatteryAdapterConfigWithPriority]] = None  # Multiple adapters with failover support
    
    @model_validator(mode='after')
    def validate_adapters(self):
        """Ensure either adapter or adapters is provided."""
        if not self.adapter and not self.adapters:
            raise ValueError("Either 'adapter' or 'adapters' must be provided in BatteryBankConfig")
        if self.adapter and self.adapters:
            raise ValueError("Cannot specify both 'adapter' and 'adapters' - use 'adapters' for failover support")
        return self

class MeterAdapterConfig(BaseModel):
    """Configuration for energy meter adapters (IAMMeter, etc.)"""
    type: str  # "iammeter", etc.
    unit_id: int = 1
    transport: str = "tcp"  # "tcp" | "rtu"
    host: Optional[str] = None  # Required for TCP
    port: int = 502  # TCP port
    serial_port: Optional[str] = None  # For RTU
    baudrate: int = 9600  # For RTU
    parity: str = "N"
    stopbits: int = 1
    bytesize: int = 8
    register_map_file: Optional[str] = None
    # IAMMeter-specific register addresses (optional, defaults provided)
    voltage_register: Optional[int] = None
    voltage_scale: Optional[int] = None
    current_register: Optional[int] = None
    current_scale: Optional[int] = None
    power_register: Optional[int] = None
    energy_register: Optional[int] = None
    energy_scale: Optional[int] = None
    frequency_register: Optional[int] = None
    frequency_scale: Optional[int] = None
    power_factor_register: Optional[int] = None
    power_factor_scale: Optional[int] = None
    # IAMMeter-specific: Prefer legacy registers (0-36) over extended registers (72-120)
    prefer_legacy_registers: bool = False

class MeterConfig(BaseModel):
    """Configuration for an energy meter"""
    id: str
    name: Optional[str] = None
    array_id: Optional[str] = None  # Array this meter is associated with (or "home" for home-level meter)
    adapter: MeterAdapterConfig

class SolarArrayParams(BaseModel):
    pv_dc_kw: float = 10.0
    tilt_deg: float = 20.0
    azimuth_deg: float = 180.0
    perf_ratio: float = 0.8
    albedo: float = 0.2

class InverterConfig(BaseModel):
    id: str
    name: Optional[str] = None
    array_id: Optional[str] = Field(default=None, description="Array this inverter belongs to (will be set by migration if missing)")
    adapter: InverterAdapterConfig
    safety: SafetyLimits = SafetyLimits()
    solar: List[SolarArrayParams] = [SolarArrayParams()]
    # Inverter type metadata
    phase_type: Optional[str] = None  # "single" | "three" | None (auto-detect from register)
    # If None, will be auto-detected from inverter_type register or phase data
    
    @model_validator(mode='before')
    @classmethod
    def ensure_array_id(cls, data: Any) -> Any:
        """Ensure array_id is present (set to None if missing)."""
        if isinstance(data, dict) and 'array_id' not in data:
            data = data.copy()
            data['array_id'] = None
        return data

class ForecastConfig(BaseModel):
    enabled: bool = False
    lat: float = 0.0
    lon: float = 0.0
    provider: str = "naive"  # naive | openmeteo | weatherapi | simple
    api_key: Optional[str] = None  # Generic API key (deprecated, use specific keys below)
    weatherapi_key: Optional[str] = None  # WeatherAPI.com API key
    openweather_key: Optional[str] = None  # OpenWeatherMap API key
    weatherbit_key: Optional[str] = None  # WeatherBit API key
    pv_dc_kw: float = 10.0
    pv_perf_ratio: float = 0.8
    tilt_deg: float = 20.0
    azimuth_deg: float = 180.0
    albedo: float = 0.2
    batt_capacity_kwh: float = 20.0
    load_history_days: int = 14

class TariffConfig(BaseModel):
    """Configuration for a single tariff window."""
    kind: str = Field(description="Tariff type: cheap, normal, peak")
    start: str = Field(description="Start time in HH:MM format")
    end: str = Field(description="End time in HH:MM format")
    price: float = Field(ge=0.1, le=10.0, description="Relative price (higher = more expensive)")
    allow_grid_charge: bool = Field(default=True, description="Allow grid charging during this window")
    allow_discharge: bool = Field(default=True, description="Allow battery discharge during this window")
    priority: int = Field(ge=1, le=10, default=1, description="Priority order (1=highest)")
    peak_shaving_enabled: bool = Field(default=False, description="Enable peak shaving during this window")

class PolicyConfig(BaseModel):
    enabled: bool = False
    target_full_before_sunset: bool = True
    overnight_min_soc_pct: int = 30
    blackout_reserve_soc_pct: int = 30
    conserve_on_bad_tomorrow: bool = True
    bad_sun_threshold_kwh: float = 0.3
    
    # Smart scheduler settings
    smart_tick_interval_secs: float = Field(ge=30, le=3600, default=1500)  # 30 seconds to 1 hour, default 5 minutes
    
    # Battery optimization settings
    dynamic_soc_enabled: bool = False
    min_self_sufficiency_pct: float = 85.0
    target_self_sufficiency_pct: float = 95.0
    max_grid_usage_kwh_per_day: float = 3.0
    emergency_reserve_hours: float = 6.0
    
    # Load and grid settings
    load_fallback_kw: float = 1.0
    max_grid_charge_w: int = 2000
    
    # Dual SOC threshold settings for grid availability
    emergency_soc_threshold_grid_available_pct: int = 45
    emergency_soc_threshold_grid_unavailable_pct: int = 30
    critical_soc_threshold_grid_available_pct: int = 35
    critical_soc_threshold_grid_unavailable_pct: int = 20
    off_grid_startup_soc_pct: int = 30
    
    # Battery power and SOC limits
    max_charge_power_w: float = Field(ge=100, le=10000, default=5000)  # Max battery charge power in watts
    max_discharge_power_w: float = Field(ge=100, le=10000, default=5000)  # Max battery discharge power in watts
    max_battery_soc_pct: float = Field(ge=50, le=100, default=100)  # Max battery SOC for charging
    
    # Tariff configuration
    tariffs: List[TariffConfig] = Field(default_factory=list, description="Tariff windows for smart scheduling")
    
    # Mode switching configuration
    primary_mode: str = Field(default="self_use", description="Primary mode: self_use or time_based")
    enable_auto_mode_switching: bool = Field(default=True, description="Enable automatic mode switching based on conditions")
    solar_target_threshold_pct: float = Field(ge=70, le=100, default=85, description="Solar target achievement threshold for mode switching")
    poor_weather_threshold_kwh: float = Field(ge=0.1, le=5.0, default=1.0, description="Poor weather threshold for discharge control")
    close_to_target_threshold_pct: float = Field(ge=1, le=20, default=5, description="SOC threshold for considering battery close to target (use self-use mode)")

class InverterSplitConfig(BaseModel):
    """Configuration for splitting array power targets across inverters."""
    mode: str = Field(default="headroom", description="Split mode: 'headroom' | 'equal' | 'rated'")
    min_w_per_inverter: int = Field(default=50, ge=0, description="Minimum power per inverter (below this -> 0)")
    step_w: int = Field(default=50, ge=1, description="Rounding step per command")
    fairness: Optional[str] = Field(default=None, description="Fairness mode: None | 'round_robin' | 'aging'")

class ArraySchedulerConfig(BaseModel):
    """Per-array scheduler configuration (overrides global if provided)."""
    enabled: Optional[bool] = None  # None = inherit from global
    policy: Optional[Dict[str, Any]] = None  # Per-array policy overrides (partial PolicyConfig)
    tou_windows: Optional[List[Dict[str, Any]]] = None  # Per-array TOU windows
    inverter_split: Optional[InverterSplitConfig] = None  # Per-inverter power splitting config


class ArrayConfig(BaseModel):
    """Configuration for a solar array (logical group of inverters)."""
    id: str
    name: Optional[str] = None
    inverter_ids: List[str] = Field(default_factory=list, description="Inverter IDs in this array")
    scheduler: Optional[ArraySchedulerConfig] = None  # Optional per-array scheduler config


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


class BatteryBankArrayConfig(BaseModel):
    """Configuration for an array of battery banks (groups multiple battery banks)."""
    id: str
    name: Optional[str] = None
    battery_bank_ids: List[str] = Field(default_factory=list, description="Battery bank IDs in this array")


class BatteryBankArrayAttachment(BaseModel):
    """Attachment of a battery bank array to an inverter array (1:1 relationship)."""
    battery_bank_array_id: str
    inverter_array_id: str
    attached_since: str  # ISO 8601 timestamp
    detached_at: Optional[str] = None  # ISO 8601 timestamp, None = active


class HomeConfig(BaseModel):
    """Top-level home configuration."""
    id: str = "home"
    name: Optional[str] = None
    description: Optional[str] = None


class SmartConfig(BaseModel):
    forecast: ForecastConfig = ForecastConfig()
    policy: PolicyConfig = PolicyConfig()

class LoggingConfig(BaseModel):
    level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    ha_debug: bool = False  # Enable debug logging for Home Assistant messages


class BillingPeakWindow(BaseModel):
    """Time-of-use peak window definition for billing (HH:MM 24h format)."""
    start: str = Field(description="Start time in HH:MM format")
    end: str = Field(description="End time in HH:MM format")


class BillingForecastConfig(BaseModel):
    """Defaults and tuning parameters for billing/energy forecasting."""
    default_method: str = Field(default="trend", description="trend | seasonal")
    lookback_months: int = Field(default=12, ge=1, le=60)
    default_months_ahead: int = Field(default=1, ge=1, le=12)
    low_confidence_threshold: float = Field(default=0.5, ge=0.0, le=1.0)


class BillingConfig(BaseModel):
    """Configuration for billing & capacity analysis (separate from smart scheduler)."""
    currency: str = Field(default="PKR", description="Display currency for billing outputs")
    anchor_day: int = Field(default=15, ge=1, le=28, description="Billing anchor day of month")

    # Energy prices
    price_offpeak_import: float = Field(default=40.0, ge=0.0, description="Price per kWh of net off-peak import")
    price_peak_import: float = Field(default=47.0, ge=0.0, description="Price per kWh of net peak import")

    # Settlement prices for credits at end of 3-month cycle
    price_offpeak_settlement: float = Field(default=40.0, ge=0.0,
                                            description="Settlement price per kWh for off-peak export credits")
    price_peak_settlement: float = Field(default=40.0, ge=0.0,
                                         description="Settlement price per kWh for peak export credits")

    # Fixed monthly charges
    fixed_charge_per_billing_month: float = Field(default=0.0, ge=0.0,
                                                  description="Fixed amount added each billing month")
    fixed_proration: str = Field(default="none", description="Fixed charge proration: 'none' | 'linear_by_day'")

    # Peak time-of-use windows
    peak_windows: List[BillingPeakWindow] = Field(
        default_factory=list,
        description="List of peak time windows; off-peak is complement"
    )

    # Forecast defaults for bill/capacity forecasting
    forecast: BillingForecastConfig = BillingForecastConfig()


class DiscoveryConfig(BaseModel):
    """Configuration for automatic USB device discovery."""
    enabled: bool = Field(default=True, description="Enable automatic device discovery")
    scan_on_startup: bool = Field(default=True, description="Run discovery scan on application startup")
    scan_interval_minutes: int = Field(default=60, ge=1, description="Periodic re-scan interval in minutes")
    priority_order: List[str] = Field(
        default_factory=lambda: ["pytes", "senergy", "powdrive", "iammeter"],
        description="Device type priority order for discovery"
    )
    identification_timeout: float = Field(default=2.0, ge=0.5, le=10.0, description="Timeout for device identification in seconds")
    max_retries: int = Field(default=2, ge=1, le=5, description="Maximum retries per device type during discovery")
    initial_retry_minutes: int = Field(default=15, ge=1, description="Initial retry delay for failed devices in minutes")
    max_retry_minutes: int = Field(default=120, ge=15, description="Maximum retry delay in minutes")
    backoff_multiplier: float = Field(default=1.5, ge=1.0, le=3.0, description="Exponential backoff multiplier")
    max_failures: int = Field(default=10, ge=1, description="Maximum consecutive failures before permanent disable")


class HubConfig(BaseModel):
    timezone: str = "Asia/Karachi"  # System timezone for all operations
    mqtt: MqttConfig
    polling: PollingConfig = PollingConfig()
    
    # Home (top-level container)
    home: Optional[HomeConfig] = None
    
    # Arrays of Inverters (logical groups of inverters)
    arrays: Optional[List[ArrayConfig]] = None  # If None, will create default array for backward compatibility
    inverters: List[InverterConfig]
    
    @model_validator(mode='before')
    @classmethod
    def ensure_inverter_array_ids(cls, data: Any) -> Any:
        """Ensure all inverters have array_id (set to None if missing)."""
        if isinstance(data, dict) and 'inverters' in data:
            inverters = data['inverters']
            if isinstance(inverters, list):
                for inv in inverters:
                    if isinstance(inv, dict) and 'array_id' not in inv:
                        inv['array_id'] = None
        return data
    
    # Battery packs (new concept, replaces battery_bank)
    battery_packs: Optional[List[BatteryPackConfig]] = None
    # Battery pack attachments (time-bounded)
    attachments: Optional[List[BatteryPackAttachment]] = None
    
    # Battery banks (array of individual battery banks with adapters)
    battery_banks: Optional[List[BatteryBankConfig]] = None
    # Arrays of Battery Banks (groups multiple battery banks)
    battery_bank_arrays: Optional[List[BatteryBankArrayConfig]] = None
    # Battery bank array attachments (1:1 with inverter arrays)
    battery_bank_array_attachments: Optional[List[BatteryBankArrayAttachment]] = None
    
    # Battery bank (optional, separate adapter) - DEPRECATED, use battery_banks
    # Kept for backward compatibility - will be migrated to battery_banks if present
    battery_bank: Optional[BatteryBankConfig] = None
    
    # Source of battery metrics for UI/schedulers: "inverter" or "battery_adapter"
    battery_data_source: str = "inverter"
    # Energy meters (grid meters, consumption meters, etc.)
    # Can be attached to an array_id or "home" for home-level aggregation
    meters: Optional[List[MeterConfig]] = None
    smart: SmartConfig = SmartConfig()
    logging: LoggingConfig = LoggingConfig()
    # Device discovery configuration
    discovery: DiscoveryConfig = DiscoveryConfig()
    # Billing & capacity analysis configuration
    billing: BillingConfig = BillingConfig()
