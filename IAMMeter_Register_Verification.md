# IAMMeter Register Verification

## Status: ✅ ALL REGISTERS IMPLEMENTED

All 37 registers from your specification (addresses 0x0-0x40) have been added to the register map JSON file and will be automatically read and published.

## Register Implementation Status

### ✅ Implemented Registers (Addresses 0x0-0x40)

| No. | Address (Dec) | Address (Hex) | Size | Register Name | Status |
|-----|---------------|---------------|------|---------------|--------|
| 1 | 0 | 0x0 | 1 | Phase A voltage | ✅ Added |
| 2 | 1 | 0x1 | 1 | Phase A current | ✅ Added |
| 3 | 2 | 0x2 | 2 | Phase A active power | ✅ Added |
| 4 | 4 | 0x4 | 2 | Phase A forward energy (pulses) | ✅ Added |
| 5 | 6 | 0x6 | 2 | Phase A reverse energy (pulses) | ✅ Added |
| 6 | 8 | 0x8 | 1 | Phase A power factor | ✅ Added |
| 7 | 9 | 0x9 | 1 | Device model | ✅ Added |
| 8 | 10 | 0xa | 1 | Phase B voltage | ✅ Added |
| 9 | 11 | 0xb | 1 | Phase B current | ✅ Added |
| 10 | 12 | 0xc | 2 | Phase B active power | ✅ Added |
| 11 | 14 | 0xe | 2 | Phase B forward energy (pulses) | ✅ Added |
| 12 | 16 | 0x10 | 2 | Phase B reverse energy (pulses) | ✅ Added |
| 13 | 18 | 0x12 | 1 | Phase B power factor | ✅ Added |
| 14 | 19 | 0x13 | 1 | PadB (not used) | ✅ Added |
| 15 | 20 | 0x14 | 1 | Phase C voltage | ✅ Added |
| 16 | 21 | 0x15 | 1 | Phase C current | ✅ Added |
| 17 | 22 | 0x16 | 2 | Phase C active power | ✅ Added |
| 18 | 24 | 0x18 | 2 | Phase C forward energy (pulses) | ✅ Added |
| 19 | 26 | 0x1a | 2 | Phase C reverse energy (pulses) | ✅ Added |
| 20 | 28 | 0x1c | 1 | Phase C power factor | ✅ Added |
| 21 | 29 | 0x1d | 1 | PadC (not used) | ✅ Added |
| 22 | 30 | 0x1e | 1 | Frequency | ✅ Added |
| 23 | 31 | 0x1f | 1 | PadH (not used) | ✅ Added |
| 24 | 32 | 0x20 | 2 | Sum of power | ✅ Added |
| 25 | 34 | 0x22 | 2 | Sum of forward energy (pulses) | ✅ Added |
| 26 | 36 | 0x24 | 2 | Sum of reverse energy (pulses) | ✅ Added |
| 27 | 38 | 0x26 | 2 | Phase A reactive power | ✅ Added |
| 28 | 40 | 0x28 | 2 | Phase A inductive KVARH | ✅ Added |
| 29 | 42 | 0x2a | 2 | Phase A capacitive KVARH | ✅ Added |
| 30 | 44 | 0x2c | 2 | Phase B reactive power | ✅ Added |
| 31 | 46 | 0x2e | 2 | Phase B inductive KVARH | ✅ Added |
| 32 | 48 | 0x30 | 2 | Phase B capacitive KVARH | ✅ Added |
| 33 | 50 | 0x32 | 2 | Phase C reactive power | ✅ Added |
| 34 | 52 | 0x34 | 2 | Phase C inductive KVARH | ✅ Added |
| 35 | 54 | 0x36 | 2 | Phase C capacitive KVARH | ✅ Added |
| 36 | 56 | 0x38 | 8 | Serial number | ✅ Already implemented |
| 37 | 64 | 0x40 | 1 | Runtime in seconds | ✅ Added |

## Register Map Coverage

The register map JSON file now contains:
- **37 registers** from your specification (addresses 0x0-0x40)
- **46 registers** from the previous specification (addresses 0x48-0x91)
- **Total: 83 registers** covering both register map versions

## Register IDs in JSON Map

All registers have been added with descriptive IDs:

### Legacy Registers (0x0-0x40)
- `voltage_phase_a_legacy` (addr: 0)
- `current_phase_a_legacy` (addr: 1)
- `active_power_phase_a_legacy` (addr: 2)
- `forward_energy_phase_a_pulses` (addr: 4)
- `reverse_energy_phase_a_pulses` (addr: 6)
- `power_factor_phase_a_legacy` (addr: 8)
- `device_model` (addr: 9) - **NEW**: Model identification
- `voltage_phase_b_legacy` (addr: 10)
- `current_phase_b_legacy` (addr: 11)
- `active_power_phase_b_legacy` (addr: 12)
- `forward_energy_phase_b_pulses` (addr: 14)
- `reverse_energy_phase_b_pulses` (addr: 16)
- `power_factor_phase_b_legacy` (addr: 18)
- `pad_b` (addr: 19)
- `voltage_phase_c_legacy` (addr: 20)
- `current_phase_c_legacy` (addr: 21)
- `active_power_phase_c_legacy` (addr: 22)
- `forward_energy_phase_c_pulses` (addr: 24)
- `reverse_energy_phase_c_pulses` (addr: 26)
- `power_factor_phase_c_legacy` (addr: 28)
- `pad_c` (addr: 29)
- `frequency_legacy` (addr: 30)
- `pad_h` (addr: 31)
- `sum_power_legacy` (addr: 32)
- `sum_forward_energy_pulses` (addr: 34)
- `sum_reverse_energy_pulses` (addr: 36)
- `reactive_power_phase_a_legacy` (addr: 38)
- `inductive_kvarh_phase_a` (addr: 40)
- `capacitive_kvarh_phase_a` (addr: 42)
- `reactive_power_phase_b_legacy` (addr: 44)
- `inductive_kvarh_phase_b` (addr: 46)
- `capacitive_kvarh_phase_b` (addr: 48)
- `reactive_power_phase_c_legacy` (addr: 50)
- `inductive_kvarh_phase_c` (addr: 52)
- `capacitive_kvarh_phase_c` (addr: 54)
- `device_serial_number` (addr: 56) - Already implemented
- `runtime_seconds` (addr: 64) - **NEW**: Runtime counter

## Automatic Reading and Publication

Since the IAMMeter adapter now uses `JsonRegisterMixin` and `read_all_registers()`:

✅ **All 83 registers** will be automatically read during `poll()`
✅ **All register values** are published in `telemetry.extra["registers"]`
✅ **Proper scaling** is applied based on register definitions
✅ **Data types** are correctly decoded (U16, U32, S32, string)

## Accessing Register Values

All register values are available in telemetry:

```python
telemetry = await adapter.poll()
all_registers = telemetry.extra.get("registers", {})

# Access legacy registers (0x0-0x40)
voltage_a = all_registers.get("voltage_phase_a_legacy")
current_a = all_registers.get("current_phase_a_legacy")
power_a = all_registers.get("active_power_phase_a_legacy")
model = all_registers.get("device_model")  # 1:WEM3080, 2:WEM3080T, 3:WEM3046T, 4:WEM3050T
runtime = all_registers.get("runtime_seconds")

# Access newer registers (0x48-0x91)
voltage_a_new = all_registers.get("voltage_phase_a")
# ... etc
```

## Notes

- **Two Register Maps**: The JSON file now contains both register map versions:
  - Legacy map: addresses 0x0-0x40 (37 registers)
  - Extended map: addresses 0x48-0x91 (46 registers)
  
- **Model Detection**: Register `device_model` (address 0x9) can be used to identify the device model:
  - 1: WEM3080
  - 2: WEM3080T
  - 3: WEM3046T
  - 4: WEM3050T

- **Runtime Counter**: Register `runtime_seconds` (address 0x40) provides device uptime in seconds

- **Energy in Pulses**: Registers use "pulses" format where kWh = pulses/800

- **All registers are read**: The adapter reads all registers from the JSON map automatically, so all 83 registers will be available in telemetry data.

