"""
Home Assistant discovery for inverter configuration sensors.
Publishes RW sensors marked with ha_config: true as Home Assistant entities.
"""
import json
import logging
from typing import Dict, Any, List, Optional
from solarhub.ha.discovery import HADiscoveryPublisher, _sanitize_key

log = logging.getLogger(__name__)

class InverterConfigDiscovery(HADiscoveryPublisher):
    """
    Home Assistant discovery for inverter configuration sensors.
    Publishes RW sensors marked with ha_config: true as Home Assistant entities.
    """

    def __init__(self, mqtt_client, base_topic: str, discovery_prefix: str = "homeassistant"):
        super().__init__(mqtt_client, base_topic, discovery_prefix)
        self.base_topic = base_topic.rstrip("/")

    def publish_inverter_config_sensors(self, inverter_id: str, register_map: List[Dict[str, Any]]):
        """Publish discovery messages for inverter configuration sensors."""
        try:
            log.debug(f"Publishing inverter configuration discovery messages for {inverter_id}")
            
            # Clear any old discovery messages for this inverter first
            self._clear_old_discovery_messages(inverter_id)
            
            # Force clear any old discovery messages that might be cached
            self._force_clear_all_old_discovery_messages(inverter_id)
            
            # Store register map for later use
            self._register_map = register_map
            
            # Filter for RW sensors with ha_config: true
            config_sensors = [r for r in register_map if r.get("rw") == "RW" and r.get("ha_config") is True]
            
            if not config_sensors:
                log.info(f"No configuration sensors found for {inverter_id}")
                return
            
            log.info(f"Found {len(config_sensors)} configuration sensors for {inverter_id}")
            
            for sensor in config_sensors:
                try:
                    self._publish_sensor_discovery(inverter_id, sensor)
                except Exception as e:
                    log.error(f"Failed to publish discovery for sensor {sensor.get('id', 'unknown')}: {e}")
                    continue
            
            log.info(f"Published {len(config_sensors)} inverter configuration sensors for {inverter_id}")
        except Exception as e:
            log.error(f"Failed to publish inverter configuration discovery for {inverter_id}: {e}")

    def _publish_sensor_discovery(self, inverter_id: str, sensor: Dict[str, Any]):
        """Publish discovery message for a single sensor."""
        sensor_id = sensor.get("id", "unknown")
        sensor_name = sensor.get("name", sensor_id)
        
        # Create unique entity ID
        entity_id = f"senergy_{inverter_id}_{sensor_id}"
        
        # Determine component type based on sensor properties
        component = self._determine_component_type(sensor)
        
        # Create discovery topic
        discovery_topic = f"{self.discovery_prefix}/{component}/{entity_id}/config"
        
        # Create configuration
        config = {
            "name": f"SEnergy {inverter_id.title()} {sensor_name}",
            "unique_id": entity_id,
            "device": self._get_device_info(inverter_id),
            "state_topic": f"{self.base_topic}/{inverter_id}/config/{sensor_id}",
            "command_topic": f"{self.base_topic}/{inverter_id}/config/{sensor_id}/set",
            "retain": True
        }
        
        # Add component-specific configuration
        if component == "select":
            config.update(self._get_select_config(sensor))
        elif component == "number":
            config.update(self._get_number_config(sensor))
        elif component == "switch":
            config.update(self._get_switch_config(sensor))
        
        # Add common attributes
        config.update(self._get_common_config(sensor))
        
        # Publish discovery message
        self.mqtt.pub(discovery_topic, config, retain=True)
        log.debug(f"Published {component} discovery for {entity_id}")
        log.debug(f"Discovery topic: {discovery_topic}")
        log.debug(f"Discovery config: {config}")

    def _determine_component_type(self, sensor: Dict[str, Any]) -> str:
        """Determine Home Assistant component type based on sensor properties."""
        # Check for enum (select)
        if sensor.get("enum"):
            return "select"
        
        # Check for boolean encoder (switch)
        if sensor.get("encoder") == "bool":
            return "switch"
        
        # Check for boolean enum (switch)
        enum = sensor.get("enum", {})
        if enum and len(enum) == 2:
            values = list(enum.values())
            if any("disable" in str(v).lower() or "enable" in str(v).lower() for v in values):
                return "switch"
        
        # Default to number
        return "number"

    def _get_select_config(self, sensor: Dict[str, Any]) -> Dict[str, Any]:
        """Get configuration for select component."""
        enum = sensor.get("enum", {})
        options = list(enum.values())
        
        return {
            "options": options,
            "value_template": "{{ value_json.value }}",
            "json_attributes_topic": f"{self.base_topic}/{sensor.get('id', 'unknown')}/config",
            "json_attributes_template": "{{ value_json | tojson }}"
        }

    def _get_number_config(self, sensor: Dict[str, Any]) -> Dict[str, Any]:
        """Get configuration for number component."""
        config = {
            "value_template": "{{ value_json.value }}",
            "json_attributes_topic": f"{self.base_topic}/{sensor.get('id', 'unknown')}/config",
            "json_attributes_template": "{{ value_json | tojson }}"
        }
        
        # Add min/max/step if available
        if "min" in sensor:
            config["min"] = sensor["min"]
        if "max" in sensor:
            config["max"] = sensor["max"]
        if "step" in sensor:
            config["step"] = sensor["step"]
        
        # Add unit if available
        if "unit" in sensor:
            config["unit_of_measurement"] = sensor["unit"]
        
        # Add mode if available
        if "mode" in sensor:
            config["mode"] = sensor["mode"]
        
        return config

    def _get_switch_config(self, sensor: Dict[str, Any]) -> Dict[str, Any]:
        """Get configuration for switch component."""
        return {
            "payload_on": "Enable",
            "payload_off": "Disable",
            "value_template": "{{ value_json.value }}",
            "json_attributes_topic": f"{self.base_topic}/{sensor.get('id', 'unknown')}/config",
            "json_attributes_template": "{{ value_json | tojson }}"
        }

    def _get_common_config(self, sensor: Dict[str, Any]) -> Dict[str, Any]:
        """Get common configuration for all components."""
        config = {}
        
        # Add icon
        if "icon" in sensor:
            config["icon"] = sensor["icon"]
        else:
            config["icon"] = self._get_default_icon(sensor)
        
        # Add device class if applicable
        device_class = self._get_device_class(sensor)
        if device_class:
            config["device_class"] = device_class
        
        # Add state class if applicable
        state_class = self._get_state_class(sensor)
        if state_class:
            config["state_class"] = state_class
        
        return config

    def _get_default_icon(self, sensor: Dict[str, Any]) -> str:
        """Get default icon for sensor."""
        sensor_id = sensor.get("id", "").lower()
        sensor_name = sensor.get("name", "").lower()
        
        # Power-related
        if any(keyword in sensor_id or keyword in sensor_name for keyword in ["power", "charge", "discharge"]):
            return "mdi:lightning-bolt"
        
        # Battery-related
        if any(keyword in sensor_id or keyword in sensor_name for keyword in ["battery", "soc", "capacity"]):
            return "mdi:battery"
        
        # Grid-related
        if any(keyword in sensor_id or keyword in sensor_name for keyword in ["grid", "feed"]):
            return "mdi:transmission-tower"
        
        # Mode-related
        if any(keyword in sensor_id or keyword in sensor_name for keyword in ["mode", "work", "control"]):
            return "mdi:cog"
        
        # Address-related
        if any(keyword in sensor_id or keyword in sensor_name for keyword in ["address", "comm"]):
            return "mdi:network"
        
        # Default
        return "mdi:settings"

    def _get_device_class(self, sensor: Dict[str, Any]) -> Optional[str]:
        """Get device class for sensor."""
        unit = sensor.get("unit", "").lower()
        
        if unit in ["w", "kw", "mw"]:
            return "power"
        elif unit in ["%"]:
            return "battery"
        elif unit in ["ah"]:
            return "battery"
        
        return None

    def _get_state_class(self, sensor: Dict[str, Any]) -> Optional[str]:
        """Get state class for sensor."""
        unit = sensor.get("unit", "").lower()
        
        if unit in ["w", "kw", "mw", "%", "ah"]:
            return "measurement"
        
        return None

    def _get_device_info(self, inverter_id: str) -> Dict[str, Any]:
        """Get device information for inverter."""
        return {
            "identifiers": [inverter_id],
            "name": f"SEnergy {inverter_id.title()}",
            "manufacturer": "SEnergy",
            "model": "Hybrid Inverter",
            "sw_version": "1.0"
        }

    def publish_sensor_state(self, inverter_id: str, sensor_id: str, value: Any, attributes: Dict[str, Any] = None):
        """Publish sensor state."""
        log.debug(f"Starting to publish sensor state for {sensor_id}={value}")
        state_topic = f"{self.base_topic}/{inverter_id}/config/{sensor_id}"
        
        payload = {
            "value": value,
            "timestamp": self._get_timestamp()
        }
        
        if attributes:
            payload.update(attributes)
        
        log.debug(f"Publishing to topic: {state_topic}")
        self.mqtt.pub(state_topic, payload, retain=True)
        log.debug(f"Successfully published state for {sensor_id}: {value}")

    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        from solarhub.timezone_utils import now_configured_iso
        return now_configured_iso()

    def publish_current_inverter_config_values(self, inverter_id: str, telemetry_data: Dict[str, Any], register_map: List[Dict[str, Any]] = None):
        """Publish current inverter configuration values to state topics."""
        try:
            # Use provided register map or fall back to stored one
            if register_map is not None:
                config_sensors = [r for r in register_map if r.get("rw") == "RW" and r.get("ha_config") is True]
            elif hasattr(self, '_register_map'):
                config_sensors = [r for r in self._register_map if r.get("rw") == "RW" and r.get("ha_config") is True]
            else:
                log.warning("Register map not available for publishing current values")
                return
            log.info(f"Syncing current inverter config values for {inverter_id} (candidates: {len(config_sensors)})")
            
            published = 0
            for sensor in config_sensors:
                sensor_id = sensor.get("id")
                if not sensor_id:
                    continue
                
                # Get current value from telemetry
                current_value = telemetry_data.get(sensor_id)
                if current_value is not None:
                    # Publish current value to state topic
                    self.publish_sensor_state(inverter_id, sensor_id, current_value)
                    published += 1
                    log.debug(f"Published current inverter config state {sensor_id}={current_value}")
                else:
                    log.debug(f"No current value found for {sensor_id}")
            log.info(f"Published {published} current inverter config states for {inverter_id}")
                    
        except Exception as e:
            log.error(f"Failed to publish current inverter config values: {e}")

    def _clear_old_discovery_messages(self, inverter_id: str):
        """Clear old discovery messages that might point to wrong command topics."""
        try:
            # List of known inverter config sensors that might have old discovery messages
            known_sensors = [
                "hybrid_work_mode", "battery_type_selection", "bms_comm_address", "battery_ah_ah_",
                "grid_charge", "maximum_grid_charge_power", "capacity_of_grid_charger_end",
                "max_charge_power", "capacity_of_charger_end_soc_", "max_discharge_power",
                "capacity_of_discharger_end_eod_", "off_grid_mode", "off_grid_start_up_battery_capacity",
                "modbus_address", "maximum_feed_in_grid_power", "inverter_control"
            ]
            
            # Clear old discovery messages for these sensors
            cleared_count = 0
            for sensor_id in known_sensors:
                entity_id = f"senergy_{inverter_id}_{sensor_id}"
                # Clear for all possible component types
                for component in ["select", "number", "switch"]:
                    old_topic = f"{self.discovery_prefix}/{component}/{entity_id}/config"
                    self.mqtt.pub(old_topic, "", retain=True)
                    cleared_count += 1
                    log.debug(f"Cleared old discovery message: {old_topic}")
            
            # Also clear any old discovery messages that might use different naming patterns
            # Clear old patterns that might exist
            old_patterns = [
                f"{self.discovery_prefix}/select/{inverter_id}_*/config",
                f"{self.discovery_prefix}/number/{inverter_id}_*/config", 
                f"{self.discovery_prefix}/switch/{inverter_id}_*/config"
            ]
            
            for pattern in old_patterns:
                # Note: MQTT doesn't support wildcards in publish, but we can try common variations
                for sensor_id in known_sensors:
                    old_topic = pattern.replace("*", sensor_id)
                    self.mqtt.pub(old_topic, "", retain=True)
                    cleared_count += 1
                    log.debug(f"Cleared old discovery message pattern: {old_topic}")
            
            log.debug(f"Cleared {cleared_count} old discovery messages for {inverter_id}")
        except Exception as e:
            log.warning(f"Failed to clear old discovery messages for {inverter_id}: {e}")

    def _force_clear_all_old_discovery_messages(self, inverter_id: str):
        """Force clear all possible old discovery message patterns."""
        try:
            # Clear all possible old discovery message patterns that might exist
            patterns_to_clear = [
                # Standard patterns
                f"{self.discovery_prefix}/select/{inverter_id}_*/config",
                f"{self.discovery_prefix}/number/{inverter_id}_*/config",
                f"{self.discovery_prefix}/switch/{inverter_id}_*/config",
                # Alternative patterns
                f"{self.discovery_prefix}/select/senergy_{inverter_id}_*/config",
                f"{self.discovery_prefix}/number/senergy_{inverter_id}_*/config", 
                f"{self.discovery_prefix}/switch/senergy_{inverter_id}_*/config",
                # Direct patterns
                f"{self.discovery_prefix}/select/{inverter_id}*/config",
                f"{self.discovery_prefix}/number/{inverter_id}*/config",
                f"{self.discovery_prefix}/switch/{inverter_id}*/config"
            ]
            
            # Since MQTT doesn't support wildcards in publish, we'll clear specific known entities
            known_entities = [
                f"{inverter_id}_hybrid_work_mode", f"senergy_{inverter_id}_hybrid_work_mode",
                f"{inverter_id}_grid_charge", f"senergy_{inverter_id}_grid_charge",
                f"{inverter_id}_capacity_of_grid_charger_end", f"senergy_{inverter_id}_capacity_of_grid_charger_end",
                f"{inverter_id}_max_charge_power", f"senergy_{inverter_id}_max_charge_power",
                f"{inverter_id}_capacity_of_charger_end_soc_", f"senergy_{inverter_id}_capacity_of_charger_end_soc_",
                f"{inverter_id}_max_discharge_power", f"senergy_{inverter_id}_max_discharge_power",
                f"{inverter_id}_capacity_of_discharger_end_eod_", f"senergy_{inverter_id}_capacity_of_discharger_end_eod_"
            ]
            
            cleared_count = 0
            for entity in known_entities:
                for component in ["select", "number", "switch"]:
                    topic = f"{self.discovery_prefix}/{component}/{entity}/config"
                    self.mqtt.pub(topic, "", retain=True)
                    cleared_count += 1
                    log.debug(f"Force cleared old discovery message: {topic}")
            
            log.debug(f"Force cleared {cleared_count} old discovery messages for {inverter_id}")
        except Exception as e:
            log.warning(f"Failed to force clear old discovery messages for {inverter_id}: {e}")
