#!/usr/bin/env python3
"""
Example usage of the SmartScheduler test script.
This shows how to run individual test scenarios.
"""

import asyncio
from test_smart_scheduler import SmartSchedulerTester

async def run_custom_test():
    """Run a custom test scenario."""
    
    # Initialize the tester
    tester = SmartSchedulerTester()
    
    # Test scenario: Evening with high load
    await tester.run_tick_test(
        "Evening High Load Scenario",
        "Test during evening hours with high load to trigger discharge windows",
        modify_telemetry=lambda adapter: adapter.last_tel.update({
            'battery_soc': 80.0,
            'mppt1_power': 200.0,        # Low solar (evening)
            'phase_r_watt_of_load': 2500.0,  # High evening load
            'phase_r_watt_of_grid': 500.0,   # Some grid import
            'battery_power': -800.0,     # Moderate charging
        })
    )
    
    # Test scenario: Night with no solar
    await tester.run_tick_test(
        "Night No Solar Scenario",
        "Test during night hours with no solar generation",
        modify_telemetry=lambda adapter: adapter.last_tel.update({
            'battery_soc': 60.0,
            'mppt1_power': 0.0,          # No solar
            'phase_r_watt_of_load': 1800.0,  # Night load
            'phase_r_watt_of_grid': 300.0,   # Grid support
            'battery_power': 1200.0,     # Discharging
        })
    )

if __name__ == "__main__":
    asyncio.run(run_custom_test())
