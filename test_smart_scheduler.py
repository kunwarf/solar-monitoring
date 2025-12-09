#!/usr/bin/env python3
"""Test script for SmartScheduler tick method with mock data."""

import asyncio
import logging
import sys
import os
from datetime import datetime, timezone
from typing import Dict, Any, List

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from solarhub.schedulers.smart import SmartScheduler
from solarhub.logging.logger import DataLogger
from solarhub.config import HubConfig, InverterConfig, InverterAdapterConfig, MqttConfig, PollingConfig, SmartConfig, PolicyConfig, ForecastConfig, SolarArrayParams

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

class MockInverterAdapter:
    """Mock inverter adapter with sample telemetry data."""
    
    def __init__(self, inverter_id: str):
        self.inverter_id = inverter_id
        self.regs = {}
        # Initialize with default telemetry data
        self.last_tel = {
            'device_model': 'SM-ONYX-UL-6KW',
            'device_serial_number': '2426-12950373PH',
            'inverter_mode': 'OnGrid mode',
            'error_code': 0,
            'mppt1_power': 2500.0,
            'mppt2_power': 0.0,
            'phase_r_watt_of_load': 1800.0,
            'phase_r_watt_of_grid': 200.0,
            'battery_power': -1200.0,
            'battery_soc': 75.0,
            'battery_voltage': 50.4,
            'battery_current': -23.8,
            'battery_temperature': 25.0,
            'today_energy': 15.2,
            'total_energy': 1250.5,
            'today_peak_power': 3200.0,
            'today_load_energy': 12.8,
            'accumulated_energy_of_load': 850.2,
            'today_import_energy': 2.1,
            'today_export_energy': 0.5,
            'inner_temperature': 45.0,
            'charge_frequency_1': 1,
            'charge_start_time_1': '10:00',
            'charge_end_time_1': '16:00',
            'charge_power_1': 2000,
            'charger_end_soc_1': 100,
            'discharge_frequency_1': 1,
            'discharge_start_time_1': '17:00',
            'discharge_end_time_1': '23:00',
            'discharge_power_1': 3000,
            'discharge_end_soc_1': 30,
            'discharge_frequency_2': 1,
            'discharge_start_time_2': '23:00',
            'discharge_end_time_2': '05:00',
            'discharge_power_2': 2000,
            'discharge_end_soc_2': 25,
            'hybrid_work_mode': 1,
            'grid_charge': 1,
            'maximum_grid_charger_power': 2000,
            'capacity_of_grid_charger_end': 100,
            'maximum_charger_power': 3000,
            'capacity_of_charger_end_soc_': 100,
            'maximum_discharger_power': 5000,
            'capacity_of_discharger_end_eod_': 20,
            'off_grid_mode': 1,
            'off_grid_start_up_battery_capacity': 30,
            # Additional standardized telemetry fields
            'grid_power_w': 200.0,  # Grid power (positive = import, negative = export)
            'pv_power_w': 2500.0,   # Total PV power generation
            'load_power_w': 1800.0, # Total load power consumption
            'batt_soc_pct': 75.0,   # Battery state of charge percentage
            'batt_voltage_v': 50.4, # Battery voltage in volts
            'batt_current_a': -23.8, # Battery current in amps (negative = charging)
            'batt_power_w': -1200.0, # Battery power in watts (negative = charging)
            'inverter_temp_c': 45.0, # Inverter temperature in Celsius
            'grid_import_wh': 2100.0, # Grid import energy in watt-hours (today)
            'grid_export_wh': 500.0,  # Grid export energy in watt-hours (today)
        }
        
    def poll(self):
        """Return mock telemetry data."""
        return self.last_tel
        
    async def read_all_registers(self):
        """Mock read_all_registers method for fallback telemetry access."""
        return self.last_tel

class MockCommandQueue:
    """Mock command queue that prints commands instead of executing them."""
    
    def __init__(self):
        self.commands = []
        
    def enqueue_command(self, inverter_id: str, command: Dict[str, Any]) -> bool:
        """Mock command enqueue - just print the command."""
        log.info(f"🔧 COMMAND QUEUED for {inverter_id}: {command}")
        self.commands.append((inverter_id, command))
        return True
    
    def get_commands(self) -> List[tuple]:
        """Get all queued commands."""
        return self.commands.copy()
    
    def clear_commands(self):
        """Clear all commands."""
        self.commands.clear()

class MockMqtt:
    """Mock MQTT client."""
    def __init__(self):
        pass
    
    def sub(self, topic, callback):
        """Mock subscribe - do nothing."""
        pass
    
    def pub(self, topic, payload, retain=False):
        """Mock publish - do nothing."""
        pass

class MockHub:
    """Mock hub class for SmartScheduler."""
    
    def __init__(self):
        self.cfg = self._create_mock_config()
        self.inverters = [self._create_mock_inverter()]
        self.logger = DataLogger()
        self.mqtt = MockMqtt()
        
    def _create_mock_config(self) -> HubConfig:
        """Create mock configuration."""
        return HubConfig(
            mqtt=MqttConfig(
                host="localhost",
                port=1883,
                username="test",
                password="test",
                base_topic="solar/fleet"
            ),
            polling=PollingConfig(interval_secs=5.0),
            inverters=[InverterConfig(
                id="senergy1",
                name="Test Inverter",
                adapter=InverterAdapterConfig(
                    type="senergy",
                    unit_id=1,
                    transport="rtu",
                    serial_port="/dev/ttyUSB0",
                    baudrate=9600
                ),
                solar=[SolarArrayParams(
                    pv_dc_kw=6.0,
                    tilt_deg=20.0,
                    azimuth_deg=180.0,
                    perf_ratio=0.8
                )]
            )],
            smart=SmartConfig(
                policy=PolicyConfig(
                    enabled=True,
                    target_soc_pct=100,
                    max_battery_soc_pct=98,  # Target SOC for charging
                    solar_charge_deadline_hours_before_sunset=2,  # 2 hours before sunset
                    target_full_before_sunset=True,
                    overnight_min_soc_pct=20,
                    blackout_reserve_soc_pct=20,
                    emergency_soc_threshold_grid_available_pct=20,
                    emergency_soc_threshold_grid_unavailable_pct=30,
                    critical_soc_threshold_pct=25,
                    night_load_estimate_kw=1.5,
                    reliability_buffer_pct=5.0,
                    max_grid_charge_power_w=2000,
                    max_discharge_power_w=5000
                ),
                forecast=ForecastConfig(
                    provider="openweather",
                    api_key="test_key",
                    lat=31.5497,
                    lon=74.3436,
                    tz="Asia/Karachi"
                )
            )
        )
    
    def _create_mock_inverter(self):
        """Create mock inverter runtime."""
        class MockInverterRuntime:
            def __init__(self):
                self.cfg = InverterConfig(
                    id="senergy1",
                    name="Test Inverter",
                    adapter=InverterAdapterConfig(
                        type="senergy",
                        unit_id=1,
                        transport="rtu",
                        serial_port="/dev/ttyUSB0",
                        baudrate=9600
                    ),
                    solar=[SolarArrayParams(
                        pv_dc_kw=6.0,
                        tilt_deg=20.0,
                        azimuth_deg=180.0,
                        perf_ratio=0.8
                    )]
                )
                self.adapter = MockInverterAdapter("senergy1")
                
        return MockInverterRuntime()

class SmartSchedulerTester:
    """Test class for SmartScheduler with mock data."""
    
    def __init__(self):
        self.hub = MockHub()
        self.command_queue = MockCommandQueue()
        self.hub.command_queue = self.command_queue
        
        # Initialize smart scheduler
        self.smart_scheduler = SmartScheduler(self.hub.logger, self.hub)
        self.smart_scheduler.hub.command_queue = self.command_queue
        
        # Monkey patch the scheduler to use test time when available
        original_tick = self.smart_scheduler.tick
        async def patched_tick():
            # Use test time if available, otherwise use current time
            if hasattr(self.smart_scheduler, '_test_tznow'):
                import pandas as pd
                # Temporarily replace the timezone-aware now function
                original_now = pd.Timestamp.now
                def test_now(tz=None):
                    if tz is None:
                        return self.smart_scheduler._test_tznow
                    return self.smart_scheduler._test_tznow.tz_convert(tz)
                pd.Timestamp.now = test_now
                try:
                    await original_tick()
                finally:
                    pd.Timestamp.now = original_now
            else:
                await original_tick()
        
        self.smart_scheduler.tick = patched_tick
        
        # Store original timezone for restoration
        self.original_tz = None
        
        log.info("SmartSchedulerTester initialized with mock data")
    
    def set_test_time(self, hour: int, minute: int = 0):
        """Set the test time for the scheduler (simulates different times of day)."""
        import pandas as pd
        from datetime import datetime
        
        # Create a test datetime with the specified hour and minute
        test_date = datetime(2025, 10, 15, hour, minute, 0)
        test_tz = pd.Timestamp(test_date, tz='Asia/Karachi')
        
        # Mock the timezone-aware timestamp for the scheduler
        self.smart_scheduler._test_tznow = test_tz
        
        print(f"🕐 Test time set to: {test_tz.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        
    def restore_time(self):
        """Restore normal time behavior."""
        if hasattr(self.smart_scheduler, '_test_tznow'):
            delattr(self.smart_scheduler, '_test_tznow')
            print(f"🕐 Test time restored to current time")
        
    def print_telemetry_summary(self):
        """Print current telemetry data summary."""
        tel = self.hub.inverters[0].adapter.last_tel
        print(f"\nCURRENT TELEMETRY:")
        print(f"   SOC: {tel.get('batt_soc_pct', tel.get('battery_soc', 0)):.1f}%")
        print(f"   PV Power: {tel.get('pv_power_w', tel.get('mppt1_power', 0)):.0f}W")
        print(f"   Load Power: {tel.get('load_power_w', tel.get('phase_r_watt_of_load', 0)):.0f}W")
        print(f"   Grid Power: {tel.get('grid_power_w', tel.get('phase_r_watt_of_grid', 0)):.0f}W")
        print(f"   Battery Power: {tel.get('batt_power_w', tel.get('battery_power', 0)):.0f}W")
        print(f"   Battery Voltage: {tel.get('batt_voltage_v', tel.get('battery_voltage', 0)):.1f}V")
        print(f"   Battery Current: {tel.get('batt_current_a', tel.get('battery_current', 0)):.1f}A")
        print(f"   Inverter Temp: {tel.get('inverter_temp_c', tel.get('inner_temperature', 0)):.1f}°C")
        print(f"   Inverter Mode: {tel.get('inverter_mode', 'Unknown')}")
        
    def print_commands_summary(self):
        """Print summary of all commands generated."""
        commands = self.command_queue.get_commands()
        if not commands:
            print(f"\nNO COMMANDS GENERATED")
            return
            
        print(f"\nCOMMANDS GENERATED ({len(commands)} total):")
        for i, (inverter_id, command) in enumerate(commands, 1):
            action = command.get('action', 'unknown')
            print(f"   {i:2d}. {action}")
            
            if action.startswith('set_tou_'):
                if 'charge' in action:
                    print(f"       Charge: {command.get('chg_start', 'N/A')}-{command.get('chg_end', 'N/A')}")
                    print(f"       Power: {command.get('charge_power_w', 0)}W, Target SOC: {command.get('charge_end_soc', 0)}%")
                elif 'discharge' in action:
                    print(f"       Discharge: {command.get('dch_start', 'N/A')}-{command.get('dch_end', 'N/A')}")
                    print(f"       Power: {command.get('discharge_power_w', 0)}W, End SOC: {command.get('discharge_end_soc', 0)}%")
            elif action == 'set_work_mode':
                print(f"       Mode: {command.get('mode', 'N/A')}")
                
    async def run_tick_test(self, scenario_name: str, description: str, 
                          modify_telemetry: callable = None, test_hour: int = None, test_minute: int = 0):
        """Run a single tick test with the given scenario."""
        print(f"\n{'='*60}")
        print(f"TEST SCENARIO: {scenario_name}")
        print(f"Description: {description}")
        print(f"{'='*60}")
        
        # Clear previous commands
        self.command_queue.clear_commands()
        
        # Set test time if specified
        if test_hour is not None:
            self.set_test_time(test_hour, test_minute)
        
        # Modify telemetry if callback provided
        if modify_telemetry:
            modify_telemetry(self.hub.inverters[0].adapter)
            
        # Print current telemetry
        self.print_telemetry_summary()
        
        # Run the tick method
        print(f"\nRunning SmartScheduler.tick()...")
        try:
            await self.smart_scheduler.tick()
            print(f"Tick completed successfully")
        except Exception as e:
            print(f"Tick failed with error: {e}")
            import traceback
            traceback.print_exc()
            
        # Print commands generated
        self.print_commands_summary()
        
        # Restore time if it was set
        if test_hour is not None:
            self.restore_time()
        
    async def run_all_tests(self):
        """Run multiple test scenarios."""
        print(f"Starting SmartScheduler Test Suite")
        print(f"Test time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Test 1: Normal operation
        await self.run_tick_test(
            "Normal Operation - Good SOC",
            "Test with 75% SOC, good solar generation, normal load"
        )
        
        # Test 2: Low SOC scenario
        await self.run_tick_test(
            "Low SOC Scenario",
            "Test with 25% SOC to trigger charging behavior",
            modify_telemetry=lambda adapter: adapter.last_tel.update({
                'battery_soc': 25.0,
                'battery_power': 500.0,
                'mppt1_power': 800.0,
                'phase_r_watt_of_load': 2000.0,
                # Update standardized fields
                'batt_soc_pct': 25.0,
                'batt_power_w': 500.0,
                'pv_power_w': 800.0,
                'load_power_w': 2000.0,
            })
        )
        
        # Test 3: High SOC scenario
        await self.run_tick_test(
            "High SOC Scenario", 
            "Test with 95% SOC to trigger discharge behavior",
            modify_telemetry=lambda adapter: adapter.last_tel.update({
                'battery_soc': 95.0,
                'battery_power': -2000.0,
                'mppt1_power': 3000.0,
                'phase_r_watt_of_load': 1500.0,
                # Update standardized fields
                'batt_soc_pct': 95.0,
                'batt_power_w': -2000.0,
                'pv_power_w': 3000.0,
                'load_power_w': 1500.0,
            })
        )
        
        # Test 4: Solar-first charging scenario (2 hours before sunset)
        await self.run_tick_test(
            "Solar-First Charging Scenario",
            "Test solar-first charging: 77% SOC, hour 15, sunset 17, target 98%",
            modify_telemetry=lambda adapter: adapter.last_tel.update({
                'battery_soc': 77.0,
                'battery_power': 1000.0,  # Charging
                'mppt1_power': 2000.0,    # Good solar generation
                'phase_r_watt_of_load': 500.0,  # Moderate load
                'phase_r_watt_of_grid': 0.0,    # No grid import/export
                # Update standardized fields
                'batt_soc_pct': 77.0,
                'batt_power_w': 1000.0,
                'pv_power_w': 2000.0,
                'load_power_w': 500.0,
                'grid_power_w': 0.0,
            }),
            test_hour=15  # 3 PM - 2 hours before sunset
        )
        
        # Test 5: Post-solar-deadline discharge scenario (after hour 15)
        await self.run_tick_test(
            "Post-Solar-Deadline Discharge Scenario",
            "Test discharge after solar deadline: 98% SOC, hour 16, sunset 17",
            modify_telemetry=lambda adapter: adapter.last_tel.update({
                'battery_soc': 98.0,
                'battery_power': -1500.0,  # Discharging
                'mppt1_power': 500.0,      # Low solar (evening)
                'phase_r_watt_of_load': 2000.0,  # High evening load
                'phase_r_watt_of_grid': 0.0,     # No grid import/export
                # Update standardized fields
                'batt_soc_pct': 98.0,
                'batt_power_w': -1500.0,
                'pv_power_w': 500.0,
                'load_power_w': 2000.0,
                'grid_power_w': 0.0,
            }),
            test_hour=16  # 4 PM - 1 hour before sunset, after solar deadline
        )
        
        # Test 6: Original log scenario - exact conditions from the user's log
        await self.run_tick_test(
            "Original Log Scenario - Solar-First Charging",
            "Exact scenario from log: 77% SOC, hour 15, sunset 17, target 98%, net_until_deadline should be corrected",
            modify_telemetry=lambda adapter: adapter.last_tel.update({
                'battery_soc': 77.0,
                'battery_power': 1000.0,  # Charging
                'mppt1_power': 1003.0,    # Exact value from log
                'phase_r_watt_of_load': 311.4,  # Exact value from log
                'phase_r_watt_of_grid': 0.0,    # No grid import/export
                # Update standardized fields
                'batt_soc_pct': 77.0,
                'batt_power_w': 1000.0,
                'pv_power_w': 1003.0,
                'load_power_w': 311.4,
                'grid_power_w': 0.0,
            }),
            test_hour=15  # 3 PM - exact time from log
        )
        
        # Test 7: Charge Power Calculation Fix - Mid-Solar Window Scenario
        await self.run_tick_test(
            "Charge Power Calculation Fix - Mid-Solar Window",
            "Test the fix: 79% SOC at 14:30, solar window 09:00-15:00, need 3.4kWh in 0.5h remaining = 6.8kW required",
            modify_telemetry=lambda adapter: adapter.last_tel.update({
                'battery_soc': 79.0,      # 79% SOC (14.22kWh)
                'battery_power': -554.4,  # Charging at 554W
                'mppt1_power': 1538.0,    # Good solar generation
                'phase_r_watt_of_load': 566.0,  # Moderate load
                'phase_r_watt_of_grid': -230.0, # Grid export
                # Update standardized fields
                'batt_soc_pct': 79.0,
                'batt_power_w': -554.4,
                'pv_power_w': 1538.0,
                'load_power_w': 566.0,
                'grid_power_w': -230.0,
            }),
            test_hour=14,  # 2:30 PM - in the middle of solar window
            test_minute=30
        )
        
        # Test 8: Charge Power Calculation Fix - Early Solar Window Scenario
        await self.run_tick_test(
            "Charge Power Calculation Fix - Early Solar Window",
            "Test the fix: 75% SOC at 10:00, solar window 09:00-15:00, need 4.1kWh in 5h remaining = 820W required",
            modify_telemetry=lambda adapter: adapter.last_tel.update({
                'battery_soc': 75.0,      # 75% SOC (13.5kWh)
                'battery_power': -800.0,  # Charging at 800W
                'mppt1_power': 2000.0,    # Good solar generation
                'phase_r_watt_of_load': 600.0,  # Moderate load
                'phase_r_watt_of_grid': -600.0, # Grid export
                # Update standardized fields
                'batt_soc_pct': 75.0,
                'batt_power_w': -800.0,
                'pv_power_w': 2000.0,
                'load_power_w': 600.0,
                'grid_power_w': -600.0,
            }),
            test_hour=10  # 10:00 AM - early in solar window
        )
        
        print(f"\nAll tests completed!")

async def main():
    """Main test function."""
    try:
        tester = SmartSchedulerTester()
        await tester.run_all_tests()
    except Exception as e:
        log.error(f"Test suite failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
