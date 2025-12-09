# Effective Min SOC Scope Fix Summary

## ✅ **Issue Resolved: NameError: cannot access local variable 'effective_min_soc' where it is not associated with a value**

### **Problem:**
The SolarHub service was encountering a runtime error:
```
SmartScheduler error: cannot access local variable 'effective_min_soc' where it is not associated with a value
```

### **Root Cause:**
The `effective_min_soc` variable was being used in the `_detect_grid_availability` method call before it was defined. The variable was calculated later in the code (line 1251) but was being referenced earlier (line 1204).

### **The Issue:**
```python
# Line 1204: Trying to use effective_min_soc before it's defined
grid_available = self._detect_grid_availability(last_tel, tznow, soc_pct, effective_min_soc)

# Line 1251: effective_min_soc is defined here (too late!)
effective_min_soc = self.reliability.get_effective_min_soc(current_hour, forecast_uncertainty)
```

### **Fix Applied:**

#### **1. Moved Reliability System Calculation Earlier:**
Moved the entire reliability system block (including `effective_min_soc` calculation) to occur before the grid availability detection:

```python
# BEFORE: Reliability system was at line 1253
# AFTER: Reliability system moved to line 1203

# RELIABILITY SYSTEM: Hard 20% SOC constraint with dynamic cushion
current_hour = tznow.hour

# Assess forecast uncertainty (with accuracy feedback)
pv_forecast_values = list(site_pv_hourly.values())
load_forecast_values = list(site_load_hourly.values())
forecast_uncertainty = self.reliability.assess_forecast_uncertainty(pv_forecast_values, load_forecast_values)

# Override with accuracy-based uncertainty if available
accuracy_uncertainty = self._get_forecast_uncertainty_from_accuracy()
if accuracy_uncertainty.get('pv_confidence') != 'medium' or accuracy_uncertainty.get('load_confidence') != 'medium':
    # Create new ForecastUncertainty with accuracy-based confidence
    from solarhub.schedulers.reliability import ForecastUncertainty
    forecast_uncertainty = ForecastUncertainty(
        pv_confidence=accuracy_uncertainty.get('pv_confidence', 'medium'),
        load_confidence=accuracy_uncertainty.get('load_confidence', 'medium'),
        pv_p25=forecast_uncertainty.pv_p25,
        pv_p75=forecast_uncertainty.pv_p75,
        pv_p90=forecast_uncertainty.pv_p90,
        load_p25=forecast_uncertainty.load_p25,
        load_p75=forecast_uncertainty.load_p75,
        load_p90=forecast_uncertainty.load_p90
    )
    log.info(f"Updated forecast uncertainty based on accuracy: PV={forecast_uncertainty.pv_confidence}, Load={forecast_uncertainty.load_confidence}")

# Get effective minimum SOC (20% emergency reserve + dynamic cushion)
effective_min_soc = self.reliability.get_effective_min_soc(current_hour, forecast_uncertainty)

# Grid availability detection from telemetry and inverter registers with hysteresis
grid_available = self._detect_grid_availability(last_tel, tznow, soc_pct, effective_min_soc)
```

#### **2. Removed Duplicate Reliability System Block:**
Removed the duplicate reliability system block that was later in the code to prevent confusion and ensure single source of truth.

#### **3. Fixed Multiple Indentation Errors:**
During the code reorganization, several indentation errors were introduced and fixed:
- Line 838: Missing indentation after `try:` statement
- Line 1195: Missing indentation after `else:` statement  
- Line 1827: Missing indentation after `if` statement
- Line 1880: Missing indentation after `if` statement

### **Why This Was Critical:**
The `effective_min_soc` variable is essential for:
- **Grid Availability Detection**: The night-time logic in `_get_raw_grid_availability` needs to know the effective minimum SOC to determine if battery mode should be preferred
- **Reliability System**: The dynamic cushion calculation based on outage probability and forecast uncertainty
- **Threshold Management**: Ensuring emergency and critical thresholds never go below the effective minimum

### **Expected Result:**
The SolarHub service should now run without the `NameError` and properly execute the reliability system with:
- ✅ Dynamic SOC thresholds based on grid availability
- ✅ Night-time battery switching logic
- ✅ Forecast uncertainty assessment
- ✅ Grid instability detection

### **Verification:**
- ✅ No syntax errors
- ✅ Module imports successfully
- ✅ All variable dependencies resolved
- ✅ Indentation errors fixed

### **Files Modified:**
- `solarhub/schedulers/smart.py` - Moved reliability system calculation earlier and fixed indentation errors

The system should now properly calculate effective minimum SOC before using it in grid availability detection, enabling the full reliability system to function correctly.
