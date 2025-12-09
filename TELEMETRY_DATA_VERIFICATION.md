# Telemetry Data Verification

## Fields Showing N/A or Unknown

### 1. Inverter Mode: "Unknown"
- **Expected:** "Normal", "Standby", "Self-check", "Alarm", or "Fault"
- **Where it's read:** `solarhub/adapters/powdrive.py` line 359-378
- **Where it's stored:** `tel.extra["inverter_mode"]` and `tel.inverter_mode`
- **API mapping:** `solarhub/api_server.py` line 282
- **Issue:** The API should check `extra.get("inverter_mode")` first

### 2. Battery Power: N/A
- **Expected:** Number (W)
- **Where it's read:** `solarhub/adapters/powdrive.py` line 273
- **Where it's stored:** `tel.batt_power_w` and `tel.extra["battery_power_w"]`
- **API mapping:** `solarhub/api_server.py` line 279
- **Issue:** API should check both `tel.get("batt_power_w")` and `extra.get("battery_power_w")`

### 3. Battery Temperature: N/A
- **Expected:** Number (°C)
- **Where it's read:** `solarhub/adapters/powdrive.py` line 455
- **Where it's stored:** `tel.extra["battery_temp_c"]`
- **API mapping:** `solarhub/api_server.py` line 279
- **Issue:** API correctly checks `extra.get("battery_temp_c")`

### 4. Device Model: N/A
- **Expected:** String like "Type-0005"
- **Where it's read:** `solarhub/adapters/powdrive.py` line 464
- **Where it's stored:** `tel.extra["device_model"]`
- **API mapping:** `solarhub/api_server.py` line 287
- **Issue:** API correctly checks `extra.get("device_model")`

### 5. Device Serial Number: N/A
- **Expected:** String (ASCII from registers 3-7)
- **Where it's read:** `solarhub/adapters/powdrive.py` line 459
- **Where it's stored:** `tel.extra["device_serial_number"]`
- **API mapping:** `solarhub/api_server.py` line 288
- **Issue:** API correctly checks `extra.get("device_serial_number")`

### 6. Rated Power: N/A
- **Expected:** Number (W, U32 from registers 20-21, scale 0.1)
- **Where it's read:** `solarhub/adapters/powdrive.py` line 461
- **Where it's stored:** `tel.extra["rated_power_w"]`
- **API mapping:** `solarhub/api_server.py` line 289
- **Issue:** API correctly checks `extra.get("rated_power_w")`

### 7. Grid L1/L2/L3 Power: N/A
- **Expected:** Numbers (W)
- **Where it's read:** `solarhub/adapters/powdrive.py` line 424-426
- **Where it's stored:** `tel.extra["grid_l1_power_w"]`, etc.
- **API mapping:** `solarhub/api_server.py` line 261-263
- **Issue:** API correctly checks `extra.get("grid_l1_power_w")`

### 8. Grid L1/L2/L3 Voltage: N/A
- **Expected:** Numbers (V)
- **Where it's read:** `solarhub/adapters/powdrive.py` line 427-429
- **Where it's stored:** `tel.extra["grid_l1_voltage_v"]`, etc.
- **API mapping:** `solarhub/api_server.py` line 264-266
- **Issue:** API correctly checks `extra.get("grid_l1_voltage_v")`

### 9. Load L1/L2/L3 Current: N/A
- **Expected:** Numbers (A) - computed from power/voltage
- **Where it's computed:** `solarhub/adapters/powdrive.py` line 417-422
- **Where it's stored:** `tel.extra["load_l1_current_a"]`, etc.
- **API mapping:** `solarhub/api_server.py` line 255-257
- **Issue:** API correctly checks `extra.get("load_l1_current_a")`

### 10. Total Energy: N/A
- **Expected:** Number (kWh)
- **Where it's read:** Not currently read - needs to be added
- **Issue:** Register map may not have this field, or it needs to be calculated

### 11. Peak Power: N/A
- **Expected:** Number (W)
- **Where it's read:** Not currently read - needs to be added
- **Issue:** Register map may not have this field

## Verification Steps

1. Check logs for "Powdrive poll" to see what's being read
2. Check logs for "API /api/now" to see what's being returned
3. Verify register map has all required registers
4. Check if reads are failing silently (exceptions caught)

## Fixed Issues

1. ✅ Battery power stored in `extra` with normalized value
2. ✅ Inverter mode stored in `extra["inverter_mode"]`
3. ✅ API checks both `tel` and `extra` for all fields
4. ✅ Added debug logging to trace data flow
5. ✅ Frontend `getValue` function checks both direct properties and `extra`

