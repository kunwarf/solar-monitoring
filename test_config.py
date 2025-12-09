"""
Unit tests for configuration classes
Tests the Pydantic models and validation
"""

import pytest
from pydantic import ValidationError

from solarhub.config import (
    MqttConfig, PollingConfig, SafetyLimits, InverterAdapterConfig,
    SolarArrayParams, InverterConfig, ForecastConfig, PolicyConfig,
    SmartConfig, HubConfig
)


class TestMqttConfig:
    """Test MQTT configuration"""
    
    def test_default_values(self):
        """Test default MQTT configuration values"""
        config = MqttConfig(host="localhost")
        
        assert config.host == "localhost"
        assert config.port == 1883
        assert config.username is None
        assert config.password is None
        assert config.base_topic == "solar/fleet"
        assert config.client_id == "solar-hub"
        assert config.ha_discovery is False
    
    def test_custom_values(self):
        """Test custom MQTT configuration values"""
        config = MqttConfig(
            host="192.168.1.100",
            port=8883,
            username="user",
            password="pass",
            base_topic="custom/solar",
            client_id="custom-hub",
            ha_discovery=True
        )
        
        assert config.host == "192.168.1.100"
        assert config.port == 8883
        assert config.username == "user"
        assert config.password == "pass"
        assert config.base_topic == "custom/solar"
        assert config.client_id == "custom-hub"
        assert config.ha_discovery is True
    
    def test_missing_required_field(self):
        """Test validation with missing required field"""
        with pytest.raises(ValidationError):
            MqttConfig()  # host is required


class TestPollingConfig:
    """Test polling configuration"""
    
    def test_default_values(self):
        """Test default polling configuration values"""
        config = PollingConfig()
        
        assert config.interval_secs == 2.0
        assert config.timeout_ms == 1500
        assert config.concurrent == 5
    
    def test_custom_values(self):
        """Test custom polling configuration values"""
        config = PollingConfig(
            interval_secs=5.0,
            timeout_ms=3000,
            concurrent=10
        )
        
        assert config.interval_secs == 5.0
        assert config.timeout_ms == 3000
        assert config.concurrent == 10
    
    def test_interval_validation(self):
        """Test interval validation (must be >= 0.5)"""
        # Valid values
        config = PollingConfig(interval_secs=0.5)
        assert config.interval_secs == 0.5
        
        config = PollingConfig(interval_secs=10.0)
        assert config.interval_secs == 10.0
        
        # Invalid value
        with pytest.raises(ValidationError):
            PollingConfig(interval_secs=0.1)  # Too small


class TestSafetyLimits:
    """Test safety limits configuration"""
    
    def test_default_values(self):
        """Test default safety limits"""
        limits = SafetyLimits()
        
        assert limits.max_batt_voltage_v == 60.0
        assert limits.min_batt_voltage_v == 44.0
        assert limits.max_charge_a == 120
        assert limits.max_discharge_a == 120
        assert limits.max_inverter_temp_c == 85.0
    
    def test_custom_values(self):
        """Test custom safety limits"""
        limits = SafetyLimits(
            max_batt_voltage_v=58.8,
            min_batt_voltage_v=45.0,
            max_charge_a=100,
            max_discharge_a=100,
            max_inverter_temp_c=80.0
        )
        
        assert limits.max_batt_voltage_v == 58.8
        assert limits.min_batt_voltage_v == 45.0
        assert limits.max_charge_a == 100
        assert limits.max_discharge_a == 100
        assert limits.max_inverter_temp_c == 80.0


class TestInverterAdapterConfig:
    """Test inverter adapter configuration"""
    
    def test_default_values(self):
        """Test default adapter configuration"""
        config = InverterAdapterConfig(type="senergy")
        
        assert config.type == "senergy"
        assert config.unit_id == 1
        assert config.transport == "rtu"
        assert config.host is None
        assert config.port == 502
        assert config.serial_port is None
        assert config.baudrate == 9600
        assert config.parity == "N"
        assert config.stopbits == 1
        assert config.bytesize == 8
        assert config.register_map_file is None
    
    def test_rtu_configuration(self):
        """Test RTU transport configuration"""
        config = InverterAdapterConfig(
            type="senergy",
            transport="rtu",
            unit_id=2,
            serial_port="/dev/ttyUSB0",
            baudrate=19200,
            parity="E",
            stopbits=2,
            bytesize=7
        )
        
        assert config.transport == "rtu"
        assert config.unit_id == 2
        assert config.serial_port == "/dev/ttyUSB0"
        assert config.baudrate == 19200
        assert config.parity == "E"
        assert config.stopbits == 2
        assert config.bytesize == 7
    
    def test_tcp_configuration(self):
        """Test TCP transport configuration"""
        config = InverterAdapterConfig(
            type="senergy",
            transport="tcp",
            host="192.168.1.100",
            port=502,
            unit_id=1
        )
        
        assert config.transport == "tcp"
        assert config.host == "192.168.1.100"
        assert config.port == 502


class TestSolarArrayParams:
    """Test solar array parameters"""
    
    def test_default_values(self):
        """Test default solar array parameters"""
        params = SolarArrayParams()
        
        assert params.pv_dc_kw == 10.0
        assert params.tilt_deg == 20.0
        assert params.azimuth_deg == 180.0
        assert params.perf_ratio == 0.8
        assert params.albedo == 0.2
    
    def test_custom_values(self):
        """Test custom solar array parameters"""
        params = SolarArrayParams(
            pv_dc_kw=5.0,
            tilt_deg=30.0,
            azimuth_deg=200.0,
            perf_ratio=0.85,
            albedo=0.3
        )
        
        assert params.pv_dc_kw == 5.0
        assert params.tilt_deg == 30.0
        assert params.azimuth_deg == 200.0
        assert params.perf_ratio == 0.85
        assert params.albedo == 0.3


class TestInverterConfig:
    """Test inverter configuration"""
    
    def test_minimal_config(self):
        """Test minimal inverter configuration"""
        adapter_config = InverterAdapterConfig(type="senergy")
        
        config = InverterConfig(
            id="inverter1",
            adapter=adapter_config
        )
        
        assert config.id == "inverter1"
        assert config.name is None
        assert config.adapter.type == "senergy"
        assert isinstance(config.safety, SafetyLimits)
        assert len(config.solar) == 1
        assert isinstance(config.solar[0], SolarArrayParams)
    
    def test_full_config(self):
        """Test full inverter configuration"""
        adapter_config = InverterAdapterConfig(
            type="senergy",
            transport="rtu",
            serial_port="/dev/ttyUSB0"
        )
        
        safety_limits = SafetyLimits(
            max_batt_voltage_v=58.8,
            max_charge_a=100
        )
        
        solar_arrays = [
            SolarArrayParams(pv_dc_kw=3.0, tilt_deg=15),
            SolarArrayParams(pv_dc_kw=2.0, tilt_deg=25)
        ]
        
        config = InverterConfig(
            id="inverter1",
            name="East Roof",
            adapter=adapter_config,
            safety=safety_limits,
            solar=solar_arrays
        )
        
        assert config.id == "inverter1"
        assert config.name == "East Roof"
        assert config.safety.max_batt_voltage_v == 58.8
        assert len(config.solar) == 2
        assert config.solar[0].pv_dc_kw == 3.0


class TestForecastConfig:
    """Test forecast configuration"""
    
    def test_default_values(self):
        """Test default forecast configuration"""
        config = ForecastConfig()
        
        assert config.enabled is False
        assert config.lat == 0.0
        assert config.lon == 0.0
        assert config.tz == "Asia/Karachi"
        assert config.provider == "naive"
        assert config.api_key is None
        assert config.pv_dc_kw == 10.0
        assert config.pv_perf_ratio == 0.8
        assert config.tilt_deg == 20.0
        assert config.azimuth_deg == 180.0
        assert config.albedo == 0.2
        assert config.batt_capacity_kwh == 20.0
        assert config.load_history_days == 14
    
    def test_custom_values(self):
        """Test custom forecast configuration"""
        config = ForecastConfig(
            enabled=True,
            lat=31.5204,
            lon=74.3587,
            tz="Asia/Karachi",
            provider="openmeteo",
            api_key="test_key",
            pv_dc_kw=12.0,
            pv_perf_ratio=0.82,
            tilt_deg=25.0,
            azimuth_deg=200.0,
            albedo=0.25,
            batt_capacity_kwh=18.0,
            load_history_days=30
        )
        
        assert config.enabled is True
        assert config.lat == 31.5204
        assert config.lon == 74.3587
        assert config.tz == "Asia/Karachi"
        assert config.provider == "openmeteo"
        assert config.api_key == "test_key"
        assert config.pv_dc_kw == 12.0
        assert config.pv_perf_ratio == 0.82
        assert config.tilt_deg == 25.0
        assert config.azimuth_deg == 200.0
        assert config.albedo == 0.25
        assert config.batt_capacity_kwh == 18.0
        assert config.load_history_days == 30


class TestPolicyConfig:
    """Test policy configuration"""
    
    def test_default_values(self):
        """Test default policy configuration"""
        config = PolicyConfig()
        
        assert config.enabled is False
        assert config.target_full_before_sunset is True
        assert config.overnight_min_soc_pct == 30
        assert config.conserve_on_bad_tomorrow is True
        assert config.bad_sun_threshold_kwh == 0.3
    
    def test_custom_values(self):
        """Test custom policy configuration"""
        config = PolicyConfig(
            enabled=True,
            target_full_before_sunset=False,
            overnight_min_soc_pct=25,
            conserve_on_bad_tomorrow=False,
            bad_sun_threshold_kwh=0.5
        )
        
        assert config.enabled is True
        assert config.target_full_before_sunset is False
        assert config.overnight_min_soc_pct == 25
        assert config.conserve_on_bad_tomorrow is False
        assert config.bad_sun_threshold_kwh == 0.5


class TestSmartConfig:
    """Test smart configuration"""
    
    def test_default_values(self):
        """Test default smart configuration"""
        config = SmartConfig()
        
        assert isinstance(config.forecast, ForecastConfig)
        assert isinstance(config.policy, PolicyConfig)
    
    def test_custom_values(self):
        """Test custom smart configuration"""
        forecast_config = ForecastConfig(enabled=True, lat=31.5204, lon=74.3587)
        policy_config = PolicyConfig(enabled=True, overnight_min_soc_pct=25)
        
        config = SmartConfig(
            forecast=forecast_config,
            policy=policy_config
        )
        
        assert config.forecast.enabled is True
        assert config.forecast.lat == 31.5204
        assert config.policy.enabled is True
        assert config.policy.overnight_min_soc_pct == 25


class TestHubConfig:
    """Test hub configuration"""
    
    def test_minimal_config(self):
        """Test minimal hub configuration"""
        mqtt_config = MqttConfig(host="localhost")
        inverter_config = InverterConfig(
            id="inverter1",
            adapter=InverterAdapterConfig(type="senergy")
        )
        
        config = HubConfig(
            mqtt=mqtt_config,
            inverters=[inverter_config]
        )
        
        assert config.mqtt.host == "localhost"
        assert len(config.inverters) == 1
        assert config.inverters[0].id == "inverter1"
        assert isinstance(config.polling, PollingConfig)
        assert isinstance(config.smart, SmartConfig)
    
    def test_full_config(self):
        """Test full hub configuration"""
        mqtt_config = MqttConfig(
            host="192.168.1.100",
            port=1883,
            base_topic="solar/fleet"
        )
        
        polling_config = PollingConfig(interval_secs=5.0)
        
        smart_config = SmartConfig(
            forecast=ForecastConfig(enabled=True, lat=31.5204, lon=74.3587),
            policy=PolicyConfig(enabled=True)
        )
        
        inverter_config = InverterConfig(
            id="inverter1",
            name="East Roof",
            adapter=InverterAdapterConfig(
                type="senergy",
                transport="rtu",
                serial_port="/dev/ttyUSB0"
            ),
            safety=SafetyLimits(max_batt_voltage_v=58.8),
            solar=[SolarArrayParams(pv_dc_kw=3.0)]
        )
        
        config = HubConfig(
            mqtt=mqtt_config,
            polling=polling_config,
            inverters=[inverter_config],
            smart=smart_config
        )
        
        assert config.mqtt.host == "192.168.1.100"
        assert config.polling.interval_secs == 5.0
        assert config.smart.forecast.enabled is True
        assert len(config.inverters) == 1
        assert config.inverters[0].name == "East Roof"
        assert config.inverters[0].safety.max_batt_voltage_v == 58.8


class TestConfigValidation:
    """Test configuration validation and edge cases"""
    
    def test_invalid_port_numbers(self):
        """Test validation of port numbers"""
        # Valid ports
        MqttConfig(host="localhost", port=1883)
        MqttConfig(host="localhost", port=8883)
        
        # Invalid ports (should still work as Pydantic doesn't validate port ranges by default)
        MqttConfig(host="localhost", port=0)
        MqttConfig(host="localhost", port=65536)
    
    def test_invalid_coordinates(self):
        """Test validation of coordinate values"""
        # Valid coordinates
        ForecastConfig(lat=31.5204, lon=74.3587)
        ForecastConfig(lat=-31.5204, lon=-74.3587)
        
        # Edge cases (should still work as Pydantic doesn't validate coordinate ranges by default)
        ForecastConfig(lat=90.0, lon=180.0)
        ForecastConfig(lat=-90.0, lon=-180.0)
    
    def test_empty_strings(self):
        """Test handling of empty strings"""
        # Empty strings should be allowed
        MqttConfig(host="", username="", password="")
        InverterConfig(id="", adapter=InverterAdapterConfig(type=""))
    
    def test_none_values(self):
        """Test handling of None values"""
        # None values should be allowed for optional fields
        config = MqttConfig(host="localhost", username=None, password=None)
        assert config.username is None
        assert config.password is None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

