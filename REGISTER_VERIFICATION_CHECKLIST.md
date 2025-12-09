# Powdrive Register Verification Checklist

Please verify these register addresses from the MODBUS_RTU_DEYE.pdf specification:

## ✅ Currently Implemented (Please Verify These Are Correct)

### Load Registers
- [ ] **Register 653**: Total Load Power (S16, W) - ✅ Already in register map

### Working Mode & Status
- [ ] **Register 500**: Working Mode (U16) - ✅ Already in register map
- [ ] **Register 552**: Grid Status (U16) - ✅ Already in register map
- [ ] **Register 555-558**: Fault Words 0-3 (U16) - ✅ Already in register map
- [ ] **Register 224**: Battery Status (U16) - ✅ Already in register map

---

## ❌ Missing Registers (Please Confirm These Exist in PDF)

### Load Per-Phase Registers (HIGH PRIORITY)
- [ ] **Register 650**: Load L1 Power (S16, W) - **Please confirm address and type**
- [ ] **Register 651**: Load L2 Power (S16, W) - **Please confirm address and type**
- [ ] **Register 652**: Load L3 Power (S16, W) - **Please confirm address and type**
- [ ] **Register 644**: Load L1 Voltage (U16, V, scale 0.1) - **Please confirm address and type**
- [ ] **Register 645**: Load L2 Voltage (U16, V, scale 0.1) - **Please confirm address and type**
- [ ] **Register 646**: Load L3 Voltage (U16, V, scale 0.1) - **Please confirm address and type**
- [ ] **Load L1 Current**: Register address? (S16, A, scale 0.01) - **Please provide address**
- [ ] **Load L2 Current**: Register address? (S16, A, scale 0.01) - **Please provide address**
- [ ] **Load L3 Current**: Register address? (S16, A, scale 0.01) - **Please provide address**

### Phase-to-Phase Voltages (MEDIUM PRIORITY)
- [ ] **VL1-L2 Voltage**: Register address? (U16, V, scale 0.1) - **Please provide address**
- [ ] **VL2-L3 Voltage**: Register address? (U16, V, scale 0.1) - **Please provide address**
- [ ] **VL3-L1 Voltage**: Register address? (U16, V, scale 0.1) - **Please provide address**

### Working Mode Enum (MEDIUM PRIORITY)
Please confirm the enum values for Register 500 (Working Mode):
- [ ] **0x0000**: Standby (待机)?
- [ ] **0x0001**: Self-test (自检)?
- [ ] **0x0002**: Normal (normal)?
- [ ] **0x0003**: Alarm (alarm)?
- [ ] **0x0004**: Fault (Fault)?
- [ ] **Other values?**: Please list any additional values

### Grid Status Bit Definitions (MEDIUM PRIORITY)
Please confirm the bit definitions for Register 552 (Grid Status):
- [ ] **Bit 0**: ?
- [ ] **Bit 1**: ?
- [ ] **Bit 2**: Grid connected? (used for off-grid detection)
- [ ] **Bit 3**: ?
- [ ] **Bit 4**: ?
- [ ] **Other bits**: Please list all bit definitions

### Fault Word Bit Definitions (MEDIUM PRIORITY)
Please confirm bit definitions for each fault word:

**Register 555 (Fault Word 0):**
- [ ] Bit 0: ?
- [ ] Bit 1: ?
- [ ] ... (Please list all bit definitions)

**Register 556 (Fault Word 1):**
- [ ] Bit 0: ?
- [ ] Bit 1: ?
- [ ] ... (Please list all bit definitions)

**Register 557 (Fault Word 2):**
- [ ] Bit 0: ?
- [ ] Bit 1: ?
- [ ] ... (Please list all bit definitions)

**Register 558 (Fault Word 3):**
- [ ] Bit 0: ?
- [ ] Bit 1: ?
- [ ] ... (Please list all bit definitions)

### Battery Status Bit Definitions (LOW PRIORITY)
**Register 224 (Battery Status):**
- [ ] Bit 0: ?
- [ ] Bit 1: ?
- [ ] ... (Please list all bit definitions)

---

## 📋 Additional Registers to Check

Please check if these exist in the PDF:

- [ ] **Reactive Power (VAR)** registers for grid/load/inverter?
- [ ] **Power Factor** registers for grid/load/inverter?
- [ ] **Load per-phase energy** (daily/total) registers?
- [ ] **Generator voltage/current/frequency** registers?
- [ ] **Additional diagnostic/status** registers?
- [ ] **Network/communication** parameters?
- [ ] **Other important registers** not currently in our implementation?

---

## 🎯 Next Steps

Once you confirm the register addresses and definitions:

1. I will add all missing registers to `powdrive_registers.json`
2. I will add enum definitions for working_mode_raw
3. I will implement decoding logic in the adapter for:
   - Working mode → inverter_mode
   - Grid status → off_grid_mode
   - Fault words → error_code
4. I will update the adapter poll() method to read all new registers
5. I will update the telemetry extra dict with all new values

**Please review the PDF and confirm the register addresses and definitions above.**

