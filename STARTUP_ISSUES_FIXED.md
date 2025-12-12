# Startup Issues Fixed

## Issues Identified and Fixed

### 1. ✅ Fixed: Telemetry Validation Column Name Error
**Error**: `no such column: timestamp`
**Root Cause**: Validation script was using `timestamp` but tables use `ts`
**Fix**: Updated all queries in `validate_telemetry.py` to use `ts` instead of `timestamp`
**Files Changed**: `solarhub/validate_telemetry.py`

### 2. ✅ Fixed: Failover Adapter Connection Check
**Error**: `Battery adapter for jkbms_bank_ble not connected` (false positive)
**Root Cause**: Connection check was looking for `adapter.client` but `jkbms_tcpip` uses `raw_conn` (socket), not a modbus client
**Fix**: 
- Added check for `raw_conn` attribute (socket connection)
- Check socket connection status using `getpeername()` for TCP sockets
- Check `is_open` for serial ports
**Files Changed**: `solarhub/app.py`

### 3. ⚠️ Remaining: Inverters Have No Adapters
**Warning**: `Inverter powdrive2/senergy1/powdrive1 has no adapter configured, skipping`
**Root Cause**: Inverters in database don't have `adapter_id` set, or adapters aren't being loaded correctly
**Investigation Needed**:
- Check if `inverters` table has `adapter_id` values
- Check if `adapters` table has entries for these inverters
- Check if adapter linking logic in `HierarchyLoader` is working correctly
**Impact**: Inverters won't be initialized, no telemetry collection

### 4. ⚠️ Remaining: jkbms_bank_ble Returns No Data
**Issue**: Adapter connects successfully but returns `has_soc=False, has_voltage=False, has_power=False`
**Possible Causes**:
- Adapter connects but `poll()` method fails silently
- No data being received from RS485 gateway
- Data parsing issues
- Listening task not started or stopped
**Investigation Needed**:
- Check if `_listening_task` is running
- Check if data is being received from socket
- Check if frame parsing is working
- Add debug logging to `poll()` method

### 5. ⚠️ Remaining: Missing Daily Energy Tables
**Error**: Missing tables: `daily_energy`, `array_daily_energy`, `system_daily_energy`, `meter_daily_energy`
**Root Cause**: These tables may not be created during migration
**Investigation Needed**:
- Check if tables should exist or are optional
- Check migration scripts for daily energy table creation
- Update validation to mark these as optional if they're not required

## Validation Results Summary

The validation script now correctly:
- ✅ Uses correct column names (`ts` instead of `timestamp`)
- ✅ Checks all telemetry tables
- ✅ Reports missing data per device
- ✅ Checks recent data (last 24 hours)
- ✅ Validates aggregation tables

## Next Steps

1. **Investigate Inverter Adapter Issue**:
   - Query database: `SELECT inverter_id, adapter_id FROM inverters`
   - Query database: `SELECT * FROM adapters WHERE device_type = 'inverter'`
   - Check if adapters are being created during migration

2. **Investigate jkbms_tcpip Data Issue**:
   - Add debug logging to `poll()` method
   - Check if `_listening_task` is running
   - Verify RS485 gateway is sending data
   - Check frame parsing logic

3. **Check Daily Energy Tables**:
   - Determine if these tables are required or optional
   - Update migration if needed
   - Update validation script to handle optional tables

## Commands to Debug

```sql
-- Check inverter adapters
SELECT i.inverter_id, i.adapter_id, a.adapter_type, a.device_id
FROM inverters i
LEFT JOIN adapters a ON i.adapter_id = a.adapter_id;

-- Check battery pack adapters
SELECT bp.pack_id, bpa.adapter_id, a.adapter_type
FROM battery_packs bp
JOIN battery_pack_adapters bpa ON bp.pack_id = bpa.pack_id
JOIN adapters a ON bpa.adapter_id = a.adapter_id;

-- Check meter adapters
SELECT m.meter_id, m.adapter_id, a.adapter_type
FROM meters m
LEFT JOIN adapters a ON m.adapter_id = a.adapter_id;
```

