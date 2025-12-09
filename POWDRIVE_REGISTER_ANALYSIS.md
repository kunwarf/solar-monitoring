# Powdrive Register Map Analysis

## Current Status: 147 Registers

Comparing against **MODBUS RTU三相储能通信规约** specification.

---

## ✅ Implemented Registers

### Device Information (Addresses 0-59) - PARTIAL
- ✅ 0: `inverter_type` - Device Type
- ✅ 1: `modbus_address` - Modbus Address
- ✅ 2: `protocol_version_raw` - Protocol Version
- ✅ 3-7: `device_serial_number` - Serial Number (ASCII, 5 words)
- ✅ 20-21: `rated_power_w` - Rated Power (U32, 2 words)

**Missing:**
- ⚠️ 8-19: Various reserved/firmware version fields
- ⚠️ 22: MPPT number and phases
- ⚠️ 23-32: Model selection, battery routes, phase output, EU/UL, fan config, RTC, MCU types

### Configuration (Addresses 60-499) - PARTIAL
**Implemented:**
- ✅ 98: `battery_type` - Battery Type
- ✅ 99: `battery_equalization_voltage` - Equalization V
- ✅ 100: `battery_absorption_voltage` - Absorption V
- ✅ 101: `battery_floating_voltage` - Float V
- ✅ 102: `battery_capacity_ah` - Battery Capacity
- ✅ 104: `zero_export_power_w` - Zero Export Power
- ✅ 105: `battery_equalization_day_cycle` - Equalization Day Cycle
- ✅ 106: `battery_equalization_time` - Equalization Time
- ✅ 108: `battery_max_charge_current_a` - Max Charge Current
- ✅ 109: `battery_max_discharge_current_a` - Max Discharge Current
- ✅ 111: `battery_mode_source` - Voltage/Capacity Mode
- ✅ 115-120: Battery thresholds (shutdown/restart/low)
- ✅ 126-130: Grid/Gen charging settings
- ✅ 133-137: SmartLoad settings
- ✅ 141: `solar_priority` - Energy Management
- ✅ 142: `limit_control_function` - Limit Control
- ✅ 143: `max_export_power_w` - Max Export Power
- ✅ 145: `solar_sell` - Solar Sell
- ✅ 146: `tou_selling` - TOU Enable
- ✅ 148-177: TOU Windows (6 windows)
- ✅ 223: `lithium_battery_type` - Lithium Battery Type

**Missing:**
- ⚠️ 60-97: System time, communication, power regulation, work mode, factory settings
- ⚠️ 103: `battery_empty_voltage_v` - Empty Voltage
- ⚠️ 107: `battery_tempco` - Temperature Compensation
- ⚠️ 110: `parallel_bat_bat2` - Parallel Battery
- ⚠️ 112-114: Lithium battery wake-up, resistance, efficiency
- ⚠️ 121-125: Generator settings
- ⚠️ 131-132: AC couple, force generator
- ⚠️ 138-140: Output voltage, min solar power, gen grid signal
- ⚠️ 147: Grid phase sequence
- ⚠️ 178-222: Control board special functions, arc fault, grid standards, etc.
- ⚠️ 224-499: Lithium battery config, parallel, grid protection, Volt-VAR, Freq-Watt, etc.

### Telemetry (Addresses 500-2000) - PARTIAL
**Implemented:**
- ✅ 500: `working_mode_raw` - Working Mode
- ✅ 502: `day_active_energy_kwh` - Day Active Energy
- ✅ 514-515: Battery energy today
- ✅ 516-519: Battery energy total
- ✅ 520-525: Grid energy (import/export, today/total)
- ✅ 526-528: Load energy today/total
- ✅ 529: `pv_energy_today_kwh` - PV Energy Today
- ✅ 534-535: PV energy total
- ✅ 536: `day_gen_energy_kwh` - Gen Energy Today
- ✅ 540: `inverter_temp_c` - Inverter Temperature
- ✅ 586-590: Battery 1 (temp, voltage, SOC, power, current)
- ✅ 598-612: Grid (voltage L1/L2/L3, current L1/L2/L3, power L1/L2/L3)
- ✅ 625: `grid_power_w` - Grid Total Power
- ✅ 627-638: Inverter (voltage L1/L2/L3, current L1/L2/L3, power L1/L2/L3, frequency)
- ✅ 636: `inverter_power_w` - Inverter Total Power
- ✅ 644-653: Load (voltage L1/L2/L3, power L1/L2/L3, total)
- ✅ 664-667: Gen (power L1/L2/L3, total)
- ✅ 672-673: PV1/PV2 Power
- ✅ 676-679: PV1/PV2 Voltage/Current
- ✅ 601-603: Grid line voltages (AB, BC, CA)
- ✅ 551-554: Status registers (power on/off, AC relay, warnings)

**Missing:**
- ⚠️ 501: Reactive energy today
- ⚠️ 503: Grid connection time today
- ⚠️ 504-507: Active/reactive energy total (high words)
- ⚠️ 508-511: Inverter status bits, reserved
- ⚠️ 512-513: Gen history hours
- ⚠️ 530-533: PV per-string energy (PV1/PV2/PV3/PV4)
- ⚠️ 537-538: Gen energy total (high word)
- ⚠️ 539: Gen working hours today
- ⚠️ 541-544: Heat sink and other temperatures
- ⚠️ 545-546: Load energy year
- ⚠️ 548-550: Communication board status, MCU/LCD test flags
- ⚠️ 593-596: Battery 2 (voltage, current, power, temp)
- ⚠️ 597: Reserved
- ⚠️ 608: Grid apparent power
- ⚠️ 613-615: Grid external current (L1/L2/L3)
- ⚠️ 616-620: Grid external power (L1/L2/L3, total, apparent)
- ⚠️ 621: Grid power factor
- ⚠️ 622-625: Grid side power (L1/L2/L3, total) - varies by built-in/external
- ⚠️ 626: Reserved
- ⚠️ 639: Reserved
- ⚠️ 640-643: UPS load-side power (L1/L2/L3, total)
- ⚠️ 647-649: Load current (marked as invalid/no use)
- ⚠️ 654: Load apparent power
- ⚠️ 655: Load frequency
- ⚠️ 656-660: Load power high words (L1/L2/L3, total, apparent)
- ⚠️ 661-663: Gen port voltage (L1/L2/L3)
- ⚠️ 668-671: Gen port power high words (L1/L2/L3, total)
- ⚠️ 674-675: PV3/PV4 Power
- ⚠️ 680-683: PV3/PV4 Voltage/Current
- ⚠️ 684-686: Reserved
- ⚠️ **687-709: High words for 32-bit values (V104 update)** - CRITICAL
  - 687-690: Grid side power high words (L1/L2/L3, total)
  - 691-695: Inverter power high words (L1/L2/L3, total, apparent)
  - 696-699: UPS load power high words (L1/L2/L3, total)
  - 700-704: Grid inner power high words (L1/L2/L3, total, apparent)
  - 705-709: Grid external power high words (L1/L2/L3, total, apparent)

---

## 🔍 Standardization Issues

### ✅ Good Standardization
- Core telemetry: `battery_voltage_v`, `battery_current_a`, `battery_power_w`, `battery_soc_pct`
- PV: `pv1_power_w`, `pv1_voltage_v`, `pv1_current_a`
- Grid: `grid_power_w`, `grid_voltage_v`, `grid_frequency_hz`
- Load: `load_power_w`, `load_l1_power_w`, `load_l1_voltage_v`
- Energy: `pv_energy_today_kwh`, `battery_charge_energy_today_kwh`

### ⚠️ Inconsistencies Found

1. **TOU Window Registers:**
   - Current: `prog1_time`, `prog1_power_w`, `prog1_voltage_v`, `prog1_capacity_pct`, `prog1_charge_mode`
   - Standard doc says: `prog{1-5}_time` (but Powdrive has 6 windows, not 5)
   - **Issue:** Standard doc needs update to `prog{1-6}`

2. **Missing Units:**
   - `rated_power_w` ✅ (has `_w`)
   - `protocol_version_raw` ⚠️ (no unit suffix - OK for non-measurement)
   - `working_mode_raw` ⚠️ (no unit suffix - OK for enum)
   - `grid_status_raw` ⚠️ (no unit suffix - OK for bit field)

3. **Inconsistent Naming:**
   - `day_gen_energy_kwh` vs `day_active_energy_kwh` - both exist, different meanings
   - `battery_absorption_voltage` vs `battery_absorption_voltage_v` - should use `_v` suffix
   - `battery_equalization_voltage` vs `battery_equalization_voltage_v` - should use `_v` suffix
   - `battery_floating_voltage` vs `battery_floating_voltage_v` - should use `_v` suffix

4. **Missing Standardized IDs:**
   - Generator: `gen_l1_voltage_v`, `gen_l2_voltage_v`, `gen_l3_voltage_v` (missing)
   - Generator: `gen_l1_current_a`, `gen_l2_current_a`, `gen_l3_current_a` (missing)
   - UPS: `ups_load_l1_power_w`, etc. (missing)
   - PV4: `pv4_power_w`, `pv4_voltage_v`, `pv4_current_a` (missing)

---

## 📋 Missing Critical Registers

### High Priority (32-bit Support - V104)
**Addresses 687-709:** High words for 32-bit values
- 687-690: Grid side power high words
- 691-695: Inverter power high words
- 696-699: UPS load power high words
- 700-704: Grid inner power high words
- 705-709: Grid external power high words

**Impact:** Current implementation only reads low 16-bit words, missing high 16-bit words for 32-bit values.

### Medium Priority
1. **Generator Per-Phase:**
   - Gen L1/L2/L3 voltage (661-663) - ✅ Present as `gen_l1_voltage_v` (need to verify)
   - Gen L1/L2/L3 current (missing)

2. **PV4:**
   - PV4 power (675)
   - PV4 voltage/current (682-683)

3. **Battery 2:**
   - Battery 2 voltage/current/power/temp (593-596)

4. **Grid Protection:**
   - Grid power factor (621)
   - Grid apparent power (608, 620, 704, 709)

5. **Load:**
   - Load frequency (655)
   - Load apparent power (654, 660)
   - Load power high words (656-660)

6. **UPS:**
   - UPS load-side power (640-643, 696-699)

---

## 🔧 Recommendations

### 1. Add Missing High-Word Registers (687-709)
**Critical for V104 specification compliance.**

### 2. Standardize Voltage Register Names
- `battery_absorption_voltage` → `battery_absorption_voltage_v`
- `battery_equalization_voltage` → `battery_equalization_voltage_v`
- `battery_floating_voltage` → `battery_floating_voltage_v`

### 3. Add Missing Generator Registers
- Gen L1/L2/L3 voltage (if not already present)
- Gen L1/L2/L3 current

### 4. Add Missing Configuration Registers
- Battery empty voltage (103)
- Temperature compensation (107)
- Generator settings (121-125)
- Grid protection settings (185-188, 354-361)
- Volt-VAR, Freq-Watt modes (363-412)

### 5. Update Standard Document
- Update `prog{1-5}` to `prog{1-6}` for Powdrive
- Add 3-phase specific registers (L1/L2/L3 suffixes)

---

## ✅ Summary

**Current Status:**
- ✅ Core telemetry: Well standardized
- ✅ TOU windows: Complete (6 windows)
- ⚠️ Missing: ~100+ registers from spec
- ⚠️ Critical: 32-bit high-word registers (687-709)
- ⚠️ Minor: Some voltage registers missing `_v` suffix

**Priority Actions:**
1. Add 32-bit high-word registers (687-709) - **CRITICAL**
2. Standardize voltage register names (add `_v` suffix)
3. Add missing generator per-phase registers
4. Add missing PV4 registers
5. Add missing configuration registers (if needed)

