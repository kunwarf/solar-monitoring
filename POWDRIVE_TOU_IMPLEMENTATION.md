# Powdrive TOU (Time-of-Use) Window Implementation

## Overview

Based on the **MODBUS RTU三相储能通信规约** specification, Powdrive supports 6 bidirectional TOU windows with a complex register structure requiring bit manipulation.

---

## ✅ Register Structure (Registers 146-177)

### Register 146: TOU Enable (`tou_selling`)
**Address:** 146  
**Type:** U16 (RW)  
**Bit Manipulation:**
- **Bit 0:** Enable/disable TOU (0=disable, 1=enable)
- **Bit 1:** Monday (0=disable, 1=enable)
- **Bit 2:** Tuesday (0=disable, 1=enable)
- **Bit 3:** Wednesday (0=disable, 1=enable)
- **Bit 4:** Thursday (0=disable, 1=enable)
- **Bit 5:** Friday (0=disable, 1=enable)
- **Bit 6:** Saturday (0=disable, 1=enable)
- **Bit 7:** Sunday (0=disable, 1=enable)
- **Bit 8:** Spanish mode (0=disable, 1=enable)

**Example:**
- Enable TOU for all days: `0x01FF` (Bit 0 + Bits 1-7 = 1 + 127 = 255)
- Enable TOU only for weekdays: `0x01F8` (Bit 0 + Bits 1-5 = 1 + 120 = 248)

---

### Time Points (Registers 148-153)
**Format:** HHMM (e.g., 2359 = 23:59)

| Register | Address | Name | Description |
|----------|---------|------|-------------|
| `prog1_time` | 148 | Sell mode time point 1 | Start time of window 1, also end time of window 6 |
| `prog2_time` | 149 | Sell mode time point 2 | Start time of window 2, also end time of window 1 |
| `prog3_time` | 150 | Sell mode time point 3 | Start time of window 3, also end time of window 2 |
| `prog4_time` | 151 | Sell mode time point 4 | Start time of window 4, also end time of window 3 |
| `prog5_time` | 152 | Sell mode time point 5 | Start time of window 5, also end time of window 4 |
| `prog6_time` | 153 | Sell mode time point 6 | Start time of window 6, also end time of window 5 |

**Note:** Time points are **shared** - each time point serves as both the start of one window and the end of the previous window.

**Example:**
- Window 1: Start = `prog1_time` (148), End = `prog2_time` (149)
- Window 2: Start = `prog2_time` (149), End = `prog3_time` (150)
- Window 3: Start = `prog3_time` (150), End = `prog4_time` (151)
- Window 4: Start = `prog4_time` (151), End = `prog5_time` (152)
- Window 5: Start = `prog5_time` (152), End = `prog6_time` (153)
- Window 6: Start = `prog6_time` (153), End = `prog1_time` (148) ← wraps around

---

### Power (Registers 154-159)
**Format:** U16 (W) - Always positive (absolute value)

| Register | Address | Name | Description |
|----------|---------|------|-------------|
| `prog1_power_w` | 154 | Sell mode time point 1 power | Charge/discharge power for window 1 |
| `prog2_power_w` | 155 | Sell mode time point 2 power | Charge/discharge power for window 2 |
| `prog3_power_w` | 156 | Sell mode time point 3 power | Charge/discharge power for window 3 |
| `prog4_power_w` | 157 | Sell mode time point 4 power | Charge/discharge power for window 4 |
| `prog5_power_w` | 158 | Sell mode time point 5 power | Charge/discharge power for window 5 |
| `prog6_power_w` | 159 | Sell mode time point 6 power | Charge/discharge power for window 6 |

**Note:** Power is always positive. Direction (charge/discharge) is determined by comparing target SOC/voltage to current value.

---

### Target Voltage (Registers 160-165) - Used if Register 111 = 0 (Voltage Mode)
**Format:** U16 (0.01V scale)

| Register | Address | Name | Description |
|----------|---------|------|-------------|
| `prog1_voltage_v` | 160 | Sell mode time point 1 voltage | Target voltage for window 1 |
| `prog2_voltage_v` | 161 | Sell mode time point 2 voltage | Target voltage for window 2 |
| `prog3_voltage_v` | 162 | Sell mode time point 3 voltage | Target voltage for window 3 |
| `prog4_voltage_v` | 163 | Sell mode time point 4 voltage | Target voltage for window 4 |
| `prog5_voltage_v` | 164 | Sell mode time point 5 voltage | Target voltage for window 5 |
| `prog6_voltage_v` | 165 | Sell mode time point 6 voltage | Target voltage for window 6 |

**Usage:** Only used if `battery_mode_source` (register 111) = 0 (voltage mode)

---

### Target SOC (Registers 166-171) - Used if Register 111 = 1 (Capacity Mode)
**Format:** U16 (%)

| Register | Address | Name | Description |
|----------|---------|------|-------------|
| `prog1_capacity_pct` | 166 | 1 capacity (window 1 SOC) | Target SOC for window 1 |
| `prog2_capacity_pct` | 167 | 2 capacity (window 2 SOC) | Target SOC for window 2 |
| `prog3_capacity_pct` | 168 | 3 capacity (window 3 SOC) | Target SOC for window 3 |
| `prog4_capacity_pct` | 169 | 4 capacity (window 4 SOC) | Target SOC for window 4 |
| `prog5_capacity_pct` | 170 | 5 capacity (window 5 SOC) | Target SOC for window 5 |
| `prog6_capacity_pct` | 171 | 6 capacity (window 6 SOC) | Target SOC for window 6 |

**Usage:** Only used if `battery_mode_source` (register 111) = 1 (capacity mode)

---

### Charge Enable (Registers 172-177) - Bit Manipulation Required
**Format:** U16 (RW) - Bit manipulation

| Register | Address | Name | Description |
|----------|---------|------|-------------|
| `prog1_charge_mode` | 172 | Time point 1 charge enable | Bit manipulation for window 1 |
| `prog2_charge_mode` | 173 | Time point 2 charge enable | Bit manipulation for window 2 |
| `prog3_charge_mode` | 174 | Time point 3 charge enable | Bit manipulation for window 3 |
| `prog4_charge_mode` | 175 | Time point 4 charge enable | Bit manipulation for window 4 |
| `prog5_charge_mode` | 176 | Time point 5 charge enable | Bit manipulation for window 5 |
| `prog6_charge_mode` | 177 | Time point 6 charge enable | Bit manipulation for window 6 |

**Bit Manipulation:**
- **Bit 0:** Grid charging enable (0=disable, 1=enable)
- **Bit 1:** Gen charging enable (0=disable, 1=enable)
- **Bit 2:** Spanish GM mode (0=disable, 1=enable)
- **Bit 3:** Spanish BU mode (0=disable, 1=enable)
- **Bit 4:** Spanish CH mode (0=disable, 1=enable)

**Example:**
- Enable grid charging only: `0x0001` (Bit 0 = 1)
- Enable grid and gen charging: `0x0003` (Bits 0-1 = 3)
- Enable grid charging + Spanish GM: `0x0005` (Bits 0 + 2 = 5)

---

## 🔧 Implementation Details

### Register 111: Battery Mode Source
**Address:** 111  
**Type:** U16 (RW)  
**Values:**
- `0` = Voltage mode (use registers 160-165 for target voltage)
- `1` = Capacity mode (use registers 166-171 for target SOC)
- `2` = No battery

**Impact:** Determines which target registers are used (voltage vs. capacity)

---

### Direction Determination (Charge vs. Discharge)

Powdrive automatically determines charge/discharge direction by comparing target to current value:

**For Voltage Mode (register 111 = 0):**
- If `target_voltage > current_voltage` → **Charge**
- If `target_voltage < current_voltage` → **Discharge**

**For Capacity Mode (register 111 = 1):**
- If `target_soc_pct > current_soc_pct` → **Charge**
- If `target_soc_pct < current_soc_pct` → **Discharge**

**Note:** Charge enable bits (registers 172-177) must still be set correctly to enable grid/gen charging.

---

## 📋 Adapter Implementation

### `get_tou_window_capability()`

Returns:
```python
{
    "max_windows": 6,  # Powdrive supports 6 windows (not 5)
    "bidirectional": True,
    "separate_charge_discharge": False,
    "max_charge_windows": 6,
    "max_discharge_windows": 6
}
```

---

### `handle_command()` - `set_tou_window{1-6}`

**Command Format:**
```python
{
    "action": "set_tou_window1",  # or set_tou_window2, ..., set_tou_window6
    "start_time": "08:00",  # HH:MM format
    "end_time": "12:00",    # HH:MM format (becomes next window's start)
    "power_w": 3000,        # Absolute power (always positive)
    "target_soc_pct": 80,   # Target SOC (used if register 111=1)
    "target_voltage_v": 54.0,  # Optional: Target voltage (used if register 111=0)
    "type": "auto",         # "charge", "discharge", or "auto"
    "enable_gen_charging": False,  # Optional: Enable gen charging
    "enable_spanish_gm": False,    # Optional: Enable Spanish GM mode
    "enable_spanish_bu": False,   # Optional: Enable Spanish BU mode
    "enable_spanish_ch": False    # Optional: Enable Spanish CH mode
}
```

**Implementation Steps:**

1. **Read battery_mode_source (register 111)** to determine voltage vs. capacity mode
2. **Set start time** (register 148-153) - `prog{idx}_time`
3. **Set power** (register 154-159) - `prog{idx}_power_w` (absolute value)
4. **Set target** based on mode:
   - If `battery_mode_source == 0` (voltage mode): Set `prog{idx}_voltage_v` (register 160-165)
   - If `battery_mode_source == 1` (capacity mode): Set `prog{idx}_capacity_pct` (register 166-171)
5. **Set charge enable** (register 172-177) with bit manipulation:
   - Determine if charge or discharge window (compare target to current SOC/voltage)
   - Set Bit 0 (grid charging enable) if charge window
   - Set Bit 1 (gen charging enable) if `enable_gen_charging` is True
   - Set Bits 2-4 (Spanish modes) if enabled

**Note:** End time is automatically set as the next window's start time (or window 1's start for window 6).

---

## 🎯 Smart Scheduler Integration

The smart scheduler has been updated to support 6 windows instead of 5:

```python
max_windows = min(capability.get("max_windows", 6), len(all_windows))
```

When clearing unused windows:
```python
max_windows = capability.get("max_windows", 6) if capability else 6
for idx in range(len(active_windows) + 1, max_windows + 1):
    cmds.append({"action": f"set_tou_window{idx}", "chg_start": "00:00", "chg_end": "00:00"})
```

---

## ✅ Summary

**All TOU window registers have been updated:**

✅ Register 146: TOU enable with bit manipulation (days of week, Spanish mode)  
✅ Registers 148-153: Time points (start/end times with shared structure)  
✅ Registers 154-159: Power (absolute values)  
✅ Registers 160-165: Target voltage (if register 111=0)  
✅ Registers 166-171: Target SOC (if register 111=1)  
✅ Registers 172-177: Charge enable with bit manipulation (grid/gen/Spanish modes)  
✅ Adapter implementation with proper bit manipulation  
✅ Smart scheduler updated to support 6 windows

The implementation now correctly handles:
- Time point sharing (start of window N = end of window N-1)
- Voltage vs. capacity mode based on register 111
- Bit manipulation for TOU enable and charge enable registers
- Automatic direction determination (charge vs. discharge)

