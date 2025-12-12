# discovery.py
import json
import logging
import sqlite3
from typing import Any, Dict, List, Optional
from datetime import datetime, date
from solarhub.timezone_utils import now_configured, to_configured

log = logging.getLogger("solarhub.ha.discovery")

DISCOVERY_PREFIX = "homeassistant"

def _sanitize_key(s: str) -> str:
    return "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in str(s).strip().lower()).strip("_")

def _entity_id(runtime, key: str) -> str:
    base = getattr(runtime.cfg, "id", "inverter")
    return f"{_sanitize_key(base)}_{_sanitize_key(key)}"

def _register_to_telemetry_mapping() -> Dict[str, str]:
    """
    Map register IDs to telemetry field names for calculated values.
    This ensures Home Assistant gets the calculated values instead of raw register values.
    """
    return {
        # Power calculations - use calculated values instead of raw registers
        # Standardized IDs (preferred)
        "battery_power_w": "batt_power_w",  # Use calculated battery power (voltage * current)
        "pv1_power_w": "pv1_power_w",       # PV1 power from register
        "pv2_power_w": "pv2_power_w",       # PV2 power from register
        "pv_power": "pv_power_w",            # Use calculated PV power (sum of MPPT powers)
        "load_power_w": "load_power_w",      # Use calculated load power (load + EPS)
        "grid_power_w": "grid_power_w",      # Use calculated grid power
        
        # Other telemetry mappings - standardized IDs
        "battery_voltage_v": "batt_voltage_v",
        "battery_current_a": "batt_current_a", 
        "battery_soc_pct": "batt_soc_pct",
        "inverter_temp_c": "inverter_temp_c",
        
        # Backward compatibility mappings (deprecated)
        "battery_power": "batt_power_w",
        "battery_voltage": "batt_voltage_v",
        "battery_current": "batt_current_a", 
        "battery_soc": "batt_soc_pct",
        "inner_temperature": "inverter_temp_c",
    }

def _component_for_register(r: Dict[str, Any]) -> str:
    rw = str(r.get("rw", "RO")).upper()
    enc = (r.get("encoder") or "").lower()
    has_enum = isinstance(r.get("enum"), dict) and len(r["enum"]) > 0
    if rw in ("RW", "WO"):
        if enc == "bool":
            return "switch"
        if has_enum:
            return "select"
        if enc == "ascii":
            return "text"
        return "number"
    return "sensor"

class HADiscoveryPublisher:
    """
    Simple HA discovery:
      - All entities read from:  <base>/<id>/regs
      - value_template:          {{ value_json.<key> }}
      - RW entities write to:    <base>/<id>/write
    """

    def __init__(self, mqtt_client, base_topic: str, discovery_prefix: str = DISCOVERY_PREFIX, db_path: Optional[str] = None) -> None:
        self.mqtt = mqtt_client
        self.base_topic = base_topic.rstrip("/")
        self.discovery_prefix = discovery_prefix.rstrip("/")
        self.db_path = db_path  # Database path for energy calculations

    def _disc_topic(self, component: str, object_id: str) -> str:
        return f"{self.discovery_prefix}/{component}/{object_id}/config"
    
    def _clear_discovery_entity(self, component: str, object_id: str) -> None:
        """Clear a discovery entity by publishing empty payload."""
        topic = self._disc_topic(component, object_id)
        try:
            self.mqtt.pub(topic, "", retain=True)
            log.debug(f"Cleared discovery entity: {topic}")
        except Exception as e:
            log.warning(f"Failed to clear discovery entity {topic}: {e}")

    def _regs_topic(self, device_id: str) -> str:
        return f"{self.base_topic}/{device_id}/regs"


    def _device_block(self, runtime) -> Dict[str, Any]:
        dev_id = getattr(runtime.cfg, "id", "inverter")
        manufacturer = getattr(runtime.cfg, "manufacturer", "Senergy")
        model = getattr(runtime.cfg, "model", "Hybrid Inverter")
        # Use inverter ID as device name, not the config name (which might be "west roof" or array name)
        # The config name can be used as a friendly name, but device identifier should be the inverter ID
        name = dev_id  # Use ID as device name for clarity in HA
        # Ensure all required fields are present to avoid "unknown device"
        device_info = {
            "identifiers": [dev_id],
            "manufacturer": manufacturer or "Unknown",
            "model": model or "Hybrid Inverter",
            "name": name or dev_id,
        }
        # Add serial number if available from telemetry
        if hasattr(runtime.adapter, 'last_tel') and runtime.adapter.last_tel:
            tel_dict = runtime.adapter.last_tel.model_dump() if hasattr(runtime.adapter.last_tel, 'model_dump') else runtime.adapter.last_tel.dict()
            if tel_dict and tel_dict.get("device_serial_number"):
                device_info["serial_number"] = str(tel_dict["device_serial_number"])
        return device_info

    # Public API expected by app.py
    def publish_all_for_inverter(self, runtime, inverter_count: int = 1, array_id: Optional[str] = None) -> None:
        """
        Publish all registers for an inverter according to Telemetry & Hierarchy Specification.
        
        Publishes:
        - All register-based sensors (existing functionality)
        - Calculated power fields (load_power, solar_power, grid_power, battery_power)
        - Energy sensors (cumulative and daily) if not already in registers
        
        Args:
            runtime: InverterRuntime object
            inverter_count: Number of inverters in the system (default: 1)
            array_id: Optional array ID for via_device relationship
        """
        regs = getattr(runtime.adapter, "regs", []) or []
        
        # Get inverter metadata to determine what to publish
        from solarhub.inverter_metadata import get_inverter_metadata
        
        # Try to get metadata from last telemetry if available
        metadata = None
        if hasattr(runtime.adapter, 'last_tel') and runtime.adapter.last_tel:
            tel_dict = runtime.adapter.last_tel.model_dump() if hasattr(runtime.adapter.last_tel, 'model_dump') else runtime.adapter.last_tel.dict()
            if runtime.adapter.last_tel.extra:
                tel_dict.update(runtime.adapter.last_tel.extra)
            
            config_phase_type = getattr(runtime.cfg, 'phase_type', None)
            metadata = get_inverter_metadata(tel_dict, config_phase_type, inverter_count)
        
        for r in regs:
            # Skip all RW sensors (they should only be published as config entities by inverter config discovery when ha_config: true)
            if r.get("rw") == "RW":
                continue
            
            # For three-phase inverters, publish phase-specific registers
            # For single-phase inverters, skip phase-specific registers
            reg_id = r.get("id", "").lower()
            is_phase_register = any(phase in reg_id for phase in ["_l1_", "_l2_", "_l3_", "_line_voltage_ab", "_line_voltage_bc", "_line_voltage_ca"])
            
            if is_phase_register:
                # Only publish phase registers for three-phase inverters
                if metadata and metadata.phase_type == "three":
                    self.publish_register(runtime, r, array_id=array_id)
                # Skip for single-phase inverters
                continue
            
            self.publish_register(runtime, r, array_id=array_id)
        
        # Publish calculated/standardized fields that might not be registers
        # These are in the MQTT payload but need explicit HA discovery entities
        self._publish_calculated_fields(runtime, array_id=array_id)
    
    def _publish_calculated_fields(self, runtime, array_id: Optional[str] = None) -> None:
        """
        Publish HA discovery for calculated/standardized fields that are in the MQTT payload
        but might not be registers (e.g., pv_power_w which is calculated from pv1_power_w + pv2_power_w).
        Also publishes energy sensors according to Telemetry & Hierarchy Specification.
        
        Args:
            runtime: InverterRuntime object
            array_id: Optional array ID for via_device relationship
        """
        device_id = getattr(runtime.cfg, "id", "inverter")
        regs_topic = self._regs_topic(device_id)
        
        # Get device_info with via_device if array_id is provided
        device_info = self._device_block(runtime)
        if array_id:
            device_info["via_device"] = f"array:{array_id}"
        
        # List of calculated power fields that should always be published
        calculated_power_fields = [
            ("pv_power_w", "PV Power", "W", "power"),
            ("solar_power", "Solar Power", "W", "power"),  # Alias for pv_power_w
            ("load_power", "Load Power", "W", "power"),
            ("grid_power", "Grid Power", "W", "power"),  # positive = import, negative = export
            ("battery_power", "Battery Power", "W", "power"),  # positive = discharge, negative = charge
        ]
        
        for field_key, name, unit, device_class in calculated_power_fields:
            object_id = _entity_id(runtime, field_key)
            
            # Check if this field was already published as a register
            regs = getattr(runtime.adapter, "regs", []) or []
            already_published = any(
                r.get("id") == field_key or 
                r.get("standard_id") == field_key or
                _register_to_telemetry_mapping().get(r.get("id")) == field_key
                for r in regs
            )
            
            if already_published:
                continue  # Skip if already published as a register
            
            cfg: Dict[str, Any] = {
                "name": name,
                "unique_id": object_id,
                "state_topic": regs_topic,
                "value_template": f"{{{{ value_json.{field_key} | default(value_json.{field_key.replace('_power', '_power_w')}, 0) }}}}",
                "device": device_info,
                "unit_of_measurement": unit,
                "device_class": device_class,
                "state_class": "measurement",
            }
            
            disc_topic = self._disc_topic("sensor", object_id)
            try:
                self.mqtt.pub(disc_topic, cfg, retain=True)
                log.debug(f"Published calculated power field discovery: {disc_topic}")
            except Exception as e:
                log.error(f"Failed to publish calculated power field discovery to {disc_topic}: {e}", exc_info=True)
        
        # Energy sensors (cumulative and daily) - these may not be in registers, add them
        # Note: These will be populated from hourly_energy table when telemetry is published
        energy_sensors = [
            # Cumulative energy
            ("total_load_energy", "Total Load Energy", "kWh", "energy", "total_increasing"),
            ("total_grid_import", "Total Grid Import", "kWh", "energy", "total_increasing"),
            ("total_grid_export", "Total Grid Export", "kWh", "energy", "total_increasing"),
            ("total_solar_energy", "Total Solar Energy", "kWh", "energy", "total_increasing"),
            ("total_battery_discharge", "Total Battery Discharge", "kWh", "energy", "total_increasing"),
            ("total_battery_charge", "Total Battery Charge", "kWh", "energy", "total_increasing"),
            # Daily energy
            ("today_load_energy", "Today Load Energy", "kWh", "energy", "total_increasing"),
            ("today_grid_import", "Today Grid Import", "kWh", "energy", "total_increasing"),
            ("today_grid_export", "Today Grid Export", "kWh", "energy", "total_increasing"),
            ("today_solar_energy", "Today Solar Energy", "kWh", "energy", "total_increasing"),
            ("today_battery_discharge", "Today Battery Discharge", "kWh", "energy", "total_increasing"),
            ("today_battery_charge", "Today Battery Charge", "kWh", "energy", "total_increasing"),
        ]
        
        for field_key, name, unit, device_class, state_class in energy_sensors:
            object_id = _entity_id(runtime, field_key)
            
            # Check if this field was already published as a register
            regs = getattr(runtime.adapter, "regs", []) or []
            already_published = any(
                r.get("id") == field_key or 
                r.get("standard_id") == field_key
                for r in regs
            )
            
            if already_published:
                continue  # Skip if already published as a register
            
            cfg: Dict[str, Any] = {
                "name": name,
                "unique_id": object_id,
                "state_topic": regs_topic,
                "value_template": f"{{{{ value_json.{field_key} | default(0) }}}}",
                "device": device_info,
                "unit_of_measurement": unit,
                "device_class": device_class,
                "state_class": state_class,
            }
            
            disc_topic = self._disc_topic("sensor", object_id)
            try:
                self.mqtt.pub(disc_topic, cfg, retain=True)
                log.debug(f"Published calculated energy field discovery: {disc_topic}")
            except Exception as e:
                log.error(f"Failed to publish calculated energy field discovery to {disc_topic}: {e}", exc_info=True)

    def publish_all(self, runtime, register_specs: Optional[List[Dict[str, Any]]] = None) -> None:
        if register_specs:
            for r in register_specs:
                # Skip all RW sensors (they should only be published as config entities by inverter config discovery when ha_config: true)
                if r.get("rw") == "RW":
                    continue
                self.publish_register(runtime, r)
        else:
            self.publish_all_for_inverter(runtime)

    def refresh_device_info(self, runtime, inverter_count: int = 1) -> None:
        """
        Refresh device info and republish all registers.
        
        Args:
            runtime: InverterRuntime object
            inverter_count: Number of inverters in the system (default: 1)
        """
        self.publish_all_for_inverter(runtime, inverter_count)

    def publish_register(self, runtime, r: Dict[str, Any], array_id: Optional[str] = None) -> None:
        component = _component_for_register(r)

        # decide field key used in flat /regs
        # Priority: standard_id > ha_key > reg_id > name
        reg_id = r.get("id")
        name = r.get("name")
        
        # Use standard_id if available (from TelemetryMapper)
        field_key = r.get("standard_id")
        
        # Fallback to ha_key if standard_id not available
        if not field_key:
            field_key = r.get("ha_key")
        
        # Fallback to reg_id or name
        if not field_key:
            field_key = reg_id if reg_id else name
        
        # Final fallback to address-based key
        if not field_key:
            if "addr" in r:
                try:
                    field_key = f"reg_{int(r['addr']):04x}"
                except Exception:
                    field_key = "value"
            else:
                field_key = "value"
        
        # Map register ID to telemetry field name for calculated values (backward compatibility)
        telemetry_mapping = _register_to_telemetry_mapping()
        if reg_id in telemetry_mapping:
            # Only use mapping if standard_id wasn't already set
            if not r.get("standard_id"):
                field_key = telemetry_mapping[reg_id]
                log.debug(f"Mapped register {reg_id} to telemetry field {field_key}")
        
        # Debug logging for device model and serial number discovery
        if reg_id in ["device_model", "device_serial_number"]:
            log.debug(f"Discovery for {reg_id}: field_key='{field_key}', name='{name}'")

        device_id = getattr(runtime.cfg, "id", "inverter")
        object_id = _entity_id(runtime, field_key)
        regs_topic = self._regs_topic(device_id)

        # Get device_info with via_device if array_id is provided
        device_info = self._device_block(runtime)
        if array_id:
            device_info["via_device"] = f"array:{array_id}"

        cfg: Dict[str, Any] = {
            "name": name or reg_id or field_key.replace("_", " ").title(),
            "unique_id": object_id,
            "state_topic": regs_topic,
            "value_template": f"{{{{ value_json.{field_key} }}}}",
            "device": device_info,
        }
        
        # Add unit of measurement and energy device class for sensors
        if r.get("unit") and r["unit"] != "ascii":
            cfg["unit_of_measurement"] = r["unit"]
            
            # Add energy device class and state class for energy-related sensors
            if r["unit"].lower() in ["kwh", "wh", "mwh"]:
                cfg["device_class"] = "energy"
                # Determine state class based on sensor type
                sensor_id = r.get("id", "").lower()
                sensor_name = r.get("name", "").lower()
                
                # Cumulative/total energy sensors should use "total_increasing"
                if any(keyword in sensor_id or keyword in sensor_name for keyword in 
                       ["total", "accumulated", "daily", "today"]):
                    cfg["state_class"] = "total_increasing"
                else:
                    # Other energy sensors use "measurement"
                    cfg["state_class"] = "measurement"

        disc_topic = self._disc_topic(component, object_id)
        try:
            self.mqtt.pub(disc_topic, cfg, retain=True)
            log.debug(f"Published HA discovery: {disc_topic}")
        except Exception as e:
            log.error(f"Failed to publish HA discovery to {disc_topic}: {e}", exc_info=True)
    
    def _array_state_topic(self, array_id: str) -> str:
        """Get MQTT topic for array state."""
        return f"{self.base_topic}/arrays/{array_id}/state"
    
    def _pack_state_topic(self, pack_id: str) -> str:
        """Get MQTT topic for battery pack state."""
        return f"{self.base_topic}/packs/{pack_id}/state"
    
    def _home_state_topic(self, home_id: str = "home") -> str:
        """Get MQTT topic for home state."""
        return f"{self.base_topic}/home/{home_id}/state"
    
    def _get_array_energy_totals(self, array_id: str) -> Dict[str, float]:
        """
        Get cumulative and daily energy totals for an array from array_hourly_energy table.
        
        Returns:
            Dictionary with cumulative and daily energy values in kWh
        """
        if not self.db_path:
            return {}
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get cumulative totals (sum of all hourly energy)
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(solar_energy_kwh), 0) as total_solar,
                    COALESCE(SUM(load_energy_kwh), 0) as total_load,
                    COALESCE(SUM(grid_import_energy_kwh), 0) as total_grid_import,
                    COALESCE(SUM(grid_export_energy_kwh), 0) as total_grid_export,
                    COALESCE(SUM(battery_charge_energy_kwh), 0) as total_battery_charge,
                    COALESCE(SUM(battery_discharge_energy_kwh), 0) as total_battery_discharge
                FROM array_hourly_energy
                WHERE array_id = ?
            """, (array_id,))
            
            row = cursor.fetchone()
            cumulative = {
                "total_solar_energy": row[0] if row else 0.0,
                "total_load_energy": row[1] if row else 0.0,
                "total_grid_import": row[2] if row else 0.0,
                "total_grid_export": row[3] if row else 0.0,
                "total_battery_charge": row[4] if row else 0.0,
                "total_battery_discharge": row[5] if row else 0.0,
            }
            
            # Get today's totals (sum of today's hourly energy)
            today = now_configured().date()
            today_str = today.strftime('%Y-%m-%d')
            
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(solar_energy_kwh), 0) as today_solar,
                    COALESCE(SUM(load_energy_kwh), 0) as today_load,
                    COALESCE(SUM(grid_import_energy_kwh), 0) as today_grid_import,
                    COALESCE(SUM(grid_export_energy_kwh), 0) as today_grid_export,
                    COALESCE(SUM(battery_charge_energy_kwh), 0) as today_battery_charge,
                    COALESCE(SUM(battery_discharge_energy_kwh), 0) as today_battery_discharge
                FROM array_hourly_energy
                WHERE array_id = ? AND date = ?
            """, (array_id, today_str))
            
            row = cursor.fetchone()
            daily = {
                "today_solar_energy": row[0] if row else 0.0,
                "today_load_energy": row[1] if row else 0.0,
                "today_grid_import": row[2] if row else 0.0,
                "today_grid_export": row[3] if row else 0.0,
                "today_battery_charge": row[4] if row else 0.0,
                "today_battery_discharge": row[5] if row else 0.0,
            }
            
            conn.close()
            return {**cumulative, **daily}
            
        except Exception as e:
            log.error(f"Failed to get array energy totals for {array_id}: {e}", exc_info=True)
            return {}
    
    def publish_array_entities(self, array_id: str, array_name: Optional[str] = None, inverter_ids: Optional[List[str]] = None, pack_ids: Optional[List[str]] = None, system_id: Optional[str] = None) -> None:
        """
        Publish Home Assistant discovery entities for an inverter array according to Telemetry & Hierarchy Specification.
        
        Publishes:
        - Real-time power telemetry (load_power, solar_power, grid_power, battery_power)
        - Cumulative energy telemetry (total_*)
        - Daily energy telemetry (today_*)
        
        Args:
            array_id: Array ID
            array_name: Optional array name
            inverter_ids: List of inverter IDs in this array
            pack_ids: List of battery pack IDs attached to this array
            system_id: Optional system ID (for via_device relationships)
        """
        device_id = f"array_{_sanitize_key(array_id)}"
        device_name = array_name or array_id.replace("_", " ").title()
        state_topic = self._array_state_topic(array_id)
        
        device_info = {
            "identifiers": [f"array:{array_id}"],
            "name": device_name,
            "model": "Inverter Array",
            "manufacturer": "SolarHub",
        }
        
        # Add via_device relationship - prefer system
        if system_id:
            device_info["via_device"] = f"system:{system_id}"
        elif inverter_ids:
            # Fallback to first inverter if no system
            device_info["via_device"] = f"inverter:{inverter_ids[0]}"
        
        # Real-time power sensors (W)
        power_sensors = [
            ("load_power", "Load Power", "W", "power"),
            ("solar_power", "Solar Power", "W", "power"),
            ("grid_power", "Grid Power", "W", "power"),  # positive = import, negative = export
            ("battery_power", "Battery Power", "W", "power"),  # positive = discharge, negative = charge
        ]
        
        for field_key, name, unit, device_class in power_sensors:
            object_id = f"{device_id}_{field_key}"
            cfg = {
                "name": f"{device_name} {name}",
                "unique_id": object_id,
                "state_topic": state_topic,
                "value_template": f"{{{{ value_json.{field_key} }}}}",
                "device": device_info,
                "unit_of_measurement": unit,
                "device_class": device_class,
                "state_class": "measurement",
            }
            disc_topic = self._disc_topic("sensor", object_id)
            try:
                self.mqtt.pub(disc_topic, cfg, retain=True)
                log.debug(f"Published array power sensor discovery: {disc_topic}")
            except Exception as e:
                log.error(f"Failed to publish array power sensor discovery to {disc_topic}: {e}", exc_info=True)
        
        # Cumulative energy sensors (kWh) - total_increasing state_class
        cumulative_energy_sensors = [
            ("total_load_energy", "Total Load Energy", "kWh", "energy"),
            ("total_grid_import", "Total Grid Import", "kWh", "energy"),
            ("total_grid_export", "Total Grid Export", "kWh", "energy"),
            ("total_solar_energy", "Total Solar Energy", "kWh", "energy"),
            ("total_battery_discharge", "Total Battery Discharge", "kWh", "energy"),
            ("total_battery_charge", "Total Battery Charge", "kWh", "energy"),
        ]
        
        for field_key, name, unit, device_class in cumulative_energy_sensors:
            object_id = f"{device_id}_{field_key}"
            cfg = {
                "name": f"{device_name} {name}",
                "unique_id": object_id,
                "state_topic": state_topic,
                "value_template": f"{{{{ value_json.{field_key} }}}}",
                "device": device_info,
                "unit_of_measurement": unit,
                "device_class": device_class,
                "state_class": "total_increasing",
            }
            disc_topic = self._disc_topic("sensor", object_id)
            try:
                self.mqtt.pub(disc_topic, cfg, retain=True)
                log.debug(f"Published array cumulative energy sensor discovery: {disc_topic}")
            except Exception as e:
                log.error(f"Failed to publish array cumulative energy sensor discovery to {disc_topic}: {e}", exc_info=True)
        
        # Daily energy sensors (kWh) - total_increasing state_class (resets daily)
        daily_energy_sensors = [
            ("today_load_energy", "Today Load Energy", "kWh", "energy"),
            ("today_grid_import", "Today Grid Import", "kWh", "energy"),
            ("today_grid_export", "Today Grid Export", "kWh", "energy"),
            ("today_solar_energy", "Today Solar Energy", "kWh", "energy"),
            ("today_battery_discharge", "Today Battery Discharge", "kWh", "energy"),
            ("today_battery_charge", "Today Battery Charge", "kWh", "energy"),
        ]
        
        for field_key, name, unit, device_class in daily_energy_sensors:
            object_id = f"{device_id}_{field_key}"
            cfg = {
                "name": f"{device_name} {name}",
                "unique_id": object_id,
                "state_topic": state_topic,
                "value_template": f"{{{{ value_json.{field_key} }}}}",
                "device": device_info,
                "unit_of_measurement": unit,
                "device_class": device_class,
                "state_class": "total_increasing",  # Resets daily
            }
            disc_topic = self._disc_topic("sensor", object_id)
            try:
                self.mqtt.pub(disc_topic, cfg, retain=True)
                log.debug(f"Published array daily energy sensor discovery: {disc_topic}")
            except Exception as e:
                log.error(f"Failed to publish array daily energy sensor discovery to {disc_topic}: {e}", exc_info=True)
        
        log.info(f"Published HA discovery for inverter array {array_id} with {len(power_sensors) + len(cumulative_energy_sensors) + len(daily_energy_sensors)} sensors")
    
    def publish_pack_entities(self, pack_id: str, pack_name: Optional[str] = None, array_id: Optional[str] = None, battery_array_id: Optional[str] = None, system_id: Optional[str] = None) -> None:
        """
        Publish Home Assistant discovery entities for a battery pack.
        
        Args:
            pack_id: Battery pack ID
            pack_name: Optional pack name
            array_id: Optional attached inverter array ID (legacy)
            battery_array_id: Optional battery array ID (for via_device relationships)
            system_id: Optional system ID (for via_device relationships)
        """
        device_id = f"pack_{_sanitize_key(pack_id)}"
        device_name = pack_name or pack_id.replace("_", " ").title()
        state_topic = self._pack_state_topic(pack_id)
        
        device_info = {
            "identifiers": [f"pack:{pack_id}"],
            "name": device_name,
            "model": "Battery Pack",
            "manufacturer": "SolarHub",
        }
        
        # Add via_device relationship - prefer battery_array, then system, then inverter array
        # Note: via_device should be a single string, not a list (HA MQTT discovery spec)
        if battery_array_id:
            device_info["via_device"] = f"battery_array:{battery_array_id}"
        elif system_id:
            device_info["via_device"] = f"system:{system_id}"
        elif array_id:
            device_info["via_device"] = f"array:{array_id}"
        
        # Pack sensors
        sensors = [
            ("soc_pct", "SOC", "%", "battery"),
            ("voltage_v", "Voltage", "V", "voltage"),
            ("current_a", "Current", "A", "current"),
            ("power_w", "Power", "W", "power"),
            ("temperature_c", "Temperature", "°C", "temperature"),
        ]
        
        for field_key, name, unit, device_class in sensors:
            object_id = f"{device_id}_{field_key}"
            cfg = {
                "name": f"{device_name} {name}",
                "unique_id": object_id,
                "state_topic": state_topic,
                "value_template": f"{{{{ value_json.{field_key} }}}}",
                "device": device_info,
                "unit_of_measurement": unit,
                "device_class": device_class,
                "state_class": "measurement",
            }
            disc_topic = self._disc_topic("sensor", object_id)
            try:
                self.mqtt.pub(disc_topic, cfg, retain=True)
                log.debug(f"Published pack sensor discovery: {disc_topic}")
            except Exception as e:
                log.error(f"Failed to publish pack sensor discovery to {disc_topic}: {e}", exc_info=True)
        
        log.info(f"Published HA discovery for battery pack {pack_id}")
    
    def _battery_bank_state_topic(self, bank_id: str) -> str:
        """Get MQTT topic for battery bank state."""
        return f"{self.base_topic}/battery/{bank_id}/regs"
    
    def publish_battery_bank_entities(self, bank_id: str, bank_name: Optional[str] = None, pack_ids: Optional[List[str]] = None, bank_cfg: Optional[Any] = None) -> None:
        """
        Publish Home Assistant discovery entities for a battery bank (accumulated data from all packs).
        
        Args:
            bank_id: Battery bank ID
            bank_name: Optional bank name
            pack_ids: List of battery pack IDs in this bank
            bank_cfg: Optional battery bank config object (for manufacturer/model info)
        """
        device_id = f"battery_bank_{_sanitize_key(bank_id)}"
        device_name = bank_name or f"{bank_id.replace('_', ' ').title()} Battery Bank"
        # State topic matches what's published in _poll_battery: {base_topic}/battery/{bank_id}/regs
        state_topic = self._battery_bank_state_topic(bank_id)
        
        log.info(f"Publishing battery bank discovery: device_id={device_id}, device_name={device_name}, state_topic={state_topic}, bank_id={bank_id}")
        
        # Get manufacturer and model from config if available
        manufacturer = "SolarHub"
        model = "Battery Bank"
        if bank_cfg:
            if hasattr(bank_cfg, 'adapter'):
                adapter = bank_cfg.adapter
                if hasattr(adapter, 'manufacturer') and adapter.manufacturer:
                    manufacturer = adapter.manufacturer
                if hasattr(adapter, 'model') and adapter.model:
                    model = adapter.model
        
        device_info = {
            "identifiers": [f"battery_bank:{bank_id}"],
            "name": device_name,
            "model": model,
            "manufacturer": manufacturer,
        }
        
        # Don't add via_device for battery bank - it's a top-level device
        # Battery bank is independent, packs are separate entities
        
        # Battery bank sensors (accumulated data)
        sensors = [
            ("soc", "SOC", "%", "battery"),
            ("voltage", "Voltage", "V", "voltage"),
            ("current", "Current", "A", "current"),
            ("power", "Power", "W", "power"),  # Calculated: voltage * current
            ("temperature", "Temperature", "°C", "temperature"),
            ("batteries_count", "Battery Count", None, None),
            ("cells_per_battery", "Cells per Battery", None, None),
        ]
        
        for field_key, name, unit, device_class in sensors:
            object_id = f"{device_id}_{field_key}"
            cfg = {
                "name": f"{device_name} {name}",
                "unique_id": object_id,
                "state_topic": state_topic,
                "value_template": f"{{{{ value_json.{field_key} }}}}",
                "device": device_info,
            }
            
            if unit:
                cfg["unit_of_measurement"] = unit
            if device_class:
                cfg["device_class"] = device_class
            if device_class in ("battery", "voltage", "current", "temperature", "power"):
                cfg["state_class"] = "measurement"
            
            disc_topic = self._disc_topic("sensor", object_id)
            try:
                self.mqtt.pub(disc_topic, cfg, retain=True)
                log.info(f"Published battery bank sensor discovery: {disc_topic}, object_id={object_id}, state_topic={state_topic}, field={field_key}")
            except Exception as e:
                log.error(f"Failed to publish battery bank sensor discovery to {disc_topic}: {e}", exc_info=True)
        
        log.info(f"Published HA discovery for battery bank {bank_id} with {len(sensors)} sensors, state_topic={state_topic}")
    
    def _get_battery_unit_device_info(self, bank_id: str, unit_power: int, bank_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get device info for a battery unit. This ensures consistent device_info across unit and cell entities.
        
        Args:
            bank_id: Battery bank ID
            unit_power: Battery unit power/ID (from BatteryUnit.power)
            bank_name: Optional bank name
            
        Returns:
            Device info dictionary for Home Assistant discovery
        """
        device_name = f"{bank_name or bank_id.replace('_', ' ').title()} Battery {unit_power}"
        return {
            "identifiers": [f"battery_unit:{bank_id}:{unit_power}"],
            "name": device_name,
            "model": "Battery Unit",
            "manufacturer": "SolarHub",
            "via_device": f"battery_bank:{bank_id}",
        }
    
    def publish_battery_unit_entities(self, bank_id: str, unit_power: int, bank_name: Optional[str] = None, pack_id: Optional[str] = None) -> None:
        """
        Publish Home Assistant discovery entities for an individual battery unit according to Telemetry & Hierarchy Specification.
        
        Publishes:
        - Real-time battery power & basic telemetry (battery_power, pack_voltage, pack_current, state_of_charge, temperature)
        - Cumulative energy telemetry (total_battery_discharge, total_battery_charge)
        - Daily energy telemetry (today_battery_discharge, today_battery_charge)
        
        Args:
            bank_id: Battery bank ID
            unit_power: Battery unit power/ID (from BatteryUnit.power)
            bank_name: Optional bank name
            pack_id: Optional pack ID (for via_device relationships)
        """
        device_id = f"battery_{_sanitize_key(bank_id)}_unit_{unit_power}"
        device_name = f"{bank_name or bank_id.replace('_', ' ').title()} Battery {unit_power}"
        # State topic matches what's published: {base_topic}/battery/{bank_id}/{unit_power}/regs
        state_topic = f"{self.base_topic}/battery/{bank_id}/{unit_power}/regs"
        
        # Use helper method to ensure device_info is consistent with cell entities
        device_info = self._get_battery_unit_device_info(bank_id, unit_power, bank_name)
        
        # Update via_device to use pack_id if available
        if pack_id:
            device_info["via_device"] = f"pack:{pack_id}"
        # Otherwise keep existing via_device from _get_battery_unit_device_info (battery_bank)
        
        # Real-time battery power & basic telemetry sensors
        power_sensors = [
            ("battery_power", "Battery Power", "W", "power"),  # or "power" field
            ("pack_voltage", "Pack Voltage", "V", "voltage"),  # or "voltage" field
            ("pack_current", "Pack Current", "A", "current"),  # or "current" field
            ("state_of_charge", "State of Charge", "%", "battery"),  # or "soc" field
            ("temperature", "Temperature", "°C", "temperature"),
        ]
        
        for field_key, name, unit, device_class in power_sensors:
            # Map standardized names to actual field names in telemetry
            # Try standardized name first, then fallback to common variations
            actual_field = field_key
            if field_key == "pack_voltage":
                actual_field = "voltage"  # Fallback
            elif field_key == "pack_current":
                actual_field = "current"  # Fallback
            elif field_key == "state_of_charge":
                actual_field = "soc"  # Fallback
            
            object_id = f"{device_id}_{field_key}"
            cfg = {
                "name": f"{device_name} {name}",
                "unique_id": object_id,
                "state_topic": state_topic,
                # Try standardized field first, then fallback
                "value_template": f"{{{{ value_json.{actual_field} | default(value_json.{field_key}, 0) }}}}",
                "device": device_info,
                "unit_of_measurement": unit,
                "device_class": device_class,
                "state_class": "measurement",
            }
            disc_topic = self._disc_topic("sensor", object_id)
            try:
                self.mqtt.pub(disc_topic, cfg, retain=True)
                log.debug(f"Published battery unit power sensor discovery: {disc_topic}")
            except Exception as e:
                log.error(f"Failed to publish battery unit power sensor discovery to {disc_topic}: {e}", exc_info=True)
        
        # Cumulative energy sensors (kWh) - total_increasing state_class
        # Note: Battery unit energy would need to be calculated from battery_unit_samples
        # For now, we'll add the sensors but they may not have data until we implement unit-level energy aggregation
        cumulative_energy_sensors = [
            ("total_battery_discharge", "Total Battery Discharge", "kWh", "energy"),
            ("total_battery_charge", "Total Battery Charge", "kWh", "energy"),
        ]
        
        for field_key, name, unit, device_class in cumulative_energy_sensors:
            object_id = f"{device_id}_{field_key}"
            cfg = {
                "name": f"{device_name} {name}",
                "unique_id": object_id,
                "state_topic": state_topic,
                "value_template": f"{{{{ value_json.{field_key} | default(0) }}}}",
                "device": device_info,
                "unit_of_measurement": unit,
                "device_class": device_class,
                "state_class": "total_increasing",
            }
            disc_topic = self._disc_topic("sensor", object_id)
            try:
                self.mqtt.pub(disc_topic, cfg, retain=True)
                log.debug(f"Published battery unit cumulative energy sensor discovery: {disc_topic}")
            except Exception as e:
                log.error(f"Failed to publish battery unit cumulative energy sensor discovery to {disc_topic}: {e}", exc_info=True)
        
        # Daily energy sensors (kWh) - total_increasing state_class (resets daily)
        daily_energy_sensors = [
            ("today_battery_discharge", "Today Battery Discharge", "kWh", "energy"),
            ("today_battery_charge", "Today Battery Charge", "kWh", "energy"),
        ]
        
        for field_key, name, unit, device_class in daily_energy_sensors:
            object_id = f"{device_id}_{field_key}"
            cfg = {
                "name": f"{device_name} {name}",
                "unique_id": object_id,
                "state_topic": state_topic,
                "value_template": f"{{{{ value_json.{field_key} | default(0) }}}}",
                "device": device_info,
                "unit_of_measurement": unit,
                "device_class": device_class,
                "state_class": "total_increasing",  # Resets daily
            }
            disc_topic = self._disc_topic("sensor", object_id)
            try:
                self.mqtt.pub(disc_topic, cfg, retain=True)
                log.debug(f"Published battery unit daily energy sensor discovery: {disc_topic}")
            except Exception as e:
                log.error(f"Failed to publish battery unit daily energy sensor discovery to {disc_topic}: {e}", exc_info=True)
        
        # Additional status sensors (keep existing)
        status_sensors = [
            ("basic_st", "Basic Status", None, None),
            ("volt_st", "Voltage Status", None, None),
            ("current_st", "Current Status", None, None),
            ("temp_st", "Temperature Status", None, None),
        ]
        
        for field_key, name, unit, device_class in status_sensors:
            object_id = f"{device_id}_{field_key}"
            cfg = {
                "name": f"{device_name} {name}",
                "unique_id": object_id,
                "state_topic": state_topic,
                "value_template": f"{{{{ value_json.{field_key} }}}}",
                "device": device_info,
            }
            if unit:
                cfg["unit_of_measurement"] = unit
            if device_class:
                cfg["device_class"] = device_class
            disc_topic = self._disc_topic("sensor", object_id)
            try:
                self.mqtt.pub(disc_topic, cfg, retain=True)
                log.debug(f"Published battery unit status sensor discovery: {disc_topic}")
            except Exception as e:
                log.error(f"Failed to publish battery unit status sensor discovery to {disc_topic}: {e}", exc_info=True)
        
        log.info(f"Published HA discovery for battery unit {unit_power} in bank {bank_id} with {len(power_sensors) + len(cumulative_energy_sensors) + len(daily_energy_sensors) + len(status_sensors)} sensors")
    
    def publish_battery_cell_entities(self, bank_id: str, unit_power: int, cell_index: int, bank_name: Optional[str] = None) -> None:
        """
        Publish Home Assistant discovery entities for battery cell sensors directly under the battery unit device.
        This creates cell sensors as entities under the battery unit device rather than separate devices.
        
        Args:
            bank_id: Battery bank ID
            unit_power: Battery unit power/ID (from BatteryUnit.power)
            cell_index: Cell index (1-based)
            bank_name: Optional bank name
        """
        # Use EXACTLY the same device info as the battery unit to ensure cells appear under the same device
        # Use helper method to guarantee identical device_info structure
        unit_device_id = f"battery_{_sanitize_key(bank_id)}_unit_{unit_power}"
        unit_device_name = f"{bank_name or bank_id.replace('_', ' ').title()} Battery {unit_power}"
        
        # State topic matches what's published: {base_topic}/battery/{bank_id}/{unit_power}/cells/{cell_index}/regs
        state_topic = f"{self.base_topic}/battery/{bank_id}/{unit_power}/cells/{cell_index}/regs"
        
        # Use helper method to ensure device_info is EXACTLY the same as battery unit device
        # This guarantees all cell sensors appear under the same battery unit device in Home Assistant
        device_info = self._get_battery_unit_device_info(bank_id, unit_power, bank_name)
        
        # Cell sensors - primarily voltage, but also include other available fields
        # These will appear as sensors under the battery unit device
        sensors = [
            ("voltage", f"Cell {cell_index} Voltage", "V", "voltage"),
            ("current", f"Cell {cell_index} Current", "A", "current"),
            ("power", f"Cell {cell_index} Power", "W", "power"),  # Calculated: voltage * current
            ("temperature", f"Cell {cell_index} Temperature", "°C", "temperature"),
            ("soc", f"Cell {cell_index} SOC", "%", "battery"),
            ("coulomb", f"Cell {cell_index} Coulomb", "Ah", None),
        ]
        
        for field_key, name, unit, device_class in sensors:
            # Use unit device ID with cell index to make unique
            object_id = f"{unit_device_id}_cell_{cell_index}_{field_key}"
            cfg = {
                "name": f"{unit_device_name} {name}",
                "unique_id": object_id,
                "state_topic": state_topic,
                "value_template": f"{{{{ value_json.{field_key} }}}}",
                "device": device_info,
            }
            
            if unit:
                cfg["unit_of_measurement"] = unit
            if device_class:
                cfg["device_class"] = device_class
            if device_class in ("battery", "voltage", "current", "temperature", "power"):
                cfg["state_class"] = "measurement"
            
            disc_topic = self._disc_topic("sensor", object_id)
            try:
                self.mqtt.pub(disc_topic, cfg, retain=True)
                log.debug(f"Published battery cell sensor discovery: {disc_topic} (under battery unit {unit_power})")
            except Exception as e:
                log.error(f"Failed to publish battery cell sensor discovery to {disc_topic}: {e}", exc_info=True)
        
        log.debug(f"Published HA discovery for cell {cell_index} sensors under battery unit {unit_power} in bank {bank_id}")
    
    def _meter_state_topic(self, meter_id: str) -> str:
        """Get MQTT topic for meter state."""
        return f"{self.base_topic}/meter/{meter_id}/regs"
    
    def publish_meter_entities(self, meter_id: str, meter_name: Optional[str] = None, meter_cfg: Optional[Any] = None) -> None:
        """
        Publish Home Assistant discovery entities for an energy meter (IAMMeter, etc.).
        
        Args:
            meter_id: Meter ID
            meter_name: Optional meter name
            meter_cfg: Optional meter config object (for manufacturer/model info)
        """
        device_id = f"meter_{_sanitize_key(meter_id)}"
        device_name = meter_name or f"{meter_id.replace('_', ' ').title()} Meter"
        state_topic = self._meter_state_topic(meter_id)
        
        # Get manufacturer and model from config if available
        manufacturer = "IAMMeter"
        model = "Energy Meter"
        if meter_cfg:
            if hasattr(meter_cfg, 'adapter'):
                adapter = meter_cfg.adapter
                if hasattr(adapter, 'manufacturer') and adapter.manufacturer:
                    manufacturer = adapter.manufacturer
                if hasattr(adapter, 'model') and adapter.model:
                    model = adapter.model
        
        device_info = {
            "identifiers": [f"meter:{meter_id}"],
            "name": device_name,
            "model": model,
            "manufacturer": manufacturer,
        }
        
        # Add via_device relationship if system_id is available from meter_cfg
        # Meters can be system-level (array_id=None) or array-level
        if meter_cfg:
            # Try to get system_id from meter_cfg
            if hasattr(meter_cfg, 'system_id') and meter_cfg.system_id:
                device_info["via_device"] = f"system:{meter_cfg.system_id}"
            elif hasattr(meter_cfg, 'array_id') and meter_cfg.array_id:
                # Array-level meter
                device_info["via_device"] = f"array:{meter_cfg.array_id}"
        
        # Main meter sensors
        sensors = [
            ("grid_power_w", "Grid Power", "W", "power"),
            ("grid_voltage_v", "Grid Voltage", "V", "voltage"),
            ("grid_current_a", "Grid Current", "A", "current"),
            ("grid_frequency_hz", "Grid Frequency", "Hz", "frequency"),
            ("power_factor", "Power Factor", None, None),
            ("energy_kwh", "Total Energy", "kWh", "energy"),
            ("grid_import_wh", "Daily Import", "Wh", "energy"),
            ("grid_export_wh", "Daily Export", "Wh", "energy"),
        ]
        
        for field_key, name, unit, device_class in sensors:
            object_id = f"{device_id}_{field_key}"
            cfg = {
                "name": f"{device_name} {name}",
                "unique_id": object_id,
                "state_topic": state_topic,
                "value_template": f"{{{{ value_json.{field_key} }}}}",
                "device": device_info,
            }
            
            if unit:
                cfg["unit_of_measurement"] = unit
            if device_class:
                cfg["device_class"] = device_class
            if device_class in ("power", "voltage", "current", "frequency", "energy"):
                cfg["state_class"] = "measurement"
            # Energy sensors should use total_increasing for cumulative values
            if device_class == "energy" and field_key in ("energy_kwh",):
                cfg["state_class"] = "total_increasing"
            
            disc_topic = self._disc_topic("sensor", object_id)
            try:
                self.mqtt.pub(disc_topic, cfg, retain=True)
                log.debug(f"Published meter sensor discovery: {disc_topic}")
            except Exception as e:
                log.error(f"Failed to publish meter sensor discovery to {disc_topic}: {e}", exc_info=True)
        
        # Phase-specific sensors (for three-phase meters)
        phase_sensors = [
            ("voltage_phase_a", "Phase A Voltage", "V", "voltage"),
            ("voltage_phase_b", "Phase B Voltage", "V", "voltage"),
            ("voltage_phase_c", "Phase C Voltage", "V", "voltage"),
            ("current_phase_a", "Phase A Current", "A", "current"),
            ("current_phase_b", "Phase B Current", "A", "current"),
            ("current_phase_c", "Phase C Current", "A", "current"),
            ("power_phase_a", "Phase A Power", "W", "power"),
            ("power_phase_b", "Phase B Power", "W", "power"),
            ("power_phase_c", "Phase C Power", "W", "power"),
        ]
        
        for field_key, name, unit, device_class in phase_sensors:
            object_id = f"{device_id}_{field_key}"
            cfg = {
                "name": f"{device_name} {name}",
                "unique_id": object_id,
                "state_topic": state_topic,
                "value_template": f"{{{{ value_json.{field_key} }}}}",
                "device": device_info,
            }
            
            if unit:
                cfg["unit_of_measurement"] = unit
            if device_class:
                cfg["device_class"] = device_class
            if device_class in ("power", "voltage", "current"):
                cfg["state_class"] = "measurement"
            
            disc_topic = self._disc_topic("sensor", object_id)
            try:
                self.mqtt.pub(disc_topic, cfg, retain=True)
                log.debug(f"Published meter phase sensor discovery: {disc_topic}")
            except Exception as e:
                log.error(f"Failed to publish meter phase sensor discovery to {disc_topic}: {e}", exc_info=True)
    
    def _home_state_topic(self, home_id: str = "home") -> str:
        """Get MQTT topic for home state."""
        return f"{self.base_topic}/home/{home_id}/state"
    
    def _system_state_topic(self, system_id: str) -> str:
        """Get MQTT topic for system state."""
        return f"{self.base_topic}/systems/{system_id}/state"
    
    def _battery_array_state_topic(self, battery_array_id: str) -> str:
        """Get MQTT topic for battery array state."""
        return f"{self.base_topic}/battery_arrays/{battery_array_id}/state"
    
    def _get_system_energy_totals(self, system_id: str) -> Dict[str, float]:
        """
        Get cumulative and daily energy totals for a system from system_hourly_energy table.
        
        Returns:
            Dictionary with cumulative and daily energy values in kWh
        """
        if not self.db_path:
            return {}
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get cumulative totals (sum of all hourly energy)
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(solar_energy_kwh), 0) as total_solar,
                    COALESCE(SUM(load_energy_kwh), 0) as total_load,
                    COALESCE(SUM(grid_import_energy_kwh), 0) as total_grid_import,
                    COALESCE(SUM(grid_export_energy_kwh), 0) as total_grid_export,
                    COALESCE(SUM(battery_charge_energy_kwh), 0) as total_battery_charge,
                    COALESCE(SUM(battery_discharge_energy_kwh), 0) as total_battery_discharge
                FROM system_hourly_energy
                WHERE system_id = ?
            """, (system_id,))
            
            row = cursor.fetchone()
            cumulative = {
                "total_solar_energy": row[0] if row else 0.0,
                "total_load_energy": row[1] if row else 0.0,
                "total_grid_import": row[2] if row else 0.0,
                "total_grid_export": row[3] if row else 0.0,
                "total_battery_charge": row[4] if row else 0.0,
                "total_battery_discharge": row[5] if row else 0.0,
            }
            
            # Get today's totals (sum of today's hourly energy)
            today = now_configured().date()
            today_str = today.strftime('%Y-%m-%d')
            
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(solar_energy_kwh), 0) as today_solar,
                    COALESCE(SUM(load_energy_kwh), 0) as today_load,
                    COALESCE(SUM(grid_import_energy_kwh), 0) as today_grid_import,
                    COALESCE(SUM(grid_export_energy_kwh), 0) as today_grid_export,
                    COALESCE(SUM(battery_charge_energy_kwh), 0) as today_battery_charge,
                    COALESCE(SUM(battery_discharge_energy_kwh), 0) as today_battery_discharge
                FROM system_hourly_energy
                WHERE system_id = ? AND date = ?
            """, (system_id, today_str))
            
            row = cursor.fetchone()
            daily = {
                "today_solar_energy": row[0] if row else 0.0,
                "today_load_energy": row[1] if row else 0.0,
                "today_grid_import": row[2] if row else 0.0,
                "today_grid_export": row[3] if row else 0.0,
                "today_battery_charge": row[4] if row else 0.0,
                "today_battery_discharge": row[5] if row else 0.0,
            }
            
            conn.close()
            return {**cumulative, **daily}
            
        except Exception as e:
            log.error(f"Failed to get system energy totals for {system_id}: {e}", exc_info=True)
            return {}
    
    def publish_system_entities(self, system_id: str, system_name: Optional[str] = None, array_ids: Optional[List[str]] = None, meter_ids: Optional[List[str]] = None) -> None:
        """
        Publish Home Assistant discovery entities for system according to Telemetry & Hierarchy Specification.
        
        Publishes:
        - Real-time power telemetry (load_power, solar_power, grid_power, battery_power)
        - Cumulative energy telemetry (total_*)
        - Daily energy telemetry (today_*)
        
        Args:
            system_id: System ID
            system_name: Optional system name
            array_ids: List of array IDs in this system (for via_device relationships)
            meter_ids: List of meter IDs in this system (for via_device relationships)
        """
        device_id = f"system_{_sanitize_key(system_id)}"
        device_name = system_name or "Solar System"
        state_topic = self._system_state_topic(system_id)
        
        device_info = {
            "identifiers": [f"system:{system_id}"],
            "name": device_name,
            "model": "Solar System",
            "manufacturer": "SolarHub",
            # System is top-level device, no via_device
        }
        
        # Real-time power sensors (W)
        power_sensors = [
            ("load_power", "Load Power", "W", "power"),
            ("solar_power", "Solar Power", "W", "power"),
            ("grid_power", "Grid Power", "W", "power"),  # positive = import, negative = export
            ("battery_power", "Battery Power", "W", "power"),  # positive = discharge, negative = charge
        ]
        
        for field_key, name, unit, device_class in power_sensors:
            object_id = f"{device_id}_{field_key}"
            cfg = {
                "name": f"{device_name} {name}",
                "unique_id": object_id,
                "state_topic": state_topic,
                "value_template": f"{{{{ value_json.{field_key} }}}}",
                "device": device_info,
                "unit_of_measurement": unit,
                "device_class": device_class,
                "state_class": "measurement",
            }
            disc_topic = self._disc_topic("sensor", object_id)
            try:
                self.mqtt.pub(disc_topic, cfg, retain=True)
                log.debug(f"Published system power sensor discovery: {disc_topic}")
            except Exception as e:
                log.error(f"Failed to publish system power sensor discovery to {disc_topic}: {e}", exc_info=True)
        
        # Cumulative energy sensors (kWh) - total_increasing state_class
        cumulative_energy_sensors = [
            ("total_load_energy", "Total Load Energy", "kWh", "energy"),
            ("total_grid_import", "Total Grid Import", "kWh", "energy"),
            ("total_grid_export", "Total Grid Export", "kWh", "energy"),
            ("total_solar_energy", "Total Solar Energy", "kWh", "energy"),
            ("total_battery_discharge", "Total Battery Discharge", "kWh", "energy"),
            ("total_battery_charge", "Total Battery Charge", "kWh", "energy"),
        ]
        
        for field_key, name, unit, device_class in cumulative_energy_sensors:
            object_id = f"{device_id}_{field_key}"
            cfg = {
                "name": f"{device_name} {name}",
                "unique_id": object_id,
                "state_topic": state_topic,
                "value_template": f"{{{{ value_json.{field_key} }}}}",
                "device": device_info,
                "unit_of_measurement": unit,
                "device_class": device_class,
                "state_class": "total_increasing",
            }
            disc_topic = self._disc_topic("sensor", object_id)
            try:
                self.mqtt.pub(disc_topic, cfg, retain=True)
                log.debug(f"Published system cumulative energy sensor discovery: {disc_topic}")
            except Exception as e:
                log.error(f"Failed to publish system cumulative energy sensor discovery to {disc_topic}: {e}", exc_info=True)
        
        # Daily energy sensors (kWh) - total_increasing state_class (resets daily)
        daily_energy_sensors = [
            ("today_load_energy", "Today Load Energy", "kWh", "energy"),
            ("today_grid_import", "Today Grid Import", "kWh", "energy"),
            ("today_grid_export", "Today Grid Export", "kWh", "energy"),
            ("today_solar_energy", "Today Solar Energy", "kWh", "energy"),
            ("today_battery_discharge", "Today Battery Discharge", "kWh", "energy"),
            ("today_battery_charge", "Today Battery Charge", "kWh", "energy"),
        ]
        
        for field_key, name, unit, device_class in daily_energy_sensors:
            object_id = f"{device_id}_{field_key}"
            cfg = {
                "name": f"{device_name} {name}",
                "unique_id": object_id,
                "state_topic": state_topic,
                "value_template": f"{{{{ value_json.{field_key} }}}}",
                "device": device_info,
                "unit_of_measurement": unit,
                "device_class": device_class,
                "state_class": "total_increasing",  # Resets daily
            }
            disc_topic = self._disc_topic("sensor", object_id)
            try:
                self.mqtt.pub(disc_topic, cfg, retain=True)
                log.debug(f"Published system daily energy sensor discovery: {disc_topic}")
            except Exception as e:
                log.error(f"Failed to publish system daily energy sensor discovery to {disc_topic}: {e}", exc_info=True)
        
        log.info(f"Published HA discovery for system {system_id} with {len(power_sensors) + len(cumulative_energy_sensors) + len(daily_energy_sensors)} sensors")
    
    def _get_battery_array_energy_totals(self, battery_array_id: str, pack_ids: List[str]) -> Dict[str, float]:
        """
        Get cumulative and daily energy totals for a battery array from battery_bank_hourly table.
        
        Args:
            battery_array_id: Battery array ID
            pack_ids: List of pack IDs in this array
            
        Returns:
            Dictionary with cumulative and daily energy values in kWh
        """
        if not self.db_path or not pack_ids:
            return {}
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create placeholders for pack_ids
            placeholders = ','.join(['?'] * len(pack_ids))
            
            # Get cumulative totals (sum of all hourly energy for all packs in array)
            cursor.execute(f"""
                SELECT 
                    COALESCE(SUM(charge_energy_kwh), 0) as total_charge,
                    COALESCE(SUM(discharge_energy_kwh), 0) as total_discharge
                FROM battery_bank_hourly
                WHERE pack_id IN ({placeholders})
            """, pack_ids)
            
            row = cursor.fetchone()
            cumulative = {
                "total_battery_charge": row[0] if row else 0.0,
                "total_battery_discharge": row[1] if row else 0.0,
            }
            
            # Get today's totals (sum of today's hourly energy)
            today = now_configured().date()
            today_str = today.strftime('%Y-%m-%d')
            
            cursor.execute(f"""
                SELECT 
                    COALESCE(SUM(charge_energy_kwh), 0) as today_charge,
                    COALESCE(SUM(discharge_energy_kwh), 0) as today_discharge
                FROM battery_bank_hourly
                WHERE pack_id IN ({placeholders}) AND date = ?
            """, pack_ids + [today_str])
            
            row = cursor.fetchone()
            daily = {
                "today_battery_charge": row[0] if row else 0.0,
                "today_battery_discharge": row[1] if row else 0.0,
            }
            
            conn.close()
            return {**cumulative, **daily}
            
        except Exception as e:
            log.error(f"Failed to get battery array energy totals for {battery_array_id}: {e}", exc_info=True)
            return {}
    
    def publish_battery_array_entities(self, battery_array_id: str, battery_array_name: Optional[str] = None, pack_ids: Optional[List[str]] = None, system_id: Optional[str] = None) -> None:
        """
        Publish Home Assistant discovery entities for a battery array according to Telemetry & Hierarchy Specification.
        
        Publishes:
        - Real-time battery power (battery_power)
        - Cumulative energy telemetry (total_battery_discharge, total_battery_charge)
        - Daily energy telemetry (today_battery_discharge, today_battery_charge)
        - Additional sensors (SOC, voltage, current, temperature)
        
        Args:
            battery_array_id: Battery array ID
            battery_array_name: Optional battery array name
            pack_ids: List of battery pack IDs in this array
            system_id: Optional system ID (for via_device relationships)
        """
        device_id = f"battery_array_{_sanitize_key(battery_array_id)}"
        device_name = battery_array_name or battery_array_id.replace("_", " ").title()
        state_topic = self._battery_array_state_topic(battery_array_id)
        
        device_info = {
            "identifiers": [f"battery_array:{battery_array_id}"],
            "name": device_name,
            "model": "Battery Array",
            "manufacturer": "SolarHub",
        }
        
        # Add via_device relationship - prefer system
        if system_id:
            device_info["via_device"] = f"system:{system_id}"
        elif pack_ids:
            # Fallback to first pack if no system
            device_info["via_device"] = f"pack:{pack_ids[0]}"
        
        # Real-time battery power sensor (W)
        power_sensors = [
            ("battery_power", "Battery Power", "W", "power"),  # positive = discharge, negative = charge
        ]
        
        for field_key, name, unit, device_class in power_sensors:
            object_id = f"{device_id}_{field_key}"
            cfg = {
                "name": f"{device_name} {name}",
                "unique_id": object_id,
                "state_topic": state_topic,
                "value_template": f"{{{{ value_json.{field_key} }}}}",
                "device": device_info,
                "unit_of_measurement": unit,
                "device_class": device_class,
                "state_class": "measurement",
            }
            disc_topic = self._disc_topic("sensor", object_id)
            try:
                self.mqtt.pub(disc_topic, cfg, retain=True)
                log.debug(f"Published battery array power sensor discovery: {disc_topic}")
            except Exception as e:
                log.error(f"Failed to publish battery array power sensor discovery to {disc_topic}: {e}", exc_info=True)
        
        # Cumulative energy sensors (kWh) - total_increasing state_class
        cumulative_energy_sensors = [
            ("total_battery_discharge", "Total Battery Discharge", "kWh", "energy"),
            ("total_battery_charge", "Total Battery Charge", "kWh", "energy"),
        ]
        
        for field_key, name, unit, device_class in cumulative_energy_sensors:
            object_id = f"{device_id}_{field_key}"
            cfg = {
                "name": f"{device_name} {name}",
                "unique_id": object_id,
                "state_topic": state_topic,
                "value_template": f"{{{{ value_json.{field_key} }}}}",
                "device": device_info,
                "unit_of_measurement": unit,
                "device_class": device_class,
                "state_class": "total_increasing",
            }
            disc_topic = self._disc_topic("sensor", object_id)
            try:
                self.mqtt.pub(disc_topic, cfg, retain=True)
                log.debug(f"Published battery array cumulative energy sensor discovery: {disc_topic}")
            except Exception as e:
                log.error(f"Failed to publish battery array cumulative energy sensor discovery to {disc_topic}: {e}", exc_info=True)
        
        # Daily energy sensors (kWh) - total_increasing state_class (resets daily)
        daily_energy_sensors = [
            ("today_battery_discharge", "Today Battery Discharge", "kWh", "energy"),
            ("today_battery_charge", "Today Battery Charge", "kWh", "energy"),
        ]
        
        for field_key, name, unit, device_class in daily_energy_sensors:
            object_id = f"{device_id}_{field_key}"
            cfg = {
                "name": f"{device_name} {name}",
                "unique_id": object_id,
                "state_topic": state_topic,
                "value_template": f"{{{{ value_json.{field_key} }}}}",
                "device": device_info,
                "unit_of_measurement": unit,
                "device_class": device_class,
                "state_class": "total_increasing",  # Resets daily
            }
            disc_topic = self._disc_topic("sensor", object_id)
            try:
                self.mqtt.pub(disc_topic, cfg, retain=True)
                log.debug(f"Published battery array daily energy sensor discovery: {disc_topic}")
            except Exception as e:
                log.error(f"Failed to publish battery array daily energy sensor discovery to {disc_topic}: {e}", exc_info=True)
        
        # Additional battery array sensors (already exist, keep them)
        additional_sensors = [
            ("total_soc_pct", "Total SOC", "%", "battery"),
            ("total_voltage_v", "Total Voltage", "V", "voltage"),
            ("total_current_a", "Total Current", "A", "current"),
            ("avg_temperature_c", "Average Temperature", "°C", "temperature"),
        ]
        
        for field_key, name, unit, device_class in additional_sensors:
            object_id = f"{device_id}_{field_key}"
            cfg = {
                "name": f"{device_name} {name}",
                "unique_id": object_id,
                "state_topic": state_topic,
                "value_template": f"{{{{ value_json.{field_key} }}}}",
                "device": device_info,
                "unit_of_measurement": unit,
                "device_class": device_class,
                "state_class": "measurement",
            }
            disc_topic = self._disc_topic("sensor", object_id)
            try:
                self.mqtt.pub(disc_topic, cfg, retain=True)
                log.debug(f"Published battery array sensor discovery: {disc_topic}")
            except Exception as e:
                log.error(f"Failed to publish battery array sensor discovery to {disc_topic}: {e}", exc_info=True)
        
        log.info(f"Published HA discovery for battery array {battery_array_id} with {len(power_sensors) + len(cumulative_energy_sensors) + len(daily_energy_sensors) + len(additional_sensors)} sensors")
    
    def publish_home_entities(self, home_id: str = "home", home_name: Optional[str] = None, array_ids: Optional[List[str]] = None) -> None:
        """
        Publish Home Assistant discovery entities for home (accumulated power from all arrays).
        
        Args:
            home_id: Home ID (default: "home")
            home_name: Optional home name
            array_ids: List of array IDs in this home (for via_device relationships)
        """
        device_id = f"home_{_sanitize_key(home_id)}"
        device_name = home_name or "Solar Home"
        state_topic = self._home_state_topic(home_id)
        
        device_info = {
            "identifiers": [f"home:{home_id}"],
            "name": device_name,
            "model": "Solar Home",
            "manufacturer": "SolarHub",
        }
        
        # Add via_device relationships if arrays are provided
        # Note: via_device should be a single string, not a list (HA MQTT discovery spec)
        if array_ids:
            # Use the first array as the via_device (HA only supports one)
            device_info["via_device"] = f"array:{array_ids[0]}"
        
        # Home-level accumulated power sensors
        sensors = [
            ("total_pv_power_w", "Total Solar Power", "W", "power"),
            ("total_load_power_w", "Total Load Power", "W", "power"),
            ("total_grid_power_w", "Total Grid Power", "W", "power"),
            ("total_batt_power_w", "Total Battery Power", "W", "power"),
        ]
        
        for field_key, name, unit, device_class in sensors:
            object_id = f"{device_id}_{field_key}"
            cfg = {
                "name": f"{device_name} {name}",
                "unique_id": object_id,
                "state_topic": state_topic,
                "value_template": f"{{{{ value_json.{field_key} }}}}",
                "device": device_info,
                "unit_of_measurement": unit,
                "device_class": device_class,
                "state_class": "measurement",
            }
            disc_topic = self._disc_topic("sensor", object_id)
            try:
                self.mqtt.pub(disc_topic, cfg, retain=True)
                log.debug(f"Published home sensor discovery: {disc_topic}")
            except Exception as e:
                log.error(f"Failed to publish home sensor discovery to {disc_topic}: {e}", exc_info=True)
        
        # Battery SOC sensor
        object_id = f"{device_id}_avg_batt_soc_pct"
        cfg = {
            "name": f"{device_name} Average Battery SOC",
            "unique_id": object_id,
            "state_topic": state_topic,
            "value_template": "{{ value_json.avg_batt_soc_pct }}",
            "device": device_info,
            "unit_of_measurement": "%",
            "device_class": "battery",
            "state_class": "measurement",
        }
        disc_topic = self._disc_topic("sensor", object_id)
        try:
            self.mqtt.pub(disc_topic, cfg, retain=True)
            log.debug(f"Published home battery SOC discovery: {disc_topic}")
        except Exception as e:
            log.error(f"Failed to publish home battery SOC discovery to {disc_topic}: {e}", exc_info=True)
        
        log.info(f"Published HA discovery for home {home_id}")
    
    def clear_home_entities(self, home_id: str = "home") -> None:
        """
        Clear legacy home entities from MQTT discovery.
        This removes old home discovery messages so new system entities can be published cleanly.
        
        Args:
            home_id: Home ID to clear (default: "home")
        """
        device_id = f"home_{_sanitize_key(home_id)}"
        
        # Clear all home sensors
        sensors = [
            "total_pv_power_w",
            "total_load_power_w",
            "total_grid_power_w",
            "total_batt_power_w",
            "avg_batt_soc_pct",
        ]
        
        for field_key in sensors:
            object_id = f"{device_id}_{field_key}"
            self._clear_discovery_entity("sensor", object_id)
        
        log.info(f"Cleared legacy home discovery entities for {home_id}")