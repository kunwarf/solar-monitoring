# Scheduler Fixes Summary

## Issues Fixed

### 1. ✅ Periodic Device Discovery Disabled

**Problem**: Discovery was running every 60 minutes regardless of need.

**Solution**: 
- Disabled periodic discovery loop
- Discovery now only runs:
  1. On startup (if `scan_on_startup` enabled)
  2. When devices disconnect (via recovery manager retry mechanism)

**Changes**:
- Removed `_discovery_task` creation in `run()`
- `_discovery_loop()` method kept for backward compatibility but returns immediately
- Added logging to explain discovery behavior

**Files Modified**: `solarhub/app.py`

---

### 2. ✅ Billing Scheduler Enhanced Logging

**Problem**: Billing scheduler might not be running but no diagnostic logs.

**Solution**:
- Added detailed debug logging to show why billing job runs or doesn't run
- Logs current time, target time, last run date
- Logs when billing config is found/not found

**Changes**:
- Added debug logs when billing job is not running (shows why)
- Added info log when billing config is found
- Enhanced error logging

**Files Modified**: `solarhub/app.py` (lines 775-804)

**Billing Scheduler Behavior**:
- Runs daily at 00:30 local time
- Checks every hour
- Only runs once per day
- Requires billing config to be present

---

### 3. ✅ Energy Calculator Hourly Execution Fixed

**Problem**: Energy calculator was tied to polling loop, so if polling was suspended or devices disconnected, energy calculation wouldn't run.

**Solution**:
- Created separate background task `_energy_calculator_hourly_loop()`
- Runs independently every hour at :00 minutes
- Checks every 60 seconds to catch hour boundary accurately
- Removed from polling loop

**Changes**:
- Created `_energy_calculator_hourly_loop()` background task
- Modified `_execute_energy_calculator()` to accept optional `hour_start` parameter
- Removed `energy_calc_tick` counter from polling loop
- Energy calculator now runs independently

**Files Modified**: `solarhub/app.py`

**Energy Calculator Behavior**:
- Runs every hour at :00 minutes (e.g., 10:00, 11:00, 12:00)
- Processes previous hour's data
- Runs independently of polling loop
- Continues even if devices are disconnected

---

## Background Tasks Now Running

1. **Billing Scheduler** (`_billing_scheduler_loop`)
   - Runs daily at 00:30 local time
   - Checks every hour
   - Independent background task

2. **Energy Calculator** (`_energy_calculator_hourly_loop`)
   - Runs every hour at :00 minutes
   - Checks every 60 seconds
   - Independent background task

3. **Device Recovery** (`_recovery_loop`)
   - Checks every minute for devices ready to retry
   - Triggers discovery when devices reconnect

4. **Polling Loop** (`run()`)
   - Main polling loop for device telemetry
   - Smart scheduler tick
   - No longer handles energy calculation

---

## Logging Improvements

### Billing Scheduler Logs:
- `"Starting billing scheduler background task"` - Task started
- `"Billing scheduler: Waiting for 00:30. Current time: XX:XX, target: 00:30"` - Waiting for time
- `"Billing scheduler: Already ran for YYYY-MM-DD"` - Already ran today
- `"Running daily billing job for YYYY-MM-DD at XX:XX"` - Job starting
- `"Billing config found, executing daily billing job"` - Config found
- `"Billing configuration not found"` - Config missing

### Energy Calculator Logs:
- `"Starting energy calculator hourly background task"` - Task started
- `"Running energy calculator for hour: YYYY-MM-DD HH:00:00"` - Processing hour
- `"Energy calculator completed successfully for hour: YYYY-MM-DD HH:00:00"` - Success

### Discovery Logs:
- `"Device discovery periodic scan disabled - discovery runs only on startup or device disconnection"` - Periodic disabled

---

## Testing Recommendations

1. **Billing Scheduler**:
   - Check logs for "Starting billing scheduler background task"
   - Wait until 00:30 and check for "Running daily billing job"
   - Verify billing config is present in config.yaml

2. **Energy Calculator**:
   - Check logs for "Starting energy calculator hourly background task"
   - Wait until :00 minutes and check for "Running energy calculator for hour"
   - Verify hourly_energy table is populated

3. **Discovery**:
   - Verify no periodic discovery logs after startup
   - Verify discovery runs on startup (if enabled)
   - Verify discovery runs when devices disconnect (via recovery)

---

## Configuration

No configuration changes needed. All fixes are backward compatible.

**Discovery**: Still respects `discovery.scan_on_startup` setting
**Billing**: Still requires `billing` section in config.yaml
**Energy Calculator**: No configuration needed, runs automatically

