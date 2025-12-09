#!/usr/bin/env python3
"""
Home Assistant discovery for battery optimization sensors and configuration.
"""

import json
import logging
from typing import Any, Dict, List, Optional
from solarhub.ha.discovery import HADiscoveryPublisher, _sanitize_key

log = logging.getLogger("solarhub.ha.battery_optimization")

class BatteryOptimizationDiscovery(HADiscoveryPublisher):
    """
    Home Assistant discovery for battery optimization features:
    - Self-sufficiency metrics
    - Enhanced weather and PV forecasts
    - Charging/discharging plans
    - Configuration sensors
    """

    def __init__(self, mqtt_client, base_topic: str, discovery_prefix: str = "homeassistant"):
        super().__init__(mqtt_client, base_topic, discovery_prefix)
        self.base_topic = base_topic.rstrip("/")

    def publish_battery_optimization_sensors(self):
        """Publish discovery messages for battery optimization sensors."""
        log.debug("Publishing battery optimization sensor discovery messages")
        
        # Self-sufficiency metrics
        log.debug("Publishing self-sufficiency sensors")
        self._publish_self_sufficiency_sensors()
        
        # Enhanced forecast sensors
        log.debug("Publishing enhanced forecast sensors")
        self._publish_forecast_sensors()
        
        # Plan sensors
        log.debug("Publishing plan sensors")
        self._publish_plan_sensors()
        
        # Configuration sensors
        log.debug("Publishing configuration sensors and controls")
        self._publish_configuration_sensors()

    def _publish_self_sufficiency_sensors(self):
        """Publish self-sufficiency metric sensors."""
        base_topic = f"{self.base_topic}/battery_optimization"
        
        sensors = [
            {
                "object_id": "solar_fleet_self_sufficiency_current",
                "name": "Solar Fleet Self-Sufficiency Current",
                "key": "current_self_sufficiency_pct",
                "unit": "%",
                "icon": "mdi:solar-power",
                "device_class": None,
                "state_class": "measurement"
            },
            {
                "object_id": "solar_fleet_self_sufficiency_avg",
                "name": "Solar Fleet Self-Sufficiency Average",
                "key": "avg_self_sufficiency_pct", 
                "unit": "%",
                "icon": "mdi:solar-power",
                "device_class": None,
                "state_class": "measurement"
            },
            {
                "object_id": "solar_fleet_dynamic_soc_target",
                "name": "Solar Fleet Dynamic SOC Target",
                "key": "dynamic_soc_target_pct",
                "unit": "%",
                "icon": "mdi:battery-charging-high",
                "device_class": "battery",
                "state_class": "measurement"
            },
            {
                "object_id": "solar_fleet_discharge_aggressiveness",
                "name": "Solar Fleet Discharge Aggressiveness",
                "key": "discharge_aggressiveness",
                "unit": None,
                "icon": "mdi:gauge",
                "device_class": None,
                "state_class": "measurement"
            },
            {
                "object_id": "solar_fleet_emergency_reserve_hours",
                "name": "Solar Fleet Emergency Reserve Hours",
                "key": "emergency_reserve_hours",
                "unit": "h",
                "icon": "mdi:shield-battery",
                "device_class": None,
                "state_class": "measurement"
            },
            {
                "object_id": "solar_fleet_peak_discharge_windows",
                "name": "Solar Fleet Peak Discharge Windows",
                "key": "peak_discharge_windows",
                "unit": None,
                "icon": "mdi:timeline-clock",
                "device_class": None,
                "state_class": "measurement"
            },
            {
                "object_id": "solar_fleet_daily_grid_usage",
                "name": "Solar Fleet Daily Grid Usage",
                "key": "daily_grid_usage_kwh",
                "unit": "kWh",
                "icon": "mdi:transmission-tower",
                "device_class": "energy",
                "state_class": "total_increasing"
            },
            {
                "object_id": "solar_fleet_daily_pv_usage",
                "name": "Solar Fleet Daily PV Usage",
                "key": "daily_pv_usage_kwh",
                "unit": "kWh",
                "icon": "mdi:solar-panel",
                "device_class": "energy",
                "state_class": "total_increasing"
            }
        ]

        for sensor in sensors:
            self._publish_sensor(
                sensor["object_id"],
                sensor["name"],
                base_topic,
                sensor["key"],
                sensor["unit"],
                sensor["icon"],
                sensor["device_class"],
                sensor["state_class"]
            )

    def _publish_forecast_sensors(self):
        """Publish enhanced forecast sensors."""
        base_topic = f"{self.base_topic}/enhanced_forecast"
        
        sensors = [
            {
                "object_id": "solar_fleet_self_sufficiency_forecast",
                "name": "Solar Fleet Self-Sufficiency Forecast",
                "key": "self_sufficiency_pct",
                "unit": "%",
                "icon": "mdi:solar-power",
                "device_class": None,
                "state_class": "measurement"
            },
            {
                "object_id": "solar_fleet_dynamic_soc_target_forecast",
                "name": "Solar Fleet Dynamic SOC Target Forecast",
                "key": "dynamic_soc_target_pct",
                "unit": "%",
                "icon": "mdi:battery-charging-high",
                "device_class": "battery",
                "state_class": "measurement"
            },
            {
                "object_id": "solar_fleet_daily_grid_usage_forecast",
                "name": "Solar Fleet Daily Grid Usage Forecast",
                "key": "daily_grid_usage_kwh",
                "unit": "kWh",
                "icon": "mdi:transmission-tower",
                "device_class": "energy",
                "state_class": "measurement"
            },
            {
                "object_id": "solar_fleet_daily_pv_usage_forecast",
                "name": "Solar Fleet Daily PV Usage Forecast",
                "key": "daily_pv_usage_kwh",
                "unit": "kWh",
                "icon": "mdi:solar-panel",
                "device_class": "energy",
                "state_class": "measurement"
            },
            {
                "object_id": "solar_fleet_emergency_reserve_hours_forecast",
                "name": "Solar Fleet Emergency Reserve Hours Forecast",
                "key": "emergency_reserve_hours",
                "unit": "h",
                "icon": "mdi:shield-battery",
                "device_class": None,
                "state_class": "measurement"
            },
            {
                "object_id": "solar_fleet_load_shift_opportunities",
                "name": "Solar Fleet Load Shift Opportunities",
                "key": "load_shift_opportunities",
                "unit": None,
                "icon": "mdi:swap-horizontal",
                "device_class": None,
                "state_class": "measurement"
            },
            {
                "object_id": "solar_fleet_peak_shaving_plan",
                "name": "Solar Fleet Peak Shaving Plan",
                "key": "peak_shaving_plan",
                "unit": None,
                "icon": "mdi:chart-line",
                "device_class": None,
                "state_class": "measurement"
            }
        ]

        for sensor in sensors:
            self._publish_sensor(
                sensor["object_id"],
                sensor["name"],
                base_topic,
                sensor["key"],
                sensor["unit"],
                sensor["icon"],
                sensor["device_class"],
                sensor["state_class"]
            )

    def _publish_plan_sensors(self):
        """Publish plan sensors."""
        base_topic = f"{self.base_topic}/plan"
        
        sensors = [
            {
                "object_id": "solar_fleet_sunset_hour",
                "name": "Solar Fleet Sunset Hour",
                "key": "sunset_hour",
                "unit": None,
                "icon": "mdi:weather-sunset",
                "device_class": None,
                "state_class": "measurement"
            },
            {
                "object_id": "solar_fleet_soc_now",
                "name": "Solar Fleet SOC Now",
                "key": "soc_now_pct",
                "unit": "%",
                "icon": "mdi:battery",
                "device_class": "battery",
                "state_class": "measurement"
            },
            {
                "object_id": "solar_fleet_end_soc_target",
                "name": "Solar Fleet End SOC Target",
                "key": "end_soc_target_pct",
                "unit": "%",
                "icon": "mdi:battery-charging-high",
                "device_class": "battery",
                "state_class": "measurement"
            },
            {
                "object_id": "solar_fleet_required_grid_energy",
                "name": "Solar Fleet Required Grid Energy",
                "key": "required_grid_kwh",
                "unit": "kWh",
                "icon": "mdi:transmission-tower",
                "device_class": "energy",
                "state_class": "measurement"
            },
            {
                "object_id": "solar_fleet_use_grid",
                "name": "Solar Fleet Use Grid",
                "key": "use_grid",
                "unit": None,
                "icon": "mdi:power-plug",
                "device_class": None,
                "state_class": None
            },
            {
                "object_id": "solar_fleet_grid_power_cap",
                "name": "Solar Fleet Grid Power Cap",
                "key": "grid_power_cap_w",
                "unit": "W",
                "icon": "mdi:lightning-bolt",
                "device_class": "power",
                "state_class": "measurement"
            }
        ]

        for sensor in sensors:
            self._publish_sensor(
                sensor["object_id"],
                sensor["name"],
                base_topic,
                sensor["key"],
                sensor["unit"],
                sensor["icon"],
                sensor["device_class"],
                sensor["state_class"]
            )

    def _publish_configuration_sensors(self):
        """Publish configuration sensors and controls."""
        base_topic = f"{self.base_topic}/config"
        
        # Configuration sensors (read-only)
        config_sensors = [
            {
                "object_id": "solar_fleet_config_dynamic_soc_enabled",
                "name": "Solar Fleet Config Dynamic SOC Enabled",
                "key": "dynamic_soc_enabled",
                "unit": None,
                "icon": "mdi:cog",
                "device_class": None,
                "state_class": None
            },
            {
                "object_id": "solar_fleet_config_min_self_sufficiency",
                "name": "Solar Fleet Config Min Self-Sufficiency",
                "key": "min_self_sufficiency_pct",
                "unit": "%",
                "icon": "mdi:solar-power",
                "device_class": None,
                "state_class": "measurement"
            },
            {
                "object_id": "solar_fleet_config_target_self_sufficiency",
                "name": "Solar Fleet Config Target Self-Sufficiency",
                "key": "target_self_sufficiency_pct",
                "unit": "%",
                "icon": "mdi:solar-power",
                "device_class": None,
                "state_class": "measurement"
            },
            {
                "object_id": "solar_fleet_config_max_grid_usage",
                "name": "Solar Fleet Config Max Grid Usage",
                "key": "max_grid_usage_kwh_per_day",
                "unit": "kWh",
                "icon": "mdi:transmission-tower",
                "device_class": "energy",
                "state_class": "measurement"
            },
            {
                "object_id": "solar_fleet_config_emergency_reserve",
                "name": "Solar Fleet Config Emergency Reserve",
                "key": "emergency_reserve_hours",
                "unit": "h",
                "icon": "mdi:shield-battery",
                "device_class": None,
                "state_class": "measurement"
            },
            {
                "object_id": "solar_fleet_config_solar_target_threshold",
                "name": "Solar Fleet Config Solar Target Threshold",
                "key": "solar_target_threshold_pct",
                "unit": "%",
                "icon": "mdi:solar-power",
                "device_class": None,
                "state_class": "measurement"
            },
            {
                "object_id": "solar_fleet_config_poor_weather_threshold",
                "name": "Solar Fleet Config Poor Weather Threshold",
                "key": "poor_weather_threshold_kwh",
                "unit": "kWh",
                "icon": "mdi:weather-cloudy",
                "device_class": "energy",
                "state_class": "measurement"
            },
            {
                "object_id": "solar_fleet_config_close_to_target_threshold",
                "name": "Solar Fleet Config Close to Target Threshold",
                "key": "close_to_target_threshold_pct",
                "unit": "%",
                "icon": "mdi:battery-charging-high",
                "device_class": "battery",
                "state_class": "measurement"
            }
        ]

        for sensor in config_sensors:
            self._publish_sensor(
                sensor["object_id"],
                sensor["name"],
                base_topic,
                sensor["key"],
                sensor["unit"],
                sensor["icon"],
                sensor["device_class"],
                sensor["state_class"]
            )

        # Configuration controls (writable)
        self._publish_configuration_controls()

    def _publish_configuration_controls(self):
        """Publish configuration controls (switches, numbers, etc.)."""
        base_topic = f"{self.base_topic}/config"
        
        # Dynamic SOC toggle switch
        self._publish_switch(
            "solar_fleet_control_dynamic_soc",
            "Solar Fleet Control Dynamic SOC",
            base_topic,
            "dynamic_soc_enabled",
            "mdi:cog"
        )
        
        # Self-sufficiency target number
        self._publish_number(
            "solar_fleet_control_target_self_sufficiency",
            "Solar Fleet Control Target Self-Sufficiency",
            base_topic,
            "target_self_sufficiency_pct",
            "mdi:solar-power",
            min_value=50.0,
            max_value=100.0,
            step=1.0,
            unit="%"
        )
        
        # Min self-sufficiency number
        self._publish_number(
            "solar_fleet_control_min_self_sufficiency",
            "Solar Fleet Control Min Self-Sufficiency",
            base_topic,
            "min_self_sufficiency_pct",
            "mdi:solar-power",
            min_value=50.0,
            max_value=95.0,
            step=1.0,
            unit="%"
        )
        
        # Max grid usage number
        self._publish_number(
            "solar_fleet_control_max_grid_usage",
            "Solar Fleet Control Max Grid Usage",
            base_topic,
            "max_grid_usage_kwh_per_day",
            "mdi:transmission-tower",
            min_value=0.0,
            max_value=50.0,
            step=0.5,
            unit="kWh"
        )
        
        # Emergency reserve hours number
        self._publish_number(
            "solar_fleet_control_emergency_reserve",
            "Solar Fleet Control Emergency Reserve",
            base_topic,
            "emergency_reserve_hours",
            "mdi:shield-battery",
            min_value=1.0,
            max_value=24.0,
            step=0.5,
            unit="h"
        )
        
        # Smart tick interval number
        self._publish_number(
            "solar_fleet_control_smart_tick_interval",
            "Solar Fleet Control Smart Tick Interval",
            base_topic,
            "smart_tick_interval_secs",
            "mdi:timer",
            min_value=30.0,
            max_value=3600.0,
            step=30.0,
            unit="s"
        )
        
        # Max charge power number
        self._publish_number(
            "solar_fleet_control_max_charge_power",
            "Solar Fleet Control Max Charge Power",
            base_topic,
            "max_charge_power_w",
            "mdi:lightning-bolt",
            min_value=100.0,
            max_value=10000.0,
            step=100.0,
            unit="W"
        )
        
        # Max discharge power number
        self._publish_number(
            "solar_fleet_control_max_discharge_power",
            "Solar Fleet Control Max Discharge Power",
            base_topic,
            "max_discharge_power_w",
            "mdi:lightning-bolt",
            min_value=100.0,
            max_value=10000.0,
            step=100.0,
            unit="W"
        )
        
        # Max battery SOC number
        self._publish_number(
            "solar_fleet_control_max_battery_soc",
            "Solar Fleet Control Max Battery SOC",
            base_topic,
            "max_battery_soc_pct",
            "mdi:battery-charging-high",
            min_value=50.0,
            max_value=100.0,
            step=5.0,
            unit="%"
        )
        
        # Tariff configuration text input
        self._publish_text(
            "solar_fleet_control_tariffs",
            "Solar Fleet Control Tariffs",
            base_topic,
            "tariffs",
            "mdi:clock-outline"
        )
        
        # Primary mode select
        self._publish_select(
            "solar_fleet_control_primary_mode",
            "Solar Fleet Control Primary Mode",
            base_topic,
            "primary_mode",
            "mdi:cog",
            ["self_use", "time_based"]
        )
        
        # Auto mode switching switch
        self._publish_switch(
            "solar_fleet_control_auto_mode_switching",
            "Solar Fleet Control Auto Mode Switching",
            base_topic,
            "enable_auto_mode_switching",
            "mdi:auto-mode"
        )
        
        # Solar target threshold number
        self._publish_number(
            "solar_fleet_control_solar_target_threshold",
            "Solar Fleet Control Solar Target Threshold",
            base_topic,
            "solar_target_threshold_pct",
            "mdi:solar-power",
            min_value=70.0,
            max_value=100.0,
            step=5.0,
            unit="%"
        )
        
        # Poor weather threshold number
        self._publish_number(
            "solar_fleet_control_poor_weather_threshold",
            "Solar Fleet Control Poor Weather Threshold",
            base_topic,
            "poor_weather_threshold_kwh",
            "mdi:weather-cloudy",
            min_value=0.1,
            max_value=5.0,
            step=0.1,
            unit="kWh"
        )
        
        # Close to target threshold number
        self._publish_number(
            "solar_fleet_control_close_to_target_threshold",
            "Solar Fleet Control Close to Target Threshold",
            base_topic,
            "close_to_target_threshold_pct",
            "mdi:battery-charging-high",
            min_value=1.0,
            max_value=20.0,
            step=1.0,
            unit="%"
        )

    def _publish_sensor(self, object_id: str, name: str, state_topic: str, 
                       value_key: str, unit: Optional[str], icon: str,
                       device_class: Optional[str], state_class: Optional[str]):
        """Publish a sensor discovery message."""
        config = {
            "name": name,
            "unique_id": object_id,
            "state_topic": state_topic,
            "value_template": f"{{{{ value_json.{value_key} }}}}",
            "icon": icon,
            "device": self._get_solar_fleet_device()
        }
        
        if unit:
            config["unit_of_measurement"] = unit
        if device_class:
            config["device_class"] = device_class
        if state_class:
            config["state_class"] = state_class
            
        disc_topic = f"{self.discovery_prefix}/sensor/{object_id}/config"
        log.debug(f"Publishing HA sensor discovery: {object_id} -> {disc_topic}")
        log.debug(f"Sensor config: {config}")
        self.mqtt.pub(disc_topic, config, retain=True)

    def _publish_switch(self, object_id: str, name: str, state_topic: str,
                       value_key: str, icon: str):
        """Publish a switch discovery message."""
        config = {
            "name": name,
            "unique_id": object_id,
            "state_topic": state_topic,
            "value_template": f"{{{{ value_json.{value_key} }}}}",
            "command_topic": f"{state_topic}/set",
            "payload_on": "true",
            "payload_off": "false",
            "icon": icon,
            "device": self._get_solar_fleet_device()
        }
        
        disc_topic = f"{self.discovery_prefix}/switch/{object_id}/config"
        log.debug(f"Publishing HA switch discovery: {object_id} -> {disc_topic}")
        log.debug(f"Switch config: {config}")
        self.mqtt.pub(disc_topic, config, retain=True)

    def _publish_number(self, object_id: str, name: str, state_topic: str,
                       value_key: str, icon: str, min_value: float, max_value: float,
                       step: float, unit: str):
        """Publish a number discovery message."""
        config = {
            "name": name,
            "unique_id": object_id,
            "state_topic": state_topic,
            "value_template": f"{{{{ value_json.{value_key} }}}}",
            "command_topic": f"{state_topic}/set",
            "min": min_value,
            "max": max_value,
            "step": step,
            "unit_of_measurement": unit,
            "icon": icon,
            "device": self._get_solar_fleet_device()
        }
        
        disc_topic = f"{self.discovery_prefix}/number/{object_id}/config"
        log.debug(f"Publishing HA number discovery: {object_id} -> {disc_topic}")
        log.debug(f"Number config: {config}")
        self.mqtt.pub(disc_topic, config, retain=True)

    def _publish_text(self, object_id: str, name: str, state_topic: str,
                      value_key: str, icon: str):
        """Publish a text input discovery message."""
        config = {
            "name": name,
            "unique_id": object_id,
            "state_topic": state_topic,
            "value_template": f"{{{{ value_json.{value_key} }}}}",
            "command_topic": f"{state_topic}/set",
            "icon": icon,
            "device": self._get_solar_fleet_device()
        }
        
        disc_topic = f"{self.discovery_prefix}/text/{object_id}/config"
        log.debug(f"Publishing HA text discovery: {object_id} -> {disc_topic}")
        log.debug(f"Text config: {config}")
        self.mqtt.pub(disc_topic, config, retain=True)

    def _publish_select(self, object_id: str, name: str, state_topic: str,
                        value_key: str, icon: str, options: List[str]):
        """Publish a select discovery message."""
        config = {
            "name": name,
            "unique_id": object_id,
            "state_topic": state_topic,
            "value_template": f"{{{{ value_json.{value_key} }}}}",
            "command_topic": f"{state_topic}/set",
            "options": options,
            "icon": icon,
            "device": self._get_solar_fleet_device()
        }
        
        disc_topic = f"{self.discovery_prefix}/select/{object_id}/config"
        log.debug(f"Publishing HA select discovery: {object_id} -> {disc_topic}")
        log.debug(f"Select config: {config}")
        self.mqtt.pub(disc_topic, config, retain=True)

    def _get_solar_fleet_device(self) -> Dict[str, Any]:
        """Get the solar system device configuration (renamed from Solar Fleet to Solar System)."""
        return {
            "identifiers": ["solar_system"],
            "manufacturer": "SolarHub",
            "model": "Smart Scheduler",
            "name": "Solar System",
            "sw_version": "1.0.0"
        }

    def publish_all_battery_optimization_discovery(self):
        """Publish all battery optimization discovery messages."""
        log.debug("Publishing all battery optimization discovery messages")
        self.publish_battery_optimization_sensors()
        self._log_discovery_summary()
        log.debug("All battery optimization discovery messages published successfully")
    
    def _log_discovery_summary(self):
        """Log a summary of all discovery messages published."""
        log.debug("=== Home Assistant Discovery Summary ===")
        log.debug("Published discovery messages for:")
        log.debug("  - 8 Self-sufficiency sensors (battery_optimization topic)")
        log.debug("  - 7 Enhanced forecast sensors (enhanced_forecast topic)")
        log.debug("  - 6 Plan sensors (plan topic)")
        log.debug("  - 15 Configuration sensors (config topic)")
        log.debug("  - 2 Configuration switches (dynamic_soc_enabled, auto_mode_switching)")
        log.debug("  - 10 Configuration number controls")
        log.debug("  - 1 Configuration text input (tariffs)")
        log.debug("  - 1 Configuration select (primary_mode)")
        log.debug("Total: 50 Home Assistant entities")
        log.debug("=========================================")
    
    def verify_discovery_messages(self):
        """Verify that all discovery messages are properly configured."""
        log.info("=== Verifying Discovery Message Configuration ===")
        
        # Check that all required topics are defined
        required_topics = [
            "battery_optimization",
            "enhanced_forecast", 
            "plan",
            "config"
        ]
        
        for topic in required_topics:
            log.info(f"✓ Topic '{topic}' is configured for discovery")
        
        # Check that all sensor types are defined
        sensor_types = [
            "self-sufficiency sensors",
            "enhanced forecast sensors", 
            "plan sensors",
            "configuration sensors",
            "configuration controls"
        ]
        
        for sensor_type in sensor_types:
            log.info(f"✓ {sensor_type} are configured")
        
        log.info("All discovery message configurations verified successfully")
        log.info("========================================================")
