import asyncio, logging, json, sys, time
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from solarhub.config import HubConfig, InverterConfig
from solarhub.mqtt import Mqtt
from solarhub.adapters.senergy import SenergyAdapter
from solarhub.adapters.powdrive import PowdriveAdapter
from solarhub.adapters.iammeter import IAMMeterAdapter
from solarhub.adapters.base import InverterAdapter, MeterAdapter
from solarhub.adapters.battery_pytes import PytesBatteryAdapter
# from solarhub.adapters.battery_jkbms import JKBMSBatteryAdapter  # Old master mode adapter (not implemented)
from solarhub.adapters.battery_jkbms_passive import JKBMSPassiveAdapter
from solarhub.adapters.battery_jkbms_ble import JKBMSBleAdapter
from solarhub.adapters.battery_jkbms_tcpip import JKBMSTcpipAdapter
from solarhub.adapters.battery_failover import FailoverBatteryAdapter
from solarhub.adapters.command_queue import CommandQueueManager
from solarhub.logging.logger import DataLogger
from solarhub.schedulers.smart import SmartScheduler
from solarhub.ha.discovery import HADiscoveryPublisher
from solarhub.api_server import create_api, start_api_in_background


log = logging.getLogger(__name__)

ADAPTERS = {
    "senergy": SenergyAdapter,
    "powdrive": PowdriveAdapter,
}

BATTERY_ADAPTERS = {
    "pytes": PytesBatteryAdapter,
    # "jkbms": JKBMSBatteryAdapter,  # Old master mode adapter (not implemented)
    "jkbms_passive": JKBMSPassiveAdapter,
    "jkbms_ble": JKBMSBleAdapter,
    "jkbms_tcpip": JKBMSTcpipAdapter,
}

METER_ADAPTERS = {
    "iammeter": IAMMeterAdapter,
}

class InverterRuntime:
    def __init__(self, cfg: InverterConfig, adapter: InverterAdapter):
        self.cfg = cfg
        self.adapter = adapter

class MeterRuntime:
    def __init__(self, cfg, adapter: MeterAdapter):
        self.cfg = cfg
        self.adapter = adapter

class SolarApp:
    """
    App now uses **generic, JSON-driven writes** over MQTT. No hardcoded register addresses.
    Topics:
      - <base>/<inverter_id>/cmd            -> JSON payload with {"action":"write"| "write_many", ...}
      - <base>/<inverter_id>/state          -> telemetry snapshot
      - <base>/<inverter_id>/regs           -> raw decoded register dict
      - <base>/<inverter_id>/cfg_state      -> echo of config/safety
      - <base>/forecast, <base>/plan        -> smart scheduler topics
    """
    def __init__(self, cfg: HubConfig):
        self.cfg = cfg
        self._configure_logging()
        self.mqtt = Mqtt(cfg.mqtt)
        self.inverters: List[InverterRuntime] = []
        # Support for multiple battery banks
        self.battery_adapters: Dict[str, Any] = {}  # bank_id -> BatteryAdapter
        self.battery_last: Dict[str, Any] = {}  # bank_id -> BatteryBankTelemetry
        # Legacy support: single battery_adapter for backward compatibility
        self.battery_adapter = None  # Will point to first adapter if exists
        self.meters: List['MeterRuntime'] = []
        self.meter_last: Dict[str, Any] = {}
        self.smart: Optional[SmartScheduler] = None  # Legacy: single scheduler (deprecated, use smart_schedulers)
        self.smart_schedulers: Dict[str, SmartScheduler] = {}  # Per-array schedulers: array_id -> SmartScheduler
        self.logger = DataLogger()
        self._energy_acc: Dict[str, Dict[str, Any]] = {}
        self.ha = HADiscoveryPublisher(self.mqtt, cfg.mqtt.base_topic, db_path=self.logger.path)
        self.array_last: Dict[str, Any] = {}  # Store array telemetry for home aggregation
        
        # Track polling loop task for background execution
        self._polling_loop_task: Optional[asyncio.Task] = None
        # Suspend/resume control for polling loop
        self._polling_suspended: bool = False
        # Track device connection state for auto-reconnection
        self._devices_connected: bool = False
        # Prevent multiple simultaneous reconnection attempts
        self._reconnecting: bool = False
        # Disconnect/reconnect signaling - these are set by API server, handled by polling loop
        # Using simple boolean flags with lock for thread-safety (events are loop-bound, flags work across loops)
        self._disconnect_requested: bool = False
        self._reconnect_requested: bool = False
        self._reconnect_config: Optional[Dict[str, Any]] = None
        self._connection_lock: Optional[asyncio.Lock] = None
        # Billing scheduler task
        self._billing_scheduler_task: Optional[asyncio.Task] = None
        # Energy calculator hourly task
        self._energy_calculator_task: Optional[asyncio.Task] = None
        
        # Array support
        self._build_runtime_objects(cfg)
        from solarhub.array_aggregator import ArrayAggregator
        from solarhub.system_aggregator import SystemAggregator
        from solarhub.battery_array_aggregator import BatteryArrayAggregator
        self.array_aggregator = ArrayAggregator()
        self.system_aggregator = SystemAggregator()
        self.battery_array_aggregator = BatteryArrayAggregator()
    
    def _build_runtime_objects(self, cfg: HubConfig):
        """Build runtime objects from hierarchy (database-first, config.yaml fallback)."""
        # Initialize configuration manager
        from solarhub.config_manager import ConfigurationManager
        self.config_manager = ConfigurationManager(config_path="config.yaml", db_logger=self.logger)
        
        # Initialize energy calculator
        from solarhub.energy_calculator import EnergyCalculator
        self.energy_calculator = EnergyCalculator(self.logger.path)
        # Store EnergyCalculator class for use in other methods
        self._EnergyCalculator = EnergyCalculator
        
        # Initialize command queue manager
        telemetry_interval = getattr(cfg.polling, 'interval_secs', 10.0)
        self.command_queue = CommandQueueManager(telemetry_polling_interval=telemetry_interval)
        
        # Load hierarchy from database
        try:
            # First validate hierarchy integrity, data migration, and statistics
            from solarhub.hierarchy.validator import validate_and_raise
            validate_and_raise(
                self.logger.path,
                validate_data=True,
                validate_statistics=True,
                statistics_days_back=7  # Check last 7 days for statistics
            )
            log.info("Hierarchy, data migration, and statistics validation passed")
            
            # Then load hierarchy
            from solarhub.hierarchy.loader import HierarchyLoader
            loader = HierarchyLoader(self.logger.path)
            self.hierarchy_systems = loader.load_hierarchy()
            log.info(f"Loaded {len(self.hierarchy_systems)} system(s) from database hierarchy")
            
            # Build runtime objects from hierarchy
            self._build_runtime_from_hierarchy()
            
        except Exception as e:
            log.error(f"Failed to load hierarchy from database: {e}", exc_info=True)
            log.error("CRITICAL: Hierarchy migration failed. Application cannot start.")
            log.error("Please check the database migration logs and fix the issues before restarting.")
            raise RuntimeError(f"Failed to load hierarchy from database: {e}") from e
    
    def _build_runtime_from_hierarchy(self):
        """Build runtime objects (inverters, battery packs, meters) from hierarchy."""
        if not self.hierarchy_systems:
            log.warning("No hierarchy systems loaded, skipping runtime object building")
            return
        
        # Store hierarchy devices for use in init()
        self._hierarchy_inverters: Dict[str, Any] = {}  # inverter_id -> Inverter hierarchy object
        self._hierarchy_battery_packs: Dict[str, Any] = {}  # pack_id -> BatteryPack hierarchy object
        self._hierarchy_meters: Dict[str, Any] = {}  # meter_id -> Meter hierarchy object
        
        # Collect all devices from all systems
        for system_id, system in self.hierarchy_systems.items():
            # Collect inverters
            for inverter_array in system.inverter_arrays:
                for inverter in inverter_array.inverters:
                    self._hierarchy_inverters[inverter.inverter_id] = inverter
                    log.debug(f"Registered hierarchy inverter: {inverter.inverter_id} (array: {inverter.array_id}, system: {system_id})")
            
            # Collect battery packs
            for battery_array in system.battery_arrays:
                for battery_pack in battery_array.battery_packs:
                    self._hierarchy_battery_packs[battery_pack.pack_id] = battery_pack
                    log.debug(f"Registered hierarchy battery pack: {battery_pack.pack_id} (array: {battery_array.battery_array_id}, system: {system_id})")
            
            # Collect meters
            for meter in system.meters:
                self._hierarchy_meters[meter.meter_id] = meter
                log.debug(f"Registered hierarchy meter: {meter.meter_id} (system: {system_id})")
        
        log.info(f"Built runtime objects from hierarchy: {len(self._hierarchy_inverters)} inverters, "
                f"{len(self._hierarchy_battery_packs)} battery packs, {len(self._hierarchy_meters)} meters")
    
    def _adapter_instance_to_inverter_config(self, inverter, adapter_instance) -> InverterConfig:
        """Convert hierarchy Inverter + AdapterInstance to InverterConfig."""
        from solarhub.config import InverterConfig, InverterAdapterConfig, SafetyLimits, SolarArrayParams
        
        # Convert adapter config_json to InverterAdapterConfig
        adapter_config_dict = adapter_instance.config_json.copy()
        adapter_config_dict['type'] = adapter_instance.adapter_type
        adapter_config = InverterAdapterConfig(**adapter_config_dict)
        
        # Create InverterConfig
        inv_config = InverterConfig(
            id=inverter.inverter_id,
            name=inverter.name,
            array_id=inverter.array_id,
            adapter=adapter_config,
            safety=SafetyLimits(),  # Default safety limits
            solar=[SolarArrayParams()],  # Default solar array params
            phase_type=inverter.phase_type
        )
        return inv_config
    
    def _adapter_instances_to_battery_bank_config(self, battery_pack, adapter_instances) -> 'BatteryBankConfig':
        """Convert hierarchy BatteryPack + AdapterInstances to BatteryBankConfig."""
        from solarhub.config import BatteryBankConfig, BatteryAdapterConfig, BatteryAdapterConfigWithPriority
        
        if len(adapter_instances) == 1:
            # Single adapter (backward compatibility)
            adapter_instance = adapter_instances[0]
            adapter_config_dict = adapter_instance.config_json.copy()
            adapter_config_dict['type'] = adapter_instance.adapter_type
            adapter_config = BatteryAdapterConfig(**adapter_config_dict)
            
            bank_config = BatteryBankConfig(
                id=battery_pack.pack_id,
                name=battery_pack.name,
                adapter=adapter_config
            )
        else:
            # Multiple adapters (failover)
            adapters_with_priority = []
            for adapter_instance in sorted(adapter_instances, key=lambda a: a.priority):
                adapter_config_dict = adapter_instance.config_json.copy()
                adapter_config_dict['type'] = adapter_instance.adapter_type
                adapter_config = BatteryAdapterConfig(**adapter_config_dict)
                
                adapters_with_priority.append(
                    BatteryAdapterConfigWithPriority(
                        adapter=adapter_config,
                        priority=adapter_instance.priority,
                        enabled=adapter_instance.enabled
                    )
                )
            
            bank_config = BatteryBankConfig(
                id=battery_pack.pack_id,
                name=battery_pack.name,
                adapters=adapters_with_priority
            )
        
        return bank_config
    
    def _adapter_instance_to_meter_config(self, meter, adapter_instance) -> 'MeterConfig':
        """Convert hierarchy Meter + AdapterInstance to MeterConfig."""
        from solarhub.config import MeterConfig, MeterAdapterConfig
        
        # Convert adapter config_json to MeterAdapterConfig
        adapter_config_dict = adapter_instance.config_json.copy()
        adapter_config_dict['type'] = adapter_instance.adapter_type
        adapter_config = MeterAdapterConfig(**adapter_config_dict)
        
        # Create MeterConfig
        meter_config = MeterConfig(
            id=meter.meter_id,
            name=meter.name,
            attachment_target=meter.attachment_target,
            adapter=adapter_config
        )
        return meter_config
    
    def _initialize_discovery_attributes(self):
        """Initialize device discovery and recovery attributes."""
        # Device discovery and recovery
        self.device_registry = None
        self.discovery_service = None
        self.recovery_manager = None
        self._discovery_task: Optional[asyncio.Task] = None
        self._recovery_task: Optional[asyncio.Task] = None
        
        # Settings cache for inverter configuration (on-demand, not polled)
        # Structure: {inverter_id: {section: {"data": {...}, "timestamp": float}}}
        self.settings_cache: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self.settings_cache_expiry_seconds = 3600  # 1 hour
        
        # Initialize device discovery if enabled
        if cfg.discovery.enabled:
            try:
                from solarhub.device_registry import DeviceRegistry
                from solarhub.device_discovery import DeviceDiscoveryService
                from solarhub.auto_recovery import AutoRecoveryManager
                
                self.device_registry = DeviceRegistry(self.logger.path)
                self.discovery_service = DeviceDiscoveryService(
                    registry=self.device_registry,
                    adapters=ADAPTERS,
                    battery_adapters=BATTERY_ADAPTERS,
                    config_manager=self.config_manager,
                    logger=self.logger
                )
                # Configure discovery service from config
                self.discovery_service.enabled = self.cfg.discovery.enabled
                self.discovery_service.scan_on_startup = self.cfg.discovery.scan_on_startup
                self.discovery_service.scan_interval_minutes = self.cfg.discovery.scan_interval_minutes
                self.discovery_service.priority_order = self.cfg.discovery.priority_order
                self.discovery_service.identification_timeout = self.cfg.discovery.identification_timeout
                self.discovery_service.max_retries = self.cfg.discovery.max_retries
                
                self.recovery_manager = AutoRecoveryManager(
                    registry=self.device_registry,
                    discovery_service=self.discovery_service,
                    initial_retry_minutes=self.cfg.discovery.initial_retry_minutes,
                    max_retry_minutes=self.cfg.discovery.max_retry_minutes,
                    backoff_multiplier=self.cfg.discovery.backoff_multiplier,
                    max_failures=self.cfg.discovery.max_failures
                )
                log.info("Device discovery and recovery services initialized")
            except Exception as e:
                log.error(f"Failed to initialize device discovery: {e}", exc_info=True)
                self.device_registry = None
                self.discovery_service = None
                self.recovery_manager = None

    def _configure_logging(self):
        """Configure logging based on config settings."""
        log_config = self.cfg.logging
        
        print(f"Configuring logging with level: {log_config.level}")
        print(f"Logging format: {log_config.format}")
        print(f"HA debug enabled: {log_config.ha_debug}")
        
        # Set root logger level
        root_logger = logging.getLogger()
        log_level = getattr(logging, log_config.level.upper())
        root_logger.setLevel(log_level)
        print(f"Set root logger level to: {log_config.level.upper()}")
        
        # Configure console handler if not already configured
        if not root_logger.handlers:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(log_level)
            formatter = logging.Formatter(log_config.format)
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)
            print("Added console handler")
        else:
            print(f"Console handler already exists: {root_logger.handlers}")
        
        # Set specific loggers
        logging.getLogger("solarhub").setLevel(log_level)
        print(f"Set solarhub logger level to: {log_config.level.upper()}")
        
        # Suppress pymodbus auto-reconnect warnings and connection errors (these are internal to pymodbus and not actionable)
        # Pymodbus tries to auto-reconnect when it detects broken connections, but these warnings
        # are noisy and not useful since we handle reconnection ourselves
        pymodbus_logger = logging.getLogger("pymodbus")
        pymodbus_logger.setLevel(logging.CRITICAL)  # Suppress all pymodbus logs except critical issues
        print("Suppressed pymodbus WARNING and ERROR level logs (auto-reconnect and connection messages)")
        
        # Configure HA debug logging
        if log_config.ha_debug:
            logging.getLogger("solarhub.ha").setLevel(logging.DEBUG)
            logging.getLogger("solarhub.ha.discovery").setLevel(logging.DEBUG)
            print("Enabled HA debug logging")
        
        print("Logging configuration completed")
        
        # Test the logging configuration
        log.info(f"Logging configured - Level: {log_config.level}, HA Debug: {log_config.ha_debug}")
        log.debug("This is a DEBUG message - should only appear if level is DEBUG")
        log.warning("This is a WARNING message - should always appear")
        print("Test log messages sent - check if INFO level messages appear above")

    def get_settings_cache(self, inverter_id: str, section: str) -> Optional[Dict[str, Any]]:
        """Get cached settings for a section, return None if expired or missing."""
        if inverter_id not in self.settings_cache:
            return None
        if section not in self.settings_cache[inverter_id]:
            return None
        
        cache_entry = self.settings_cache[inverter_id][section]
        if 'timestamp' not in cache_entry or 'data' not in cache_entry:
            return None
        
        # Check if cache is expired
        age = time.time() - cache_entry['timestamp']
        if age >= self.settings_cache_expiry_seconds:
            log.debug(f"Settings cache expired for {inverter_id}.{section} (age: {age:.1f}s)")
            return None
        
        log.debug(f"Settings cache hit for {inverter_id}.{section} (age: {age:.1f}s)")
        return cache_entry['data']
    
    def set_settings_cache(self, inverter_id: str, section: str, data: Dict[str, Any]) -> None:
        """Store settings in cache with current timestamp."""
        if inverter_id not in self.settings_cache:
            self.settings_cache[inverter_id] = {}
        
        self.settings_cache[inverter_id][section] = {
            'data': data,
            'timestamp': time.time()
        }
        log.debug(f"Settings cached for {inverter_id}.{section}")
    
    def invalidate_settings_cache(self, inverter_id: str, section: Optional[str] = None) -> None:
        """Invalidate cache for a section or all sections for an inverter."""
        if inverter_id not in self.settings_cache:
            return
        
        if section is None:
            # Invalidate all sections for this inverter
            del self.settings_cache[inverter_id]
            log.debug(f"Settings cache invalidated for all sections of {inverter_id}")
        elif section in self.settings_cache[inverter_id]:
            # Invalidate specific section
            del self.settings_cache[inverter_id][section]
            log.debug(f"Settings cache invalidated for {inverter_id}.{section}")

    async def init(self):
        # Wait a moment for MQTT to connect (if using async connection)
        import asyncio
        await asyncio.sleep(0.5)  # Give MQTT time to establish connection
        
        # Power cycle Bluetooth on startup if any jkbms_ble adapters are configured
        has_ble_batteries = False
        bt_adapter_name = "hci0"  # Default adapter name
        
        # Check legacy battery_bank
        if getattr(self.cfg, "battery_bank", None):
            if self.cfg.battery_bank and self.cfg.battery_bank.adapter.type == "jkbms_ble":
                has_ble_batteries = True
                bt_adapter_name = getattr(self.cfg.battery_bank.adapter, "bt_adapter", "hci0") or "hci0"
        
        # Check battery_banks list
        if getattr(self.cfg, "battery_banks", None):
            for bank in self.cfg.battery_banks:
                if bank and hasattr(bank, 'adapter') and bank.adapter and bank.adapter.type == "jkbms_ble":
                    has_ble_batteries = True
                    # Use the first adapter name found, or default to hci0
                    if not bt_adapter_name or bt_adapter_name == "hci0":
                        bt_adapter_name = getattr(bank.adapter, "bt_adapter", "hci0") or "hci0"
                    break
        
        if has_ble_batteries:
            log.info(f"JK BMS Bluetooth adapter(s) detected. Power cycling Bluetooth adapter {bt_adapter_name} on startup...")
            try:
                # Create a temporary adapter instance just to call power_cycle_bluetooth
                # We'll use the first jkbms_ble bank config we find
                temp_bank = None
                if getattr(self.cfg, "battery_bank", None) and self.cfg.battery_bank.adapter.type == "jkbms_ble":
                    temp_bank = self.cfg.battery_bank
                elif getattr(self.cfg, "battery_banks", None):
                    for bank in self.cfg.battery_banks:
                        if bank and hasattr(bank, 'adapter') and bank.adapter and bank.adapter.type == "jkbms_ble":
                            temp_bank = bank
                            break
                
                if temp_bank:
                    temp_adapter = JKBMSBleAdapter(temp_bank)
                    success = await temp_adapter.power_cycle_bluetooth(bt_adapter_name)
                    if success:
                        log.info("Bluetooth power cycle completed successfully on startup")
                        await asyncio.sleep(2.0)  # Wait for Bluetooth to stabilize
                    else:
                        log.warning("Bluetooth power cycle failed on startup, but continuing...")
            except Exception as e:
                log.warning(f"Error power cycling Bluetooth on startup: {e}. Continuing with initialization...")
        
        # Run device discovery BEFORE initializing inverters
        # This allows us to update ports if devices are found on different ports
        discovered = []
        if hasattr(self, 'discovery_service') and self.discovery_service and self.cfg.discovery.scan_on_startup:
            try:
                log.info("Running device discovery on startup (before initializing devices)...")
                discovered, _ = await self.discovery_service.discover_devices(
                    manual_config_inverters=self.cfg.inverters,
                    manual_config_battery=getattr(self.cfg, "battery_bank", None)
                )
                log.info(f"Device discovery completed: {len(discovered)} devices found")
                
                # Update inverter ports in config if discovery found them on different ports
                # Match discovered devices to manually configured devices
                if self.device_registry and discovered:
                    log.info("Matching discovered devices to manually configured devices...")
                    
                    # For each manually configured inverter, find matching discovered device
                    for inv in self.cfg.inverters:
                        if not inv.adapter.serial_port:
                            continue
                        
                        # Find discovered device of same type
                        matching_discovered = [
                            d for d in discovered 
                            if d.device_type == inv.adapter.type
                        ]
                        
                        if len(matching_discovered) == 1:
                            # Only one device of this type discovered - likely a match
                            discovered_device = matching_discovered[0]
                            if discovered_device.port != inv.adapter.serial_port:
                                log.info(
                                    f"Discovery found {inv.id} ({inv.adapter.type}) on {discovered_device.port} "
                                    f"(config has {inv.adapter.serial_port}) - updating to discovered port"
                                )
                                inv.adapter.serial_port = discovered_device.port
                        elif len(matching_discovered) > 1:
                            # Multiple devices of same type - try to match by serial
                            log.debug(f"Multiple {inv.adapter.type} devices discovered, trying to match by serial for {inv.id}")
                            # Try to read serial from configured port first to identify which device this is
                            try:
                                adapter_class = ADAPTERS.get(inv.adapter.type)
                                if adapter_class:
                                    temp_adapter = adapter_class(inv)
                                    try:
                                        await temp_adapter.connect()
                                        serial = await temp_adapter.read_serial_number()
                                        await temp_adapter.close()
                                        
                                        if serial:
                                            normalized_serial = self.device_registry.normalize_serial(serial)
                                            # Find matching discovered device by serial
                                            for discovered_device in matching_discovered:
                                                if (discovered_device.serial_number == normalized_serial and
                                                    discovered_device.port != inv.adapter.serial_port):
                                                    log.info(
                                                        f"Discovery found {inv.id} (serial={normalized_serial}) on {discovered_device.port} "
                                                        f"(config has {inv.adapter.serial_port}) - updating to discovered port"
                                                    )
                                                    inv.adapter.serial_port = discovered_device.port
                                                    break
                                    except Exception as e:
                                        log.debug(f"Could not read serial for {inv.id} to match with discovery: {e}")
                            except Exception as e:
                                log.debug(f"Error matching discovered device to {inv.id}: {e}")
                
                # Also update battery port if discovered
                if self.device_registry and getattr(self.cfg, "battery_bank", None):
                    bank = self.cfg.battery_bank
                    matching_battery = [
                        d for d in discovered 
                        if d.device_type == bank.adapter.type
                    ]
                    
                    if len(matching_battery) == 1:
                        discovered_device = matching_battery[0]
                        if discovered_device.port != bank.adapter.serial_port:
                            log.info(
                                f"Discovery found battery {bank.id} on {discovered_device.port} "
                                f"(config has {bank.adapter.serial_port}) - updating to discovered port"
                            )
                            bank.adapter.serial_port = discovered_device.port
            except Exception as e:
                log.error(f"Device discovery failed: {e}", exc_info=True)
        
        # Initialize inverters from hierarchy (if available) or config
        inverters_to_init = []
        if hasattr(self, '_hierarchy_inverters') and self._hierarchy_inverters:
            log.info(f"Initializing {len(self._hierarchy_inverters)} inverters from hierarchy")
            for inverter_id, inverter in self._hierarchy_inverters.items():
                if not inverter.adapter:
                    log.warning(f"Inverter {inverter_id} has no adapter configured, skipping")
                    continue
                try:
                    inv_config = self._adapter_instance_to_inverter_config(inverter, inverter.adapter)
                    inverters_to_init.append(inv_config)
                except Exception as e:
                    log.error(f"Failed to convert hierarchy inverter {inverter_id} to config: {e}", exc_info=True)
        else:
            log.info(f"Initializing {len(self.cfg.inverters)} inverters from config.yaml")
            inverters_to_init = self.cfg.inverters
        
        for inv in inverters_to_init:
            # Skip meter adapters - they should be configured in the meters section
            if inv.adapter.type in METER_ADAPTERS:
                log.warning(
                    f"Inverter {inv.id} uses adapter type '{inv.adapter.type}' which is a meter adapter. "
                    f"Please move this configuration to the 'meters' section in config.yaml. "
                    f"Skipping inverter initialization for {inv.id}."
                )
                continue
            
            if inv.adapter.type not in ADAPTERS:
                raise ValueError(f"Unsupported adapter type: {inv.adapter.type}")
            
            port = inv.adapter.serial_port
            
            # Create fresh adapter - discovery only identifies devices, runtime creates connections
            # Note: We don't check port existence here because:
            # 1. Discovery may have just found the device on this port
            # 2. Port existence check can be unreliable (timing issues)
            # 3. The adapter.connect() will handle port errors gracefully
            log.info(f"Creating adapter for inverter {inv.id} on port {port}")
            adapter = ADAPTERS[inv.adapter.type](inv)
            try:
                await adapter.connect()
                # Verify connection after connect()
                client = getattr(adapter, 'client', None)
                if client and hasattr(client, 'connected') and client.connected:
                    log.info(f"Successfully connected adapter for inverter {inv.id} on port {port} (client.connected=True)")
                    # Set devices_connected flag immediately after successful connection
                    self._devices_connected = True
                else:
                    log.warning(f"Adapter connect() returned but client.connected=False for inverter {inv.id} on port {port}")
            except Exception as e:
                error_str = str(e).lower()
                if "port" in error_str and ("does not exist" in error_str or "no such file" in error_str or "no such device" in error_str):
                    log.warning(f"Port {port} for inverter {inv.id} does not exist - device may be disconnected. Adapter created but not connected.")
                else:
                    log.warning(f"Failed to connect adapter for inverter {inv.id} on port {port}: {e}")
            
            if adapter:
                rt = InverterRuntime(inv, adapter)
                self.inverters.append(rt)
                
                # Register adapter with command queue manager
                self.command_queue.register_adapter(inv.id, adapter)
                
                self._subscribe_command_topics(rt)
                # Availability: mark online (retain)
                try:
                    self.mqtt.pub(f"{self.cfg.mqtt.base_topic}/{rt.cfg.id}/availability", "online", retain=True)
                except Exception as e:
                    log.warning(f"Failed to publish availability for {rt.cfg.id}: {e}")
                # Publish discovery now (device model/SN may be generic for the first few seconds)
                # Get inverter count for metadata
                inverter_count = len(self.inverters) if self.inverters else 1
                # Get array_id from hierarchy or config
                array_id = None
                if hasattr(self, '_hierarchy_inverters') and rt.cfg.id in self._hierarchy_inverters:
                    hierarchy_inverter = self._hierarchy_inverters[rt.cfg.id]
                    array_id = hierarchy_inverter.array_id
                elif hasattr(rt.cfg, 'array_id') and rt.cfg.array_id:
                    array_id = rt.cfg.array_id
                try:
                    self.ha.publish_all_for_inverter(rt, inverter_count, array_id=array_id)
                    log.info(f"Published HA discovery for inverter {rt.cfg.id} (array: {array_id})")
                except Exception as e:
                    log.error(f"Failed to publish HA discovery for inverter {rt.cfg.id}: {e}", exc_info=True)

        # Initialize battery banks if configured
        # First, handle legacy battery_bank (for backward compatibility)
        if getattr(self.cfg, "battery_bank", None):
            bank = self.cfg.battery_bank
            if bank and bank.adapter.type in BATTERY_ADAPTERS:
                log.info(f"Creating battery adapter for {bank.id} on port {bank.adapter.serial_port}")
                try:
                    adapter = BATTERY_ADAPTERS[bank.adapter.type](bank)
                    await adapter.connect()
                    log.info("Battery adapter initialized: %s", bank.adapter.type)
                    
                    # Start continuous background listening for passive adapters (like jkbms_passive)
                    if hasattr(adapter, 'start_listening'):
                        try:
                            await adapter.start_listening()
                            log.info("Started continuous background listening for battery adapter")
                        except Exception as e:
                            log.warning(f"Failed to start background listening for battery adapter: {e}")
                    
                    self.battery_adapters[bank.id] = adapter
                    # Legacy: set single adapter for backward compatibility
                    if not self.battery_adapter:
                        self.battery_adapter = adapter
                    self._devices_connected = True
                except Exception as e:
                    log.error("Failed to initialize battery adapter: %s", e)
        
        # Initialize battery banks from hierarchy (if available) or config
        battery_banks_to_init = []
        if hasattr(self, '_hierarchy_battery_packs') and self._hierarchy_battery_packs:
            log.info(f"Initializing {len(self._hierarchy_battery_packs)} battery packs from hierarchy")
            for pack_id, battery_pack in self._hierarchy_battery_packs.items():
                if not battery_pack.adapters:
                    log.warning(f"Battery pack {pack_id} has no adapters configured, skipping")
                    continue
                try:
                    # Filter enabled adapters
                    enabled_adapters = [a for a in battery_pack.adapters if a.enabled]
                    if not enabled_adapters:
                        log.warning(f"Battery pack {pack_id} has no enabled adapters, skipping")
                        continue
                    bank_config = self._adapter_instances_to_battery_bank_config(battery_pack, enabled_adapters)
                    battery_banks_to_init.append(bank_config)
                except Exception as e:
                    log.error(f"Failed to convert hierarchy battery pack {pack_id} to config: {e}", exc_info=True)
        elif getattr(self.cfg, "battery_banks", None):
            log.info(f"Initializing {len(self.cfg.battery_banks)} battery banks from config.yaml")
            battery_banks_to_init = self.cfg.battery_banks
        
        # Initialize all battery banks from battery_banks list
        if battery_banks_to_init:
            log.info(f"Found {len(battery_banks_to_init)} battery bank(s) in configuration")
            for idx, bank in enumerate(battery_banks_to_init):
                bank_id = getattr(bank, 'id', 'UNKNOWN')
                # Determine adapter type for logging
                adapter_type_str = 'NO_ADAPTER'
                if hasattr(bank, 'adapters') and bank.adapters:
                    adapter_type_str = f"failover({len(bank.adapters)} adapters)"
                elif hasattr(bank, 'adapter') and bank.adapter:
                    adapter_type_str = getattr(bank.adapter, 'type', 'UNKNOWN')
                
                log.info(f"Processing battery bank {idx+1}/{len(self.cfg.battery_banks)}: id={bank_id}, type={adapter_type_str}")
                if not bank:
                    log.warning("Skipping None battery bank entry")
                    continue
                
                # Check if multiple adapters are configured (failover support) - check this FIRST
                if hasattr(bank, 'adapters') and bank.adapters:
                    log.info(f"Creating failover adapter for {bank.id} with {len(bank.adapters)} adapter(s)")
                    try:
                        adapter = FailoverBatteryAdapter(bank, BATTERY_ADAPTERS)
                    except Exception as e:
                        log.error(f"Failed to create failover adapter for {bank.id}: {e}", exc_info=True)
                        continue
                elif hasattr(bank, 'adapter') and bank.adapter:
                    # Single adapter (backward compatibility) - validate adapter exists
                    if not hasattr(bank.adapter, 'type') or not bank.adapter.type:
                        log.warning(f"Skipping battery bank {bank.id}: adapter type is missing")
                        continue
                    # Single adapter (backward compatibility)
                    if bank.adapter.type not in BATTERY_ADAPTERS:
                        log.warning(f"Skipping battery bank {bank.id}: unsupported adapter type '{bank.adapter.type}' (available: {list(BATTERY_ADAPTERS.keys())})")
                        continue
                    log.info(f"Creating battery adapter for {bank.id} (type: {bank.adapter.type})")
                    try:
                        adapter = BATTERY_ADAPTERS[bank.adapter.type](bank)
                    except Exception as e:
                        log.error(f"Failed to create adapter for {bank.id}: {e}")
                        continue
                else:
                    log.warning(f"Skipping battery bank {bank.id}: no adapter configuration")
                    continue
                
                try:
                    log.info(f"Adapter instance created for {bank.id}, attempting connection...")
                    
                    # Determine adapter type for connection handling
                    adapter_type = None
                    if hasattr(bank, 'adapters') and bank.adapters:
                        # Failover adapter - check first adapter type
                        adapter_type = bank.adapters[0].adapter.type if bank.adapters else None
                    elif hasattr(bank, 'adapter') and bank.adapter:
                        adapter_type = bank.adapter.type
                    
                    # For Bluetooth adapters, allow initialization even if connection fails initially
                    # They will retry on first poll
                    is_ble_adapter = adapter_type == 'jkbms_ble'
                    
                    try:
                        await adapter.connect()
                        if hasattr(adapter, 'get_current_adapter_info'):
                            # Failover adapter
                            info = adapter.get_current_adapter_info()
                            log.info(f"Battery adapter initialized: {info.get('adapter_type', 'unknown')} (failover adapter)")
                        else:
                            log.info(f"Battery adapter initialized: {adapter_type}")
                        self._devices_connected = True
                    except Exception as connect_error:
                        if is_ble_adapter:
                            # For BLE adapters, allow initialization even if connection fails
                            # They will retry on first poll
                            log.warning(f"Battery adapter {bank.id} connection failed initially: {connect_error}")
                            log.info(f"Adapter {bank.id} will be added and will retry connection on first poll")
                        else:
                            # For other adapters, fail initialization
                            raise
                    
                    # Start continuous background listening for passive adapters (like jkbms_passive)
                    if hasattr(adapter, 'start_listening'):
                        try:
                            await adapter.start_listening()
                            log.info("Started continuous background listening for battery adapter {bank.id}")
                        except Exception as e:
                            log.warning(f"Failed to start background listening for battery adapter {bank.id}: {e}")
                    
                    # Add adapter to system even if connection failed (for BLE adapters)
                    self.battery_adapters[bank.id] = adapter
                    # Legacy: set single adapter for backward compatibility (first one)
                    if not self.battery_adapter:
                        self.battery_adapter = adapter
                    
                    log.info(f"Successfully initialized battery bank {bank.id}")
                except Exception as e:
                    log.error(f"Failed to initialize battery adapter for {bank.id}: {e}", exc_info=True)

        # Initialize meters from hierarchy (if available) or config
        meters_to_init = []
        if hasattr(self, '_hierarchy_meters') and self._hierarchy_meters:
            log.info(f"Initializing {len(self._hierarchy_meters)} meters from hierarchy")
            for meter_id, meter in self._hierarchy_meters.items():
                if not meter.adapter:
                    log.warning(f"Meter {meter_id} has no adapter configured, skipping")
                    continue
                try:
                    meter_config = self._adapter_instance_to_meter_config(meter, meter.adapter)
                    meters_to_init.append(meter_config)
                except Exception as e:
                    log.error(f"Failed to convert hierarchy meter {meter_id} to config: {e}", exc_info=True)
        elif getattr(self.cfg, "meters", None):
            log.info(f"Initializing {len(self.cfg.meters)} meters from config.yaml")
            meters_to_init = self.cfg.meters
        
        # Initialize meters if configured
        if meters_to_init:
            for meter_cfg in meters_to_init:
                if meter_cfg.adapter.type not in METER_ADAPTERS:
                    log.warning(f"Unsupported meter adapter type: {meter_cfg.adapter.type}")
                    continue
                
                log.info(f"Creating meter adapter for {meter_cfg.id} at {meter_cfg.adapter.host}:{meter_cfg.adapter.port}")
                adapter = METER_ADAPTERS[meter_cfg.adapter.type](meter_cfg)
                try:
                    await adapter.connect()
                    client = getattr(adapter, 'client', None)
                    if client and hasattr(client, 'connected') and client.connected:
                        log.info(f"Successfully connected meter adapter for {meter_cfg.id}")
                        self._devices_connected = True
                    else:
                        log.warning(f"Meter adapter connect() returned but client.connected=False for {meter_cfg.id}")
                except Exception as e:
                    log.warning(f"Failed to connect meter adapter for {meter_cfg.id}: {e}")
                
                if adapter:
                    rt = MeterRuntime(meter_cfg, adapter)
                    self.meters.append(rt)
                    # Publish availability
                    try:
                        self.mqtt.pub(f"{self.cfg.mqtt.base_topic}/meter/{meter_cfg.id}/availability", "online", retain=True)
                    except Exception as e:
                        log.warning(f"Failed to publish availability for meter {meter_cfg.id}: {e}")
                    
                    # Publish HA discovery for meter if enabled
                    if self.cfg.mqtt.ha_discovery:
                        try:
                            meter_name = getattr(meter_cfg, "name", None)
                            self.ha.publish_meter_entities(
                                meter_id=meter_cfg.id,
                                meter_name=meter_name,
                                meter_cfg=meter_cfg
                            )
                            log.info(f"HA discovery published for meter {meter_cfg.id}")
                        except Exception as e:
                            log.error(f"Failed to publish HA discovery for meter {meter_cfg.id}: {e}", exc_info=True)

        # Start the command queue manager
        self.command_queue.start()
        log.info("Command queue manager started")
        

        # Start embedded FastAPI for React UI access
        try:
            api = create_api(self)
            host = getattr(self.cfg.web, 'host', '0.0.0.0') if hasattr(self.cfg, 'web') else '0.0.0.0'
            port = getattr(self.cfg.web, 'port', 8000) if hasattr(self.cfg, 'web') else 8000
            start_api_in_background(api, host, port)
            log.info(f"Embedded API server started on http://{host}:{port}")
        except Exception as e:
            log.warning(f"Failed to start embedded API server: {e}")
        
        # Publish HA discovery for arrays, packs, and battery bank (regardless of smart policy)
        # Check if HA discovery is enabled
        ha_discovery_enabled = getattr(self.cfg.mqtt, 'ha_discovery', True)  # Default to True
        if ha_discovery_enabled:
            log.info("Publishing HA discovery for arrays, battery packs, and battery bank")
            
            # Publish HA discovery for arrays from hierarchy
            if hasattr(self, 'hierarchy_systems') and self.hierarchy_systems:
                for system_id, system in self.hierarchy_systems.items():
                    for inv_array in system.inverter_arrays:
                        self.ha.publish_array_entities(
                            array_id=inv_array.array_id,
                            array_name=inv_array.name,
                            inverter_ids=inv_array.inverter_ids,
                            pack_ids=inv_array.attached_pack_ids,
                            system_id=system_id
                        )
            
            # Publish HA discovery for battery packs from hierarchy
            if hasattr(self, 'hierarchy_systems') and self.hierarchy_systems:
                for system_id, system in self.hierarchy_systems.items():
                    for bat_array in system.battery_arrays:
                        for pack in bat_array.battery_packs:
                            pack_id = pack.pack_id
                            pack_name = pack.name
                            battery_array_id = bat_array.battery_array_id
                            # Find attached inverter array
                            attached_inv_array_id = bat_array.attached_inverter_array_id
                            
                            self.ha.publish_pack_entities(
                                pack_id=pack_id,
                                pack_name=pack_name,
                                array_id=attached_inv_array_id,
                                battery_array_id=battery_array_id,
                                system_id=system_id
                            )
                            
                            # Publish battery bank discovery for this pack
                            pack_ids = [p.pack_id for p in bat_array.battery_packs]
                            log.info(f"Publishing battery bank discovery: pack_id={pack_id}, pack_name={pack_name}, pack_ids={pack_ids}")
                            try:
                                self.ha.publish_battery_bank_entities(
                                    bank_id=pack_id,
                                    bank_name=pack_name,
                                    pack_ids=pack_ids,
                                    bank_cfg=None  # No config needed for hierarchy-based packs
                                )
                                log.info(f"HA discovery published for battery bank {pack_id} (state topic: {self.cfg.mqtt.base_topic}/battery/{pack_id}/regs)")
                            except Exception as e:
                                log.error(f"Failed to publish battery bank discovery for {pack_id}: {e}", exc_info=True)
                            
                            # Publish discovery for individual battery units if we have telemetry
                            if pack_id in self.battery_last and hasattr(self.battery_last[pack_id], 'devices'):
                                for battery_unit in self.battery_last[pack_id].devices:
                                    if hasattr(battery_unit, 'power'):
                                        try:
                                            self.ha.publish_battery_unit_entities(
                                                bank_id=pack_id,
                                                unit_power=battery_unit.power,
                                                bank_name=pack_name
                                            )
                                        except Exception as e:
                                            log.error(f"Failed to publish discovery for battery unit {battery_unit.power}: {e}", exc_info=True)
            
            # Publish HA discovery for systems and battery arrays from hierarchy
            if hasattr(self, 'hierarchy_systems') and self.hierarchy_systems:
                log.info("Publishing HA discovery for systems and battery arrays from hierarchy")
                
                for system_id, system in self.hierarchy_systems.items():
                    # Publish system entities
                    system_name = system.name or "Solar System"
                    array_ids = [arr.id for arr in system.inverter_arrays]
                    try:
                        self.ha.publish_system_entities(
                            system_id=system_id,
                            system_name=system_name,
                            array_ids=array_ids
                        )
                        log.info(f"HA discovery published for system {system_id} (state topic: {self.cfg.mqtt.base_topic}/systems/{system_id}/state)")
                    except Exception as e:
                        log.error(f"Failed to publish system discovery for {system_id}: {e}", exc_info=True)
                    
                    # Publish battery array entities
                    for battery_array in system.battery_arrays:
                        battery_array_id = battery_array.id
                        battery_array_name = battery_array.name
                        pack_ids = [pack.pack_id for pack in battery_array.battery_packs]
                        try:
                            self.ha.publish_battery_array_entities(
                                battery_array_id=battery_array_id,
                                battery_array_name=battery_array_name,
                                pack_ids=pack_ids,
                                system_id=system_id
                            )
                            log.info(f"HA discovery published for battery array {battery_array_id}")
                        except Exception as e:
                            log.error(f"Failed to publish battery array discovery for {battery_array_id}: {e}", exc_info=True)
            
            # Clear legacy home entities from MQTT (to allow clean publishing of new system entities)
            # Clear common home IDs that might have been used
            legacy_home_ids = ["home", "system", "default"]
            for home_id in legacy_home_ids:
                try:
                    self.ha.clear_home_entities(home_id)
                except Exception as e:
                    log.debug(f"Failed to clear legacy home entities for {home_id} (may not exist): {e}")
            
            log.info("HA discovery published for arrays, battery packs, battery bank, systems, and battery arrays (legacy home entities cleared)")
        else:
            log.info("HA discovery disabled in configuration")
        
        log.info(f"Smart policy configuration: enabled={self.cfg.smart.policy.enabled}")
        if self.cfg.smart.policy.enabled:
            # Initialize per-array schedulers from hierarchy
            if hasattr(self, 'hierarchy_systems') and self.hierarchy_systems:
                total_arrays = sum(len(system.inverter_arrays) for system in self.hierarchy_systems.values())
                log.info(f"Initializing per-array schedulers for {total_arrays} arrays")
                for system_id, system in self.hierarchy_systems.items():
                    for inv_array in system.inverter_arrays:
                        array_id = inv_array.array_id
                        # Check if array has scheduler enabled (from config or global)
                        array_cfg = next((a for a in (self.cfg.arrays or []) if a.id == array_id), None)
                        array_scheduler_enabled = True
                        if array_cfg and array_cfg.scheduler and array_cfg.scheduler.enabled is not None:
                            array_scheduler_enabled = array_cfg.scheduler.enabled
                        elif not self.cfg.smart.policy.enabled:
                            array_scheduler_enabled = False
                        
                        if array_scheduler_enabled:
                            try:
                                scheduler = SmartScheduler(self.logger, self, array_id=array_id)
                                self.smart_schedulers[array_id] = scheduler
                                log.info(f"Initialized scheduler for array {array_id}")
                            except Exception as e:
                                log.error(f"Failed to initialize scheduler for array {array_id}: {e}")
                        else:
                            log.info(f"Scheduler disabled for array {array_id}")
                
                # Create single scheduler for convenience if only one array
                if len(self.smart_schedulers) == 1:
                    self.smart = next(iter(self.smart_schedulers.values()))
                    log.info("Using single scheduler from array")
                elif not self.smart_schedulers:
                    log.warning("No schedulers initialized for any arrays")
            else:
                log.error("No hierarchy systems available - cannot initialize schedulers")
                self.smart = None
            
            # Subscribe to battery optimization configuration commands (use first scheduler for legacy compatibility)
            active_scheduler = self.smart or (next(iter(self.smart_schedulers.values())) if self.smart_schedulers else None)
            if active_scheduler:
                config_base = f"{self.cfg.mqtt.base_topic}/config"
                self.mqtt.sub(f"{config_base}/set", active_scheduler.handle_config_command)
                
                # Publish inverter configuration discovery messages at startup
                log.info("Publishing inverter configuration discovery messages at startup")
                for inverter in self.inverters:
                    if hasattr(inverter.adapter, 'regs') and inverter.adapter.regs:
                        active_scheduler.inverter_config_ha.publish_inverter_config_sensors(inverter.cfg.id, inverter.adapter.regs)
                log.info("Inverter configuration discovery messages published at startup")
                
                # Publish battery optimization discovery (Solar System device) at startup
                if ha_discovery_enabled:
                    log.info("Publishing battery optimization discovery (Solar System) at startup")
                    active_scheduler.battery_ha.publish_all_battery_optimization_discovery()
                    active_scheduler.config_ha.publish_all_config_discovery()
                    log.info("Battery optimization discovery (Solar System) published at startup")
        else:
            log.info("Smart policy disabled - inverter config commands will not be processed")

    # ---------- MQTT command subscription (generic) ----------
    def _subscribe_command_topics(self, rt: InverterRuntime):
        base = f"{self.cfg.mqtt.base_topic}/{rt.cfg.id}"

        # Single topic for all commands (preferred)
        def on_cmd(_topic: str, payload: Any):
            try:
                if isinstance(payload, (str, bytes)):
                    data = json.loads(payload)
                else:
                    data = payload
                action = (data.get("action") or "").lower()
                if action in ("write", "write_many"):
                    # Enqueue command instead of direct execution
                    success = self.command_queue.enqueue_command(rt.cfg.id, data)
                    if not success:
                        log.error(f"Failed to enqueue command for {rt.cfg.id}")
                else:
                    log.warning("Unknown action on %s/cmd: %s", base, action)
            except Exception as e:
                log.warning("Bad /cmd payload for %s: %s", base, e)

        # Optional split topics (useful for HA YAML simplicity)
        def on_write(_topic: str, payload: Any):
            try:
                if isinstance(payload, (str, bytes)):
                    data = json.loads(payload)
                else:
                    data = payload
                data["action"] = "write"
                # Enqueue command instead of direct execution
                success = self.command_queue.enqueue_command(rt.cfg.id, data)
                if not success:
                    log.error(f"Failed to enqueue write command for {rt.cfg.id}")
            except Exception as e:
                log.warning("Bad /write payload for %s: %s", base, e)

        def on_write_many(_topic: str, payload: Any):
            try:
                if isinstance(payload, (str, bytes)):
                    data = json.loads(payload)
                else:
                    data = payload
                data["action"] = "write_many"
                # Enqueue command instead of direct execution
                success = self.command_queue.enqueue_command(rt.cfg.id, data)
                if not success:
                    log.error(f"Failed to enqueue write_many command for {rt.cfg.id}")
            except Exception as e:
                log.warning("Bad /write_many payload for %s: %s", base, e)

        self.mqtt.sub(f"{base}/cmd", on_cmd)
        
        self.mqtt.sub(f"{base}/write", on_write)
        self.mqtt.sub(f"{base}/write_many", on_write_many)
        
        # Subscribe to inverter configuration commands
        def on_inverter_config(_topic: str, payload: Any):
            try:
                log.info(f"Received inverter config command on topic: {_topic}")
                if isinstance(payload, (str, bytes)):
                    data = json.loads(payload)
                else:
                    data = payload
                
                # Extract sensor_id from topic: {base}/config/{sensor_id}/set
                topic_parts = _topic.split('/')
                if len(topic_parts) >= 4 and topic_parts[-1] == 'set':
                    sensor_id = topic_parts[-2]
                    log.info(f"Extracted sensor_id: {sensor_id} from topic: {_topic}")
                    
                    # Route to smart scheduler's inverter config handler via command queue
                    if self.smart and self.smart.inverter_config_handler:
                        log.info(f"Routing command to inverter config handler for {rt.cfg.id}.{sensor_id}")
                        # Create a command for the inverter config handler
                        config_cmd = {
                            "action": "inverter_config",
                            "sensor_id": sensor_id,
                            "data": data,
                            "handler": self.smart.inverter_config_handler
                        }
                        success = self.command_queue.enqueue_command(rt.cfg.id, config_cmd)
                        if not success:
                            log.error(f"Failed to enqueue inverter config command for {rt.cfg.id}")
                    else:
                        # Try to initialize the handler if smart scheduler exists but handler doesn't
                        if self.smart and not self.smart.inverter_config_handler:
                            log.debug("Attempting to initialize inverter config handler")
                            self.smart._initialize_inverter_config_handler()
                            
                            # Try again if handler was successfully initialized
                            if self.smart.inverter_config_handler:
                                log.info(f"Handler initialized, routing command to inverter config handler for {rt.cfg.id}.{sensor_id}")
                                config_cmd = {
                                    "action": "inverter_config",
                                    "sensor_id": sensor_id,
                                    "data": data,
                                    "handler": self.smart.inverter_config_handler
                                }
                                success = self.command_queue.enqueue_command(rt.cfg.id, config_cmd)
                                if not success:
                                    log.error(f"Failed to enqueue inverter config command for {rt.cfg.id}")
                            else:
                                log.warning("Inverter config handler not available - smart: %s, handler: %s", 
                                          bool(self.smart), 
                                          bool(self.smart.inverter_config_handler) if self.smart else False)
                        else:
                            log.warning("Inverter config handler not available - smart: %s, handler: %s", 
                                      bool(self.smart), 
                                      bool(self.smart.inverter_config_handler) if self.smart else False)
                else:
                    log.warning("Invalid inverter config topic format: %s", _topic)
            except Exception as e:
                log.warning("Bad inverter config payload for %s: %s", _topic, e)
        
        # Subscribe to all inverter config command topics
        self.mqtt.sub(f"{base}/config/+/set", on_inverter_config)

    def _schedule_async_task(self, coro):
        """Safely schedule an async task, handling cases where no event loop is running."""
        try:
            # Try to get the current event loop
            loop = asyncio.get_running_loop()
            # If we have a running loop, create a task
            loop.create_task(coro)
        except RuntimeError:
            # No running event loop, try to get the event loop from the main thread
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(coro)
                else:
                    # Event loop exists but not running, schedule it
                    asyncio.ensure_future(coro, loop=loop)
            except RuntimeError:
                # No event loop at all, create a new one in a thread
                import threading
                def run_in_thread():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        new_loop.run_until_complete(coro)
                    finally:
                        new_loop.close()
                thread = threading.Thread(target=run_in_thread, daemon=True)
                thread.start()

    async def _do_adapter_cmd(self, rt: InverterRuntime, cmd: Dict[str, Any]):
        try:
            res = await rt.adapter.handle_command(cmd)
            ack = {"ok": bool(res.get("ok")), **{k:v for k,v in res.items() if k != "ok"}}
        except Exception as e:
            ack = {"ok": False, "reason": str(e)}
        self.mqtt.pub(f"{self.cfg.mqtt.base_topic}/{rt.cfg.id}/ack", ack)


    

    # ---------- Main loop ----------
    async def run(self):
        log.info("Starting solar monitoring application main loop")
        
        try:
            # Start billing scheduler background task
            self._billing_scheduler_task = asyncio.create_task(self._billing_scheduler_loop())
            log.info("Started billing scheduler background task")
            
            # Start energy calculator hourly background task
            self._energy_calculator_task = asyncio.create_task(self._energy_calculator_hourly_loop())
            log.info("Started energy calculator hourly background task")
            
            # Discovery is now only run on startup or device disconnection
            # Periodic discovery is disabled - discovery runs:
            # 1. On startup (if scan_on_startup enabled)
            # 2. When devices disconnect (via recovery manager)
            # No periodic scanning to avoid unnecessary port scanning
            log.info("Device discovery periodic scan disabled - discovery runs only on startup or device disconnection")
            
            # Start recovery task
            if hasattr(self, 'recovery_manager') and self.recovery_manager:
                self._recovery_task = asyncio.create_task(self._recovery_loop())
                log.info("Started device recovery task")
            log.info(f"Polling interval: {self.cfg.polling.interval_secs} seconds")
            log.info(f"Smart scheduler interval: {self.cfg.smart.policy.smart_tick_interval_secs} seconds")
            log.info(f"Number of inverters configured: {len(self.inverters)}")
            
            # One-time automatic backfill for today's hours up to the last complete hour
            try:
                await self._backfill_today_hourly_energy()
            except Exception as e:
                log.warning(f"Automatic hourly-energy backfill skipped due to error: {e}")

            interval = self.cfg.polling.interval_secs
            smart_tick = 0
            smart_interval = self.cfg.smart.policy.smart_tick_interval_secs
            
            # Initialize connection lock in this event loop
            if self._connection_lock is None:
                self._connection_lock = asyncio.Lock()
            
            while True:
                # Check for disconnect/reconnect signals (must be handled in polling loop's event loop)
                try:
                    # Check flags and clear them atomically
                    should_disconnect = False
                    should_reconnect = False
                    reconnect_config = None
                    
                    if self._connection_lock:
                        async with self._connection_lock:
                            if self._disconnect_requested:
                                should_disconnect = True
                                self._disconnect_requested = False
                            if self._reconnect_requested:
                                should_reconnect = True
                                reconnect_config = self._reconnect_config
                                self._reconnect_requested = False
                                self._reconnect_config = None
                    else:
                        # Lock not initialized yet, check flags directly (shouldn't happen, but safe fallback)
                        if self._disconnect_requested:
                            should_disconnect = True
                            self._disconnect_requested = False
                        if self._reconnect_requested:
                            should_reconnect = True
                            reconnect_config = self._reconnect_config
                            self._reconnect_requested = False
                            self._reconnect_config = None
                    
                    # Handle disconnect/reconnect outside the lock (they might take time)
                    if should_disconnect:
                        log.info("Disconnect requested, handling disconnect in polling loop")
                        await self._handle_disconnect_in_loop()
                        continue
                    
                    if should_reconnect:
                        log.info("Reconnect requested, handling reconnect in polling loop")
                        await self._handle_reconnect_in_loop()
                        continue
                except Exception as e:
                    log.error(f"Error handling disconnect/reconnect signals: {e}", exc_info=True)
                
                # Check if polling is suspended
                if self._polling_suspended:
                    log.debug("Polling loop suspended, skipping cycle")
                    await asyncio.sleep(interval)
                    continue
                
                # Log connection state before polling
                for rt in self.inverters:
                    port = rt.cfg.adapter.serial_port
                    client = getattr(rt.adapter, 'client', None)
                    client_state = "None"
                    if client:
                        if hasattr(client, 'connected'):
                            client_state = f"connected={client.connected}"
                        else:
                            client_state = "exists (no connected attr)"
                    log.info(f"RUN LOOP: Before polling - Inverter {rt.cfg.id} (port={port}, client={client_state})")
                
                log.info("RUN LOOP: Starting polling cycle for all inverters")
                tasks = [self._poll_one(rt) for rt in self.inverters]
                # Poll all battery banks
                tasks.extend([self._poll_battery(bank_id) for bank_id in self.battery_adapters.keys()])
                # Legacy: also poll single battery_adapter if it exists and not in battery_adapters
                if self.battery_adapter and not any(adapter == self.battery_adapter for adapter in self.battery_adapters.values()):
                    tasks.append(self._poll_battery(None))  # None means use self.battery_adapter
                # Add meter polling tasks
                tasks.extend([self._poll_meter(rt) for rt in self.meters])
                await asyncio.gather(*tasks, return_exceptions=True)
                log.debug("RUN LOOP: Polling cycle completed")
                
                # Aggregate and publish home telemetry after all arrays are processed
                self._aggregate_and_publish_home_telemetry()
                
                smart_tick += interval
                log.debug(f"Smart tick counter: {smart_tick}/{smart_interval}")
                
                if self.smart and smart_tick >= smart_interval:
                    log.info("Smart scheduler tick interval reached - executing smart scheduler")
                    smart_tick = 0
                    try:
                        # Run per-array schedulers
                        if self.smart_schedulers:
                            for array_id, scheduler in self.smart_schedulers.items():
                                try:
                                    await scheduler.tick()
                                except Exception as e:
                                    log.error(f"Error in scheduler tick for array {array_id}: {e}")
                        # Legacy: run single scheduler if exists
                        elif self.smart:
                            await self.smart.tick()
                        log.info("Smart scheduler execution completed successfully")
                    except Exception as e:
                        log.warning("SmartScheduler error: %s", e)
                else:
                    log.debug(f"Smart scheduler not yet due (next in {smart_interval - smart_tick} seconds)")
                
                # Energy calculator now runs in separate background task (_energy_calculator_hourly_loop)
                # This ensures it runs every hour at :00 minutes regardless of polling loop state
                
                await asyncio.sleep(interval)
        except KeyboardInterrupt:
            log.info("Main loop interrupted by user")
            raise
        except Exception as e:
            log.error(f"Fatal error in main loop: {e}", exc_info=True)
            raise
    
    async def _billing_scheduler_loop(self):
        """Background task that runs daily billing job at 00:30 local time."""
        from solarhub.billing_scheduler import run_daily_billing_job
        from solarhub.timezone_utils import now_configured, get_configured_timezone
        from datetime import time as dtime
        
        log.info("Starting billing scheduler background task")
        last_run_date = None
        
        while True:
            try:
                tz = get_configured_timezone()
                now = now_configured()
                current_date = now.date()
                current_time = now.time()
                
                # Check if it's 00:30 or later and we haven't run for today
                target_time = dtime(0, 30)  # 00:30
                should_run = (
                    current_time >= target_time and
                    last_run_date != current_date
                )
                
                if should_run:
                    log.info(f"Running daily billing job for {current_date} at {current_time}")
                    try:
                        # Get config from cache or load it
                        config = self.config_manager._config_cache
                        if not config:
                            config = self.config_manager.load_config()
                        if config and config.billing:
                            log.info(f"Billing config found, executing daily billing job for {current_date}")
                            success = run_daily_billing_job(
                                self.logger.path,
                                config.billing,
                                config,  # hub_cfg
                                current_date,  # target_date
                                home_id=None,  # Process all homes
                                site_id="default"
                            )
                            if success:
                                last_run_date = current_date
                                log.info(f"Daily billing job completed successfully for {current_date}")
                            else:
                                log.error(f"Daily billing job failed for {current_date}")
                        else:
                            log.warning("Billing configuration not found, skipping daily billing job. Please configure billing settings via /billing-setup")
                    except Exception as e:
                        log.error(f"Error in daily billing job: {e}", exc_info=True)
                else:
                    # Log debug info about why billing job is not running
                    if last_run_date:
                        log.debug(f"Billing scheduler: Already ran for {last_run_date}, current date: {current_date}, time: {current_time}, target: {target_time}")
                    else:
                        log.debug(f"Billing scheduler: Waiting for 00:30. Current time: {current_time}, target: {target_time}")
                
                # Sleep for 1 hour, then check again
                await asyncio.sleep(3600)
                
            except Exception as e:
                log.error(f"Error in billing scheduler loop: {e}", exc_info=True)
                await asyncio.sleep(3600)  # Continue even on error
    
    async def _discovery_loop(self):
        """
        Periodic device discovery loop - DISABLED.
        
        Discovery now only runs:
        1. On startup (if scan_on_startup enabled)
        2. When devices disconnect (via recovery manager retry mechanism)
        
        This prevents unnecessary periodic port scanning.
        """
        # This method is kept for backward compatibility but is no longer used
        # Discovery is handled by:
        # - Startup discovery in init()
        # - Recovery manager when devices fail
        log.warning("_discovery_loop called but periodic discovery is disabled")
        return
    
    async def _recovery_loop(self):
        """Periodic device recovery loop."""
        if not hasattr(self, 'recovery_manager') or not self.recovery_manager:
            return
        
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                if not self.cfg.discovery.enabled:
                    continue
                
                processed = await self.recovery_manager.process_recovery_retries()
                if processed > 0:
                    log.info(f"Recovery loop processed {processed} devices")
                
            except Exception as e:
                log.error(f"Error in recovery loop: {e}", exc_info=True)
                await asyncio.sleep(60)  # Continue on error
    
    async def start_polling_loop(self):
        """Start the polling loop as a background task if not already running, or resume if suspended."""
        if self._polling_loop_task is not None and not self._polling_loop_task.done():
            # Task is running, check if it's suspended
            if self._polling_suspended:
                log.info("Resuming suspended polling loop")
                self._polling_suspended = False
                self._devices_connected = True
            else:
                log.info("Polling loop is already running")
            return
        
        # Initialize smart scheduler if needed and not already initialized
        if self.cfg.smart.policy.enabled and self.smart is None:
            try:
                self.smart = SmartScheduler(self.logger, self)
                log.info("Smart scheduler initialized for polling loop")
                
                # Subscribe to battery optimization configuration commands
                config_base = f"{self.cfg.mqtt.base_topic}/config"
                self.mqtt.sub(f"{config_base}/set", self.smart.handle_config_command)
                
                # Publish inverter configuration discovery messages
                log.info("Publishing inverter configuration discovery messages")
                for inverter in self.inverters:
                    if hasattr(inverter.adapter, 'regs') and inverter.adapter.regs:
                        self.smart.inverter_config_ha.publish_inverter_config_sensors(inverter.cfg.id, inverter.adapter.regs)
            except Exception as e:
                log.error(f"Failed to initialize smart scheduler: {e}")
                self.smart = None
        
        log.info("Starting polling loop as background task")
        self._polling_suspended = False
        self._devices_connected = True
        self._polling_loop_task = asyncio.create_task(self.run())
        log.info("Polling loop task created and started")
    
    async def _handle_disconnect_in_loop(self):
        """Handle disconnect request in the polling loop's event loop.
        This closes the connection but keeps the client object, so it can be reused on reconnect.
        """
        try:
            log.info("Handling disconnect in polling loop - closing connections but keeping client objects")
            
            # Disconnect all inverters (close connection but keep client object)
            for rt in list(self.inverters):
                try:
                    # Publish offline availability
                    self.mqtt.pub(f"{self.cfg.mqtt.base_topic}/{rt.cfg.id}/availability", "offline", retain=True)
                    # Close connection but keep client object
                    if hasattr(rt.adapter, 'disconnect_connection'):
                        await rt.adapter.disconnect_connection()
                    else:
                        # Fallback: close the client connection
                        if hasattr(rt.adapter, 'client') and rt.adapter.client:
                            if hasattr(rt.adapter.client, 'close'):
                                await rt.adapter.client.close()
                    log.info(f"Disconnected inverter: {rt.cfg.id} (client object kept)")
                except Exception as e:
                    log.error(f"Error disconnecting inverter {rt.cfg.id}: {e}")
            
            # Disconnect all battery banks (close connection but keep client object)
            # Legacy: disconnect single battery_adapter
            if self.battery_adapter:
                try:
                    # Stop background listening task if it exists
                    if hasattr(self.battery_adapter, 'stop_listening'):
                        try:
                            await self.battery_adapter.stop_listening()
                            log.info("Stopped background listening for battery adapter")
                        except Exception as e:
                            log.warning(f"Error stopping background listening: {e}")
                    
                    # Battery adapter uses serial connection, not Modbus
                    # Use close() method which properly handles serial connections
                    if hasattr(self.battery_adapter, 'close'):
                        await self.battery_adapter.close()
                        log.info("Disconnected battery adapter (client object kept)")
                    elif hasattr(self.battery_adapter, 'client') and self.battery_adapter.client:
                        # Fallback: close the client connection directly
                        if hasattr(self.battery_adapter.client, 'close'):
                            if self.battery_adapter.client.is_open:
                                await asyncio.to_thread(self.battery_adapter.client.close)
                                log.info("Disconnected battery adapter (client object kept)")
                except Exception as e:
                    log.error(f"Error disconnecting battery: {e}", exc_info=True)
            
            # Disconnect all battery banks from battery_adapters dict
            for bank_id, adapter in self.battery_adapters.items():
                try:
                    # Skip if this is the same adapter as battery_adapter (already handled)
                    if adapter == self.battery_adapter:
                        continue
                    
                    # Stop background listening task if it exists
                    if hasattr(adapter, 'stop_listening'):
                        try:
                            await adapter.stop_listening()
                            log.info(f"Stopped background listening for battery bank {bank_id}")
                        except Exception as e:
                            log.warning(f"Error stopping background listening for bank {bank_id}: {e}")
                    
                    # Battery adapter uses serial connection, not Modbus
                    # Use close() method which properly handles serial connections
                    if hasattr(adapter, 'close'):
                        await adapter.close()
                        log.info(f"Disconnected battery bank {bank_id} (client object kept)")
                    elif hasattr(adapter, 'client') and adapter.client:
                        # Fallback: close the client connection directly
                        if hasattr(adapter.client, 'close'):
                            if adapter.client.is_open:
                                await asyncio.to_thread(adapter.client.close)
                                log.info(f"Disconnected battery bank {bank_id} (client object kept)")
                except Exception as e:
                    log.error(f"Error disconnecting battery bank {bank_id}: {e}", exc_info=True)
            
            # Suspend polling
            self._polling_suspended = True
            self._devices_connected = False
            log.info("Disconnect handled - polling suspended, client objects kept for reuse")
        except Exception as e:
            log.error(f"Error handling disconnect in polling loop: {e}", exc_info=True)
    
    async def _handle_reconnect_in_loop(self):
        """Handle reconnect request in the polling loop's event loop.
        This reconnects the same client object with updated parameters.
        """
        try:
            log.info("Handling reconnect in polling loop - reconnecting same client objects")
            
            # Reload configuration if provided
            if self._reconnect_config:
                from solarhub.config_manager import ConfigurationManager
                if self.config_manager:
                    # Update configuration from provided config
                    # This is handled by the API server before signaling reconnect
                    pass
            
            # Reconnect all inverters (reconnect same client object)
            for rt in list(self.inverters):
                try:
                    # Reconnect the same client object
                    if hasattr(rt.adapter, 'reconnect_connection'):
                        await rt.adapter.reconnect_connection()
                    else:
                        # Fallback: reconnect the client
                        if hasattr(rt.adapter, 'client') and rt.adapter.client:
                            if hasattr(rt.adapter.client, 'connect'):
                                await rt.adapter.client.connect()
                    # Publish online availability
                    self.mqtt.pub(f"{self.cfg.mqtt.base_topic}/{rt.cfg.id}/availability", "online", retain=True)
                    log.info(f"Reconnected inverter: {rt.cfg.id} (same client object)")
                except Exception as e:
                    log.error(f"Error reconnecting inverter {rt.cfg.id}: {e}")
            
            # Reconnect all battery banks (reconnect same client object)
            # Legacy: reconnect single battery_adapter
            if self.battery_adapter:
                try:
                    if hasattr(self.battery_adapter, 'reconnect_connection'):
                        await self.battery_adapter.reconnect_connection()
                    else:
                        # Fallback: reconnect the client
                        if hasattr(self.battery_adapter, 'client') and self.battery_adapter.client:
                            if hasattr(self.battery_adapter.client, 'connect'):
                                await self.battery_adapter.client.connect()
                    
                    # Restart background listening for passive adapters
                    if hasattr(self.battery_adapter, 'start_listening'):
                        try:
                            await self.battery_adapter.start_listening()
                            log.info("Restarted continuous background listening for battery adapter")
                        except Exception as e:
                            log.warning(f"Failed to restart background listening: {e}")
                    
                    log.info("Reconnected battery adapter (same client object)")
                except Exception as e:
                    log.error(f"Error reconnecting battery: {e}")
            
            # Reconnect all battery banks from battery_adapters dict
            for bank_id, adapter in self.battery_adapters.items():
                try:
                    # Skip if this is the same adapter as battery_adapter (already handled)
                    if adapter == self.battery_adapter:
                        continue
                    
                    if hasattr(adapter, 'reconnect_connection'):
                        await adapter.reconnect_connection()
                    else:
                        # Fallback: reconnect the client
                        if hasattr(adapter, 'client') and adapter.client:
                            if hasattr(adapter.client, 'connect'):
                                await adapter.client.connect()
                    
                    # Restart background listening for passive adapters
                    if hasattr(adapter, 'start_listening'):
                        try:
                            await adapter.start_listening()
                            log.info(f"Restarted continuous background listening for battery bank {bank_id}")
                        except Exception as e:
                            log.warning(f"Failed to restart background listening for bank {bank_id}: {e}")
                    
                    log.info(f"Reconnected battery bank {bank_id} (same client object)")
                except Exception as e:
                    log.error(f"Error reconnecting battery bank {bank_id}: {e}")
            
            # Resume polling
            self._polling_suspended = False
            self._devices_connected = True
            log.info("Reconnect handled - polling resumed, same client objects reused")
        except Exception as e:
            log.error(f"Error handling reconnect in polling loop: {e}", exc_info=True)
            self._devices_connected = False
    
    async def _reconnect_devices(self):
        """Attempt to reconnect disconnected devices."""
        # Prevent multiple simultaneous reconnection attempts
        if self._reconnecting:
            log.info("Reconnection already in progress, skipping _reconnect_devices()")
            return
        
        # Log stack trace to see who's calling _reconnect_devices
        import traceback
        stack = traceback.extract_stack()
        callers = []
        for i in range(min(5, len(stack) - 1)):
            frame = stack[-(i+2)] if len(stack) > i+1 else None
            if frame:
                filename = frame.filename.split('/')[-1] if '/' in frame.filename else frame.filename.split('\\')[-1]
                callers.append(f"{filename}:{frame.lineno}({frame.name})")
        caller_info = " <- ".join(callers) if callers else "unknown"
        
        log.info(f"RECONNECT: _reconnect_devices() starting - checking all device connections (called from: {caller_info})")
        self._reconnecting = True
        try:
            # Check inverter connections - only reconnect if actually disconnected
            for rt in self.inverters:
                port = rt.cfg.adapter.serial_port
                client = getattr(rt.adapter, 'client', None)
                
                # Log current connection state
                client_state = "None"
                if client:
                    if hasattr(client, 'connected'):
                        client_state = f"connected={client.connected}"
                    else:
                        client_state = "exists (no connected attr)"
                log.info(f"RECONNECT: Inverter {rt.cfg.id} connection check: port={port}, client={client_state}")
                
                # FIRST: Check if client is already connected - if so, skip reconnection
                if client and hasattr(client, 'connected') and client.connected:
                    log.info(f"RECONNECT: Inverter {rt.cfg.id} client is already connected (client.connected=True), skipping reconnection")
                    continue
                
                # First check if port exists
                if port:
                    try:
                        import os
                        if not os.path.exists(port):
                            log.warning(f"RECONNECT: Port {port} for inverter {rt.cfg.id} does not exist - skipping reconnection")
                            continue
                    except Exception as e:
                        log.debug(f"RECONNECT: Error checking port existence for {rt.cfg.id}: {e}")
                
                # Double-check: only reconnect if client is None or explicitly disconnected
                # Don't reconnect if client exists and is connected (might be false negative)
                if not client:
                    log.info(f"RECONNECT: Attempting to reconnect inverter: {rt.cfg.id} (no client, port={port})")
                    try:
                        # Try to ensure client is connected (lazy connection)
                        if hasattr(rt.adapter, '_ensure_client_in_current_loop'):
                            await rt.adapter._ensure_client_in_current_loop()
                            client = getattr(rt.adapter, 'client', None)
                            if client and hasattr(client, 'connected') and client.connected:
                                log.info(f"Successfully reconnected inverter: {rt.cfg.id}")
                                self.mqtt.pub(f"{self.cfg.mqtt.base_topic}/{rt.cfg.id}/availability", "online", retain=True)
                                # Mark device as recovered if it was in recovery state
                                if self.device_registry and rt.cfg.adapter.serial_port:
                                    devices = self.device_registry.get_all_devices()
                                    for dev in devices:
                                        if dev.port == rt.cfg.adapter.serial_port and dev.status == "recovering":
                                            self.device_registry.mark_device_recovered(dev.device_id)
                                            log.info(f"Device {dev.device_id} recovered after reconnection")
                                            break
                        else:
                            # Fallback: try to connect directly
                            await rt.adapter.connect()
                            log.info(f"Successfully reconnected inverter: {rt.cfg.id}")
                            self.mqtt.pub(f"{self.cfg.mqtt.base_topic}/{rt.cfg.id}/availability", "online", retain=True)
                            # Mark device as recovered if it was in recovery state
                            if self.device_registry and rt.cfg.adapter.serial_port:
                                devices = self.device_registry.get_all_devices()
                                for dev in devices:
                                    if dev.port == rt.cfg.adapter.serial_port and dev.status == "recovering":
                                        self.device_registry.mark_device_recovered(dev.device_id)
                                        log.info(f"Device {dev.device_id} recovered after reconnection")
                                        break
                    except Exception as e:
                        error_str = str(e).lower()
                        if "port" in error_str and ("does not exist" in error_str or "no such file" in error_str or "no such device" in error_str):
                            log.warning(f"Reconnection failed for inverter {rt.cfg.id}: Port {port} does not exist")
                        else:
                            log.warning(f"Reconnection failed for inverter {rt.cfg.id}: {e}")
                elif hasattr(client, 'connected') and not client.connected:
                    # Client exists but is disconnected - try to reconnect
                    # But first double-check - client might have connected between checks
                    client = getattr(rt.adapter, 'client', None)
                    if client and hasattr(client, 'connected') and client.connected:
                        log.info(f"RECONNECT: Inverter {rt.cfg.id} client is actually connected (double-check passed), skipping reconnection")
                        continue
                    
                    log.info(f"RECONNECT: Attempting to reconnect inverter: {rt.cfg.id} (client disconnected, port={port})")
                    try:
                        # Try to reconnect the existing client first
                        if hasattr(rt.adapter, 'reconnect_connection'):
                            await rt.adapter.reconnect_connection()
                        elif hasattr(rt.adapter, '_ensure_client_in_current_loop'):
                            await rt.adapter._ensure_client_in_current_loop()
                        else:
                            await rt.adapter.connect()
                        
                        # Verify reconnection
                        client = getattr(rt.adapter, 'client', None)
                        if client and hasattr(client, 'connected') and client.connected:
                            log.info(f"Successfully reconnected inverter: {rt.cfg.id}")
                            self.mqtt.pub(f"{self.cfg.mqtt.base_topic}/{rt.cfg.id}/availability", "online", retain=True)
                            # Mark device as recovered if it was in recovery state
                            if self.device_registry and rt.cfg.adapter.serial_port:
                                devices = self.device_registry.get_all_devices()
                                for dev in devices:
                                    if dev.port == rt.cfg.adapter.serial_port and dev.status == "recovering":
                                        self.device_registry.mark_device_recovered(dev.device_id)
                                        log.info(f"Device {dev.device_id} recovered after reconnection")
                                        break
                        else:
                            log.debug(f"Inverter {rt.cfg.id} reconnection attempt did not result in connected client")
                    except Exception as e:
                        # Don't log as warning if it's a "port not found" error (common during device changes)
                        error_str = str(e).lower()
                        if "no such file" in error_str or "no such device" in error_str:
                            log.debug(f"Reconnection attempt for inverter {rt.cfg.id} failed (port not available): {e}")
                        else:
                            log.debug(f"Reconnection attempt for inverter {rt.cfg.id} failed: {e}")
                else:
                    # Client exists and is connected - no action needed
                    log.debug(f"Inverter {rt.cfg.id} is already connected, skipping reconnection")
            
            # Check all battery bank connections - only reconnect if actually disconnected
            # Legacy: check single battery_adapter
            if self.battery_adapter:
                client = getattr(self.battery_adapter, 'client', None)
                if not client:
                    log.info("Attempting to reconnect battery adapter (no client)")
                    try:
                        await self.battery_adapter.connect()
                        log.info("Successfully reconnected battery adapter")
                    except Exception as e:
                        log.warning(f"Battery reconnection failed: {e}")
                elif hasattr(client, 'is_open') and not client.is_open:
                    log.info("Attempting to reconnect battery adapter (client closed)")
                    try:
                        await self.battery_adapter.connect()
                        log.info("Successfully reconnected battery adapter")
                    except Exception as e:
                        log.warning(f"Battery reconnection failed: {e}")
                else:
                    log.debug("Battery adapter is already connected, skipping reconnection")
            
            # Check all battery banks from battery_adapters dict
            for bank_id, adapter in self.battery_adapters.items():
                # Skip if this is the same adapter as battery_adapter (already handled)
                if adapter == self.battery_adapter:
                    continue
                
                client = getattr(adapter, 'client', None)
                if not client:
                    log.info(f"Attempting to reconnect battery bank {bank_id} (no client)")
                    try:
                        await adapter.connect()
                        # Restart listening if needed
                        if hasattr(adapter, 'start_listening'):
                            await adapter.start_listening()
                        log.info(f"Successfully reconnected battery bank {bank_id}")
                    except Exception as e:
                        log.warning(f"Battery bank {bank_id} reconnection failed: {e}")
                elif hasattr(client, 'is_open') and not client.is_open:
                    log.info(f"Attempting to reconnect battery bank {bank_id} (client closed)")
                    try:
                        await adapter.connect()
                        # Restart listening if needed
                        if hasattr(adapter, 'start_listening'):
                            await adapter.start_listening()
                        log.info(f"Successfully reconnected battery bank {bank_id}")
                    except Exception as e:
                        log.warning(f"Battery bank {bank_id} reconnection failed: {e}")
                else:
                    log.debug(f"Battery bank {bank_id} is already connected, skipping reconnection")
            
            # Update connection state based on actual client status
            all_connected = True
            for rt in self.inverters:
                client = getattr(rt.adapter, 'client', None)
                if not client:
                    all_connected = False
                    break
                if hasattr(client, 'connected') and not client.connected:
                    all_connected = False
                    break
            
            # Check all battery adapters
            if self.battery_adapter:
                client = getattr(self.battery_adapter, 'client', None)
                if not client:
                    all_connected = False
                elif hasattr(client, 'is_open') and not client.is_open:
                    all_connected = False
            
            # Check all battery banks from battery_adapters dict
            for bank_id, adapter in self.battery_adapters.items():
                # Skip if this is the same adapter as battery_adapter (already checked)
                if adapter == self.battery_adapter:
                    continue
                
                client = getattr(adapter, 'client', None)
                if not client:
                    all_connected = False
                    break
                elif hasattr(client, 'is_open') and not client.is_open:
                    all_connected = False
                    break
            
            self._devices_connected = all_connected
            if all_connected:
                log.debug("All devices connected successfully")
        except Exception as e:
            log.error(f"Error during device reconnection: {e}")
            self._devices_connected = False
        finally:
            self._reconnecting = False
    
    async def _energy_calculator_hourly_loop(self):
        """Background task that runs energy calculator every hour at :00 minutes.
        Also calculates and stores array and system hourly energy aggregations."""
        from datetime import datetime, timedelta
        from solarhub.timezone_utils import now_configured
        from solarhub.energy_calculator import EnergyCalculator
        
        log.info("Starting energy calculator hourly background task")
        last_run_hour = None
        
        while True:
            try:
                now = now_configured()
                current_hour = now.replace(minute=0, second=0, microsecond=0)
                
                # Run if we haven't run for this hour yet
                if last_run_hour != current_hour:
                    # Calculate the previous hour's start time
                    previous_hour_start = current_hour - timedelta(hours=1)
                    
                    log.info(f"Running energy calculator for hour: {previous_hour_start.strftime('%Y-%m-%d %H:00:00')}")
                    
                    try:
                        await self._execute_energy_calculator(previous_hour_start)
                        last_run_hour = current_hour
                        log.info(f"Energy calculator completed successfully for hour: {previous_hour_start.strftime('%Y-%m-%d %H:00:00')}")
                    except Exception as e:
                        log.error(f"Error in energy calculator: {e}", exc_info=True)
                
                # Sleep for 60 seconds, then check again
                # This ensures we catch the hour boundary accurately
                await asyncio.sleep(60)
                
            except Exception as e:
                log.error(f"Error in energy calculator hourly loop: {e}", exc_info=True)
                await asyncio.sleep(60)  # Continue on error
    
    async def _execute_energy_calculator(self, hour_start: datetime = None):
        """Execute energy calculator for all inverters and arrays to process the previous hour's data."""
        from solarhub.timezone_utils import now_configured
        from solarhub.energy_calculator import EnergyCalculator
        
        # Calculate the previous hour's start time if not provided
        if hour_start is None:
            now = now_configured()
            hour_start = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
        
        log.info(f"Executing energy calculator for hour: {hour_start.strftime('%Y-%m-%d %H:00:00')}")
        
        # Process each inverter
        for rt in self.inverters:
            try:
                log.info(f"Processing energy calculation for inverter: {rt.cfg.id}")
                
                # Calculate and store hourly energy data
                self.energy_calculator.calculate_and_store_hourly_energy(
                    inverter_id=rt.cfg.id,
                    hour_start=hour_start
                )
                
                log.info(f"Energy calculation completed for inverter: {rt.cfg.id}")
                
            except Exception as e:
                log.error(f"Failed to calculate energy for inverter {rt.cfg.id}: {e}", exc_info=True)
                continue
        
        # Process arrays (aggregate from member inverters and store in array_hourly_energy)
        energy_calc = EnergyCalculator(self.logger.path)
        
        # Use hierarchy if available, otherwise fallback to config arrays
        if hasattr(self, 'hierarchy_systems') and self.hierarchy_systems:
            # Process arrays from hierarchy
            for system_id, system in self.hierarchy_systems.items():
                for inverter_array in system.inverter_arrays:
                    array_id = inverter_array.id
                    inverter_ids = inverter_array.inverter_ids
                    
                    if not inverter_ids:
                        continue
                    
                    try:
                        log.info(f"Processing energy calculation for array: {array_id} (system: {system_id})")
                        
                        # Calculate and store array hourly energy
                        energy_calc.calculate_and_store_array_hourly_energy(
                            array_id=array_id,
                            system_id=system_id,
                            inverter_ids=inverter_ids,
                            hour_start=hour_start
                        )
                        
                        log.info(f"Array energy calculation and storage completed for {array_id}")
                        
                    except Exception as e:
                        log.error(f"Failed to calculate energy for array {array_id}: {e}", exc_info=True)
                        continue
                
                # Calculate and store system hourly energy
                try:
                    array_ids = [arr.id for arr in system.inverter_arrays]
                    if array_ids:
                        log.info(f"Processing energy calculation for system: {system_id}")
                        energy_calc.calculate_and_store_system_hourly_energy(
                            system_id=system_id,
                            array_ids=array_ids,
                            hour_start=hour_start
                        )
                        log.info(f"System energy calculation and storage completed for {system_id}")
                except Exception as e:
                    log.error(f"Failed to calculate energy for system {system_id}: {e}", exc_info=True)
                    
                except Exception as e:
                    log.error(f"Failed to calculate energy for array {array_id}: {e}", exc_info=True)
                    continue

    async def _backfill_today_hourly_energy(self):
        """Backfill today's hourly_energy rows up to the last completed hour for all inverters."""
        from datetime import timedelta
        from solarhub.timezone_utils import now_configured
        now = now_configured()
        last_complete = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)

        if last_complete < start_of_day:
            log.info("No backfill needed (no completed hour yet today)")
            return

        log.info(f"Backfilling hourly energy from {start_of_day.strftime('%Y-%m-%d %H:%M')} to {last_complete.strftime('%Y-%m-%d %H:%M')}")
        for rt in self.inverters:
            current = start_of_day
            while current <= last_complete:
                try:
                    # This will upsert the hour if missing, or refresh it
                    self.energy_calculator.calculate_and_store_hourly_energy(
                        inverter_id=rt.cfg.id,
                        hour_start=current
                    )
                except Exception as e:
                    log.warning(f"Backfill failed for inverter {rt.cfg.id} at {current}: {e}")
                current += timedelta(hours=1)
        log.info("Backfill completed for today's hours")
    
    def shutdown(self):
        """Shutdown the application and clean up resources."""
        log.info("Shutting down solar monitoring application")
        
        # Stop all battery adapter background listening tasks if they exist
        # Note: shutdown() is synchronous, so we can't await stop_listening()
        # The listening task will be cancelled when the event loop stops
        # Legacy: stop single battery_adapter
        if self.battery_adapter and hasattr(self.battery_adapter, '_listening_task'):
            listening_task = getattr(self.battery_adapter, '_listening_task', None)
            if listening_task and not listening_task.done():
                try:
                    listening_task.cancel()
                    log.info("Cancelled battery adapter background listening task")
                except Exception as e:
                    log.warning(f"Error cancelling battery adapter background listening task: {e}")
        
        # Stop all battery banks from battery_adapters dict
        for bank_id, adapter in self.battery_adapters.items():
            # Skip if this is the same adapter as battery_adapter (already handled)
            if adapter == self.battery_adapter:
                continue
            
            if hasattr(adapter, '_listening_task'):
                listening_task = getattr(adapter, '_listening_task', None)
                if listening_task and not listening_task.done():
                    try:
                        listening_task.cancel()
                        log.info(f"Cancelled battery bank {bank_id} background listening task")
                    except Exception as e:
                        log.warning(f"Error cancelling battery bank {bank_id} background listening task: {e}")
        
        # Stop the command queue manager
        if hasattr(self, 'command_queue'):
            self.command_queue.stop()
            log.info("Command queue manager stopped")
        
        # Disconnect from MQTT
        if hasattr(self, 'mqtt'):
            self.mqtt.disconnect()
            log.info("MQTT disconnected")
        
        log.info("Application shutdown complete")

    async def _poll_one(self, rt: InverterRuntime):
        try:
            log.debug(f"Polling inverter: {rt.cfg.id}")
            
            # Check if adapter client is connected
            client = getattr(rt.adapter, 'client', None)
            if client and hasattr(client, 'connected') and not client.connected:
                log.warning(f"Inverter {rt.cfg.id} client not connected, skipping poll")
                # Mark as disconnected for reconnection attempt
                self._devices_connected = False
                # Don't immediately count as failure - let reconnection logic handle it
                # Failure counting should only happen after reconnection attempts fail
                # This prevents rapid failure count increments during temporary disconnections
                return
            
            # Notify command queue that telemetry polling is starting
            self.command_queue.notify_telemetry_polling()
            
            tel = await rt.adapter.poll()
            
            # Reset failure count on successful poll (device is working)
            if hasattr(self, 'recovery_manager') and self.recovery_manager and rt.cfg.adapter.serial_port and hasattr(self, 'device_registry') and self.device_registry:
                # Try to find device in registry and mark as recovered if it was in recovery state
                devices = self.device_registry.get_all_devices()
                for dev in devices:
                    if dev.port == rt.cfg.adapter.serial_port and dev.status == "recovering":
                        # Device successfully polled, mark as recovered
                        self.device_registry.mark_device_recovered(dev.device_id)
                        log.info(f"Device {dev.device_id} recovered after successful poll")
                        break
            
            # Log key telemetry values with inverter mode correlation
            from solarhub.schedulers.helpers import InverterManager
            mode_str = InverterManager.get_current_work_mode(tel.extra or {})
            
            # Determine power source
            power_source = "Unknown"
            if tel.batt_power_w > 50:
                power_source = "Battery charging"
            elif tel.batt_power_w < -50:
                power_source = "Battery discharging"
            elif tel.grid_power_w > 50:
                power_source = "Grid supplying"
            elif tel.grid_power_w < -50:
                power_source = "Grid charging"
            elif tel.pv_power_w > 50:
                power_source = "Solar only"
            else:
                power_source = "Idle"
            
            log.info(f"Inverter {rt.cfg.id} telemetry - SOC: {tel.batt_soc_pct}%, Mode: {mode_str}, "
                    f"Source: {power_source}, PV: {tel.pv_power_w}W, Load: {tel.load_power_w}W, "
                    f"Batt: {tel.batt_power_w}W, Grid: {tel.grid_power_w}W")
            
            # Optionally override battery metrics from external battery adapter
            try:
                if (
                    getattr(self.cfg, "battery_data_source", "inverter") == "battery_adapter"
                    and self.battery_last
                ):
                    # Get first bank's telemetry for backward compatibility
                    if isinstance(self.battery_last, dict):
                        batt = next(iter(self.battery_last.values())) if self.battery_last else None
                    else:
                        batt = self.battery_last  # Legacy: single object
                    if batt:
                        # Mutate telemetry object so downstream (DB, API, energy calc) is consistent
                        tel.batt_soc_pct = batt.soc
                        tel.batt_voltage_v = batt.voltage
                        tel.batt_current_a = batt.current
                        if batt.voltage is not None and batt.current is not None:
                            tel.batt_power_w = round(batt.voltage * batt.current)
                        # Mark source in extra
                        if tel.extra is None:
                            tel.extra = {}
                        tel.extra["battery_data_source"] = "battery_adapter"
            except Exception as e:
                log.debug("Battery override failed: %s", e)

            # Create payload with standardized field names
            # Use model_dump with exclude={'extra'} to avoid circular references
            # We'll add extra separately after ensuring it's JSON-serializable
            tel_dict = tel.model_dump(exclude={'extra'}, mode='python')
            payload = {"id": rt.cfg.id, **tel_dict}
            
            # Add all standardized data from extra (already mapped by TelemetryMapper)
            # Ensure extra is JSON-serializable by converting to plain dict
            if tel.extra:
                # Convert extra to plain dict, filtering out any non-serializable objects
                # Use a helper to recursively make values JSON-serializable
                extra_dict = {}
                visited = set()  # Track visited objects to detect circular references
                
                def make_serializable(value: Any, visited_set: set) -> Any:
                    """Recursively make value JSON-serializable, handling circular references."""
                    # Check for circular references
                    if isinstance(value, (dict, list)):
                        obj_id = id(value)
                        if obj_id in visited_set:
                            return "<circular reference>"
                        visited_set.add(obj_id)
                    
                    try:
                        if isinstance(value, dict):
                            return {k: make_serializable(v, visited_set.copy()) for k, v in value.items()}
                        elif isinstance(value, (list, tuple)):
                            return [make_serializable(item, visited_set.copy()) for item in value]
                        elif isinstance(value, (str, int, float, bool, type(None))):
                            return value
                        else:
                            # Try to serialize, fallback to string
                            try:
                                json.dumps(value)
                                return value
                            except (TypeError, ValueError):
                                return str(value)
                    finally:
                        if isinstance(value, (dict, list)):
                            visited_set.discard(id(value))
                
                for key, value in tel.extra.items():
                    try:
                        serialized_value = make_serializable(value, visited.copy())
                        extra_dict[key] = serialized_value
                    except Exception as e:
                        log.debug(f"Skipping non-serializable key in extra: {key}, error: {e}")
                        continue
                
                payload.update(extra_dict)
            
            # If adapter has a mapper and register map, ensure all registers are included
            if hasattr(rt.adapter, 'mapper') and rt.adapter.mapper and hasattr(rt.adapter, 'regs') and rt.adapter.regs:
                # Get all standardized field names from mapper
                for reg in rt.adapter.regs:
                    reg_id = reg.get("id")
                    if not reg_id:
                        continue
                    
                    # Get standardized field name
                    standard_id = rt.adapter.mapper.get_standard_field(reg_id)
                    
                    # If we have this value in device data but not in payload, add it
                    # Check if value exists in extra but with different key
                    if standard_id not in payload:
                        # Try to find it by device-specific ID
                        if reg_id in tel.extra:
                            payload[standard_id] = tel.extra[reg_id]
                        # Also check if standard_id is already in extra with different casing
                        elif standard_id in tel.extra:
                            payload[standard_id] = tel.extra[standard_id]
            
            # Ensure backward compatibility - keep device-specific keys too
            # Note: extra_dict already contains all keys from tel.extra, so this is redundant
            # But we keep it for safety in case extra_dict was filtered
            # Values are already serialized in extra_dict above, so we can safely add them
            # (This section is now mostly redundant but kept for clarity)
            
            # Add inverter metadata (phase type, inverter count)
            from solarhub.inverter_metadata import get_inverter_metadata, get_publishable_fields
            
            # Get inverter count
            inverter_count = len(self.inverters) if self.inverters else 1
            
            # Get phase type from config or detect from telemetry
            config_phase_type = getattr(rt.cfg, 'phase_type', None)
            metadata = get_inverter_metadata(payload, config_phase_type, inverter_count)
            
            # Add metadata to payload
            payload["_metadata"] = metadata.to_dict()
            
            # For MQTT/HA, optionally filter to only publishable fields based on phase type
            # But keep all fields for backward compatibility and API access
            # The frontend/HA can use _metadata to determine what to display
            
            # Debug logging for device model and serial number
            if "device_model" in payload:
                log.debug(f"Publishing device_model: '{payload['device_model']}'")
            if "device_serial_number" in payload:
                log.debug(f"Publishing device_serial_number: '{payload['device_serial_number']}'")
            
            # Publish current inverter configuration values to Home Assistant
            if self.smart and self.smart.inverter_config_ha:
                try:
                    log.info(f"Syncing inverter config states to HA for {rt.cfg.id}")
                    # Pass the register map from the adapter if available
                    register_map = getattr(rt.adapter, 'regs', None)
                    if register_map:
                        self.smart.inverter_config_ha.publish_current_inverter_config_values(rt.cfg.id, payload, register_map)
                    else:
                        log.debug(f"No register map available for {rt.cfg.id}, skipping config state sync")
                except Exception as e:
                    log.warning(f"Failed to publish current inverter config values: {e}")
            
            # publish availability (retain)
            log.debug(f"Publishing availability for {rt.cfg.id}")
            self.mqtt.pub(f"{self.cfg.mqtt.base_topic}/{rt.cfg.id}/availability", "online", retain=True)
            
            # publish flat data to the ONLY state topic we'll use for HA entities
            log.debug(f"Publishing telemetry data for {rt.cfg.id} to MQTT")
            try:
                self.mqtt.pub(f"{self.cfg.mqtt.base_topic}/{rt.cfg.id}/regs", payload, retain=False)
            except Exception as e:
                log.error(f"Failed to publish telemetry to MQTT for {rt.cfg.id}: {e}", exc_info=True)
                # Don't raise - continue with other operations

            #self.mqtt.pub(f"{self.cfg.mqtt.base_topic}/{rt.cfg.id}/state", payload)
            if payload:
             #   self.mqtt.pub(f"{self.cfg.mqtt.base_topic}/{rt.cfg.id}/regs", tel.extra)
                model = payload.get("device_model") or payload.get("model_name")
                # Get serial number from payload dict or tel.extra dict (tel is a Pydantic model, not a dict)
                sn = payload.get("device_serial_number") or payload.get("serial_number") or (tel.extra.get("sn") if tel.extra else None) or getattr(tel, "sn", None)
                changed = False
                if model and getattr(rt, "ha_model", None) != model:
                    rt.ha_model = str(model)
                    changed = True
                if sn and getattr(rt, "ha_serial", None) != sn:
                    rt.ha_serial = str(sn)
                    changed = True
                if changed:
                    # Re-publish discovery with richer device block (same unique_ids -> HA updates)
                    inverter_count = len(self.inverters) if self.inverters else 1
                    self.ha.refresh_device_info(rt, inverter_count)
            # Log and accumulate daily PV
            log.debug(f"Storing telemetry for {rt.cfg.id} in database")
            self.logger.insert_sample(rt.cfg.id, tel)
            
            # Aggregate and store array telemetry from hierarchy
            array = None
            array_inverter_ids = []
            attached_battery_array_id = None
            
            if not hasattr(self, 'hierarchy_systems') or not self.hierarchy_systems:
                log.warning(f"No hierarchy systems available, skipping array aggregation for {rt.cfg.id}")
                return
            
            # Find array in hierarchy
            for system in self.hierarchy_systems.values():
                for inv_array in system.inverter_arrays:
                    if inv_array.array_id == tel.array_id:
                        array_inverter_ids = inv_array.inverter_ids
                        attached_battery_array_id = inv_array.attached_battery_array_id
                        array = inv_array
                        break
                if array:
                    break
            
            if array and array_inverter_ids:
                # Collect telemetry for all inverters in this array
                array_inverter_tels = {}
                for inv_rt in self.inverters:
                    if inv_rt.cfg.id in array_inverter_ids:
                        inv_tel = getattr(inv_rt.adapter, 'last_tel', None)
                        if inv_tel:
                            array_inverter_tels[inv_rt.cfg.id] = inv_tel
                
                # Get pack telemetry for attached packs
                pack_tels = {}
                pack_configs = {}
                
                # Use hierarchy battery arrays if available
                if hasattr(self, 'hierarchy_systems') and self.hierarchy_systems and attached_battery_array_id:
                    for system in self.hierarchy_systems.values():
                        for bat_array in system.battery_arrays:
                            if bat_array.battery_array_id == attached_battery_array_id:
                                # Get packs from this battery array
                                for pack in bat_array.battery_packs:
                                    pack_id = pack.pack_id
                                    if pack.nominal_kwh:
                                        pack_configs[pack_id] = {
                                            "nominal_kwh": pack.nominal_kwh,
                                            "max_charge_kw": pack.max_charge_kw or 0.0,
                                            "max_discharge_kw": pack.max_discharge_kw or 0.0,
                                        }
                                    
                                    # Get battery telemetry
                                    battery_telemetry = None
                                    if isinstance(self.battery_last, dict):
                                        battery_telemetry = self.battery_last.get(pack_id) or next(iter(self.battery_last.values())) if self.battery_last else None
                                    else:
                                        battery_telemetry = self.battery_last  # Legacy: single object
                                    
                                    if battery_telemetry:
                                        from solarhub.array_models import BatteryPackTelemetry
                                        pack_tel = BatteryPackTelemetry(
                                            pack_id=pack_id,
                                            array_id=tel.array_id,
                                            ts=battery_telemetry.ts,
                                            soc_pct=battery_telemetry.soc,
                                            voltage_v=battery_telemetry.voltage,
                                            current_a=battery_telemetry.current,
                                            power_w=battery_telemetry.voltage * battery_telemetry.current if battery_telemetry.voltage and battery_telemetry.current else None,
                                            temperature_c=battery_telemetry.temperature,
                                        )
                                        pack_tels[pack_id] = pack_tel
                                break
                        if pack_tels:
                            break
                
                # Fallback to config-based pack lookup
                if not pack_tels and self.cfg.battery_packs and self.cfg.attachments:
                    for att in self.cfg.attachments:
                        if att.array_id == tel.array_id and att.detached_at is None:
                            pack_id = att.pack_id
                            pack_cfg = next((p for p in self.cfg.battery_packs if p.id == pack_id), None)
                            if pack_cfg:
                                pack_configs[pack_id] = {
                                    "nominal_kwh": pack_cfg.nominal_kwh,
                                    "max_charge_kw": pack_cfg.max_charge_kw,
                                    "max_discharge_kw": pack_cfg.max_discharge_kw,
                                }
                                # Use battery_last if available (single pack assumption for now)
                                # Get first bank's telemetry for backward compatibility
                                battery_telemetry = None
                                if isinstance(self.battery_last, dict):
                                    battery_telemetry = next(iter(self.battery_last.values())) if self.battery_last else None
                                else:
                                    battery_telemetry = self.battery_last  # Legacy: single object
                                
                                # Check if pack_id exists in hierarchy
                                pack_exists = False
                                if hasattr(self, 'hierarchy_systems') and self.hierarchy_systems:
                                    for system in self.hierarchy_systems.values():
                                        for bat_array in system.battery_arrays:
                                            if any(p.pack_id == pack_id for p in bat_array.battery_packs):
                                                pack_exists = True
                                                break
                                        if pack_exists:
                                            break
                                
                                if battery_telemetry and pack_exists:
                                    from solarhub.array_models import BatteryPackTelemetry
                                    pack_tel = BatteryPackTelemetry(
                                        pack_id=pack_id,
                                        array_id=tel.array_id,
                                        ts=battery_telemetry.ts,
                                        soc_pct=battery_telemetry.soc,
                                        voltage_v=battery_telemetry.voltage,
                                        current_a=battery_telemetry.current,
                                        power_w=battery_telemetry.voltage * battery_telemetry.current if battery_telemetry.voltage and battery_telemetry.current else None,
                                        temperature_c=battery_telemetry.temperature,
                                    )
                                    pack_tels[pack_id] = pack_tel
                
                # Aggregate array telemetry
                if array_inverter_tels:
                    # Get system_id from hierarchy if available
                    system_id = None
                    if hasattr(self, '_hierarchy_inverters') and rt.cfg.id in self._hierarchy_inverters:
                        inverter_obj = self._hierarchy_inverters[rt.cfg.id]
                        system_id = getattr(inverter_obj, 'system_id', None)
                    
                    array_tel = self.array_aggregator.aggregate_array_telemetry(
                        tel.array_id, array_inverter_tels, pack_tels, pack_configs, system_id=system_id
                    )
                    # Store array sample
                    self.logger.insert_array_sample(array_tel)
                    # Store array telemetry for home aggregation
                    self.array_last[tel.array_id] = array_tel
                    # Publish array telemetry to MQTT
                    array_topic = f"{self.cfg.mqtt.base_topic}/arrays/{tel.array_id}/state"
                    self.mqtt.pub(array_topic, array_tel.model_dump(), retain=False)
            
            acc = self._energy_acc.setdefault(rt.cfg.id, {"last_ts": None, "wh": 0.0})
            if tel.pv_power_w is not None:
                from datetime import datetime as _dt
                from solarhub.timezone_utils import parse_iso_to_configured
                now = parse_iso_to_configured(tel.ts)
                last_ts = acc["last_ts"]
                if last_ts is not None:
                    dt_h = (now - last_ts).total_seconds()/3600.0
                    prev_p = acc.get("last_pv", tel.pv_power_w)
                    wh = ((prev_p + tel.pv_power_w)/2.0) * dt_h
                    acc["wh"] += wh
                acc["last_ts"] = now
                acc["last_pv"] = tel.pv_power_w

                from solarhub.timezone_utils import get_configured_date_string
                day = get_configured_date_string()
                self.logger.upsert_daily_pv(day, rt.cfg.id, round(acc["wh"]/1000.0, 3))

            cfg_state = {
                "max_charge_a": rt.cfg.safety.max_charge_a,
                "max_discharge_a": rt.cfg.safety.max_discharge_a,
            }
            self.mqtt.pub(f"{self.cfg.mqtt.base_topic}/{rt.cfg.id}/cfg_state", cfg_state)
        except Exception as e:
            log.warning("Poll failed for %s: %s", rt.cfg.id, e)
            # Only count as failure if it's a real error (not just disconnected client)
            # Disconnected clients are handled by reconnection logic, not failure counting
            error_str = str(e).lower()
            if "client not connected" not in error_str and "not connected" not in error_str:
                # This is a real failure (not just disconnection), handle it
                if hasattr(self, 'recovery_manager') and self.recovery_manager and rt.cfg.adapter.serial_port and hasattr(self, 'device_registry') and self.device_registry:
                    # Try to find device in registry
                    devices = self.device_registry.get_all_devices()
                    for dev in devices:
                        if dev.port == rt.cfg.adapter.serial_port:
                            # Only count failure if device is not already permanently disabled
                            if dev.status != "permanently_disabled":
                                await self.recovery_manager.handle_device_failure(dev.device_id)
                            break

    def _aggregate_and_publish_home_telemetry(self):
        """Aggregate system/home telemetry from all arrays and publish to MQTT."""
        if not self.array_last:
            return
        
        try:
            # Group arrays by system_id from hierarchy
            arrays_by_system: Dict[str, Dict[str, Any]] = {}
            
            # If we have hierarchy, group by system_id
            if hasattr(self, 'hierarchy_systems') and self.hierarchy_systems:
                for system_id, system in self.hierarchy_systems.items():
                    arrays_by_system[system_id] = {}
                    # Find arrays belonging to this system
                    for array_id, array_tel in self.array_last.items():
                        # Check if this array belongs to this system
                        for inverter_array in system.inverter_arrays:
                            if inverter_array.id == array_id:
                                arrays_by_system[system_id][array_id] = array_tel
                                break
            else:
                # Fallback: use default system_id
                default_system_id = "system"
                arrays_by_system[default_system_id] = self.array_last
            
            # Aggregate and publish telemetry for each system
            for system_id, system_arrays in arrays_by_system.items():
                if not system_arrays:
                    continue
                
                # Get system-attached meters
                meter_telemetry = {}
                meter_configs = {}
                if hasattr(self, '_hierarchy_meters') and self._hierarchy_meters:
                    for meter_id, meter_obj in self._hierarchy_meters.items():
                        if getattr(meter_obj, 'system_id', None) == system_id:
                            if meter_id in self.meter_last:
                                meter_telemetry[meter_id] = self.meter_last[meter_id]
                            # Get meter config for energy data lookup
                            if self.cfg.meters:
                                meter_cfg = next((m for m in self.cfg.meters if m.id == meter_id), None)
                                if meter_cfg:
                                    meter_configs[meter_id] = meter_cfg
                else:
                    # Fallback to config-based meter lookup
                    if self.cfg.meters:
                        for meter_cfg in self.cfg.meters:
                            attachment_target = getattr(meter_cfg, 'attachment_target', None)
                            if attachment_target == "system" or attachment_target == system_id:
                                meter_id = meter_cfg.id
                                if meter_id in self.meter_last:
                                    meter_telemetry[meter_id] = self.meter_last[meter_id]
                                meter_configs[meter_id] = meter_cfg
                
                # Get all battery bank telemetry for aggregation
                battery_bank_telemetry = {}
                if isinstance(self.battery_last, dict):
                    battery_bank_telemetry = self.battery_last
                elif self.battery_last:
                    # Legacy: single battery bank
                    battery_bank_telemetry["legacy"] = self.battery_last
                
                # Aggregate system telemetry using SystemAggregator
                system_tel = self.system_aggregator.aggregate_system_telemetry(
                    system_id, system_arrays, meter_telemetry, battery_bank_telemetry,
                    meter_configs=meter_configs if meter_configs else None
                )
                
                # Publish system telemetry to MQTT
                system_topic = f"{self.cfg.mqtt.base_topic}/systems/{system_id}/state"
                self.mqtt.pub(system_topic, system_tel.model_dump(), retain=False)
                log.debug(f"Published system telemetry to {system_topic}")
                
                # Also publish to legacy home topic for backward compatibility
                home_topic = f"{self.cfg.mqtt.base_topic}/home/{system_id}/state"
                self.mqtt.pub(home_topic, system_tel.model_dump(), retain=False)
                log.debug(f"Published home telemetry (legacy) to {home_topic}")
        except Exception as e:
            log.warning(f"Failed to aggregate and publish system/home telemetry: {e}", exc_info=True)

    # --- Live telemetry access for API ---
    def get_now(self, inverter_id: str) -> Dict[str, Any] | None:
        try:
            log.debug(f"Getting telemetry for inverter_id: {inverter_id}")
            log.debug(f"Available inverters: {[rt.cfg.id for rt in self.inverters]}")
            
            # Prefer adapter's last telemetry snapshot
            for rt in self.inverters:
                if rt.cfg.id == inverter_id:
                    tel = getattr(rt.adapter, 'last_tel', None)
                    log.debug(f"Found telemetry for {inverter_id}: {tel is not None}")
                    if tel:
                        log.debug(f"Telemetry type: {type(tel)}")
                        # Convert Telemetry object to dictionary - try both v1 and v2 methods
                        try:
                            result = tel.model_dump()  # Pydantic v2
                            log.debug(f"Successfully converted using model_dump() for {inverter_id}")
                            # Ensure inverter_id is set in the result
                            if 'inverter_id' not in result or result.get('inverter_id') != inverter_id:
                                result['inverter_id'] = inverter_id
                            log.debug(f"Returning telemetry for {inverter_id} with batt_power_w={result.get('batt_power_w')}")
                            return result
                        except AttributeError:
                            result = tel.dict()  # Pydantic v1
                            log.debug(f"Successfully converted using dict() for {inverter_id}")
                            # Ensure inverter_id is set in the result
                            if 'inverter_id' not in result or result.get('inverter_id') != inverter_id:
                                result['inverter_id'] = inverter_id
                            log.debug(f"Returning telemetry for {inverter_id} with batt_power_w={result.get('batt_power_w')}")
                            return result
            
            # Don't use fallback - return None if specific inverter not found
            # This prevents returning wrong inverter's data
            log.warning(f"Inverter '{inverter_id}' not found. Available inverters: {[rt.cfg.id for rt in self.inverters]}")
            return None
        except Exception as e:
            log.warning(f"Error getting telemetry for {inverter_id}: {e}")
            import traceback
            log.warning(f"Traceback: {traceback.format_exc()}")
            return None

    async def _poll_battery(self, bank_id: Optional[str] = None):
        """
        Poll a battery bank. If bank_id is None, uses legacy self.battery_adapter.
        If bank_id is provided, uses self.battery_adapters[bank_id].
        """
        # Determine which adapter to use
        if bank_id is None:
            # Legacy mode: use self.battery_adapter
            adapter = self.battery_adapter
            bank_cfg = getattr(self.cfg, "battery_bank", None)
        else:
            # New mode: use specific bank
            adapter = self.battery_adapters.get(bank_id)
            bank_cfg = next((b for b in (self.cfg.battery_banks or []) if b.id == bank_id), None)
            if not bank_cfg and getattr(self.cfg, "battery_bank", None) and getattr(self.cfg.battery_bank, "id", None) == bank_id:
                bank_cfg = self.cfg.battery_bank
        
        if not adapter:
            return
        
        # Check connection status - support both serial (is_open) and BLE (is_connected) adapters
        is_connected = False
        if hasattr(adapter, 'client') and adapter.client:
            # Serial adapters (pytes, jkbms_passive) use is_open
            if hasattr(adapter.client, 'is_open'):
                is_connected = adapter.client.is_open
            # Bluetooth adapters (jkbms_ble) use is_connected
            elif hasattr(adapter.client, 'is_connected'):
                is_connected = adapter.client.is_connected
        
        # For adapters with batteries dict (jkbms_ble with multiple batteries)
        if not is_connected and hasattr(adapter, 'batteries') and adapter.batteries:
            # Check if at least one battery is connected
            is_connected = any(
                hasattr(bat, 'client') and bat.client and 
                (hasattr(bat.client, 'is_connected') and bat.client.is_connected)
                for bat in adapter.batteries.values()
            )
        
        if not is_connected:
            log.warning(f"Battery adapter for {bank_id or 'legacy'} not connected, attempting reconnection...")
            try:
                await adapter.connect()
                log.info(f"Successfully reconnected battery adapter for {bank_id or 'legacy'}")
            except Exception as e:
                log.warning(f"Failed to reconnect battery adapter for {bank_id or 'legacy'}: {e}")
                # Mark as disconnected for reconnection attempt
                self._devices_connected = False
                return
        
        try:
            tel = await adapter.poll()  # type: ignore[attr-defined]
            # Store telemetry by bank_id
            actual_bank_id = bank_id or (getattr(bank_cfg, "id", None) if bank_cfg else None) or tel.id
            # Ensure battery_last is always a dict
            if not isinstance(self.battery_last, dict):
                self.battery_last = {}
            self.battery_last[actual_bank_id] = tel
            # Log a concise summary for the battery bank
            try:
                log.debug(
                    "Battery bank %s - SOC: %s%%, V: %sV, I: %sA, T: %sC, Batteries: %s, Cells/Batt: %s",
                    tel.id,
                    tel.soc,
                    tel.voltage,
                    tel.current,
                    tel.temperature,
                    tel.batteries_count,
                    tel.cells_per_battery,
                )
                # One line per battery unit
                for dev in tel.devices:
                    try:
                        log.debug(
                            "Battery #%s - SOC: %s%%, V: %sV, I: %sA, T: %sC, St: %s/%s/%s",
                            getattr(dev, 'power', None),
                            getattr(dev, 'soc', None),
                            getattr(dev, 'voltage', None),
                            getattr(dev, 'current', None),
                            getattr(dev, 'temperature', None),
                            getattr(dev, 'basic_st', None),
                            getattr(dev, 'volt_st', None),
                            getattr(dev, 'temp_st', None),
                        )
                    except Exception:
                        continue
            except Exception:
                pass
            # Use bank ID from config to ensure it matches discovery
            actual_bank_id = bank_id or (getattr(bank_cfg, "id", None) if bank_cfg else None) or tel.id
            base = f"{self.cfg.mqtt.base_topic}/battery/{actual_bank_id}"
            
            # Bank-level
            self.mqtt.pub(f"{base}/availability", "online", retain=True)
            payload = tel.model_dump()
            payload.update(tel.extra or {})
            # Ensure bank_id in payload matches what we're using
            payload["id"] = actual_bank_id
            # Calculate power from voltage and current if available
            if payload.get("voltage") is not None and payload.get("current") is not None:
                try:
                    power = float(payload["voltage"]) * float(payload["current"])
                    payload["power"] = round(power, 1)
                except (ValueError, TypeError):
                    pass
            # Log what we're publishing for debugging
            log.info(f"Publishing battery bank data: bank_id={actual_bank_id}, topic={base}/regs, has_soc={payload.get('soc') is not None}, has_voltage={payload.get('voltage') is not None}, has_power={payload.get('power') is not None}")
            self.mqtt.pub(f"{base}/regs", payload, retain=False)
            log.debug(f"Published battery bank data to {base}/regs with payload keys: {list(payload.keys())}")

            # Battery-level (each unit) - publish discovery if not already done
            for dev in tel.devices:
                try:
                    dev_payload = dev.model_dump() if hasattr(dev, 'model_dump') else dev.dict()
                    # Calculate power from voltage and current if available
                    if dev_payload.get("voltage") is not None and dev_payload.get("current") is not None:
                        try:
                            power = float(dev_payload["voltage"]) * float(dev_payload["current"])
                            dev_payload["power"] = round(power, 1)
                        except (ValueError, TypeError):
                            pass
                    self.mqtt.pub(f"{base}/{dev.power}/regs", dev_payload, retain=False)
                    log.debug(f"Published battery unit {dev.power} data to {base}/{dev.power}/regs")
                    
                    # Publish discovery for this unit if not already done (check on first poll)
                    if not hasattr(self, '_battery_units_discovered'):
                        self._battery_units_discovered = set()
                    unit_key = f"{actual_bank_id}:{dev.power}"
                    if unit_key not in self._battery_units_discovered:
                        bank_name = getattr(bank_cfg, "name", None) if bank_cfg else None
                        try:
                            self.ha.publish_battery_unit_entities(
                                bank_id=actual_bank_id,
                                unit_power=dev.power,
                                bank_name=bank_name
                            )
                            self._battery_units_discovered.add(unit_key)
                            log.info(f"Published HA discovery for battery unit {dev.power} in bank {actual_bank_id}")
                        except Exception as e:
                            log.error(f"Failed to publish discovery for battery unit {dev.power}: {e}", exc_info=True)
                except Exception as e:
                    log.warning(f"Failed to publish battery unit {getattr(dev, 'power', 'unknown')} data: {e}")
                    continue

            # Cells: publish per-battery stats and per-cell rows if present
            if tel.cells_data:
                log.debug(f"Publishing cells data for {len(tel.cells_data)} batteries")
                # Track discovered cells to avoid republishing discovery
                if not hasattr(self, '_battery_cells_discovered'):
                    self._battery_cells_discovered = set()
                
                for entry in tel.cells_data:
                    p = entry.get("power")
                    if not p:
                        continue
                    cells = entry.get("cells") or []
                    log.debug(f"Battery {p}: {len(cells)} cells, stats: {entry.get('voltage_delta', 'N/A')}V delta")
                    # publish stats except the 'cells' list
                    stats = {k: v for k, v in entry.items() if k not in ("cells", "power")}
                    if stats:
                        self.mqtt.pub(f"{base}/{p}/cells_stats", stats, retain=False)
                    for cell in cells:
                        cidx = cell.get("cell")
                        if not cidx:
                            continue
                        # Calculate power from voltage and current if available
                        cell_payload = dict(cell)  # Make a copy to avoid modifying original
                        if cell_payload.get("voltage") is not None and cell_payload.get("current") is not None:
                            try:
                                power = float(cell_payload["voltage"]) * float(cell_payload["current"])
                                cell_payload["power"] = round(power, 1)
                            except (ValueError, TypeError):
                                pass
                        # Publish cell data
                        self.mqtt.pub(f"{base}/{p}/cells/{cidx}/regs", cell_payload, retain=False)
                        log.debug(f"Published cell {cidx} data for battery {p} to {base}/{p}/cells/{cidx}/regs")
                        
                        # Publish discovery for this cell if not already done
                        cell_key = f"{actual_bank_id}:{p}:{cidx}"
                        if cell_key not in self._battery_cells_discovered:
                            bank_name = getattr(bank_cfg, "name", None) if bank_cfg else None
                            try:
                                self.ha.publish_battery_cell_entities(
                                    bank_id=actual_bank_id,
                                    unit_power=p,
                                    cell_index=cidx,
                                    bank_name=bank_name
                                )
                                self._battery_cells_discovered.add(cell_key)
                                log.debug(f"Published HA discovery for cell {cidx} in battery unit {p} of bank {actual_bank_id}")
                            except Exception as e:
                                log.error(f"Failed to publish discovery for cell {cidx} in battery {p}: {e}", exc_info=True)
            else:
                log.warning("No cells_data available in battery telemetry")
            # Persist basic bank stats
            try:
                # Bank
                self.logger.insert_battery_bank_sample(
                    bank_id=tel.id,
                    ts_iso=tel.ts,
                    voltage=tel.voltage,
                    current=tel.current,
                    temperature=tel.temperature,
                    soc=tel.soc,
                    batteries_count=tel.batteries_count,
                    cells_per_battery=tel.cells_per_battery,
                )
                # Units
                self.logger.insert_battery_unit_samples(
                    bank_id=tel.id,
                    ts_iso=tel.ts,
                    devices=tel.devices,
                )
                # Cells
                if tel.cells_data:
                    self.logger.insert_battery_cell_samples(
                        bank_id=tel.id,
                        ts_iso=tel.ts,
                        cells_data=tel.cells_data,
                    )
            except Exception as e:
                log.debug(f"Battery DB logging failed: {e}")
        except Exception as e:
            log.warning("Battery poll failed: %s", e)
    
    async def _poll_meter(self, rt: MeterRuntime):
        """Poll a single meter and publish telemetry."""
        try:
            log.debug(f"Polling meter: {rt.cfg.id}")
            
            # Check if adapter client is connected
            client = getattr(rt.adapter, 'client', None)
            if client and hasattr(client, 'connected') and not client.connected:
                log.warning(f"Meter {rt.cfg.id} client not connected, skipping poll")
                self._devices_connected = False
                return
            
            tel = await rt.adapter.poll()
            self.meter_last[rt.cfg.id] = tel
            
            # Log meter telemetry summary
            log.info(f"Meter {rt.cfg.id} telemetry - Power: {tel.grid_power_w}W, "
                    f"Voltage: {tel.grid_voltage_v}V, Current: {tel.grid_current_a}A, "
                    f"Frequency: {tel.grid_frequency_hz}Hz, Energy: {tel.energy_kwh}kWh")
            
            # Publish availability
            self.mqtt.pub(f"{self.cfg.mqtt.base_topic}/meter/{rt.cfg.id}/availability", "online", retain=True)
            
            # Publish telemetry
            payload = tel.model_dump()
            if tel.extra:
                payload.update(tel.extra)
            
            self.mqtt.pub(f"{self.cfg.mqtt.base_topic}/meter/{rt.cfg.id}/regs", payload, retain=False)
            log.debug(f"Published meter {rt.cfg.id} telemetry to MQTT")
            
            # Store in database
            if self.logger:
                try:
                    self.logger.insert_meter_sample(rt.cfg.id, tel)
                    
                    # Update daily summary using daily import/export values from telemetry
                    # The IAMMeter adapter already tracks daily import/export that resets at midnight
                    from solarhub.timezone_utils import get_configured_date_string
                    today = get_configured_date_string()
                    
                    # Use daily import/export from telemetry (already in Wh, convert to kWh)
                    import_kwh = (tel.grid_import_wh or 0) / 1000.0
                    export_kwh = (tel.grid_export_wh or 0) / 1000.0
                    net_kwh = import_kwh - export_kwh
                    
                    # Track max power for the day (from current sample)
                    current_import_w = None
                    current_export_w = None
                    if tel.grid_power_w is not None:
                        if tel.grid_power_w > 0:
                            current_import_w = tel.grid_power_w
                        elif tel.grid_power_w < 0:
                            current_export_w = abs(tel.grid_power_w)
                    
                    # Get existing daily summary to update max values
                    max_import_w = None
                    max_export_w = None
                    sample_count = 1
                    try:
                        import sqlite3
                        con = sqlite3.connect(self.logger.path)
                        cur = con.cursor()
                        cur.execute("""
                            SELECT max_import_power_w, max_export_power_w, sample_count
                            FROM meter_daily
                            WHERE meter_id = ? AND day = ?
                        """, (rt.cfg.id, today))
                        existing = cur.fetchone()
                        con.close()
                        
                        if existing:
                            max_import_w = existing[0]
                            max_export_w = existing[1]
                            sample_count = (existing[2] or 0) + 1
                            
                            # Update max values if current is higher
                            if current_import_w is not None:
                                if max_import_w is None or current_import_w > max_import_w:
                                    max_import_w = current_import_w
                            
                            if current_export_w is not None:
                                if max_export_w is None or current_export_w > max_export_w:
                                    max_export_w = current_export_w
                        else:
                            # First sample of the day
                            max_import_w = current_import_w
                            max_export_w = current_export_w
                    except Exception as e:
                        log.debug(f"Could not get existing daily summary: {e}")
                        max_import_w = current_import_w
                        max_export_w = current_export_w
                    
                    # Store/update daily summary
                    self.logger.upsert_meter_daily(
                        day=today,
                        meter_id=rt.cfg.id,
                        import_kwh=import_kwh,
                        export_kwh=export_kwh,
                        net_kwh=net_kwh,
                        max_import_w=int(max_import_w) if max_import_w else None,
                        max_export_w=int(max_export_w) if max_export_w else None,
                        array_id=tel.array_id,
                        avg_voltage=tel.grid_voltage_v,
                        avg_current=tel.grid_current_a,
                        avg_frequency=tel.grid_frequency_hz,
                        sample_count=sample_count
                    )
                    log.debug(f"Updated daily summary for {rt.cfg.id}: Import={import_kwh:.2f}kWh, Export={export_kwh:.2f}kWh, Net={net_kwh:.2f}kWh")
                        
                except Exception as e:
                    log.warning(f"Failed to store meter sample for {rt.cfg.id}: {e}")
            
            log.debug(f"Meter {rt.cfg.id} poll completed successfully")
            
        except Exception as e:
            log.warning("Meter poll failed for %s: %s", rt.cfg.id, e)
