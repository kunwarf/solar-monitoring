# Powdrive Three-Phase Hybrid Inverter - Implementation Analysis

## Current Implementation Status

### ✅ Fully Implemented

#### 1. **Core Telemetry (3-Phase)**
- ✅ Grid: L1/L2/L3 power, voltage, current, frequency
- ✅ Inverter: L1/L2/L3 power, voltage, current, frequency, total power
- ✅ Grid CT: L1/L2/L3 power, total power
- ✅ Generator: L1/L2/L3 power, total power
- ✅ Load: Total power only
- ✅ PV: PV1/PV2/PV3 power, voltage, current
- ✅ Battery: Voltage, current, power, SOC, temperature
- ✅ Inverter temperature

#### 2. **Energy Tracking**
- ✅ Daily: PV, Load, Grid Import/Export, Battery Charge/Discharge, Generator
- ✅ Total: PV, Load, Grid Import/Export, Battery Charge/Discharge

#### 3. **Device Information**
- ✅ Inverter type (enum: Inverter, Hybrid, Micro, 3-Phase Hybrid)
- ✅ Modbus address
- ✅ Protocol version
- ✅ Serial number (ASCII)
- ✅ Rated power

#### 4. **Status & Faults**
- ✅ Working mode (raw register)
- ✅ Fault words (0-3)
- ✅ Grid status (raw register)
- ✅ Battery status (raw register)

#### 5. **Configuration (RW)**
- ✅ Battery type, voltages, capacity, current limits
- ✅ Zero export power
- ✅ Grid charging settings
- ✅ Generator charging
- ✅ SmartLoad settings
- ✅ Solar priority
- ✅ Limit control function
- ✅ Max export power
- ✅ Solar sell / TOU selling
- ✅ Lithium battery type
- ✅ TOU Windows (prog1-6): time, power, capacity, voltage, charge mode

---

## ⚠️ Potential Gaps / Missing Features

### 1. **Load Per-Phase Measurements** ⚠️ HIGH PRIORITY
**Current Status:** Only total load power is implemented (register 653)
**Missing from Register Map:**
- Load L1 power (addr 650) - **Mentioned in your original spec but not in register map**
- Load L2 power (addr 651) - **Mentioned in your original spec but not in register map**
- Load L3 power (addr 652) - **Mentioned in your original spec but not in register map**
- Load L1 voltage (addr 644) - **Mentioned in your original spec but not in register map**
- Load L2 voltage (addr 645) - **Mentioned in your original spec but not in register map**
- Load L3 voltage (addr 646) - **Mentioned in your original spec but not in register map**
- Load L1/L2/L3 current (if available)

**Impact:** Dashboard won't show per-phase load distribution, which is important for 3-phase systems.
**Action Required:** Add these registers to `powdrive_registers.json` if they exist in the Modbus specification.

---

### 2. **Phase-to-Phase Voltages** ⚠️ MEDIUM PRIORITY
**Missing:**
- VL1-L2 (voltage between L1 and L2)
- VL2-L3 (voltage between L2 and L3)
- VL3-L1 (voltage between L3 and L1)

**Impact:** Important for 3-phase system diagnostics and balancing.

---

### 3. **Working Mode Enum Decoding** ⚠️ MEDIUM PRIORITY
**Current Status:** `working_mode_raw` register exists (addr 500) but not decoded in adapter
**Missing:**
- Enum mapping in register map (currently no enum defined)
- Decoding logic in adapter to map `working_mode_raw` to `inverter_mode` in Telemetry
- Human-readable mode strings (e.g., "Standby", "Self-test", "Normal", "Alarm", "Fault")

**Expected Enum Values (from typical Powdrive inverters):**
- 0x0000: Standby (待机)
- 0x0001: Self-test (自检)
- 0x0002: Normal (normal)
- 0x0003: Alarm (alarm)
- 0x0004: Fault (Fault)

**Impact:** Inverter mode shows as "Unknown" in UI.
**Action Required:** 
1. Add enum to `working_mode_raw` register in `powdrive_registers.json`
2. Update adapter to decode and set `inverter_mode` in Telemetry

---

### 4. **Fault Code Decoding** ⚠️ MEDIUM PRIORITY
**Current Status:** Fault words (0-3) are read (addr 555-558) but not decoded
**Missing:**
- Bit mask interpretation for each fault word
- Human-readable fault descriptions
- Fault priority/severity classification
- `error_code` field in Telemetry (currently not set)

**Impact:** Faults are not human-readable in logs/UI. No error_code in telemetry.
**Action Required:** Add fault decoding logic to adapter to extract meaningful error codes.

---

### 5. **Grid Status Decoding** ⚠️ MEDIUM PRIORITY
**Current Status:** `grid_status_raw` register exists (addr 552) but not decoded
**Missing:**
- Bit mask interpretation (e.g., bit 2 = grid connected)
- Off-grid mode detection logic
- `off_grid_mode` field in Telemetry (currently not set)

**Impact:** Off-grid mode detection may not work correctly. Smart scheduler may not handle off-grid scenarios.
**Action Required:** 
1. Decode `grid_status_raw` to detect off-grid mode
2. Set `off_grid_mode` in Telemetry or extra dict
3. Update smart scheduler to check this field

---

### 6. **Battery Status Decoding** ⚠️ LOW PRIORITY
**Current Status:** `battery_status_raw` register exists but not decoded
**Missing:**
- Bit mask interpretation for battery status
- Battery health indicators
- Charging/discharging state

**Impact:** Battery status details not available in UI.

---

### 7. **Reactive Power (VAR)** ⚠️ LOW PRIORITY
**Missing:**
- Grid reactive power (per-phase and total)
- Load reactive power (per-phase and total)
- Inverter reactive power

**Impact:** Power factor analysis not possible.

---

### 8. **Power Factor** ⚠️ LOW PRIORITY
**Missing:**
- Power factor per phase (grid, load, inverter)
- Total power factor

**Impact:** Power quality monitoring limited.

---

### 9. **Load Per-Phase Energy** ⚠️ LOW PRIORITY
**Missing:**
- Load L1/L2/L3 daily energy (if tracked separately)
- Load L1/L2/L3 total energy (if tracked separately)

**Impact:** Per-phase energy consumption analysis not available.

---

### 10. **Additional Generator Features** ⚠️ LOW PRIORITY
**Current Status:** Generator power is read
**Missing (if available):**
- Generator voltage, current, frequency
- Generator status/health
- Generator runtime hours

---

### 11. **PV3 Full Support** ⚠️ LOW PRIORITY
**Current Status:** PV3 power exists, but PV3 voltage/current may not be in adapter
**Note:** PV3 voltage/current are in register map (680, 681)
**Impact:** PV3 complete telemetry should be read in adapter.

---

### 12. **Inverter Mode Mapping** ⚠️ LOW PRIORITY
**Current Status:** Inverter mode shows as "Unknown"
**Missing:**
- Mapping from `working_mode_raw` to `inverter_mode` in Telemetry
- Standardized mode strings matching Senergy adapter

---

## Implementation Recommendations

### Priority 1 (Critical for 3-Phase Systems):
1. **Load Per-Phase Measurements** - Add Load L1/L2/L3 power, voltage, current
2. **Working Mode Enum Decoding** - Decode working mode to human-readable strings
3. **Grid Status Decoding** - Decode grid status for off-grid detection

### Priority 2 (Important for Diagnostics):
4. **Fault Code Decoding** - Make fault words human-readable
5. **Phase-to-Phase Voltages** - Add VL1-L2, VL2-L3, VL3-L1 if available

### Priority 3 (Nice to Have):
6. **Battery Status Decoding** - Decode battery status register
7. **Reactive Power / Power Factor** - If supported by inverter
8. **Load Per-Phase Energy** - If tracked separately

---

## Questions for User

1. **Do you have the Modbus specification diagram?** If so, please share it so I can verify:
   - Exact register addresses for missing features
   - Data types and scaling factors
   - Enum/bit mask definitions

2. **Which features would you like me to implement?**
   - Load per-phase measurements (HIGH PRIORITY)
   - Working mode enum decoding (MEDIUM PRIORITY)
   - Grid status decoding (MEDIUM PRIORITY)
   - Fault code decoding (MEDIUM PRIORITY)
   - Phase-to-phase voltages (MEDIUM PRIORITY)
   - Others (LOW PRIORITY)

3. **Do you have register addresses for:**
   - Load L1/L2/L3 power, voltage, current?
   - Phase-to-phase voltages?
   - Working mode enum values?

4. **Are there any other registers/features in the specification that are not in our current implementation?**

