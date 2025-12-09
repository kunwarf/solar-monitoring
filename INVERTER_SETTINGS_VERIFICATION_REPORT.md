# Inverter Settings Writability Verification Report

## Summary

**Status**: ⚠️ **PASSED WITH WARNINGS** (80.5% verified)

- **Total Fields Checked**: 41
- **Successfully Verified**: 33 (80.5%)
- **Warnings**: 2
- **Issues**: 8

## Issues Found

### 1. Read-Only Registers Used for Settings (1 issue)
- `grid_frequency_hz`: This is correctly read-only as it's a measurement, not a setting. The UI should not allow editing this field.

### 2. Missing Register Mappings (7 issues)

These fields are handled differently in the API but the register IDs don't match:

1. **Power Settings (Powdrive)**: 
   - `max_grid_charger_power_w`, `max_charger_power_w`, `max_discharger_power_w`
   - **Status**: ✅ **WORKING AS DESIGNED**
   - **Explanation**: Powdrive doesn't have power registers - the API converts power to current and writes to current registers (`grid_charge_battery_current_a`, `battery_max_charge_current_a`, `battery_max_discharge_current_a`). This is correct behavior.

2. **Generator Peak Shaving Power**:
   - `generator_peak_shaving_power_kw` → `generator_peak_shaving_power_w`
   - **Status**: ⚠️ **NEEDS FIX**
   - **Issue**: API uses `generator_peak_shaving_power_w` but Powdrive register map has `gen_peak_shaving_power_w`
   - **Fix**: Update API to use `gen_peak_shaving_power_w` for Powdrive

3. **Max Sell/Solar Power**:
   - `max_sell_power_kw`, `max_solar_power_kw`
   - **Status**: ⚠️ **NEEDS FIX**
   - **Issue**: API uses `max_sell_power_kw`/`max_solar_power_kw` but Powdrive register map has `max_solar_sell_power_w`
   - **Fix**: API already converts to `max_solar_sell_power_w` for Powdrive, but verification script needs update

4. **Off-Grid Startup Capacity**:
   - `off_grid_start_up_battery_capacity_pct`
   - **Status**: ✅ **WORKING AS DESIGNED**
   - **Explanation**: Powdrive uses `battery_restart_capacity_pct` instead. API correctly maps this.

### 3. Read-Only UI Fields (2 warnings)

1. **`start_grid_charge_capacity_pct`**:
   - **Status**: ⚠️ **SHOULD BE WRITABLE**
   - **Issue**: Marked as `readOnly: true` in UI but register `grid_charging_start_capacity_pct` is writable
   - **Recommendation**: Remove `readOnly: true` from UI field definition

## Verified Writable Fields (33 fields)

All these fields are correctly mapped and writable:

### Grid Settings (6/7)
- ✅ `grid_voltage_high_v`
- ✅ `grid_voltage_low_v`
- ✅ `grid_frequency_high_hz`
- ✅ `grid_frequency_low_hz`
- ✅ `grid_peak_shaving` (bit field)
- ✅ `grid_peak_shaving_power_kw`
- ⚠️ `grid_frequency_hz` (correctly read-only - measurement, not setting)

### Battery Type (3/3)
- ✅ `battery_type`
- ✅ `battery_capacity_ah`
- ✅ `battery_operation` → `battery_mode_source`

### Battery Charging (9/12)
- ✅ `max_discharge_current_a`
- ✅ `max_charge_current_a`
- ✅ `max_grid_charge_current_a`
- ✅ `battery_float_charge_voltage_v`
- ✅ `battery_absorption_charge_voltage_v`
- ✅ `battery_equalization_charge_voltage_v`
- ✅ `max_grid_charger_power_w` (converted to current for Powdrive)
- ✅ `max_charger_power_w` (converted to current for Powdrive)
- ✅ `max_discharger_power_w` (converted to current for Powdrive)
- ⚠️ `max_generator_charge_current_a` (not in Powdrive register map - may be Senergy only)

### Work Mode (7/9)
- ✅ `grid_charge` (mapped differently for Powdrive vs Senergy)
- ✅ `generator_charge` → `generator_charge_enabled`
- ✅ `output_shutdown_capacity_pct` → `battery_shutdown_capacity_pct`
- ✅ `stop_battery_discharge_capacity_pct` → `battery_low_capacity_pct`
- ✅ `start_battery_discharge_capacity_pct` → `battery_restart_capacity_pct`
- ✅ `off_grid_mode` (bit field for Powdrive)
- ✅ `off_grid_start_up_battery_capacity_pct` (uses `battery_restart_capacity_pct` for Powdrive)
- ⚠️ `remote_switch` (correctly read-only)
- ⚠️ `force_generator_on` (correctly read-only)

### Work Mode Detail (5/7)
- ✅ `work_mode` → `limit_control_function`
- ✅ `solar_export_when_battery_full` → `solar_sell`
- ✅ `energy_pattern` → `solar_priority` / `energy_management_mode`
- ✅ `grid_trickle_feed_w` → `zero_export_power_w`
- ✅ `max_export_power_w`
- ⚠️ `max_sell_power_kw` (converted to `max_solar_sell_power_w` for Powdrive)
- ⚠️ `max_solar_power_kw` (converted to `max_solar_sell_power_w` for Powdrive)

### Auxiliary Settings (4/8)
- ✅ `generator_peak_shaving` (bit field)
- ✅ `generator_start_capacity_pct` → `generator_charging_start_capacity_pct`
- ✅ `generator_max_run_time_h`
- ✅ `generator_down_time_h`
- ⚠️ `generator_peak_shaving_power_kw` (register name mismatch)
- ⚠️ `generator_stop_capacity_pct` (not in Powdrive register map)
- ⚠️ `auxiliary_port` (correctly read-only)
- ⚠️ `generator_connected_to_grid_input` (correctly read-only)

## Recommendations

### High Priority
1. **Fix register name mismatch**: Update API to use `gen_peak_shaving_power_w` for Powdrive instead of `generator_peak_shaving_power_w`
2. **Make `start_grid_charge_capacity_pct` writable**: Remove `readOnly: true` from UI field definition

### Medium Priority
3. **Document adapter-specific behavior**: Power settings are converted to current for Powdrive - this is working correctly but should be documented
4. **Add validation**: Ensure all register writes are validated against register maps before attempting write

### Low Priority
5. **Improve error messages**: When a register write fails, provide more context about why (read-only, missing register, etc.)
6. **Add unit tests**: Create unit tests that verify all writable fields can be written and read back correctly

## Conclusion

The majority of inverter settings fields (80.5%) are correctly configured and writable. The remaining issues are mostly:
- Adapter-specific mappings that work correctly but need better documentation
- A few register name mismatches that need to be fixed
- One UI field that should be writable but is marked as read-only

The system is functional but would benefit from the fixes listed above.

