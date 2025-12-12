# Issues Analysis from Logs

## Critical Errors

### 1. `NameError: name 'meter_energy_data' is not defined` in `/api/home/now`
**Location**: `solarhub/api_server.py:1096`
**Issue**: `meter_energy_data` is used but never defined before being passed to `aggregate_home_telemetry()`.
**Impact**: API endpoint `/api/home/now` fails with 500 error.
**Fix**: Define `meter_energy_data` dictionary or remove it from the function call if not needed.

### 2. `AttributeError: 'Meter' object has no attribute 'vendor'` in `/api/config`
**Location**: `solarhub/api_server.py:3485`
**Issue**: The `Meter` class doesn't have a `vendor` attribute, but the API tries to access it.
**Impact**: API endpoint `/api/config` fails with 500 error.
**Fix**: Either add `vendor` attribute to `Meter` class or remove it from the API response.

### 3. Inverters Not Found - `self.inverters` is Empty
**Location**: `solarhub/app.py:2571` and `solarhub/api_server.py` (multiple locations)
**Issue**: `self.inverters` list is empty when API tries to access inverters.
**Impact**: 
- Inverters 'powdrive2', 'senergy1', 'powdrive1' not found
- API endpoints that require inverter data fail
**Root Cause**: Inverters are initialized in `init()` method from `_hierarchy_inverters`, but may not be added to `self.inverters` list properly, or initialization may have failed silently.
**Fix**: Ensure inverters are properly added to `self.inverters` list during initialization.

## Warnings (Non-Critical)

### 4. `No cells_data available in battery telemetry`
**Location**: `solarhub/app.py:2772`
**Issue**: Battery telemetry doesn't always include `cells_data`.
**Impact**: Cell-level data not available for some battery packs.
**Status**: This is expected for some battery adapters that don't provide cell-level data.

### 5. `jkbms_bank_ble` Battery Pack Has No Data
**Location**: Multiple locations in logs
**Issue**: 
- `jkbms_bank_ble` connects successfully but returns no data
- `has_soc=False, has_voltage=False, has_power=False, devices=0`
**Impact**: Battery pack telemetry not available for this pack.
**Possible Causes**:
- Adapter connects but fails to read data
- Device not responding
- Configuration issue

### 6. Battery Adapter Reconnection Loop
**Location**: `solarhub/app.py` (battery polling)
**Issue**: `jkbms_bank_ble` adapter disconnects and reconnects repeatedly.
**Impact**: Intermittent data collection for this battery pack.
**Status**: Adapter successfully reconnects, but indicates connection stability issues.

## Telemetry Table Validation

### Tables to Check:
1. **energy_samples** - Inverter telemetry samples
2. **battery_bank_samples** - Battery pack telemetry samples
3. **meter_samples** - Meter telemetry samples
4. **battery_cells** - Battery cell data
5. **hourly_energy** - Aggregated hourly energy (inverter level)
6. **array_hourly_energy** - Aggregated hourly energy (array level)
7. **system_hourly_energy** - Aggregated hourly energy (system level)
8. **battery_bank_hourly** - Aggregated hourly energy (battery pack level)
9. **meter_hourly_energy** - Aggregated hourly energy (meter level)
10. **daily_energy** - Daily energy summaries (inverter level)
11. **array_daily_energy** - Daily energy summaries (array level)
12. **system_daily_energy** - Daily energy summaries (system level)
13. **battery_bank_daily** - Daily energy summaries (battery pack level)
14. **meter_daily_energy** - Daily energy summaries (meter level)

### Expected Data:
- **Inverters**: powdrive1, powdrive2, senergy1
- **Battery Packs**: battery1, jkbms_bank_ble, jkbms_bank
- **Meters**: grid_meter_1 (if configured)

### Validation Script:
Use `solarhub/validate_telemetry.py` to check:
- Table existence
- Data presence for each device
- Sample counts
- Latest sample timestamps
- Recent data (last 24 hours)
- Aggregation completeness

## Recommended Actions

1. **Fix Critical Errors** (Priority 1):
   - Fix `meter_energy_data` undefined variable
   - Fix `meter.vendor` attribute error
   - Fix inverter initialization to populate `self.inverters`

2. **Investigate Battery Issues** (Priority 2):
   - Debug why `jkbms_bank_ble` returns no data despite successful connection
   - Check adapter configuration and device communication
   - Investigate reconnection loop

3. **Run Telemetry Validation** (Priority 2):
   - Run `validate_telemetry.py` script to check all tables
   - Identify missing data
   - Verify aggregation is working correctly

4. **Monitor and Log** (Priority 3):
   - Add more detailed logging for inverter initialization
   - Log when inverters are added to `self.inverters`
   - Add validation checks after initialization

