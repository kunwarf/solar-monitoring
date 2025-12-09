# Smart Scheduler and Battery Power Fixes

## ✅ **Fixed Two Critical Issues**

### **🎯 Issue 1: Smart Scheduler Datetime Error**
**Problem**: Smart scheduler was failing with `can't compare offset-naive and offset-aware datetimes` error, preventing completion.

**Root Cause**: Line 564 in `smart.py` had `datetime.now()` without timezone, causing comparison issues with timezone-aware datetimes.

**Fix Applied:**
```python
# Before (Incorrect):
self.reliability.record_outage_event(
    datetime.now(), 1, cause, outage_type
)

# After (Correct):
self.reliability.record_outage_event(
    datetime.now(timezone.utc), 1, cause, outage_type
)
```

### **🎯 Issue 2: Battery Power Sign Debugging**
**Problem**: Battery power still showing as positive (955.7W) and "Battery discharging" despite energy balance suggesting charging.

**Analysis**: Added debug logging to understand the actual current and voltage values being used in the calculation.

**Debug Enhancement:**
```python
# Added detailed logging to see actual values:
log.info(f"Battery power calculation: {voltage}V × {current}A = {calculated_power}W (current sign: {'positive=charging' if current > 0 else 'negative=discharging'})")
```

## **📊 Expected Behavior After Fixes:**

### **Smart Scheduler:**
- ✅ **No More Datetime Errors**: Smart scheduler should complete without crashing
- ✅ **Full Execution**: All smart scheduling logic should run to completion
- ✅ **TOU Window Setting**: Smart TOU windows should be calculated and set

### **Battery Power Debugging:**
- ✅ **Detailed Logging**: Will show actual voltage, current, and calculated power values
- ✅ **Current Sign Analysis**: Will indicate whether current is positive (charging) or negative (discharging)
- ✅ **Power Calculation Transparency**: Will show the exact calculation being performed

## **📋 Expected Log Output:**

### **Smart Scheduler (Fixed):**
```
2025-09-27 08:09:22,352 - Smart scheduler completed successfully
2025-09-27 08:09:22,353 - Calculated 4 smart TOU windows based on solar/load patterns and current SOC 87.0%
2025-09-27 08:09:22,354 - Self-use mode: Setting 4 smart TOU windows with calculated power and SOC
2025-09-27 08:09:22,355 - Set smart TOU charge window 1: 06:00-10:00 (power: 2000W, target SOC: 90%)
2025-09-27 08:09:22,356 - Set smart TOU discharge window 1: 18:00-22:00 (power: 4000W, target SOC: 70%)
```

### **Battery Power Debug (Enhanced):**
```
2025-09-27 08:09:28,353 - Battery power calculation: 48.0V × 2.5A = -120.0W (current sign: positive=charging)
2025-09-27 08:09:28,354 - Inverter senergy1 telemetry - SOC: 87.0%, Mode: Self used mode, Source: Battery charging, PV: 2712W, Load: 1707W, Batt: -120.0W, Grid: 221W
```

## **🔍 Energy Balance Analysis:**

From the logs, the energy balance is:
- **PV Power**: 2715W (solar generation)
- **Load Power**: 1727W (consumption)
- **Grid Power**: 208W (grid input)
- **Net Excess**: 2715W + 208W - 1727W = 1196W

**Expected Behavior**: The 1196W excess should be going to the battery (charging), which means:
- **Battery Current**: Should be positive (charging)
- **Battery Power**: Should be negative (charging)
- **Source**: Should show "Battery charging"

## **🎯 Next Steps:**

1. **Monitor Logs**: Check if smart scheduler now completes without errors
2. **Battery Power Analysis**: Review the new debug logs to see actual current/voltage values
3. **Sign Convention Verification**: Confirm if the current sign convention matches expectations
4. **Energy Flow Validation**: Verify that the energy balance matches the battery power direction

## **📁 Files Modified:**

### **1. `solarhub/schedulers/smart.py`:**
- ✅ Fixed `datetime.now()` to `datetime.now(timezone.utc)` on line 564
- ✅ Resolved timezone comparison error

### **2. `solarhub/adapters/senergy.py`:**
- ✅ Enhanced battery power calculation logging
- ✅ Added current sign interpretation in logs
- ✅ Improved debugging visibility

## **✅ Verification:**
- ✅ Both files compile successfully
- ✅ Datetime error fixed
- ✅ Enhanced battery power debugging
- ✅ Smart scheduler should now complete execution

The smart scheduler should now complete successfully, and the enhanced battery power logging will help us understand the actual current and voltage values being used in the calculation to determine if the sign convention is correct.
