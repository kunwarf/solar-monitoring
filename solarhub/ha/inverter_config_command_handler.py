"""
Home Assistant command handler for inverter configuration updates.
Handles commands from Home Assistant to update inverter settings.
"""
import json
import logging
from typing import Dict, Any, Optional
from solarhub.adapters.senergy import SenergyAdapter

log = logging.getLogger(__name__)

class InverterConfigCommandHandler:
    """
    Handles Home Assistant commands for inverter configuration updates.
    """

    def __init__(self, adapter: SenergyAdapter, config_discovery=None, db_logger=None):
        self.adapter = adapter
        self.logger = logging.getLogger(__name__)
        self.config_discovery = config_discovery
        self.db_logger = db_logger
        log.info("InverterConfigCommandHandler initialized with adapter and database logger")

    async def handle_command(self, inverter_id: str, sensor_id: str, command: str) -> bool:
        """
        Handle command from Home Assistant.
        
        Args:
            inverter_id: ID of the inverter
            sensor_id: ID of the sensor/register
            command: Command value from Home Assistant
            
        Returns:
            bool: True if command was handled successfully
        """
        try:
            log.info(f"Handling command for {inverter_id}.{sensor_id}: {command}")
            
            # Parse command value
            value = self._parse_command_value(command)
            
            # Create command for adapter
            cmd = {
                "action": "write",
                "id": sensor_id,
                "value": value
            }
            
            # Execute command
            log.info(f"Updating inverter register {sensor_id} to {value}")
            result = await self.adapter.handle_command(cmd)
            log.info(f"Adapter command result: {result}")
            
            if result.get("ok", False):
                log.info(f"Successfully updated inverter register {sensor_id} to {value}")
                
                # Save to database for persistence
                log.info(f"Saving inverter config {sensor_id}={value} to database")
                self._save_to_database(inverter_id, sensor_id, value)
                
                # Republish updated sensor state to Home Assistant
                if self.config_discovery:
                    try:
                        log.debug(f"About to republish sensor state for {sensor_id}")
                        self.config_discovery.publish_sensor_state(inverter_id, sensor_id, value)
                        log.debug(f"Republished sensor state for {sensor_id} to Home Assistant")
                    except Exception as e:
                        log.warning(f"Failed to republish sensor state for {sensor_id}: {e}")
                log.debug(f"Command handler completed successfully for {sensor_id}")
                return True
            else:
                log.error(f"Failed to update {sensor_id}: {result.get('reason', 'Unknown error')}")
                return False
                
        except Exception as e:
            log.error(f"Error handling command for {sensor_id}: {e}")
            return False

    def _parse_command_value(self, command: Any) -> Any:
        """Parse command value from Home Assistant."""
        try:
            # If already parsed as number, return as-is
            if isinstance(command, (int, float)):
                return command
            
            # Convert to string for processing
            command_str = str(command)
            
            # Try to parse as JSON first
            if command_str.startswith('{') or command_str.startswith('['):
                return json.loads(command_str)
            
            # Try to parse as number
            if command_str.replace('.', '').replace('-', '').isdigit():
                if '.' in command_str:
                    return float(command_str)
                else:
                    return int(command_str)
            
            # Return as string
            return command_str
            
        except (ValueError, TypeError):
            # Return as string if parsing fails
            return str(command)

    async def get_current_value(self, inverter_id: str, sensor_id: str) -> Any:
        """
        Get current value of a sensor.
        
        Args:
            inverter_id: ID of the inverter
            sensor_id: ID of the sensor/register
            
        Returns:
            Current value of the sensor
        """
        try:
            # Read current value from adapter
            value = await self.adapter.read_by_ident(sensor_id)
            
            if value is not None:
                log.debug(f"Current value for {sensor_id}: {value}")
                return value
            else:
                log.warning(f"Could not read current value for {sensor_id}")
                return None
                
        except Exception as e:
            log.error(f"Error reading current value for {sensor_id}: {e}")
            return None

    def validate_value(self, sensor_id: str, value: Any, sensor_config: Dict[str, Any]) -> bool:
        """
        Validate value against sensor configuration.
        
        Args:
            sensor_id: ID of the sensor
            value: Value to validate
            sensor_config: Sensor configuration from register map
            
        Returns:
            bool: True if value is valid
        """
        try:
            # Check min/max constraints
            if "min" in sensor_config:
                if isinstance(value, (int, float)) and value < sensor_config["min"]:
                    log.warning(f"Value {value} below minimum {sensor_config['min']} for {sensor_id}")
                    return False
            
            if "max" in sensor_config:
                if isinstance(value, (int, float)) and value > sensor_config["max"]:
                    log.warning(f"Value {value} above maximum {sensor_config['max']} for {sensor_id}")
                    return False
            
            # Check enum constraints
            if "enum" in sensor_config:
                enum_values = list(sensor_config["enum"].values())
                if value not in enum_values:
                    log.warning(f"Value {value} not in allowed values {enum_values} for {sensor_id}")
                    return False
            
            return True
            
        except Exception as e:
            log.error(f"Error validating value for {sensor_id}: {e}")
            return False

    async def update_sensor_value(self, inverter_id: str, sensor_id: str, value: Any, sensor_config: Dict[str, Any]) -> bool:
        """
        Update sensor value with validation.
        
        Args:
            inverter_id: ID of the inverter
            sensor_id: ID of the sensor
            value: New value
            sensor_config: Sensor configuration
            
        Returns:
            bool: True if update was successful
        """
        try:
            # Validate value
            if not self.validate_value(sensor_id, value, sensor_config):
                return False
            
            # Handle enum values
            if "enum" in sensor_config:
                value = self._convert_enum_value(value, sensor_config["enum"])
            
            # Create command
            cmd = {
                "action": "write",
                "id": sensor_id,
                "value": value
            }
            
            # Execute command
            log.info(f"Updating inverter register {sensor_id} to {value}")
            result = await self.adapter.handle_command(cmd)
            log.info(f"Adapter command result: {result}")
            
            if result.get("ok", False):
                log.info(f"Successfully updated inverter register {sensor_id} to {value}")
                
                # Save to database for persistence
                log.info(f"Saving inverter config {sensor_id}={value} to database")
                self._save_to_database(inverter_id, sensor_id, value)
                
                # Republish updated sensor state to Home Assistant
                if self.config_discovery:
                    try:
                        log.debug(f"About to republish sensor state for {sensor_id}")
                        self.config_discovery.publish_sensor_state(inverter_id, sensor_id, value)
                        log.debug(f"Republished sensor state for {sensor_id} to Home Assistant")
                    except Exception as e:
                        log.warning(f"Failed to republish sensor state for {sensor_id}: {e}")
                log.debug(f"Command handler completed successfully for {sensor_id}")
                return True
            else:
                log.error(f"Failed to update {sensor_id}: {result.get('reason', 'Unknown error')}")
                return False
                
        except Exception as e:
            log.error(f"Error updating {sensor_id}: {e}")
            return False

    def _convert_enum_value(self, value: str, enum_config: Dict[str, str]) -> str:
        """Convert enum value to register value."""
        # Find the key for the given value
        for key, enum_value in enum_config.items():
            if enum_value == value:
                return key
        
        # If not found, return the value as-is
        return value

    async def handle_switch_command(self, inverter_id: str, sensor_id: str, command: str) -> bool:
        """
        Handle switch command (ON/OFF).
        
        Args:
            inverter_id: ID of the inverter
            sensor_id: ID of the sensor
            command: ON or OFF
            
        Returns:
            bool: True if command was handled successfully
        """
        try:
            # Convert ON/OFF to appropriate values
            if command.upper() == "ON":
                value = "Enable"
            elif command.upper() == "OFF":
                value = "Disable"
            else:
                log.warning(f"Invalid switch command: {command}")
                return False
            
            # Handle the command
            return await self.handle_command(inverter_id, sensor_id, value)
            
        except Exception as e:
            log.error(f"Error handling switch command for {sensor_id}: {e}")
            return False

    async def handle_select_command(self, inverter_id: str, sensor_id: str, command: str) -> bool:
        """
        Handle select command.
        
        Args:
            inverter_id: ID of the inverter
            sensor_id: ID of the sensor
            command: Selected option
            
        Returns:
            bool: True if command was handled successfully
        """
        try:
            # Handle the command
            return await self.handle_command(inverter_id, sensor_id, command)
            
        except Exception as e:
            log.error(f"Error handling select command for {sensor_id}: {e}")
            return False

    async def handle_number_command(self, inverter_id: str, sensor_id: str, command: str) -> bool:
        """
        Handle number command.
        
        Args:
            inverter_id: ID of the inverter
            sensor_id: ID of the sensor
            command: Numeric value
            
        Returns:
            bool: True if command was handled successfully
        """
        try:
            # Handle the command directly (command is already a string)
            return await self.handle_command(inverter_id, sensor_id, command)
            
        except Exception as e:
            log.error(f"Error handling number command for {sensor_id}: {e}")
            return False

    def _save_to_database(self, inverter_id: str, sensor_id: str, value: Any):
        """Save inverter configuration to database for persistence."""
        try:
            if not self.db_logger:
                log.warning("Database logger not available, cannot save inverter config")
                return
            
            # Convert value to string for database storage
            if isinstance(value, (dict, list)):
                value_str = json.dumps(value)
            else:
                value_str = str(value)
            
            # Create config path for inverter configuration
            config_path = f"inverter.{inverter_id}.{sensor_id}"
            
            # Save to database
            self.db_logger.set_config(config_path, value_str, "home_assistant")
            log.info(f"Saved inverter config {sensor_id} to database at {config_path}")
            
        except Exception as e:
            log.error(f"Error saving inverter config {sensor_id} to database: {e}")
