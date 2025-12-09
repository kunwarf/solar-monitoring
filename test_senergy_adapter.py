"""
Unit tests for SenergyAdapter
Tests the Modbus communication and register handling
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, List

from solarhub.adapters.senergy import SenergyAdapter, _coerce_enum_map, _coerce_bit_enum
from solarhub.config import InverterConfig, InverterAdapterConfig, SafetyLimits, SolarArrayParams
from solarhub.models import Telemetry


class TestSenergyAdapterHelpers:
    """Test helper functions in SenergyAdapter"""
    
    def test_sanitize_key(self):
        """Test key sanitization function"""
        assert SenergyAdapter._sanitize_key("Battery SOC") == "battery_soc"
        assert SenergyAdapter._sanitize_key("Device Model") == "device_model"
        assert SenergyAdapter._sanitize_key("MPPT1 Power") == "mppt1_power"
        assert SenergyAdapter._sanitize_key("Grid-Phase-R") == "grid_phase_r"
        assert SenergyAdapter._sanitize_key("123 Test!@#") == "123_test_"
    
    def test_coerce_enum_map(self):
        """Test enum map coercion"""
        # Test with integer keys
        enum_data = {0: "Off", 1: "On", 2: "Auto"}
        result = _coerce_enum_map({"enum": enum_data})
        assert result == {0: "Off", 1: "On", 2: "Auto"}
        
        # Test with string keys
        enum_data = {"0": "Off", "1": "On", "0x02": "Auto"}
        result = _coerce_enum_map({"enum": enum_data})
        assert result == {0: "Off", 1: "On", 2: "Auto"}
        
        # Test with invalid data
        result = _coerce_enum_map({})
        assert result is None
        
        result = _coerce_enum_map({"enum": None})
        assert result is None
    
    def test_coerce_bit_enum(self):
        """Test bit enum coercion"""
        # Test with valid bit enum
        register = {
            "bit_enum": {
                "0": "OK",
                "1": "Warning",
                "2": "Error",
                "3": "Fault"
            }
        }
        
        # Test with no bits set
        result = _coerce_bit_enum(register, 0)
        assert result == ["OK"]
        
        # Test with single bit set
        result = _coerce_bit_enum(register, 1)  # bit 0 set
        assert result == ["OK"]
        
        result = _coerce_bit_enum(register, 2)  # bit 1 set
        assert result == ["Warning"]
        
        # Test with multiple bits set
        result = _coerce_bit_enum(register, 3)  # bits 0 and 1 set
        assert result == ["OK", "Warning"]
        
        # Test with invalid data
        result = _coerce_bit_enum({}, 5)
        assert result is None


class TestSenergyAdapter:
    """Test SenergyAdapter functionality"""
    
    @pytest.fixture
    def mock_inverter_config(self):
        """Create a mock inverter configuration"""
        adapter_config = InverterAdapterConfig(
            type="senergy",
            transport="rtu",
            unit_id=1,
            serial_port="/dev/ttyUSB0",
            baudrate=9600,
            parity="N",
            stopbits=1,
            bytesize=8,
            register_map_file="test_registers.json"
        )
        
        inverter_config = InverterConfig(
            id="test_inverter",
            name="Test Inverter",
            adapter=adapter_config,
            safety=SafetyLimits(),
            solar=[SolarArrayParams()]
        )
        
        return inverter_config
    
    @pytest.fixture
    def sample_register_map(self):
        """Create a sample register map for testing"""
        return [
            {
                "id": "battery_soc",
                "name": "Battery SOC",
                "addr": 8192,
                "type": "U16",
                "rw": "RO",
                "kind": "holding",
                "size": 1,
                "unit": "%"
            },
            {
                "id": "battery_voltage",
                "name": "Battery Voltage",
                "addr": 8193,
                "type": "U16",
                "rw": "RO",
                "kind": "holding",
                "size": 1,
                "unit": "V",
                "scale": 0.1
            },
            {
                "id": "work_mode",
                "name": "Work Mode",
                "addr": 9000,
                "type": "U16",
                "rw": "RW",
                "kind": "holding",
                "size": 1,
                "enum": {
                    "0": "Self-used",
                    "1": "Backup",
                    "2": "Time-based control"
                }
            }
        ]
    
    @pytest.fixture
    def adapter_with_mock_registers(self, mock_inverter_config, sample_register_map):
        """Create an adapter with mocked register map"""
        with patch('builtins.open', mock_open_register_file(sample_register_map)):
            adapter = SenergyAdapter(mock_inverter_config)
            return adapter
    
    def test_init_with_register_map(self, mock_inverter_config, sample_register_map):
        """Test adapter initialization with register map"""
        with patch('builtins.open', mock_open_register_file(sample_register_map)):
            adapter = SenergyAdapter(mock_inverter_config)
            
            assert len(adapter.regs) == 3
            assert adapter.addr_offset == 0
            assert adapter.last_tel == {}
    
    def test_init_without_register_map(self, mock_inverter_config):
        """Test adapter initialization without register map file"""
        with patch('builtins.open', side_effect=FileNotFoundError):
            adapter = SenergyAdapter(mock_inverter_config)
            
            assert len(adapter.regs) == 0
            assert adapter.last_tel == {}
    
    def test_find_reg_by_id_or_name(self, adapter_with_mock_registers):
        """Test register lookup by ID or name"""
        # Test by ID
        reg = adapter_with_mock_registers._find_reg_by_id_or_name("battery_soc")
        assert reg["id"] == "battery_soc"
        assert reg["addr"] == 8192
        
        # Test by name
        reg = adapter_with_mock_registers._find_reg_by_id_or_name("Battery SOC")
        assert reg["id"] == "battery_soc"
        
        # Test case insensitive
        reg = adapter_with_mock_registers._find_reg_by_id_or_name("BATTERY_SOC")
        assert reg["id"] == "battery_soc"
        
        # Test not found
        with pytest.raises(KeyError):
            adapter_with_mock_registers._find_reg_by_id_or_name("nonexistent")
    
    def test_encode_value_basic_types(self, adapter_with_mock_registers):
        """Test value encoding for basic types"""
        # Test U16 encoding
        reg = {"type": "U16", "size": 1}
        result = adapter_with_mock_registers._encode_value(reg, 100)
        assert result == [100]
        
        # Test U32 encoding
        reg = {"type": "U32", "size": 2}
        result = adapter_with_mock_registers._encode_value(reg, 0x12345678)
        assert result == [0x1234, 0x5678]
        
        # Test with scaling
        reg = {"type": "U16", "size": 1, "scale": 0.1}
        result = adapter_with_mock_registers._encode_value(reg, 52.5)
        assert result == [525]  # 52.5 / 0.1 = 525
    
    def test_encode_value_special_encoders(self, adapter_with_mock_registers):
        """Test value encoding for special encoders"""
        # Test HH:MM encoder
        reg = {"encoder": "hhmm", "size": 1}
        result = adapter_with_mock_registers._encode_value(reg, "14:30")
        expected = (14 << 8) | 30  # 0x0E1E
        assert result == [expected]
        
        # Test bool encoder
        reg = {"encoder": "bool", "size": 1}
        result = adapter_with_mock_registers._encode_value(reg, True)
        assert result == [1]
        
        result = adapter_with_mock_registers._encode_value(reg, False)
        assert result == [0]
        
        # Test ASCII encoder
        reg = {"encoder": "ascii", "size": 2}
        result = adapter_with_mock_registers._encode_value(reg, "AB")
        assert result == [0x4142, 0]  # 'A'=0x41, 'B'=0x42, padded to size 2
    
    @pytest.mark.asyncio
    async def test_poll_success(self, adapter_with_mock_registers):
        """Test successful polling"""
        # Mock the Modbus client and responses
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.registers = [50, 525, 2]  # SOC=50%, Voltage=52.5V, Work mode=2
        mock_response.isError.return_value = False
        mock_client.read_holding_registers.return_value = mock_response
        
        adapter_with_mock_registers.client = mock_client
        
        # Execute poll
        result = await adapter_with_mock_registers.poll()
        
        # Verify result
        assert isinstance(result, Telemetry)
        assert result.batt_soc_pct == 50.0
        assert result.batt_voltage_v == 52.5
        
        # Verify last_tel was updated
        assert adapter_with_mock_registers.last_tel["battery_soc"] == 50.0
        assert adapter_with_mock_registers.last_tel["battery_voltage"] == 52.5
    
    @pytest.mark.asyncio
    async def test_poll_modbus_error(self, adapter_with_mock_registers):
        """Test polling with Modbus error"""
        # Mock the Modbus client with error response
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.isError.return_value = True
        mock_client.read_holding_registers.return_value = mock_response

        adapter_with_mock_registers.client = mock_client

        # Should handle error gracefully and return telemetry with empty values
        result = await adapter_with_mock_registers.poll()
        assert isinstance(result, Telemetry)
        # The result should have default/empty values due to Modbus errors
    
    @pytest.mark.asyncio
    async def test_handle_command_set_work_mode(self, adapter_with_mock_registers):
        """Test handling set_work_mode command"""
        # Add hybrid_work_mode register to mock
        adapter_with_mock_registers.regs.append({
            "id": "hybrid_work_mode",
            "name": "Hybrid work mode",
            "addr": 8448,
            "type": "U16",
            "rw": "RW",
            "kind": "holding",
            "size": 1,
            "enum": {
                "0x0000": "Self used mode",
                "0x0001": "Feed-in priority mode",
                "0x0002": "Time-based control"
            }
        })
        
        # Mock the write methods
        adapter_with_mock_registers._write_by_ident = AsyncMock()
        
        cmd = {"action": "set_work_mode", "mode": 2}
        result = await adapter_with_mock_registers.handle_command(cmd)
        
        assert result["ok"] == True
        adapter_with_mock_registers._write_by_ident.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_command_write(self, adapter_with_mock_registers):
        """Test handling generic write command"""
        # Add work_mode register to mock
        adapter_with_mock_registers.regs.append({
            "id": "work_mode",
            "name": "Work Mode",
            "addr": 0x2100,
            "type": "U16",
            "rw": "RW",
            "kind": "holding",
            "size": 1
        })
        
        # Mock the write methods
        adapter_with_mock_registers._write_holding_u16 = AsyncMock()
        
        cmd = {
            "action": "write",
            "id": "work_mode",
            "value": 1
        }
        
        result = await adapter_with_mock_registers.handle_command(cmd)
        
        assert result["ok"] == True
        adapter_with_mock_registers._write_holding_u16.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_command_write_many(self, adapter_with_mock_registers):
        """Test handling write_many command"""
        # Mock the write methods
        adapter_with_mock_registers._write_holding_u16 = AsyncMock()
        
        cmd = {
            "action": "write_many",
            "writes": [
                {"id": "work_mode", "value": 1},
                {"id": "battery_soc", "value": 80}  # This should fail (read-only)
            ]
        }
        
        result = await adapter_with_mock_registers.handle_command(cmd)
        
        # Should have errors for read-only register
        assert result["ok"] == False
        assert "errors" in result
        assert len(result["errors"]) > 0


def mock_open_register_file(register_data):
    """Helper function to mock file opening for register maps"""
    def mock_open(file_path, mode='r', encoding=None):
        if 'register' in file_path:
            mock_file = Mock()
            mock_file.__enter__ = Mock(return_value=mock_file)
            mock_file.__exit__ = Mock(return_value=None)
            mock_file.read.return_value = json.dumps(register_data)
            return mock_file
        else:
            raise FileNotFoundError(f"No such file: {file_path}")
    
    return mock_open


class TestSenergyAdapterEdgeCases:
    """Test edge cases and error conditions"""
    
    @pytest.fixture
    def minimal_adapter(self):
        """Create a minimal adapter for edge case testing"""
        mock_config = Mock()
        mock_config.adapter = Mock()
        mock_config.adapter.register_map_file = None
        
        with patch('builtins.open', side_effect=FileNotFoundError):
            adapter = SenergyAdapter(mock_config)
            return adapter
    
    def test_find_reg_empty_register_map(self, minimal_adapter):
        """Test register lookup with empty register map"""
        with pytest.raises(KeyError):
            minimal_adapter._find_reg_by_id_or_name("any_register")
    
    def test_encode_value_invalid_type(self, minimal_adapter):
        """Test value encoding with invalid type"""
        reg = {"type": "INVALID", "size": 1}
        result = minimal_adapter._encode_value(reg, 100)
        assert result == [100]  # Should fall back to basic encoding
    
    def test_encode_value_list_input(self, minimal_adapter):
        """Test value encoding with list input"""
        reg = {"type": "U16", "size": 2}
        # The current implementation doesn't handle list input directly
        # This test should expect an error or be updated to match the actual behavior
        with pytest.raises(ValueError):
            minimal_adapter._encode_value(reg, [100, 200])
    
    @pytest.mark.asyncio
    async def test_handle_command_unknown_action(self, minimal_adapter):
        """Test handling unknown command action"""
        cmd = {"action": "unknown_action", "value": 100}
        result = await minimal_adapter.handle_command(cmd)
        
        assert result["ok"] == False
        assert "unknown action" in result["reason"]
    
    @pytest.mark.asyncio
    async def test_handle_command_missing_id(self, minimal_adapter):
        """Test handling command with missing ID"""
        cmd = {"action": "write", "value": 100}
        result = await minimal_adapter.handle_command(cmd)
        
        assert result["ok"] == False
        assert "missing id/name" in result["reason"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

