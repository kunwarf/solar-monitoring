# OutageRiskProfile Constructor Fix Summary

## ✅ **Issue Resolved: OutageRiskProfile.__init__() missing required positional arguments**

### **Problem:**
The SolarHub service was encountering a runtime error:
```
SmartScheduler error: OutageRiskProfile.__init__() missing 2 required positional arguments: 'utility_outages' and 'internal_outages'
```

### **Root Cause:**
The `OutageRiskProfile` dataclass was updated to include `utility_outages` and `internal_outages` fields for outage cause classification, but several places in the code were still creating instances without providing these required parameters.

### **The Issue:**
```python
@dataclass
class OutageRiskProfile:
    """Risk profile for a specific hour."""
    hour: int
    risk_score: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 1.0
    historical_outages: int
    seasonal_factor: float
    utility_outages: int  # Outages caused by utility issues ← REQUIRED
    internal_outages: int  # Outages caused by internal protection trips ← REQUIRED
```

But the code was creating instances like this:
```python
# MISSING utility_outages and internal_outages parameters
OutageRiskProfile(
    hour=hour,
    risk_score=0.1,
    confidence=0.5,
    historical_outages=0,
    seasonal_factor=1.0
    # ← Missing utility_outages and internal_outages
)
```

### **Fix Applied:**

#### **1. Fixed Line 489 - `_build_risk_profiles` method:**
```python
# BEFORE:
self.risk_profiles[hour] = OutageRiskProfile(
    hour=hour,
    risk_score=0.1,  # Base 10% risk
    confidence=0.5,
    historical_outages=0,
    seasonal_factor=1.0,
)

# AFTER:
self.risk_profiles[hour] = OutageRiskProfile(
    hour=hour,
    risk_score=0.1,  # Base 10% risk
    confidence=0.5,
    historical_outages=0,
    seasonal_factor=1.0,
    utility_outages=0,
    internal_outages=0
)
```

#### **2. Fixed Line 645 - `get_outage_risk` method:**
```python
# BEFORE:
base_profile = self.risk_profiles.get(hour, OutageRiskProfile(
    hour=hour, risk_score=0.1, confidence=0.5, 
    historical_outages=0, seasonal_factor=1.0
))

# AFTER:
base_profile = self.risk_profiles.get(hour, OutageRiskProfile(
    hour=hour, risk_score=0.1, confidence=0.5, 
    historical_outages=0, seasonal_factor=1.0,
    utility_outages=0, internal_outages=0
))
```

#### **3. Fixed Line 658 - `get_outage_risk` adjusted profile:**
```python
# BEFORE:
adjusted_profile = OutageRiskProfile(
    hour=hour,
    risk_score=min(base_profile.risk_score * multiplier, 1.0),
    confidence=base_profile.confidence,
    historical_outages=base_profile.historical_outages,
    seasonal_factor=base_profile.seasonal_factor
)

# AFTER:
adjusted_profile = OutageRiskProfile(
    hour=hour,
    risk_score=min(base_profile.risk_score * multiplier, 1.0),
    confidence=base_profile.confidence,
    historical_outages=base_profile.historical_outages,
    seasonal_factor=base_profile.seasonal_factor,
    utility_outages=base_profile.utility_outages,
    internal_outages=base_profile.internal_outages
)
```

### **Why This Was Important:**
The `utility_outages` and `internal_outages` fields enable:
- **Outage Cause Classification**: Distinguishing between utility-caused vs. internal protection trip outages
- **Risk Profile Accuracy**: Only utility outages should boost risk buffers for grid reliability planning
- **Equipment Diagnostics**: Internal outages route to equipment diagnostics rather than grid risk assessment

### **Expected Result:**
The SolarHub service should now run without the `OutageRiskProfile` constructor error and properly execute the reliability system with:
- ✅ Outage cause classification (utility vs. internal)
- ✅ Accurate risk profile building
- ✅ Proper equipment diagnostic routing
- ✅ Enhanced grid reliability planning

### **Verification:**
- ✅ `solarhub/schedulers/reliability.py` - No syntax errors
- ✅ Module imports successfully
- ✅ All `OutageRiskProfile` constructor calls provide required parameters
- ✅ Smart scheduler imports successfully (depends on reliability module)

### **Files Modified:**
- `solarhub/schedulers/reliability.py` - Fixed 3 `OutageRiskProfile` constructor calls

The reliability system should now properly initialize all risk profiles with outage cause classification, enabling the advanced features like utility-only risk scoring and internal outage diagnostics.
