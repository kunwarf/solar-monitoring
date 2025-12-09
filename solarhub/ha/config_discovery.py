"""
Home Assistant discovery for all configurable settings.
Exposes polling, logging, smart, policy, and tariff settings as HA entities.
"""
import json
import logging
from datetime import datetime
from typing import Dict, Any, List
from solarhub.config import HubConfig

log = logging.getLogger(__name__)

class ConfigDiscoveryPublisher:
    """Publishes Home Assistant discovery messages for all configurable settings."""
    
    def __init__(self, mqtt, base_topic: str, config: HubConfig):
        self.mqtt = mqtt
        self.base_topic = base_topic
        self.config = config
        self.discovery_topic = f"{base_topic}/config"
        
    def publish_all_config_discovery(self):
        """Publish discovery messages for all configurable settings."""
        log.debug("Publishing configuration discovery messages")
        
        # Polling settings
        self._publish_polling_config()
        
        # Logging settings  
        self._publish_logging_config()
        
        # Smart forecast settings
        self._publish_forecast_config()
        
        # Policy settings
        self._publish_policy_config()
        
        # Tariff settings
        self._publish_tariff_config()
        
        # Battery adapter settings
        self._publish_battery_config()

        # Daily audit sensors
        self._publish_daily_audit_sensors()
        
        log.info("All configuration discovery messages published")
    
    def _publish_polling_config(self):
        """Publish polling configuration discovery."""
        # Polling interval
        self.mqtt.pub(
            f"homeassistant/number/solar_fleet_config_polling_interval/config",
            {
                "name": "Solar Fleet Polling Interval",
                "unique_id": "solar_fleet_config_polling_interval",
                "device": self._get_device_info(),
                "state_topic": f"{self.discovery_topic}/polling_interval_secs",
                "command_topic": f"{self.discovery_topic}/set",
                "min": 0.5,
                "max": 60.0,
                "step": 0.5,
                "unit_of_measurement": "s",
                "icon": "mdi:timer",
                "value_template": "{{ value_json.polling_interval_secs }}",
                "json_attributes_topic": f"{self.discovery_topic}/polling_interval_secs",
                "json_attributes_template": "{{ value_json | tojson }}"
            },
            retain=True
        )
        
        # Polling timeout
        self.mqtt.pub(
            f"homeassistant/number/solar_fleet_config_polling_timeout/config",
            {
                "name": "Solar Fleet Polling Timeout",
                "unique_id": "solar_fleet_config_polling_timeout",
                "device": self._get_device_info(),
                "state_topic": f"{self.discovery_topic}/polling_timeout_ms",
                "command_topic": f"{self.discovery_topic}/set",
                "min": 500,
                "max": 10000,
                "step": 100,
                "unit_of_measurement": "ms",
                "icon": "mdi:timer-outline",
                "value_template": "{{ value_json.polling_timeout_ms }}",
                "json_attributes_topic": f"{self.discovery_topic}/polling_timeout_ms",
                "json_attributes_template": "{{ value_json | tojson }}"
            },
            retain=True
        )
    
    def _publish_logging_config(self):
        """Publish logging configuration discovery."""
        # Log level
        self.mqtt.pub(
            f"homeassistant/select/solar_fleet_config_log_level/config",
            {
                "name": "Solar Fleet Log Level",
                "unique_id": "solar_fleet_config_log_level",
                "device": self._get_device_info(),
                "state_topic": f"{self.discovery_topic}/logging_level",
                "command_topic": f"{self.discovery_topic}/set",
                "options": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                "icon": "mdi:file-document-outline",
                "value_template": "{{ value_json.logging_level }}",
                "json_attributes_topic": f"{self.discovery_topic}/logging_level",
                "json_attributes_template": "{{ value_json | tojson }}"
            },
            retain=True
        )
        
        # HA Debug
        self.mqtt.pub(
            f"homeassistant/switch/solar_fleet_config_ha_debug/config",
            {
                "name": "Solar Fleet HA Debug",
                "unique_id": "solar_fleet_config_ha_debug",
                "device": self._get_device_info(),
                "state_topic": f"{self.discovery_topic}/logging_ha_debug",
                "command_topic": f"{self.discovery_topic}/set",
                "icon": "mdi:bug",
                "value_template": "{{ value_json.logging_ha_debug }}",
                "json_attributes_topic": f"{self.discovery_topic}/logging_ha_debug",
                "json_attributes_template": "{{ value_json | tojson }}"
            },
            retain=True
        )
    
    def _publish_forecast_config(self):
        """Publish forecast configuration discovery."""
        # Weather provider
        self.mqtt.pub(
            f"homeassistant/select/solar_fleet_config_weather_provider/config",
            {
                "name": "Solar Fleet Weather Provider",
                "unique_id": "solar_fleet_config_weather_provider",
                "device": self._get_device_info(),
                "state_topic": f"{self.discovery_topic}/forecast_provider",
                "command_topic": f"{self.discovery_topic}/set",
                "options": ["naive", "openmeteo", "weatherapi", "openweather", "simple"],
                "icon": "mdi:weather-cloudy",
                "value_template": "{{ value_json.forecast_provider }}",
                "json_attributes_topic": f"{self.discovery_topic}/forecast_provider",
                "json_attributes_template": "{{ value_json | tojson }}"
            },
            retain=True
        )
        
        # Forecast enabled
        self.mqtt.pub(
            f"homeassistant/switch/solar_fleet_config_forecast_enabled/config",
            {
                "name": "Solar Fleet Forecast Enabled",
                "unique_id": "solar_fleet_config_forecast_enabled",
                "device": self._get_device_info(),
                "state_topic": f"{self.discovery_topic}/forecast_enabled",
                "command_topic": f"{self.discovery_topic}/set",
                "icon": "mdi:weather-sunny",
                "value_template": "{{ value_json.forecast_enabled }}",
                "json_attributes_topic": f"{self.discovery_topic}/forecast_enabled",
                "json_attributes_template": "{{ value_json | tojson }}"
            },
            retain=True
        )
        
        # Latitude
        self.mqtt.pub(
            f"homeassistant/number/solar_fleet_config_latitude/config",
            {
                "name": "Solar Fleet Latitude",
                "unique_id": "solar_fleet_config_latitude",
                "device": self._get_device_info(),
                "state_topic": f"{self.discovery_topic}/forecast_lat",
                "command_topic": f"{self.discovery_topic}/set",
                "min": -90.0,
                "max": 90.0,
                "step": 0.0001,
                "unit_of_measurement": "°",
                "icon": "mdi:latitude",
                "value_template": "{{ value_json.forecast_lat }}",
                "json_attributes_topic": f"{self.discovery_topic}/forecast_lat",
                "json_attributes_template": "{{ value_json | tojson }}"
            },
            retain=True
        )
        
        # Longitude
        self.mqtt.pub(
            f"homeassistant/number/solar_fleet_config_longitude/config",
            {
                "name": "Solar Fleet Longitude",
                "unique_id": "solar_fleet_config_longitude",
                "device": self._get_device_info(),
                "state_topic": f"{self.discovery_topic}/forecast_lon",
                "command_topic": f"{self.discovery_topic}/set",
                "min": -180.0,
                "max": 180.0,
                "step": 0.0001,
                "unit_of_measurement": "°",
                "icon": "mdi:longitude",
                "value_template": "{{ value_json.forecast_lon }}",
                "json_attributes_topic": f"{self.discovery_topic}/forecast_lon",
                "json_attributes_template": "{{ value_json | tojson }}"
            },
            retain=True
        )
        
        # Timezone
        self.mqtt.pub(
            f"homeassistant/text/solar_fleet_config_timezone/config",
            {
                "name": "Solar Fleet Timezone",
                "unique_id": "solar_fleet_config_timezone",
                "device": self._get_device_info(),
                "state_topic": f"{self.discovery_topic}/forecast_tz",
                "command_topic": f"{self.discovery_topic}/set",
                "icon": "mdi:clock-outline",
                "value_template": "{{ value_json.forecast_tz }}",
                "json_attributes_topic": f"{self.discovery_topic}/forecast_tz",
                "json_attributes_template": "{{ value_json | tojson }}"
            },
            retain=True
        )
        
        # PV DC kW
        self.mqtt.pub(
            f"homeassistant/number/solar_fleet_config_pv_dc_kw/config",
            {
                "name": "Solar Fleet PV DC kW",
                "unique_id": "solar_fleet_config_pv_dc_kw",
                "device": self._get_device_info(),
                "state_topic": f"{self.discovery_topic}/forecast_pv_dc_kw",
                "command_topic": f"{self.discovery_topic}/set",
                "min": 0.1,
                "max": 100.0,
                "step": 0.1,
                "unit_of_measurement": "kW",
                "icon": "mdi:solar-power",
                "value_template": "{{ value_json.forecast_pv_dc_kw }}",
                "json_attributes_topic": f"{self.discovery_topic}/forecast_pv_dc_kw",
                "json_attributes_template": "{{ value_json | tojson }}"
            },
            retain=True
        )
        
        # Battery capacity
        self.mqtt.pub(
            f"homeassistant/number/solar_fleet_config_battery_capacity/config",
            {
                "name": "Solar Fleet Battery Capacity",
                "unique_id": "solar_fleet_config_battery_capacity",
                "device": self._get_device_info(),
                "state_topic": f"{self.discovery_topic}/forecast_batt_capacity_kwh",
                "command_topic": f"{self.discovery_topic}/set",
                "min": 1.0,
                "max": 100.0,
                "step": 0.1,
                "unit_of_measurement": "kWh",
                "device_class": "energy",
                "state_class": "measurement",
                "icon": "mdi:battery",
                "value_template": "{{ value_json.forecast_batt_capacity_kwh }}",
                "json_attributes_topic": f"{self.discovery_topic}/forecast_batt_capacity_kwh",
                "json_attributes_template": "{{ value_json | tojson }}"
            },
            retain=True
        )
        
        # WeatherAPI Key
        self.mqtt.pub(
            f"homeassistant/text/solar_fleet_config_weatherapi_key/config",
            {
                "name": "Solar Fleet WeatherAPI Key",
                "unique_id": "solar_fleet_config_weatherapi_key",
                "device": self._get_device_info(),
                "state_topic": f"{self.discovery_topic}/forecast_weatherapi_key",
                "command_topic": f"{self.discovery_topic}/set",
                "icon": "mdi:key",
                "value_template": "{{ value_json.forecast_weatherapi_key }}",
                "json_attributes_topic": f"{self.discovery_topic}/forecast_weatherapi_key",
                "json_attributes_template": "{{ value_json | tojson }}"
            },
            retain=True
        )
        
        # OpenWeatherMap Key
        self.mqtt.pub(
            f"homeassistant/text/solar_fleet_config_openweather_key/config",
            {
                "name": "Solar Fleet OpenWeatherMap Key",
                "unique_id": "solar_fleet_config_openweather_key",
                "device": self._get_device_info(),
                "state_topic": f"{self.discovery_topic}/forecast_openweather_key",
                "command_topic": f"{self.discovery_topic}/set",
                "icon": "mdi:key",
                "value_template": "{{ value_json.forecast_openweather_key }}",
                "json_attributes_topic": f"{self.discovery_topic}/forecast_openweather_key",
                "json_attributes_template": "{{ value_json | tojson }}"
            },
            retain=True
        )
        
        # WeatherBit Key
        self.mqtt.pub(
            f"homeassistant/text/solar_fleet_config_weatherbit_key/config",
            {
                "name": "Solar Fleet WeatherBit Key",
                "unique_id": "solar_fleet_config_weatherbit_key",
                "device": self._get_device_info(),
                "state_topic": f"{self.discovery_topic}/forecast_weatherbit_key",
                "command_topic": f"{self.discovery_topic}/set",
                "icon": "mdi:key",
                "value_template": "{{ value_json.forecast_weatherbit_key }}",
                "json_attributes_topic": f"{self.discovery_topic}/forecast_weatherbit_key",
                "json_attributes_template": "{{ value_json | tojson }}"
            },
            retain=True
        )
    
    def _publish_policy_config(self):
        """Publish policy configuration discovery."""
        # Policy dials: Self-sufficiency aggressiveness
        self.mqtt.pub(
            f"homeassistant/select/solar_fleet_config_self_sufficiency_aggressiveness/config",
            {
                "name": "Self-sufficiency Aggressiveness",
                "unique_id": "solar_fleet_config_self_sufficiency_aggressiveness",
                "device": self._get_device_info(),
                "state_topic": f"{self.discovery_topic}/self_sufficiency_aggressiveness",
                "command_topic": f"{self.discovery_topic}/set",
                "options": ["low", "balanced", "high"],
                "icon": "mdi:leaf",
                "value_template": "{{ value_json.self_sufficiency_aggressiveness }}",
                "json_attributes_topic": f"{self.discovery_topic}/self_sufficiency_aggressiveness",
                "json_attributes_template": "{{ value_json | tojson }}"
            },
            retain=True
        )

        # Policy dials: Reliability posture
        self.mqtt.pub(
            f"homeassistant/select/solar_fleet_config_reliability_posture/config",
            {
                "name": "Reliability Posture",
                "unique_id": "solar_fleet_config_reliability_posture",
                "device": self._get_device_info(),
                "state_topic": f"{self.discovery_topic}/reliability_posture",
                "command_topic": f"{self.discovery_topic}/set",
                "options": ["normal", "resilient"],
                "icon": "mdi:shield-half-full",
                "value_template": "{{ value_json.reliability_posture }}",
                "json_attributes_topic": f"{self.discovery_topic}/reliability_posture",
                "json_attributes_template": "{{ value_json | tojson }}"
            },
            retain=True
        )
        # Policy enabled
        self.mqtt.pub(
            f"homeassistant/switch/solar_fleet_config_policy_enabled/config",
            {
                "name": "Solar Fleet Policy Enabled",
                "unique_id": "solar_fleet_config_policy_enabled",
                "device": self._get_device_info(),
                "state_topic": f"{self.discovery_topic}/policy_enabled",
                "command_topic": f"{self.discovery_topic}/set",
                "icon": "mdi:cog",
                "value_template": "{{ value_json.policy_enabled }}",
                "json_attributes_topic": f"{self.discovery_topic}/policy_enabled",
                "json_attributes_template": "{{ value_json | tojson }}"
            },
            retain=True
        )
        
        # Smart tick interval
        self.mqtt.pub(
            f"homeassistant/number/solar_fleet_config_smart_tick_interval/config",
            {
                "name": "Solar Fleet Smart Tick Interval",
                "unique_id": "solar_fleet_config_smart_tick_interval",
                "device": self._get_device_info(),
                "state_topic": f"{self.discovery_topic}/smart_tick_interval_secs",
                "command_topic": f"{self.discovery_topic}/set",
                "min": 30,
                "max": 3600,
                "step": 30,
                "unit_of_measurement": "s",
                "icon": "mdi:timer-cog",
                "value_template": "{{ value_json.smart_tick_interval_secs }}",
                "json_attributes_topic": f"{self.discovery_topic}/smart_tick_interval_secs",
                "json_attributes_template": "{{ value_json | tojson }}"
            },
            retain=True
        )
        
        # Overnight min SOC
        self.mqtt.pub(
            f"homeassistant/number/solar_fleet_config_overnight_min_soc/config",
            {
                "name": "Solar Fleet Overnight Min SOC",
                "unique_id": "solar_fleet_config_overnight_min_soc",
                "device": self._get_device_info(),
                "state_topic": f"{self.discovery_topic}/overnight_min_soc_pct",
                "command_topic": f"{self.discovery_topic}/set",
                "min": 10,
                "max": 50,
                "step": 1,
                "unit_of_measurement": "%",
                "icon": "mdi:battery-low",
                "value_template": "{{ value_json.overnight_min_soc_pct }}",
                "json_attributes_topic": f"{self.discovery_topic}/overnight_min_soc_pct",
                "json_attributes_template": "{{ value_json | tojson }}"
            },
            retain=True
        )
        
        # Blackout reserve SOC
        self.mqtt.pub(
            f"homeassistant/number/solar_fleet_config_blackout_reserve_soc/config",
            {
                "name": "Solar Fleet Blackout Reserve SOC",
                "unique_id": "solar_fleet_config_blackout_reserve_soc",
                "device": self._get_device_info(),
                "state_topic": f"{self.discovery_topic}/blackout_reserve_soc_pct",
                "command_topic": f"{self.discovery_topic}/set",
                "min": 10,
                "max": 50,
                "step": 1,
                "unit_of_measurement": "%",
                "icon": "mdi:battery-alert",
                "value_template": "{{ value_json.blackout_reserve_soc_pct }}",
                "json_attributes_topic": f"{self.discovery_topic}/blackout_reserve_soc_pct",
                "json_attributes_template": "{{ value_json | tojson }}"
            },
            retain=True
        )
        
        # Emergency SOC threshold
        self.mqtt.pub(
            f"homeassistant/number/solar_fleet_config_emergency_soc_threshold/config",
            {
                "name": "Solar Fleet Emergency SOC Threshold",
                "unique_id": "solar_fleet_config_emergency_soc_threshold",
                "device": self._get_device_info(),
                "state_topic": f"{self.discovery_topic}/emergency_soc_threshold_grid_available_pct",
                "command_topic": f"{self.discovery_topic}/set",
                "min": 20,
                "max": 60,
                "step": 1,
                "unit_of_measurement": "%",
                "icon": "mdi:battery-alert-variant",
                "value_template": "{{ value_json.emergency_soc_threshold_grid_available_pct }}",
                "json_attributes_topic": f"{self.discovery_topic}/emergency_soc_threshold_grid_available_pct",
                "json_attributes_template": "{{ value_json | tojson }}"
            },
            retain=True
        )
        
        # Emergency SOC threshold (Grid Available)
        self.mqtt.pub(
            f"homeassistant/number/solar_fleet_config_emergency_soc_threshold_grid_available/config",
            {
                "name": "Solar Fleet Emergency SOC Threshold (Grid Available)",
                "unique_id": "solar_fleet_config_emergency_soc_threshold_grid_available",
                "device": self._get_device_info(),
                "state_topic": f"{self.discovery_topic}/emergency_soc_threshold_grid_available_pct",
                "command_topic": f"{self.discovery_topic}/set",
                "min": 30,
                "max": 60,
                "step": 1,
                "unit_of_measurement": "%",
                "icon": "mdi:battery-alert-variant",
                "value_template": "{{ value_json.emergency_soc_threshold_grid_available_pct }}",
                "json_attributes_topic": f"{self.discovery_topic}/emergency_soc_threshold_grid_available_pct",
                "json_attributes_template": "{{ value_json | tojson }}"
            },
            retain=True
        )
        
        # Emergency SOC threshold (Grid Unavailable)
        self.mqtt.pub(
            f"homeassistant/number/solar_fleet_config_emergency_soc_threshold_grid_unavailable/config",
            {
                "name": "Solar Fleet Emergency SOC Threshold (Grid Unavailable)",
                "unique_id": "solar_fleet_config_emergency_soc_threshold_grid_unavailable",
                "device": self._get_device_info(),
                "state_topic": f"{self.discovery_topic}/emergency_soc_threshold_grid_unavailable_pct",
                "command_topic": f"{self.discovery_topic}/set",
                "min": 15,
                "max": 40,
                "step": 1,
                "unit_of_measurement": "%",
                "icon": "mdi:battery-alert-variant",
                "value_template": "{{ value_json.emergency_soc_threshold_grid_unavailable_pct }}",
                "json_attributes_topic": f"{self.discovery_topic}/emergency_soc_threshold_grid_unavailable_pct",
                "json_attributes_template": "{{ value_json | tojson }}"
            },
            retain=True
        )
        
        # Critical SOC threshold (Grid Available)
        self.mqtt.pub(
            f"homeassistant/number/solar_fleet_config_critical_soc_threshold_grid_available/config",
            {
                "name": "Solar Fleet Critical SOC Threshold (Grid Available)",
                "unique_id": "solar_fleet_config_critical_soc_threshold_grid_available",
                "device": self._get_device_info(),
                "state_topic": f"{self.discovery_topic}/critical_soc_threshold_grid_available_pct",
                "command_topic": f"{self.discovery_topic}/set",
                "min": 20,
                "max": 50,
                "step": 1,
                "unit_of_measurement": "%",
                "icon": "mdi:battery-alert-variant-outline",
                "value_template": "{{ value_json.critical_soc_threshold_grid_available_pct }}",
                "json_attributes_topic": f"{self.discovery_topic}/critical_soc_threshold_grid_available_pct",
                "json_attributes_template": "{{ value_json | tojson }}"
            },
            retain=True
        )
        
        # Critical SOC threshold (Grid Unavailable)
        self.mqtt.pub(
            f"homeassistant/number/solar_fleet_config_critical_soc_threshold_grid_unavailable/config",
            {
                "name": "Solar Fleet Critical SOC Threshold (Grid Unavailable)",
                "unique_id": "solar_fleet_config_critical_soc_threshold_grid_unavailable",
                "device": self._get_device_info(),
                "state_topic": f"{self.discovery_topic}/critical_soc_threshold_grid_unavailable_pct",
                "command_topic": f"{self.discovery_topic}/set",
                "min": 10,
                "max": 25,
                "step": 1,
                "unit_of_measurement": "%",
                "icon": "mdi:battery-alert-variant-outline",
                "value_template": "{{ value_json.critical_soc_threshold_grid_unavailable_pct }}",
                "json_attributes_topic": f"{self.discovery_topic}/critical_soc_threshold_grid_unavailable_pct",
                "json_attributes_template": "{{ value_json | tojson }}"
            },
            retain=True
        )
        
        # Off-grid startup SOC threshold
        self.mqtt.pub(
            f"homeassistant/number/solar_fleet_config_off_grid_startup_soc/config",
            {
                "name": "Solar Fleet Off-Grid Startup SOC",
                "unique_id": "solar_fleet_config_off_grid_startup_soc",
                "device": self._get_device_info(),
                "state_topic": f"{self.discovery_topic}/off_grid_startup_soc_pct",
                "command_topic": f"{self.discovery_topic}/set",
                "min": 20,
                "max": 80,
                "step": 1,
                "unit_of_measurement": "%",
                "icon": "mdi:battery-arrow-up",
                "value_template": "{{ value_json.off_grid_startup_soc_pct }}",
                "json_attributes_topic": f"{self.discovery_topic}/off_grid_startup_soc_pct",
                "json_attributes_template": "{{ value_json | tojson }}"
            },
            retain=True
        )
        
        # Target full before sunset
        self.mqtt.pub(
            f"homeassistant/switch/solar_fleet_config_target_full_before_sunset/config",
            {
                "name": "Solar Fleet Target Full Before Sunset",
                "unique_id": "solar_fleet_config_target_full_before_sunset",
                "device": self._get_device_info(),
                "state_topic": f"{self.discovery_topic}/target_full_before_sunset",
                "command_topic": f"{self.discovery_topic}/set",
                "icon": "mdi:weather-sunset",
                "value_template": "{{ value_json.target_full_before_sunset }}",
                "json_attributes_topic": f"{self.discovery_topic}/target_full_before_sunset",
                "json_attributes_template": "{{ value_json | tojson }}"
            },
            retain=True
        )
        
        # Max charge power
        self.mqtt.pub(
            f"homeassistant/number/solar_fleet_config_max_charge_power/config",
            {
                "name": "Solar Fleet Max Charge Power",
                "unique_id": "solar_fleet_config_max_charge_power",
                "device": self._get_device_info(),
                "state_topic": f"{self.discovery_topic}/max_charge_power_w",
                "command_topic": f"{self.discovery_topic}/set",
                "min": 100,
                "max": 10000,
                "step": 100,
                "unit_of_measurement": "W",
                "icon": "mdi:battery-charging",
                "value_template": "{{ value_json.max_charge_power_w }}",
                "json_attributes_topic": f"{self.discovery_topic}/max_charge_power_w",
                "json_attributes_template": "{{ value_json | tojson }}"
            },
            retain=True
        )
        
        # Max discharge power
        self.mqtt.pub(
            f"homeassistant/number/solar_fleet_config_max_discharge_power/config",
            {
                "name": "Solar Fleet Max Discharge Power",
                "unique_id": "solar_fleet_config_max_discharge_power",
                "device": self._get_device_info(),
                "state_topic": f"{self.discovery_topic}/max_discharge_power_w",
                "command_topic": f"{self.discovery_topic}/set",
                "min": 100,
                "max": 10000,
                "step": 100,
                "unit_of_measurement": "W",
                "icon": "mdi:battery-minus",
                "value_template": "{{ value_json.max_discharge_power_w }}",
                "json_attributes_topic": f"{self.discovery_topic}/max_discharge_power_w",
                "json_attributes_template": "{{ value_json | tojson }}"
            },
            retain=True
        )
        
        # Max battery SOC
        self.mqtt.pub(
            f"homeassistant/number/solar_fleet_config_max_battery_soc/config",
            {
                "name": "Solar Fleet Max Battery SOC",
                "unique_id": "solar_fleet_config_max_battery_soc",
                "device": self._get_device_info(),
                "state_topic": f"{self.discovery_topic}/max_battery_soc_pct",
                "command_topic": f"{self.discovery_topic}/set",
                "min": 50,
                "max": 100,
                "step": 1,
                "unit_of_measurement": "%",
                "icon": "mdi:battery-plus",
                "value_template": "{{ value_json.max_battery_soc_pct }}",
                "json_attributes_topic": f"{self.discovery_topic}/max_battery_soc_pct",
                "json_attributes_template": "{{ value_json | tojson }}"
            },
            retain=True
        )
        
        # Max grid charge power
        self.mqtt.pub(
            f"homeassistant/number/solar_fleet_config_max_grid_charge_power/config",
            {
                "name": "Solar Fleet Max Grid Charge Power",
                "unique_id": "solar_fleet_config_max_grid_charge_power",
                "device": self._get_device_info(),
                "state_topic": f"{self.discovery_topic}/max_grid_charge_w",
                "command_topic": f"{self.discovery_topic}/set",
                "min": 0,
                "max": 10000,
                "step": 100,
                "unit_of_measurement": "W",
                "icon": "mdi:transmission-tower",
                "value_template": "{{ value_json.max_grid_charge_w }}",
                "json_attributes_topic": f"{self.discovery_topic}/max_grid_charge_w",
                "json_attributes_template": "{{ value_json | tojson }}"
            },
            retain=True
        )
        
        # Load fallback
        self.mqtt.pub(
            f"homeassistant/number/solar_fleet_config_load_fallback/config",
            {
                "name": "Solar Fleet Load Fallback",
                "unique_id": "solar_fleet_config_load_fallback",
                "device": self._get_device_info(),
                "state_topic": f"{self.discovery_topic}/load_fallback_kw",
                "command_topic": f"{self.discovery_topic}/set",
                "min": 0.1,
                "max": 10.0,
                "step": 0.1,
                "unit_of_measurement": "kW",
                "icon": "mdi:home-lightning-bolt",
                "value_template": "{{ value_json.load_fallback_kw }}",
                "json_attributes_topic": f"{self.discovery_topic}/load_fallback_kw",
                "json_attributes_template": "{{ value_json | tojson }}"
            },
            retain=True
        )
        
        # Primary mode
        self.mqtt.pub(
            f"homeassistant/select/solar_fleet_config_primary_mode/config",
            {
                "name": "Solar Fleet Primary Mode",
                "unique_id": "solar_fleet_config_primary_mode",
                "device": self._get_device_info(),
                "state_topic": f"{self.discovery_topic}/primary_mode",
                "command_topic": f"{self.discovery_topic}/set",
                "options": ["self_use", "time_based"],
                "icon": "mdi:cog-transfer",
                "value_template": "{{ value_json.primary_mode }}",
                "json_attributes_topic": f"{self.discovery_topic}/primary_mode",
                "json_attributes_template": "{{ value_json | tojson }}"
            },
            retain=True
        )
        
        # Auto mode switching
        self.mqtt.pub(
            f"homeassistant/switch/solar_fleet_config_auto_mode_switching/config",
            {
                "name": "Solar Fleet Auto Mode Switching",
                "unique_id": "solar_fleet_config_auto_mode_switching",
                "device": self._get_device_info(),
                "state_topic": f"{self.discovery_topic}/enable_auto_mode_switching",
                "command_topic": f"{self.discovery_topic}/set",
                "icon": "mdi:auto-fix",
                "value_template": "{{ value_json.enable_auto_mode_switching }}",
                "json_attributes_topic": f"{self.discovery_topic}/enable_auto_mode_switching",
                "json_attributes_template": "{{ value_json | tojson }}"
            },
            retain=True
        )
        
        # SOC logging interval
        self.mqtt.pub(
            f"homeassistant/number/solar_fleet_config_soc_log_interval/config",
            {
                "name": "Solar Fleet SOC Log Interval",
                "unique_id": "solar_fleet_config_soc_log_interval",
                "device": self._get_device_info(),
                "state_topic": f"{self.discovery_topic}/soc_log_interval_secs",
                "command_topic": f"{self.discovery_topic}/set",
                "min": 60,
                "max": 1800,
                "step": 30,
                "unit_of_measurement": "s",
                "icon": "mdi:clock-outline",
                "value_template": "{{ value_json.soc_log_interval_secs }}",
                "json_attributes_topic": f"{self.discovery_topic}/soc_log_interval_secs",
                "json_attributes_template": "{{ value_json | tojson }}"
            },
            retain=True
        )
        
        # Command queue timeout
        self.mqtt.pub(
            f"homeassistant/number/solar_fleet_config_command_timeout/config",
            {
                "name": "Solar Fleet Command Timeout",
                "unique_id": "solar_fleet_config_command_timeout",
                "device": self._get_device_info(),
                "state_topic": f"{self.discovery_topic}/command_timeout_secs",
                "command_topic": f"{self.discovery_topic}/set",
                "min": 5,
                "max": 120,
                "step": 5,
                "unit_of_measurement": "s",
                "icon": "mdi:timer-sand",
                "value_template": "{{ value_json.command_timeout_secs }}",
                "json_attributes_topic": f"{self.discovery_topic}/command_timeout_secs",
                "json_attributes_template": "{{ value_json | tojson }}"
            },
            retain=True
        )
        
    
    def _publish_tariff_config(self):
        """Publish tariff configuration discovery."""
        # Tariffs as text input (JSON format)
        self.mqtt.pub(
            f"homeassistant/text/solar_fleet_config_tariffs/config",
            {
                "name": "Solar Fleet Tariffs",
                "unique_id": "solar_fleet_config_tariffs",
                "device": self._get_device_info(),
                "state_topic": f"{self.discovery_topic}/tariffs",
                "command_topic": f"{self.discovery_topic}/set",
                "icon": "mdi:currency-usd",
                "value_template": "{{ value_json.tariffs }}",
                "json_attributes_topic": f"{self.discovery_topic}/tariffs",
                "json_attributes_template": "{{ value_json | tojson }}",
                "max": 2000
            },
            retain=True
        )
    
    def _get_device_info(self) -> Dict[str, Any]:
        """Get device information for HA discovery."""
        return {
            "identifiers": [["solar_fleet", "config"]],
            "name": "Solar Fleet Configuration",
            "manufacturer": "Solar Hub",
            "model": "Configuration Manager",
            "sw_version": "1.0.0"
        }
    
    def publish_current_config(self):
        """Publish current configuration values."""
        log.info("Publishing current configuration values")
        
        # Polling config
        self.mqtt.pub(f"{self.discovery_topic}/polling_interval_secs", {
            "polling_interval_secs": self.config.polling.interval_secs
        })
        self.mqtt.pub(f"{self.discovery_topic}/polling_timeout_ms", {
            "polling_timeout_ms": self.config.polling.timeout_ms
        })
        
        # Logging config
        self.mqtt.pub(f"{self.discovery_topic}/logging_level", {
            "logging_level": self.config.logging.level
        })
        self.mqtt.pub(f"{self.discovery_topic}/logging_ha_debug", {
            "logging_ha_debug": self.config.logging.ha_debug
        })
        
        # Forecast config
        self.mqtt.pub(f"{self.discovery_topic}/forecast_provider", {
            "forecast_provider": self.config.smart.forecast.provider
        })
        self.mqtt.pub(f"{self.discovery_topic}/forecast_enabled", {
            "forecast_enabled": self.config.smart.forecast.enabled
        })
        self.mqtt.pub(f"{self.discovery_topic}/forecast_lat", {
            "forecast_lat": self.config.smart.forecast.lat
        })
        self.mqtt.pub(f"{self.discovery_topic}/forecast_lon", {
            "forecast_lon": self.config.smart.forecast.lon
        })
        self.mqtt.pub(f"{self.discovery_topic}/forecast_tz", {
            "forecast_tz": self.config.timezone
        })
        self.mqtt.pub(f"{self.discovery_topic}/forecast_pv_dc_kw", {
            "forecast_pv_dc_kw": self.config.smart.forecast.pv_dc_kw
        })
        self.mqtt.pub(f"{self.discovery_topic}/forecast_batt_capacity_kwh", {
            "forecast_batt_capacity_kwh": self.config.smart.forecast.batt_capacity_kwh
        })
        self.mqtt.pub(f"{self.discovery_topic}/forecast_weatherapi_key", {
            "forecast_weatherapi_key": self.config.smart.forecast.weatherapi_key or ""
        })
        self.mqtt.pub(f"{self.discovery_topic}/forecast_openweather_key", {
            "forecast_openweather_key": self.config.smart.forecast.openweather_key or ""
        })
        self.mqtt.pub(f"{self.discovery_topic}/forecast_weatherbit_key", {
            "forecast_weatherbit_key": self.config.smart.forecast.weatherbit_key or ""
        })
        
        # Policy config
        self.mqtt.pub(f"{self.discovery_topic}/policy_enabled", {
            "policy_enabled": self.config.smart.policy.enabled
        })
        # Publish policy dials current values (fallback defaults if not present)
        self.mqtt.pub(f"{self.discovery_topic}/self_sufficiency_aggressiveness", {
            "self_sufficiency_aggressiveness": getattr(self.config.smart.policy, 'self_sufficiency_aggressiveness', 'balanced')
        })
        self.mqtt.pub(f"{self.discovery_topic}/reliability_posture", {
            "reliability_posture": getattr(self.config.smart.policy, 'reliability_posture', 'normal')
        })
        self.mqtt.pub(f"{self.discovery_topic}/smart_tick_interval_secs", {
            "smart_tick_interval_secs": self.config.smart.policy.smart_tick_interval_secs
        })
        self.mqtt.pub(f"{self.discovery_topic}/overnight_min_soc_pct", {
            "overnight_min_soc_pct": self.config.smart.policy.overnight_min_soc_pct
        })
        self.mqtt.pub(f"{self.discovery_topic}/blackout_reserve_soc_pct", {
            "blackout_reserve_soc_pct": self.config.smart.policy.blackout_reserve_soc_pct
        })
        self.mqtt.pub(f"{self.discovery_topic}/target_full_before_sunset", {
            "target_full_before_sunset": self.config.smart.policy.target_full_before_sunset
        })
        self.mqtt.pub(f"{self.discovery_topic}/max_charge_power_w", {
            "max_charge_power_w": self.config.smart.policy.max_charge_power_w
        })
        self.mqtt.pub(f"{self.discovery_topic}/max_discharge_power_w", {
            "max_discharge_power_w": self.config.smart.policy.max_discharge_power_w
        })
        self.mqtt.pub(f"{self.discovery_topic}/max_battery_soc_pct", {
            "max_battery_soc_pct": self.config.smart.policy.max_battery_soc_pct
        })
        self.mqtt.pub(f"{self.discovery_topic}/max_grid_charge_w", {
            "max_grid_charge_w": self.config.smart.policy.max_grid_charge_w
        })
        self.mqtt.pub(f"{self.discovery_topic}/load_fallback_kw", {
            "load_fallback_kw": self.config.smart.policy.load_fallback_kw
        })
        self.mqtt.pub(f"{self.discovery_topic}/primary_mode", {
            "primary_mode": self.config.smart.policy.primary_mode
        })
        self.mqtt.pub(f"{self.discovery_topic}/enable_auto_mode_switching", {
            "enable_auto_mode_switching": self.config.smart.policy.enable_auto_mode_switching
        })
        self.mqtt.pub(f"{self.discovery_topic}/soc_log_interval_secs", {
            "soc_log_interval_secs": getattr(self.config.smart.policy, 'soc_log_interval_secs', 300)
        })
        self.mqtt.pub(f"{self.discovery_topic}/command_timeout_secs", {
            "command_timeout_secs": getattr(self.config.smart.policy, 'command_timeout_secs', 30)
        })
        self.mqtt.pub(f"{self.discovery_topic}/emergency_soc_threshold_grid_available_pct", {
            "emergency_soc_threshold_grid_available_pct": self.config.smart.policy.emergency_soc_threshold_grid_available_pct
        })
        self.mqtt.pub(f"{self.discovery_topic}/critical_soc_threshold_grid_available_pct", {
            "critical_soc_threshold_grid_available_pct": self.config.smart.policy.critical_soc_threshold_grid_available_pct
        })
        self.mqtt.pub(f"{self.discovery_topic}/critical_soc_threshold_grid_unavailable_pct", {
            "critical_soc_threshold_grid_unavailable_pct": self.config.smart.policy.critical_soc_threshold_grid_unavailable_pct
        })
        
        # Tariffs config
        tariffs_json = json.dumps([tariff.model_dump() for tariff in self.config.smart.policy.tariffs])
        self.mqtt.pub(f"{self.discovery_topic}/tariffs", {
            "tariffs": tariffs_json
        })
        
        # Battery config current values
        # Data source
        self.mqtt.pub(f"{self.discovery_topic}/battery_data_source", {
            "battery_data_source": getattr(self.config, 'battery_data_source', 'inverter')
        })
        # Bank + adapter (guard optional)
        bank = getattr(self.config, 'battery_bank', None)
        if bank and getattr(bank, 'adapter', None):
            ad = bank.adapter
            self.mqtt.pub(f"{self.discovery_topic}/battery_adapter_serial_port", {
                "battery_adapter_serial_port": getattr(ad, 'serial_port', None) or ""
            })
            self.mqtt.pub(f"{self.discovery_topic}/battery_adapter_baudrate", {
                "battery_adapter_baudrate": getattr(ad, 'baudrate', 115200)
            })
            self.mqtt.pub(f"{self.discovery_topic}/battery_adapter_parity", {
                "battery_adapter_parity": getattr(ad, 'parity', 'N')
            })
            self.mqtt.pub(f"{self.discovery_topic}/battery_adapter_stopbits", {
                "battery_adapter_stopbits": getattr(ad, 'stopbits', 1)
            })
            self.mqtt.pub(f"{self.discovery_topic}/battery_adapter_bytesize", {
                "battery_adapter_bytesize": getattr(ad, 'bytesize', 8)
            })
            self.mqtt.pub(f"{self.discovery_topic}/battery_adapter_batteries", {
                "battery_adapter_batteries": getattr(ad, 'batteries', 1)
            })
            self.mqtt.pub(f"{self.discovery_topic}/battery_adapter_cells_per_battery", {
                "battery_adapter_cells_per_battery": getattr(ad, 'cells_per_battery', 16)
            })
            self.mqtt.pub(f"{self.discovery_topic}/battery_adapter_dev_name", {
                "battery_adapter_dev_name": getattr(ad, 'dev_name', 'battery_bank')
            })
            self.mqtt.pub(f"{self.discovery_topic}/battery_adapter_manufacturer", {
                "battery_adapter_manufacturer": getattr(ad, 'manufacturer', '') or ''
            })
            self.mqtt.pub(f"{self.discovery_topic}/battery_adapter_model", {
                "battery_adapter_model": getattr(ad, 'model', '') or ''
            })

        # Daily audit sensors (publish current values)
        self._publish_daily_audit_current_values()
        
        log.info("Current configuration values published")

    def _publish_battery_config(self):
        """Publish battery data source and adapter settings discovery."""
        # Data source select
        self.mqtt.pub(
            f"homeassistant/select/solar_fleet_config_battery_source/config",
            {
                "name": "Battery Data Source",
                "unique_id": "solar_fleet_config_battery_source",
                "device": self._get_device_info(),
                "state_topic": f"{self.discovery_topic}/battery_data_source",
                "command_topic": f"{self.discovery_topic}/set",
                "options": ["inverter", "battery_adapter"],
                "icon": "mdi:battery",
                "value_template": "{{ value_json.battery_data_source }}",
                "json_attributes_topic": f"{self.discovery_topic}/battery_data_source",
                "json_attributes_template": "{{ value_json | tojson }}",
            },
            retain=True,
        )

        # Serial port (text)
        self.mqtt.pub(
            f"homeassistant/text/solar_fleet_config_battery_serial_port/config",
            {
                "name": "Battery Serial Port",
                "unique_id": "solar_fleet_config_battery_serial_port",
                "device": self._get_device_info(),
                "state_topic": f"{self.discovery_topic}/battery_adapter_serial_port",
                "command_topic": f"{self.discovery_topic}/set",
                "icon": "mdi:usb-port",
                "value_template": "{{ value_json.battery_adapter_serial_port }}",
                "json_attributes_topic": f"{self.discovery_topic}/battery_adapter_serial_port",
                "json_attributes_template": "{{ value_json | tojson }}",
            },
            retain=True,
        )

        # Baudrate (number)
        self.mqtt.pub(
            f"homeassistant/number/solar_fleet_config_battery_baudrate/config",
            {
                "name": "Battery Baudrate",
                "unique_id": "solar_fleet_config_battery_baudrate",
                "device": self._get_device_info(),
                "state_topic": f"{self.discovery_topic}/battery_adapter_baudrate",
                "command_topic": f"{self.discovery_topic}/set",
                "min": 1200,
                "max": 921600,
                "step": 300,
                "icon": "mdi:speedometer",
                "value_template": "{{ value_json.battery_adapter_baudrate }}",
                "json_attributes_topic": f"{self.discovery_topic}/battery_adapter_baudrate",
                "json_attributes_template": "{{ value_json | tojson }}",
            },
            retain=True,
        )

        # Parity (select)
        self.mqtt.pub(
            f"homeassistant/select/solar_fleet_config_battery_parity/config",
            {
                "name": "Battery Parity",
                "unique_id": "solar_fleet_config_battery_parity",
                "device": self._get_device_info(),
                "state_topic": f"{self.discovery_topic}/battery_adapter_parity",
                "command_topic": f"{self.discovery_topic}/set",
                "options": ["N", "E", "O"],
                "icon": "mdi:alpha-p",
                "value_template": "{{ value_json.battery_adapter_parity }}",
                "json_attributes_topic": f"{self.discovery_topic}/battery_adapter_parity",
                "json_attributes_template": "{{ value_json | tojson }}",
            },
            retain=True,
        )

        # Stopbits (select)
        self.mqtt.pub(
            f"homeassistant/select/solar_fleet_config_battery_stopbits/config",
            {
                "name": "Battery Stopbits",
                "unique_id": "solar_fleet_config_battery_stopbits",
                "device": self._get_device_info(),
                "state_topic": f"{self.discovery_topic}/battery_adapter_stopbits",
                "command_topic": f"{self.discovery_topic}/set",
                "options": [1, 2],
                "icon": "mdi:numeric",
                "value_template": "{{ value_json.battery_adapter_stopbits }}",
                "json_attributes_topic": f"{self.discovery_topic}/battery_adapter_stopbits",
                "json_attributes_template": "{{ value_json | tojson }}",
            },
            retain=True,
        )

        # Bytesize (select)
        self.mqtt.pub(
            f"homeassistant/select/solar_fleet_config_battery_bytesize/config",
            {
                "name": "Battery Bytesize",
                "unique_id": "solar_fleet_config_battery_bytesize",
                "device": self._get_device_info(),
                "state_topic": f"{self.discovery_topic}/battery_adapter_bytesize",
                "command_topic": f"{self.discovery_topic}/set",
                "options": [7, 8],
                "icon": "mdi:format-list-numbered",
                "value_template": "{{ value_json.battery_adapter_bytesize }}",
                "json_attributes_topic": f"{self.discovery_topic}/battery_adapter_bytesize",
                "json_attributes_template": "{{ value_json | tojson }}",
            },
            retain=True,
        )

        # Bank topology: batteries and cells per battery (numbers)
        self.mqtt.pub(
            f"homeassistant/number/solar_fleet_config_battery_count/config",
            {
                "name": "Battery Count",
                "unique_id": "solar_fleet_config_battery_count",
                "device": self._get_device_info(),
                "state_topic": f"{self.discovery_topic}/battery_adapter_batteries",
                "command_topic": f"{self.discovery_topic}/set",
                "min": 1,
                "max": 16,
                "step": 1,
                "icon": "mdi:battery-multiple",
                "value_template": "{{ value_json.battery_adapter_batteries }}",
                "json_attributes_topic": f"{self.discovery_topic}/battery_adapter_batteries",
                "json_attributes_template": "{{ value_json | tojson }}",
            },
            retain=True,
        )
        self.mqtt.pub(
            f"homeassistant/number/solar_fleet_config_cells_per_battery/config",
            {
                "name": "Cells per Battery",
                "unique_id": "solar_fleet_config_cells_per_battery",
                "device": self._get_device_info(),
                "state_topic": f"{self.discovery_topic}/battery_adapter_cells_per_battery",
                "command_topic": f"{self.discovery_topic}/set",
                "min": 8,
                "max": 24,
                "step": 1,
                "icon": "mdi:battery-high",
                "value_template": "{{ value_json.battery_adapter_cells_per_battery }}",
                "json_attributes_topic": f"{self.discovery_topic}/battery_adapter_cells_per_battery",
                "json_attributes_template": "{{ value_json | tojson }}",
            },
            retain=True,
        )

        # Names (text)
        for field, name, icon in (
            ("battery_adapter_dev_name", "Battery Dev Name", "mdi:identifier"),
            ("battery_adapter_manufacturer", "Battery Manufacturer", "mdi:factory"),
            ("battery_adapter_model", "Battery Model", "mdi:information-outline"),
        ):
            self.mqtt.pub(
                f"homeassistant/text/solar_fleet_config_{field}/config",
                {
                    "name": name,
                    "unique_id": f"solar_fleet_config_{field}",
                    "device": self._get_device_info(),
                    "state_topic": f"{self.discovery_topic}/{field}",
                    "command_topic": f"{self.discovery_topic}/set",
                    "icon": icon,
                    "value_template": f"{{{{ value_json.{field} }}}}",
                    "json_attributes_topic": f"{self.discovery_topic}/{field}",
                    "json_attributes_template": "{{ value_json | tojson }}",
                },
                retain=True,
            )
    
    def _publish_daily_audit_sensors(self):
        """Publish daily audit sensor discovery messages."""
        # Daily self-sufficiency percentage
        self.mqtt.pub(
            f"homeassistant/sensor/solar_fleet_daily_self_sufficiency/config",
            {
                "name": "Daily Self-Sufficiency",
                "unique_id": "solar_fleet_daily_self_sufficiency",
                "device": self._get_device_info(),
                "state_topic": f"{self.discovery_topic}/daily_self_sufficiency_pct",
                "unit_of_measurement": "%",
                "icon": "mdi:leaf",
                "value_template": "{{ value_json.daily_self_sufficiency_pct }}",
                "json_attributes_topic": f"{self.discovery_topic}/daily_self_sufficiency_pct",
                "json_attributes_template": "{{ value_json | tojson }}"
            },
            retain=True
        )
        
        # Daily grid energy used
        self.mqtt.pub(
            f"homeassistant/sensor/solar_fleet_daily_grid_energy/config",
            {
                "name": "Daily Grid Energy",
                "unique_id": "solar_fleet_daily_grid_energy",
                "device": self._get_device_info(),
                "state_topic": f"{self.discovery_topic}/daily_grid_energy_kwh",
                "unit_of_measurement": "kWh",
                "device_class": "energy",
                "state_class": "total_increasing",
                "icon": "mdi:transmission-tower",
                "value_template": "{{ value_json.daily_grid_energy_kwh }}",
                "json_attributes_topic": f"{self.discovery_topic}/daily_grid_energy_kwh",
                "json_attributes_template": "{{ value_json | tojson }}"
            },
            retain=True
        )
        
        # Daily solar energy generated
        self.mqtt.pub(
            f"homeassistant/sensor/solar_fleet_daily_solar_energy/config",
            {
                "name": "Daily Solar Energy",
                "unique_id": "solar_fleet_daily_solar_energy",
                "device": self._get_device_info(),
                "state_topic": f"{self.discovery_topic}/daily_solar_energy_kwh",
                "unit_of_measurement": "kWh",
                "device_class": "energy",
                "state_class": "total_increasing",
                "icon": "mdi:solar-power",
                "value_template": "{{ value_json.daily_solar_energy_kwh }}",
                "json_attributes_topic": f"{self.discovery_topic}/daily_solar_energy_kwh",
                "json_attributes_template": "{{ value_json | tojson }}"
            },
            retain=True
        )
        
        # Daily battery energy cycled
        self.mqtt.pub(
            f"homeassistant/sensor/solar_fleet_daily_battery_cycled/config",
            {
                "name": "Daily Battery Energy Cycled",
                "unique_id": "solar_fleet_daily_battery_cycled",
                "device": self._get_device_info(),
                "state_topic": f"{self.discovery_topic}/daily_battery_cycled_kwh",
                "unit_of_measurement": "kWh",
                "device_class": "energy",
                "state_class": "total_increasing",
                "icon": "mdi:battery-sync",
                "value_template": "{{ value_json.daily_battery_cycled_kwh }}",
                "json_attributes_topic": f"{self.discovery_topic}/daily_battery_cycled_kwh",
                "json_attributes_template": "{{ value_json | tojson }}"
            },
            retain=True
        )
        
        # Daily load energy
        self.mqtt.pub(
            f"homeassistant/sensor/solar_fleet_daily_load_energy/config",
            {
                "name": "Daily Load Energy",
                "unique_id": "solar_fleet_daily_load_energy",
                "device": self._get_device_info(),
                "state_topic": f"{self.discovery_topic}/daily_load_energy_kwh",
                "unit_of_measurement": "kWh",
                "device_class": "energy",
                "state_class": "total_increasing",
                "icon": "mdi:home-lightning-bolt",
                "value_template": "{{ value_json.daily_load_energy_kwh }}",
                "json_attributes_topic": f"{self.discovery_topic}/daily_load_energy_kwh",
                "json_attributes_template": "{{ value_json | tojson }}"
            },
            retain=True
        )
        
        # Daily forecast accuracy
        self.mqtt.pub(
            f"homeassistant/sensor/solar_fleet_daily_forecast_accuracy/config",
            {
                "name": "Daily Forecast Accuracy",
                "unique_id": "solar_fleet_daily_forecast_accuracy",
                "device": self._get_device_info(),
                "state_topic": f"{self.discovery_topic}/daily_forecast_accuracy_pct",
                "unit_of_measurement": "%",
                "icon": "mdi:chart-line",
                "value_template": "{{ value_json.daily_forecast_accuracy_pct }}",
                "json_attributes_topic": f"{self.discovery_topic}/daily_forecast_accuracy_pct",
                "json_attributes_template": "{{ value_json | tojson }}"
            },
            retain=True
        )
    
    def _publish_daily_audit_current_values(self):
        """Publish current values for daily audit sensors."""
        # For now, publish placeholder values - these would be populated from actual daily data
        # In a real implementation, these would come from the daily aggregator or database
        
        from solarhub.timezone_utils import now_configured
        today = now_configured().strftime('%Y-%m-%d')
        
        # Daily self-sufficiency percentage (placeholder)
        self.mqtt.pub(f"{self.discovery_topic}/daily_self_sufficiency_pct", {
            "daily_self_sufficiency_pct": 0.0,
            "date": today,
            "timestamp": now_configured().isoformat()
        })
        
        # Daily grid energy used (placeholder)
        self.mqtt.pub(f"{self.discovery_topic}/daily_grid_energy_kwh", {
            "daily_grid_energy_kwh": 0.0,
            "date": today,
            "timestamp": now_configured().isoformat()
        })
        
        # Daily solar energy generated (placeholder)
        self.mqtt.pub(f"{self.discovery_topic}/daily_solar_energy_kwh", {
            "daily_solar_energy_kwh": 0.0,
            "date": today,
            "timestamp": now_configured().isoformat()
        })
        
        # Daily battery energy cycled (placeholder)
        self.mqtt.pub(f"{self.discovery_topic}/daily_battery_cycled_kwh", {
            "daily_battery_cycled_kwh": 0.0,
            "date": today,
            "timestamp": now_configured().isoformat()
        })
        
        # Daily load energy (placeholder)
        self.mqtt.pub(f"{self.discovery_topic}/daily_load_energy_kwh", {
            "daily_load_energy_kwh": 0.0,
            "date": today,
            "timestamp": now_configured().isoformat()
        })
        
        # Daily forecast accuracy (placeholder)
        self.mqtt.pub(f"{self.discovery_topic}/daily_forecast_accuracy_pct", {
            "daily_forecast_accuracy_pct": 0.0,
            "date": today,
            "timestamp": now_configured().isoformat()
        })
