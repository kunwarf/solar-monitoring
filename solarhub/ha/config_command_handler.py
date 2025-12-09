"""
Handles Home Assistant configuration commands and updates settings in real-time.
"""
import json
import logging
from typing import Dict, Any, Optional
from solarhub.config import HubConfig, TariffConfig
from solarhub.logging.logger import DataLogger

log = logging.getLogger(__name__)

class ConfigCommandHandler:
    """Handles configuration commands from Home Assistant."""
    
    def __init__(self, config: HubConfig, logger: DataLogger, config_discovery=None):
        self.config = config
        self.logger = logger
        self.config_discovery = config_discovery
        
    async def handle_config_command(self, topic: str, payload: Any):
        """Handle configuration command from Home Assistant."""
        try:
            if isinstance(payload, (str, bytes)):
                data = json.loads(payload)
            else:
                data = payload
                
            log.info(f"Received config command: {data}")
            
            # Extract the setting name and value
            setting_name = data.get("setting")
            value = data.get("value")
            
            if not setting_name:
                log.warning("No setting name provided in config command")
                return
                
            # Update the configuration
            success = await self._update_config(setting_name, value)
            
            if success:
                log.info(f"Successfully updated {setting_name} to {value}")
                # Save to database for persistence
                self._save_to_database(setting_name, value)
                # Republish updated configuration values to Home Assistant
                if self.config_discovery:
                    try:
                        self.config_discovery.publish_current_config()
                        log.info(f"Republished configuration values to Home Assistant after updating {setting_name}")
                    except Exception as e:
                        log.warning(f"Failed to republish configuration values: {e}")
            else:
                log.warning(f"Failed to update {setting_name} to {value}")
                
        except Exception as e:
            log.error(f"Error handling config command: {e}")
    
    async def _update_config(self, setting_name: str, value: Any) -> bool:
        """Update configuration setting."""
        try:
            # Polling settings
            if setting_name == "polling_interval_secs":
                self.config.polling.interval_secs = float(value)
                return True
            elif setting_name == "polling_timeout_ms":
                self.config.polling.timeout_ms = int(value)
                return True
            
            # Logging settings
            elif setting_name == "logging_level":
                if value in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
                    self.config.logging.level = value
                    return True
            elif setting_name == "logging_ha_debug":
                self.config.logging.ha_debug = bool(value)
                return True
            
            # Forecast settings
            elif setting_name == "forecast_provider":
                if value in ["naive", "openmeteo", "weatherapi", "openweather", "simple"]:
                    self.config.smart.forecast.provider = value
                    return True
            elif setting_name == "forecast_enabled":
                self.config.smart.forecast.enabled = bool(value)
                return True
            elif setting_name == "forecast_lat":
                self.config.smart.forecast.lat = float(value)
                return True
            elif setting_name == "forecast_lon":
                self.config.smart.forecast.lon = float(value)
                return True
            elif setting_name == "forecast_tz":
                self.config.timezone = str(value)
                return True
            elif setting_name == "forecast_pv_dc_kw":
                self.config.smart.forecast.pv_dc_kw = float(value)
                return True
            elif setting_name == "forecast_batt_capacity_kwh":
                self.config.smart.forecast.batt_capacity_kwh = float(value)
                return True
            elif setting_name == "forecast_weatherapi_key":
                self.config.smart.forecast.weatherapi_key = str(value) if value else None
                return True
            elif setting_name == "forecast_openweather_key":
                self.config.smart.forecast.openweather_key = str(value) if value else None
                return True
            elif setting_name == "forecast_weatherbit_key":
                self.config.smart.forecast.weatherbit_key = str(value) if value else None
                return True
            
            # Policy settings
            elif setting_name == "policy_enabled":
                self.config.smart.policy.enabled = bool(value)
                return True
            elif setting_name == "smart_tick_interval_secs":
                self.config.smart.policy.smart_tick_interval_secs = float(value)
                return True
            elif setting_name == "overnight_min_soc_pct":
                self.config.smart.policy.overnight_min_soc_pct = int(value)
                return True
            elif setting_name == "blackout_reserve_soc_pct":
                self.config.smart.policy.blackout_reserve_soc_pct = int(value)
                return True
            elif setting_name == "target_full_before_sunset":
                self.config.smart.policy.target_full_before_sunset = bool(value)
                return True
            elif setting_name == "max_charge_power_w":
                self.config.smart.policy.max_charge_power_w = float(value)
                return True
            elif setting_name == "max_discharge_power_w":
                self.config.smart.policy.max_discharge_power_w = float(value)
                return True
            elif setting_name == "max_battery_soc_pct":
                self.config.smart.policy.max_battery_soc_pct = float(value)
                return True
            elif setting_name == "max_grid_charge_w":
                self.config.smart.policy.max_grid_charge_w = int(value)
                return True
            elif setting_name == "load_fallback_kw":
                self.config.smart.policy.load_fallback_kw = float(value)
                return True
            elif setting_name == "primary_mode":
                if value in ["self_use", "time_based"]:
                    self.config.smart.policy.primary_mode = value
                    return True
            elif setting_name == "enable_auto_mode_switching":
                self.config.smart.policy.enable_auto_mode_switching = bool(value)
                return True
            
            # Tariff settings
            elif setting_name == "tariffs":
                try:
                    tariffs_data = json.loads(value) if isinstance(value, str) else value
                    tariffs = [TariffConfig(**tariff) for tariff in tariffs_data]
                    self.config.smart.policy.tariffs = tariffs
                    return True
                except Exception as e:
                    log.error(f"Error parsing tariffs: {e}")
                    return False
            
            # Battery settings
            elif setting_name == "battery_data_source":
                if value in ["inverter", "battery_adapter"]:
                    # Set top-level selection for battery metrics source
                    setattr(self.config, 'battery_data_source', value)
                    return True
                return False
            elif setting_name == "battery_adapter_serial_port":
                if getattr(self.config, 'battery_bank', None) and getattr(self.config.battery_bank, 'adapter', None):
                    self.config.battery_bank.adapter.serial_port = str(value) if value else None
                    return True
                return False
            elif setting_name == "battery_adapter_baudrate":
                if getattr(self.config, 'battery_bank', None) and getattr(self.config.battery_bank, 'adapter', None):
                    self.config.battery_bank.adapter.baudrate = int(value)
                    return True
                return False
            elif setting_name == "battery_adapter_parity":
                if getattr(self.config, 'battery_bank', None) and getattr(self.config.battery_bank, 'adapter', None):
                    v = str(value).upper()
                    if v in ("N", "E", "O"):
                        self.config.battery_bank.adapter.parity = v
                        return True
                return False
            elif setting_name == "battery_adapter_stopbits":
                if getattr(self.config, 'battery_bank', None) and getattr(self.config.battery_bank, 'adapter', None):
                    self.config.battery_bank.adapter.stopbits = int(value)
                    return True
                return False
            elif setting_name == "battery_adapter_bytesize":
                if getattr(self.config, 'battery_bank', None) and getattr(self.config.battery_bank, 'adapter', None):
                    self.config.battery_bank.adapter.bytesize = int(value)
                    return True
                return False
            elif setting_name == "battery_adapter_batteries":
                if getattr(self.config, 'battery_bank', None) and getattr(self.config.battery_bank, 'adapter', None):
                    self.config.battery_bank.adapter.batteries = int(value)
                    return True
                return False
            elif setting_name == "battery_adapter_cells_per_battery":
                if getattr(self.config, 'battery_bank', None) and getattr(self.config.battery_bank, 'adapter', None):
                    self.config.battery_bank.adapter.cells_per_battery = int(value)
                    return True
                return False
            elif setting_name == "battery_adapter_dev_name":
                if getattr(self.config, 'battery_bank', None) and getattr(self.config.battery_bank, 'adapter', None):
                    self.config.battery_bank.adapter.dev_name = str(value)
                    return True
                return False
            elif setting_name == "battery_adapter_manufacturer":
                if getattr(self.config, 'battery_bank', None) and getattr(self.config.battery_bank, 'adapter', None):
                    self.config.battery_bank.adapter.manufacturer = str(value) if value else None
                    return True
                return False
            elif setting_name == "battery_adapter_model":
                if getattr(self.config, 'battery_bank', None) and getattr(self.config.battery_bank, 'adapter', None):
                    self.config.battery_bank.adapter.model = str(value) if value else None
                    return True
                return False
            else:
                log.warning(f"Unknown setting: {setting_name}")
                return False
                
        except Exception as e:
            log.error(f"Error updating config {setting_name}: {e}")
            return False
    
    def _save_to_database(self, setting_name: str, value: Any):
        """Save configuration to database for persistence."""
        try:
            # Convert value to string for database storage
            if isinstance(value, (dict, list)):
                value_str = json.dumps(value)
            else:
                value_str = str(value)
            
            # Determine the correct config path based on setting name
            if setting_name.startswith("forecast_"):
                config_path = f"smart.forecast.{setting_name}"
            elif setting_name.startswith("polling_"):
                config_path = f"polling.{setting_name}"
            elif setting_name.startswith("logging_"):
                config_path = f"logging.{setting_name}"
            else:
                # Battery settings
                if setting_name.startswith("battery_adapter_"):
                    # Map to battery_bank.adapter.*
                    suffix = setting_name[len("battery_adapter_"):]
                    config_path = f"battery_bank.adapter.{suffix}"
                elif setting_name == "battery_data_source":
                    config_path = "battery_data_source"
                else:
                    config_path = f"smart.policy.{setting_name}"
            
            # Save to database
            self.logger.set_config(config_path, value_str, "home_assistant")
            log.info(f"Saved {setting_name} to database at {config_path}")
            
        except Exception as e:
            log.error(f"Error saving {setting_name} to database: {e}")
