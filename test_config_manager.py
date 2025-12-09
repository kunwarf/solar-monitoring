"""
Unit tests for ConfigurationManager
Tests the configuration persistence and management functionality
"""

import pytest
import json
import tempfile
import os
from unittest.mock import Mock, patch, mock_open
from pathlib import Path

from solarhub.config_manager import ConfigurationManager
from solarhub.config import HubConfig, MqttConfig, PollingConfig, SmartConfig, ForecastConfig, PolicyConfig
from solarhub.config import InverterConfig, InverterAdapterConfig, SafetyLimits, SolarArrayParams
from solarhub.logging.logger import DataLogger


class TestConfigurationManager:
    """Test ConfigurationManager functionality"""
    
    @pytest.fixture
    def mock_db_logger(self):
        """Create a mock database logger"""
        mock_logger = Mock(spec=DataLogger)
        mock_logger.path = "/tmp/test.db"
        return mock_logger
    
    @pytest.fixture
    def sample_config(self):
        """Create a sample configuration for testing"""
        mqtt_config = MqttConfig(
            host="localhost",
            port=1883,
            base_topic="test/solar"
        )
        
        forecast_config = ForecastConfig(
            enabled=True,
            lat=31.5204,
            lon=74.3587,
            tz="Asia/Karachi",
            provider="naive",
            batt_capacity_kwh=18.0
        )
        
        policy_config = PolicyConfig(
            enabled=True,
            target_full_before_sunset=True,
            overnight_min_soc_pct=30,
            blackout_reserve_soc_pct=30,
            smart_tick_interval_secs=300,
            max_charge_power_w=5000,
            max_discharge_power_w=5000,
            max_battery_soc_pct=100
        )
        
        smart_config = SmartConfig(
            forecast=forecast_config,
            policy=policy_config
        )
        
        adapter_config = InverterAdapterConfig(
            type="senergy",
            transport="rtu",
            unit_id=1,
            serial_port="/dev/ttyUSB0"
        )
        
        inverter_config = InverterConfig(
            id="test_inverter",
            name="Test Inverter",
            adapter=adapter_config,
            safety=SafetyLimits(),
            solar=[SolarArrayParams(pv_dc_kw=3.0)]
        )
        
        hub_config = HubConfig(
            mqtt=mqtt_config,
            polling=PollingConfig(),
            inverters=[inverter_config],
            smart=smart_config
        )
        
        return hub_config
    
    @pytest.fixture
    def config_manager(self, mock_db_logger):
        """Create a ConfigurationManager instance for testing"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("test: config")
            temp_path = f.name
        
        try:
            manager = ConfigurationManager(temp_path, mock_db_logger)
            yield manager
        finally:
            os.unlink(temp_path)
    
    def test_initialization(self, config_manager, mock_db_logger):
        """Test ConfigurationManager initialization"""
        assert config_manager.config_path is not None
        assert config_manager.db_logger == mock_db_logger
        assert config_manager._config_cache is None
    
    def test_load_from_file(self, config_manager, sample_config):
        """Test loading configuration from file"""
        # Mock the file content
        config_dict = sample_config.model_dump()
        
        with patch('builtins.open', mock_open(read_data=json.dumps(config_dict))), \
             patch('yaml.safe_load', return_value=config_dict):
            
            result = config_manager._load_from_file()
            
            assert isinstance(result, HubConfig)
            assert result.mqtt.host == "localhost"
            assert result.smart.policy.enabled is True
    
    def test_load_from_database_empty(self, config_manager):
        """Test loading from empty database"""
        # Mock empty database
        config_manager.db_logger.get_all_configs.return_value = {}
        
        result = config_manager._load_from_database()
        
        assert result is None
        config_manager.db_logger.get_all_configs.assert_called_once()
    
    def test_load_from_database_with_data(self, config_manager, sample_config):
        """Test loading from database with data"""
        # Mock database with configuration data
        config_dict = sample_config.model_dump()
        flat_configs = config_manager._dict_to_flat_configs(config_dict)
        
        # Convert to string format as stored in database
        db_configs = {}
        for key, value in flat_configs.items():
            if isinstance(value, (dict, list)):
                db_configs[key] = json.dumps(value)
            else:
                db_configs[key] = str(value)
        
        config_manager.db_logger.get_all_configs.return_value = db_configs
        
        result = config_manager._load_from_database()
        
        assert isinstance(result, HubConfig)
        assert result.mqtt.host == "localhost"
        assert result.smart.policy.enabled is True
    
    def test_save_to_database(self, config_manager, sample_config):
        """Test saving configuration to database"""
        config_manager._save_to_database(sample_config)
        
        # Verify that set_config was called for each configuration key
        assert config_manager.db_logger.set_config.called
    
    def test_dict_to_flat_configs(self, config_manager, sample_config):
        """Test flattening nested configuration dictionary"""
        config_dict = sample_config.model_dump()
        flat_configs = config_manager._dict_to_flat_configs(config_dict)
        
        # Check that nested keys are flattened
        assert "mqtt.host" in flat_configs
        assert "smart.policy.enabled" in flat_configs
        # Note: inverters is a list, so it's handled differently
        assert "inverters" in flat_configs
        
        # Check values
        assert flat_configs["mqtt.host"] == "localhost"
        assert flat_configs["smart.policy.enabled"] is True
        # Check that inverters is a list
        assert isinstance(flat_configs["inverters"], list)
    
    def test_update_nested_config(self, config_manager, sample_config):
        """Test updating nested configuration values"""
        # Test updating a simple value
        config_manager._update_nested_config(sample_config, "smart.policy.enabled", False)
        assert sample_config.smart.policy.enabled is False
        
        # Test updating a nested value
        config_manager._update_nested_config(sample_config, "mqtt.port", 8883)
        assert sample_config.mqtt.port == 8883
    
    def test_get_config_value(self, config_manager, sample_config):
        """Test getting configuration values"""
        # Set up cache first
        config_manager._config_cache = sample_config
        
        # Test getting a simple value
        value = config_manager.get_config_value("smart.policy.enabled")
        assert value is True
        
        # Test getting a nested value
        value = config_manager.get_config_value("mqtt.port")
        assert value == 1883
    
    def test_update_config(self, config_manager, sample_config):
        """Test updating configuration values"""
        # Mock the database logger methods
        config_manager.db_logger.set_config = Mock()
        
        # Set up the config cache to avoid loading from file
        config_manager._config_cache = sample_config
        
        # Test updating a simple value
        config_manager.update_config("smart.policy.enabled", False)
        
        # Verify the value was updated in memory
        assert sample_config.smart.policy.enabled is False
        
        # Verify it was saved to database
        config_manager.db_logger.set_config.assert_called()
    
    def test_sync_to_file(self, config_manager, sample_config):
        """Test syncing configuration to file"""
        config_manager._config_cache = sample_config
        
        with patch('builtins.open', mock_open()) as mock_file, \
             patch('yaml.dump') as mock_yaml_dump:
            
            config_manager.sync_to_file()
            
            # Verify file was opened for writing
            mock_file.assert_called_once()
            
            # Verify yaml.dump was called
            mock_yaml_dump.assert_called_once()
    
    def test_reload_config(self, config_manager, sample_config):
        """Test reloading configuration"""
        # Set up cache
        config_manager._config_cache = sample_config
        
        # Mock database with new data
        new_config = sample_config.model_dump()
        new_config["mqtt"]["host"] = "newhost"
        flat_configs = config_manager._dict_to_flat_configs(new_config)
        
        db_configs = {}
        for key, value in flat_configs.items():
            if isinstance(value, (dict, list)):
                db_configs[key] = json.dumps(value)
            else:
                db_configs[key] = str(value)
        
        config_manager.db_logger.get_all_configs.return_value = db_configs
        
        result = config_manager.reload_config()
        
        # Verify cache was cleared and new config loaded
        assert result.mqtt.host == "newhost"
        # Note: reload_config doesn't clear the cache, it updates it
        assert config_manager._config_cache is not None
    
    def test_load_config_database_first(self, config_manager, sample_config):
        """Test loading configuration with database first"""
        # Mock database with data
        config_dict = sample_config.model_dump()
        flat_configs = config_manager._dict_to_flat_configs(config_dict)
        
        db_configs = {}
        for key, value in flat_configs.items():
            if isinstance(value, (dict, list)):
                db_configs[key] = json.dumps(value)
            else:
                db_configs[key] = str(value)
        
        config_manager.db_logger.get_all_configs.return_value = db_configs
        
        result = config_manager.load_config()
        
        # Should load from database
        assert isinstance(result, HubConfig)
        assert result.mqtt.host == "localhost"
    
    def test_load_config_file_fallback(self, config_manager, sample_config):
        """Test loading configuration with file fallback"""
        # Mock empty database
        config_manager.db_logger.get_all_configs.return_value = {}
        
        # Mock file content
        config_dict = sample_config.model_dump()
        
        with patch('builtins.open', mock_open(read_data=json.dumps(config_dict))), \
             patch('yaml.safe_load', return_value=config_dict):
            
            result = config_manager.load_config()
            
            # Should load from file and save to database
            assert isinstance(result, HubConfig)
            assert result.mqtt.host == "localhost"
            assert config_manager.db_logger.set_config.called


class TestConfigurationManagerEdgeCases:
    """Test edge cases and error conditions"""
    
    @pytest.fixture
    def mock_db_logger(self):
        """Create a mock database logger"""
        mock_logger = Mock(spec=DataLogger)
        mock_logger.path = "/tmp/test.db"
        return mock_logger
    
    def test_initialization_no_db_logger(self):
        """Test initialization without database logger"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("test: config")
            temp_path = f.name
        
        try:
            manager = ConfigurationManager(temp_path, None)
            assert manager.db_logger is None
        finally:
            os.unlink(temp_path)
    
    def test_load_from_database_exception(self, mock_db_logger):
        """Test handling exceptions when loading from database"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("test: config")
            temp_path = f.name
        
        try:
            manager = ConfigurationManager(temp_path, mock_db_logger)
            
            # Mock database to raise exception
            mock_db_logger.get_all_configs.side_effect = Exception("Database error")
            
            result = manager._load_from_database()
            
            # Should return None on exception
            assert result is None
        finally:
            os.unlink(temp_path)
    
    def test_save_to_database_exception(self, mock_db_logger):
        """Test handling exceptions when saving to database"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("test: config")
            temp_path = f.name
        
        try:
            manager = ConfigurationManager(temp_path, mock_db_logger)
            
            # Create a simple config
            config = HubConfig(
                mqtt=MqttConfig(host="localhost"),
                polling=PollingConfig(),
                inverters=[],
                smart=SmartConfig(
                    forecast=ForecastConfig(enabled=True, lat=0, lon=0, tz="UTC", provider="naive", batt_capacity_kwh=10),
                    policy=PolicyConfig(enabled=True)
                )
            )
            
            # Mock database to raise exception
            mock_db_logger.set_config.side_effect = Exception("Database error")
            
            # Should not raise exception
            manager._save_to_database(config)
            
        finally:
            os.unlink(temp_path)
    
    def test_sync_to_file_exception(self, mock_db_logger):
        """Test handling exceptions when syncing to file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("test: config")
            temp_path = f.name
        
        try:
            manager = ConfigurationManager(temp_path, mock_db_logger)
            
            # Create a simple config
            config = HubConfig(
                mqtt=MqttConfig(host="localhost"),
                polling=PollingConfig(),
                inverters=[],
                smart=SmartConfig(
                    forecast=ForecastConfig(enabled=True, lat=0, lon=0, tz="UTC", provider="naive", batt_capacity_kwh=10),
                    policy=PolicyConfig(enabled=True)
                )
            )
            
            manager._config_cache = config
            
            # Mock file operations to raise exception
            with patch('builtins.open', side_effect=Exception("File error")):
                # Should not raise exception
                manager.sync_to_file()
                
        finally:
            os.unlink(temp_path)


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
