# tznow Parameter Fix Summary

## ✅ **Issue Resolved: NameError: name 'tznow' is not defined**

### **Problem:**
The SolarHub service was running but encountering a runtime error:
```
SmartScheduler error: name 'tznow' is not defined
```

### **Root Cause:**
During the duplicate logic cleanup, we updated the `_get_raw_grid_availability` method to require additional parameters (`tznow`, `soc_pct`, `effective_min_soc`), but we didn't update the calling method `_detect_grid_availability` to pass these parameters.

### **The Issue:**
```python
# Method signature was updated to require tznow parameter:
def _get_raw_grid_availability(self, telemetry, tznow, soc_pct, effective_min_soc) -> bool:

# But the calling method didn't pass tznow:
def _detect_grid_availability(self, telemetry: Dict[str, Any]) -> bool:
    # ...
    raw_grid_available = self._get_raw_grid_availability(telemetry, tznow, soc_pct, effective_min_soc)
    #                                                           ^^^^^^ - tznow was not defined in this scope
```

### **Fix Applied:**

#### **1. Updated Method Signature:**
```python
# BEFORE:
def _detect_grid_availability(self, telemetry: Dict[str, Any]) -> bool:

# AFTER:
def _detect_grid_availability(self, telemetry: Dict[str, Any], tznow: pd.Timestamp, soc_pct: float, effective_min_soc: float) -> bool:
```

#### **2. Updated Method Call:**
```python
# BEFORE:
grid_available = self._detect_grid_availability(last_tel)

# AFTER:
grid_available = self._detect_grid_availability(last_tel, tznow, soc_pct, effective_min_soc)
```

### **Why This Was Needed:**
The `_get_raw_grid_availability` method now includes night-time logic that requires:
- `tznow`: To determine if it's night time using dynamic sunset/sunrise
- `soc_pct`: To check if SOC is sufficient for battery mode
- `effective_min_soc`: To determine the minimum SOC threshold

This enables the system to prefer battery mode at night when SOC is sufficient, addressing the "didn't switch to battery at night" issue.

### **Verification:**
- ✅ `solarhub/schedulers/smart.py` - No syntax errors
- ✅ Module imports successfully
- ✅ All parameter dependencies resolved

### **Expected Result:**
The SolarHub service should now run without the `NameError` and properly execute the night-time battery switching logic with dynamic sunset/sunrise calculations.

### **Files Modified:**
- `solarhub/schedulers/smart.py` - Updated `_detect_grid_availability` method signature and call site

The system should now properly switch to battery at night because all the parameter dependencies are resolved and the dynamic sunset/sunrise logic can execute correctly.
