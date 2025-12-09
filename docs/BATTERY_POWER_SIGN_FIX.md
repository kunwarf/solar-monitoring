# Battery Power Sign Convention Fix

## ✅ **Fixed Battery Power Sign Interpretation**

### **🎯 Problem Identified:**
The battery was actually **charging** (positive current flowing into the battery), but the system was interpreting it as **discharging** because of incorrect sign convention in the battery power calculation.

**Evidence from logs:**
```
2025-09-27 08:09:01,269 - Battery power discrepancy: calculated=955.7W, raw=429495727.6W, diff=100.0%
2025-09-27 08:09:01,270 - Inverter senergy1 telemetry - SOC: 87.0%, Mode: Self used mode, Source: Battery discharging, PV: 2718W, Load: 1704W, Batt: 955.7W, Grid: 192
```

**Issue**: Battery power was showing as **+955.7W** (positive), which the app interpreted as "Battery discharging", but the battery was actually **charging**.

### **🔧 Root Cause:**
The battery power calculation was using the wrong sign convention:

**Current Convention (Incorrect):**
- Positive current (charging) → Positive power → Interpreted as "discharging"
- Negative current (discharging) → Negative power → Interpreted as "charging"

**Correct Convention (Fixed):**
- Positive current (charging) → Negative power → Interpreted as "charging" ✅
- Negative current (discharging) → Positive power → Interpreted as "discharging" ✅

### **🔧 Fix Applied:**

**Before (Incorrect):**
```python
# Calculate power from V*I with correct sign convention
calculated_power = voltage * current  # Wrong sign convention
```

**After (Correct):**
```python
# Calculate power from V*I with correct sign convention
# Based on user feedback: positive current = charging, negative current = discharging
# For power convention: positive power = discharging (power flowing out), negative power = charging (power flowing in)
# So we need to invert the sign: charging (positive current) → negative power, discharging (negative current) → positive power
calculated_power = -(voltage * current)  # Correct sign convention
```

### **📊 How It Works Now:**

#### **Battery Current Sign Convention:**
- **Positive Current**: Current flowing INTO the battery (charging)
- **Negative Current**: Current flowing OUT of the battery (discharging)

#### **Battery Power Sign Convention:**
- **Positive Power**: Power flowing OUT of the battery (discharging)
- **Negative Power**: Power flowing INTO the battery (charging)

#### **App Interpretation Logic:**
```python
if tel.batt_power_w > 50:
    power_source = "Battery discharging"  # Positive power = discharging
elif tel.batt_power_w < -50:
    power_source = "Battery charging"     # Negative power = charging
```

### **🎯 Example Scenarios:**

#### **Scenario 1: Battery Charging**
- **Battery Current**: +2.5A (positive = charging)
- **Battery Voltage**: 48.0V
- **Calculated Power**: -(48.0 × 2.5) = **-120.0W** (negative = charging)
- **App Interpretation**: "Battery charging" ✅

#### **Scenario 2: Battery Discharging**
- **Battery Current**: -3.0A (negative = discharging)
- **Battery Voltage**: 47.5V
- **Calculated Power**: -(47.5 × (-3.0)) = **+142.5W** (positive = discharging)
- **App Interpretation**: "Battery discharging" ✅

### **📋 Expected Log Output (After Fix):**

#### **When Battery is Charging:**
```
Battery power calculated: 48.0V × 2.5A = -120.0W
Inverter senergy1 telemetry - SOC: 87.0%, Mode: Self used mode, Source: Battery charging, PV: 2718W, Load: 1704W, Batt: -120.0W, Grid: 192
```

#### **When Battery is Discharging:**
```
Battery power calculated: 47.5V × -3.0A = 142.5W
Inverter senergy1 telemetry - SOC: 87.0%, Mode: Self used mode, Source: Battery discharging, PV: 2718W, Load: 1704W, Batt: 142.5W, Grid: 192
```

### **✅ Benefits of the Fix:**

#### **1. Correct Power Interpretation:**
- ✅ **Charging Detection**: Positive current now correctly shows as negative power (charging)
- ✅ **Discharging Detection**: Negative current now correctly shows as positive power (discharging)
- ✅ **App Logic Alignment**: Power signs now match the app's interpretation logic

#### **2. Accurate System Status:**
- ✅ **Correct Source Display**: "Battery charging" vs "Battery discharging" now accurate
- ✅ **Proper Energy Flow**: Power direction now correctly represents energy flow
- ✅ **Consistent Convention**: All power calculations follow the same sign convention

#### **3. Better Monitoring:**
- ✅ **Accurate Logging**: Battery power logs now show correct charging/discharging status
- ✅ **Proper Alerts**: System alerts based on battery power will now be accurate
- ✅ **Correct Analytics**: Energy flow analytics will show correct battery behavior

### **📁 Files Modified:**

#### **1. `solarhub/adapters/senergy.py`:**
- ✅ Fixed `_calculate_battery_power()` method to use correct sign convention
- ✅ Added clear comments explaining the sign convention
- ✅ Inverted the power calculation: `calculated_power = -(voltage * current)`

### **✅ Verification:**
- ✅ File compiles successfully
- ✅ Sign convention corrected
- ✅ Power calculation logic updated
- ✅ Comments added for clarity

The battery power calculation now correctly interprets the sign convention, so when the battery is charging (positive current), it will show negative power and be correctly interpreted as "Battery charging" by the application!
