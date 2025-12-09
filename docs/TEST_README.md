# SmartScheduler Test Suite

This test suite allows you to test the SmartScheduler's `tick` method independently without connecting to real inverters. It uses mock data and prints all commands instead of executing them.

## Files

- `test_smart_scheduler.py` - Main test script with mock data and test scenarios
- `test_usage_example.py` - Example showing how to run custom test scenarios
- `TEST_README.md` - This documentation file

## Features

### Mock Data
- **MockInverterAdapter**: Provides realistic telemetry data
- **MockCommandQueue**: Captures and prints commands instead of executing them
- **MockHub**: Provides the interface expected by SmartScheduler

### Test Scenarios
1. **Normal Operation**: 75% SOC, good solar, normal load
2. **Low SOC**: 25% SOC to trigger charging behavior
3. **High SOC**: 95% SOC to trigger discharge behavior

### Command Output
The test prints all commands that would be sent to the inverter:
- TOU window settings (charge/discharge)
- Work mode changes
- Power limit settings
- SOC targets

## Usage

### Run All Tests
```bash
python test_smart_scheduler.py
```

### Run Custom Test
```python
from test_smart_scheduler import SmartSchedulerTester
import asyncio

async def my_test():
    tester = SmartSchedulerTester()
    
    # Custom scenario: Low solar, high load
    await tester.run_tick_test(
        "Custom Scenario",
        "Low solar with high load",
        modify_telemetry=lambda adapter: adapter.last_tel.update({
            'battery_soc': 40.0,
            'mppt1_power': 500.0,      # Low solar
            'phase_r_watt_of_load': 3000.0,  # High load
        })
    )

asyncio.run(my_test())
```

### Modify Test Data
You can modify the mock telemetry data in `MockInverterAdapter.poll()` to test different scenarios:

```python
# In MockInverterAdapter.poll()
self.last_tel = {
    'battery_soc': 75.0,        # Change SOC
    'mppt1_power': 2500.0,      # Change PV power
    'phase_r_watt_of_load': 1800.0,  # Change load power
    'inverter_mode': 'OnGrid mode',   # Change mode
    # ... other fields
}
```

## Expected Output

The test will show:
1. **Telemetry Summary**: Current SOC, PV, load, grid, and battery power
2. **Command Generation**: All commands that would be sent to the inverter
3. **Command Details**: Specific parameters for each command

Example output:
```
📊 CURRENT TELEMETRY:
   SOC: 75.0%
   PV Power: 2500W
   Load Power: 1800W
   Grid Power: 200W
   Battery Power: -1200W
   Inverter Mode: OnGrid mode

🔧 COMMANDS GENERATED (3 total):
    1. set_tou_window1
       Charge: 10:00-16:00
       Power: 2000W, Target SOC: 100%
    2. set_tou_discharge_window1
       Discharge: 18:00-22:00
       Power: 4000W, End SOC: 30%
    3. set_work_mode
       Mode: Self used mode
```

## Benefits

1. **No Hardware Required**: Test without real inverters
2. **Safe Testing**: Commands are printed, not executed
3. **Multiple Scenarios**: Test different conditions easily
4. **Debugging**: See exactly what commands would be sent
5. **Validation**: Verify TOU window logic and SOC targets

## Troubleshooting

If you get import errors, make sure you're running from the project root directory and that all dependencies are installed.

The test uses the same SmartScheduler class as the real system, so the logic should be identical to production behavior.