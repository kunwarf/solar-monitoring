# Powdrive Modbus Specification Verification

Based on the Modbus RTU Deye specification PDF, I need to verify the following register addresses and decode missing information.

## Registers to Verify/Add

### 1. Load Per-Phase Registers ⚠️ HIGH PRIORITY

Please confirm from the PDF:
- **Load L1 Power** - Register address: **650**? (Type: S16, Unit: W)
- **Load L2 Power** - Register address: **651**? (Type: S16, Unit: W)
- **Load L3 Power** - Register address: **652**? (Type: S16, Unit: W)
- **Load L1 Voltage** - Register address: **644**? (Type: U16, Unit: V, Scale: 0.1)
- **Load L2 Voltage** - Register address: **645**? (Type: U16, Unit: V, Scale: 0.1)
- **Load L3 Voltage** - Register address: **646**? (Type: U16, Unit: V, Scale: 0.1)
- **Load L1 Current** - Register address? (Type: S16, Unit: A, Scale: 0.01)
- **Load L2 Current** - Register address? (Type: S16, Unit: A, Scale: 0.01)
- **Load L3 Current** - Register address? (Type: S16, Unit: A, Scale: 0.01)

### 2. Working Mode (Register 500) ⚠️ MEDIUM PRIORITY

Please confirm the enum values from the PDF:
- **0x0000**: Standby (待机)?
- **0x0001**: Self-test (自检)?
- **0x0002**: Normal (normal)?
- **0x0003**: Alarm (alarm)?
- **0x0004**: Fault (Fault)?

### 3. Grid Status (Register 552) ⚠️ MEDIUM PRIORITY

Please confirm the bit definitions from the PDF:
- **Bit 0**: ?
- **Bit 1**: ?
- **Bit 2**: Grid connected? (used for off-grid detection)
- **Other bits**: ?

### 4. Fault Words (Registers 555-558) ⚠️ MEDIUM PRIORITY

Please confirm from the PDF:
- **Fault Word 0 (555)**: What are the bit definitions?
- **Fault Word 1 (556)**: What are the bit definitions?
- **Fault Word 2 (557)**: What are the bit definitions?
- **Fault Word 3 (558)**: What are the bit definitions?

### 5. Phase-to-Phase Voltages ⚠️ MEDIUM PRIORITY

Please confirm from the PDF if these registers exist:
- **VL1-L2** (L1-L2 voltage) - Register address?
- **VL2-L3** (L2-L3 voltage) - Register address?
- **VL3-L1** (L3-L1 voltage) - Register address?

### 6. Battery Status (Register 224) ⚠️ LOW PRIORITY

Please confirm from the PDF:
- What are the bit definitions for battery status?

### 7. Missing Registers Check

Please check if there are any other important registers in the PDF that are not in our current implementation:
- Reactive power (VAR) registers?
- Power factor registers?
- Additional generator parameters?
- Load per-phase energy (daily/total)?
- Other diagnostic/status registers?

---

## Implementation Plan

Once you confirm the register addresses and definitions, I will:

1. **Add missing Load per-phase registers** to `powdrive_registers.json`
2. **Add enum to working_mode_raw** register
3. **Implement working mode decoding** in adapter to set `inverter_mode`
4. **Implement grid status decoding** to detect off-grid mode
5. **Implement fault code decoding** to extract error codes
6. **Add phase-to-phase voltages** if available
7. **Update adapter poll()** to read all new registers
8. **Update telemetry extra dict** with all new values

Would you like me to proceed with implementing these features once you confirm the register addresses?

