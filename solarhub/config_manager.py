"""
Configuration Manager for SolarHub

Handles loading configuration from database with fallback to config.yaml file.
Persists Home Assistant configuration changes to database.
"""

import yaml
import json
import logging
from typing import Any, Dict, Optional
from pathlib import Path
from solarhub.logging.logger import DataLogger
from solarhub.config import HubConfig
from solarhub.timezone_utils import initialize_timezones

log = logging.getLogger(__name__)

class ConfigurationManager:
    """Manages configuration loading from database and file with persistence."""
    
    def __init__(self, config_path: str = "config.yaml", db_logger: DataLogger = None):
        self.config_path = Path(config_path)
        self.db_logger = db_logger
        self._config_cache: Optional[HubConfig] = None
        
    def load_config(self) -> HubConfig:
        """Load configuration from database first, then fallback to config.yaml."""
        log.info("Loading configuration from database with fallback to config.yaml")
        
        # Try to load from database first
        if self.db_logger:
            db_config = self._load_from_database()
            if db_config:
                log.info("Configuration loaded from database")
                self._config_cache = db_config
                return db_config
        
        # Fallback to config.yaml
        log.info("No database configuration found, loading from config.yaml")
        file_config = self._load_from_file()
        self._config_cache = file_config
        
        # Save initial config to database for future use
        if self.db_logger:
            self._save_to_database(file_config)
            log.info("Initial configuration saved to database")
        
        # Initialize timezone utilities with the loaded configuration
        initialize_timezones(file_config.timezone)
        
        return file_config
    
    def _load_from_database(self) -> Optional[HubConfig]:
        """Load configuration from database."""
        try:
            db_configs = self.db_logger.get_all_configs()
            if not db_configs:
                return None
            
            # Convert database key-value pairs back to nested config structure
            config_dict = self._db_configs_to_dict(db_configs)
            
            # Ensure all inverters have array_id (set to None if missing for migration)
            if 'inverters' in config_dict and isinstance(config_dict['inverters'], list):
                for inv in config_dict['inverters']:
                    if isinstance(inv, dict) and 'array_id' not in inv:
                        inv['array_id'] = None
            
            # Handle optional list fields that might be stored as 'None' string
            # Convert 'None' strings to None, and None to empty lists for list fields
            list_fields = ['arrays', 'battery_packs', 'attachments', 'battery_bank_arrays', 'battery_bank_array_attachments', 'battery_banks', 'meters']
            for field in list_fields:
                if field in config_dict:
                    value = config_dict[field]
                    if value is None or (isinstance(value, str) and value.lower() in ('none', 'null', '')):
                        config_dict[field] = []
                    elif not isinstance(value, list):
                        # If it's not a list and not None/empty, try to parse it
                        try:
                            parsed = json.loads(value) if isinstance(value, str) else value
                            if isinstance(parsed, list):
                                config_dict[field] = parsed
                            else:
                                config_dict[field] = []
                        except:
                            config_dict[field] = []
                else:
                    # Field not in config, set to empty list as default
                    config_dict[field] = []
            
            # Handle billing config defaults if billing section exists
            if 'billing' in config_dict and isinstance(config_dict['billing'], dict):
                billing = config_dict['billing']
                # Set default for fixed_proration if missing or None
                if 'fixed_proration' not in billing or billing.get('fixed_proration') is None:
                    billing['fixed_proration'] = 'none'
                # Ensure forecast section exists with defaults
                if 'forecast' not in billing or not isinstance(billing.get('forecast'), dict):
                    billing['forecast'] = {
                        'default_method': 'trend',
                        'lookback_months': 12,
                        'default_months_ahead': 1,
                        'low_confidence_threshold': 0.5
                    }
                # Ensure peak_windows exists
                if 'peak_windows' not in billing or billing.get('peak_windows') is None:
                    billing['peak_windows'] = []
            
            # Create SolarHubConfig object
            config = HubConfig(**config_dict)
            
            # Initialize timezone utilities with the loaded configuration
            initialize_timezones(config.timezone)
            
            return config
            
        except Exception as e:
            log.error(f"Failed to load configuration from database: {e}")
            return None
    
    def _load_from_file(self) -> HubConfig:
        """Load configuration from config.yaml file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            config_dict = yaml.safe_load(f)
        
        # Ensure all inverters have array_id (set to None if missing for migration)
        # This is critical for backward compatibility with configs that don't have array_id
        if config_dict and 'inverters' in config_dict:
            inverters = config_dict['inverters']
            if isinstance(inverters, list):
                for i, inv in enumerate(inverters):
                    if isinstance(inv, dict):
                        if 'array_id' not in inv:
                            inv['array_id'] = None
                            log.debug(f"Added array_id=None to inverter {inv.get('id', i)}")
                    else:
                        log.warning(f"Inverter at index {i} is not a dict: {type(inv)}")
            else:
                log.warning(f"inverters is not a list: {type(inverters)}")
        
        return HubConfig(**config_dict)
    
    def _db_configs_to_dict(self, db_configs: Dict[str, str]) -> Dict[str, Any]:
        """Convert flat database configs to nested dictionary structure."""
        config_dict = {}
        
        for key, value in db_configs.items():
            # Parse nested keys like "smart.policy.max_charge_power_w"
            keys = key.split('.')
            current = config_dict
            
            # Navigate/create nested structure
            for k in keys[:-1]:
                if k not in current:
                    current[k] = {}
                current = current[k]
            
            # Set the final value with proper type conversion
            current[keys[-1]] = self._convert_value(value)
        
        return config_dict
    
    def _convert_value(self, value: str) -> Any:
        """Convert string value from database to appropriate Python type."""
        # Handle None/null values
        if value is None or value == '' or value.lower() in ('none', 'null'):
            return None
        
        # Try JSON parsing first (for complex types like lists, dicts)
        try:
            parsed = json.loads(value)
            # If JSON parsing returns the string 'None', convert to None
            if parsed == 'None':
                return None
            return parsed
        except (json.JSONDecodeError, TypeError):
            pass
        
        # Try boolean conversion
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # Try numeric conversion
        try:
            if '.' in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            pass
        
        # Return as string
        return value
    
    def _save_to_database(self, config: HubConfig):
        """Save configuration to database."""
        try:
            config_dict = config.model_dump()
            flat_configs = self._dict_to_flat_configs(config_dict)
            
            for key, value in flat_configs.items():
                # Convert value to string for database storage
                if isinstance(value, (dict, list)):
                    value_str = json.dumps(value)
                else:
                    value_str = str(value)
                
                self.db_logger.set_config(key, value_str, "config_file")
                
        except Exception as e:
            log.error(f"Failed to save configuration to database: {e}")
    
    def _dict_to_flat_configs(self, config_dict: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
        """Convert nested dictionary to flat key-value pairs.
        
        Handles:
        - Nested dictionaries (recursively flattened)
        - Lists (stored as JSON strings for complex objects, or as-is for simple types)
        - Simple values (stored as-is)
        """
        flat_configs = {}
        
        for key, value in config_dict.items():
            full_key = f"{prefix}.{key}" if prefix else key
            
            if isinstance(value, dict):
                # Recursively flatten nested dictionaries
                flat_configs.update(self._dict_to_flat_configs(value, full_key))
            elif isinstance(value, list):
                # For lists, store as JSON string (will be parsed back on load)
                # This handles complex objects like arrays, battery_bank_arrays, etc.
                flat_configs[full_key] = value  # Will be JSON encoded in _save_to_database
            else:
                # Simple values (strings, numbers, booleans, None)
                flat_configs[full_key] = value
        
        return flat_configs
    
    def update_config(self, key: str, value: Any, source: str = "home_assistant"):
        """Update a specific configuration value and persist to database."""
        log.info(f"Updating configuration: {key} = {value} (source: {source})")
        
        if not self._config_cache:
            log.warning("No configuration cache available, reloading config")
            self.load_config()
        
        # Update the cached configuration
        self._update_nested_config(self._config_cache, key, value)
        
        # Persist to database
        if self.db_logger:
            value_str = json.dumps(value) if isinstance(value, (dict, list)) else str(value)
            self.db_logger.set_config(key, value_str, source)
        
        log.info(f"Configuration updated successfully: {key} = {value}")
    
    def update_config_bulk(self, config_updates: Dict[str, Any], source: str = "api") -> bool:
        """Update multiple configuration values at once."""
        try:
            log.info(f"Updating bulk configuration: {len(config_updates)} values (source: {source})")
            
            if not self._config_cache:
                log.warning("No configuration cache available, reloading config")
                self.load_config()
            
            # Track which values actually changed
            changed_values = {}
            
            # Update each configuration value
            for key, value in config_updates.items():
                # Get current value to check if it actually changed
                try:
                    current_value = self.get_config_value(key)
                    if current_value != value:
                        changed_values[key] = value
                        self._update_nested_config(self._config_cache, key, value)
                        
                        # Persist to database
                        if self.db_logger:
                            value_str = json.dumps(value) if isinstance(value, (dict, list)) else str(value)
                            self.db_logger.set_config(key, value_str, source)
                    else:
                        log.debug(f"Configuration value {key} unchanged, skipping update")
                except Exception as e:
                    log.warning(f"Failed to check current value for {key}: {e}")
                    # If we can't check the current value, update anyway
                    changed_values[key] = value
                    self._update_nested_config(self._config_cache, key, value)
                    
                    # Persist to database
                    if self.db_logger:
                        value_str = json.dumps(value) if isinstance(value, (dict, list)) else str(value)
                        self.db_logger.set_config(key, value_str, source)
            
            log.info(f"Bulk configuration update completed successfully: {len(changed_values)} values changed out of {len(config_updates)} provided")
            return True
            
        except Exception as e:
            log.error(f"Error updating bulk configuration: {e}", exc_info=True)
            return False
    
    def _update_nested_config(self, config: HubConfig, key: str, value: Any):
        """Update nested configuration value."""
        keys = key.split('.')
        current = config
        
        # Navigate to the parent object
        for k in keys[:-1]:
            current = getattr(current, k)
        
        # Set the final value
        setattr(current, keys[-1], value)
    
    def get_config_value(self, key: str) -> Any:
        """Get a specific configuration value."""
        if not self._config_cache:
            self.load_config()
        
        keys = key.split('.')
        current = self._config_cache
        
        for k in keys:
            current = getattr(current, k)
        
        return current
    
    def update_config_single(self, key: str, value: Any, source: str = "api") -> bool:
        """Update a single configuration value."""
        try:
            log.info(f"Updating single configuration: {key} = {value} (source: {source})")
            
            if not self._config_cache:
                log.warning("No configuration cache available, reloading config")
                self.load_config()
            
            # Check if the value actually changed
            try:
                current_value = self.get_config_value(key)
                if current_value == value:
                    log.debug(f"Configuration value {key} unchanged, skipping update")
                    return True
            except Exception as e:
                log.warning(f"Failed to check current value for {key}: {e}")
                # If we can't check the current value, update anyway
            
            # Update the configuration value
            self._update_nested_config(self._config_cache, key, value)
            
            # Persist to database
            if self.db_logger:
                value_str = json.dumps(value) if isinstance(value, (dict, list)) else str(value)
                self.db_logger.set_config(key, value_str, source)
            
            log.info(f"Single configuration update completed successfully: {key} = {value}")
            return True
            
        except Exception as e:
            log.error(f"Error updating single configuration {key}: {e}", exc_info=True)
            return False
    
    def reload_config(self) -> HubConfig:
        """Reload configuration from database/file."""
        log.info("Reloading configuration")
        self._config_cache = None
        return self.load_config()
    
    def sync_to_file(self):
        """Sync current configuration back to config.yaml file."""
        if not self._config_cache:
            log.warning("No configuration cache available for sync")
            return
        
        try:
            config_dict = self._config_cache.model_dump()
            
            with open(self.config_path, 'w') as f:
                yaml.dump(config_dict, f, default_flow_style=False, indent=2)
            
            log.info(f"Configuration synced to {self.config_path}")
            
        except Exception as e:
            log.error(f"Failed to sync configuration to file: {e}")
