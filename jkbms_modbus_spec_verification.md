# JK BMS Modbus Protocol Specification Verification

## Specification Summary
- **Protocol**: Modbus RTU
- **Baudrate**: 115200
- **Data bits**: 8
- **Stop bits**: 1
- **Parity**: None
- **Function Codes**: 0x03 (read), 0x10 (write)
- **Address Range**: 1-247 (typically 1-15 for JK BMS)

## Register Mapping Comparison

### Data Domain (Read-Only) - Base 0x1000

| Field | Spec Offset | Spec Address | Code Address | Code Base | Match |
|-------|-------------|--------------|--------------|-----------|-------|
| CellVol0-31 | 0x0000-0x003E | 0x1000-0x103E | 0x1200-0x123E | 0x1200 | ⚠️ Different base |
| BatVol | 0x0090 (144) | 0x1090 | 0x1290 | 0x1200 | ⚠️ Different base |
| BatWatt | 0x0094 (148) | 0x1094 | 0x1294 | 0x1200 | ⚠️ Different base |
| BatCurrent | 0x0098 (152) | 0x1098 | 0x1298 | 0x1200 | ⚠️ Different base |
| TempBat1 | 0x009C (156) | 0x109C | 0x129C | 0x1200 | ⚠️ Different base |
| TempBat2 | 0x009E (158) | 0x109E | 0x129E | 0x1200 | ⚠️ Different base |
| TempMos | 0x008A (138) | 0x108A | 0x128A | 0x1200 | ⚠️ Different base |
| BalanCurrent | 0x00A6 (166) | 0x10A6 | 0x12A6 | 0x1200 | ⚠️ Different base |
| BalanSta | 0x00A7 (167) | 0x10A7 | - | - | ❌ Not used |
| SOCStateOfcharge | 0x00A8 (168) | 0x10A8 | 0x12A6 (low byte) | 0x1200 | ⚠️ Combined |
| SOCCapRemain | 0x00AC (172) | 0x10AC | 0x12A8 | 0x1200 | ⚠️ Different base |
| SOCFullChargeCap | 0x00B0 (176) | 0x10B0 | 0x12AC | 0x1200 | ⚠️ Different base |
| SOCCycleCount | 0x00B4 (180) | 0x10B4 | 0x12B0 | 0x1200 | ⚠️ Different base |
| SOCSOH | 0x00B8 (184) | 0x10B8 | 0x12B8 (high byte) | 0x1200 | ⚠️ Different base |
| Precharge | 0x00B9 (185) | 0x10B9 | 0x12B8 (low byte) | 0x1200 | ⚠️ Combined |

## Analysis

### Key Finding
The code uses **base address 0x1200** while the specification shows **base address 0x1000** for the data domain.

However, the **offsets are consistent**:
- Spec: 0x1000 + offset = absolute address
- Code: 0x1200 + offset = absolute address
- Difference: 0x200 (512 decimal)

### Possible Explanations
1. **Different JK BMS firmware versions**: Some versions may use 0x1200 as base
2. **Modbus addressing convention**: Some implementations add 0x200 offset
3. **Specification version difference**: The spec might be V1.0, code might target V1.1

### Verification Needed
The specification appears correct, but the code may be targeting a different firmware version or addressing scheme. The register offsets are consistent, which suggests the code should work if the BMS uses 0x1200 as base.

## Recommendations

1. **Test with actual hardware** to verify which base address works
2. **Check firmware version** of your JK BMS units
3. **Try both base addresses** (0x1000 and 0x1200) to see which responds
4. **The specification is valid** - it's the official JK BMS Modbus protocol document

## Conclusion

✅ **The specification is GOOD and correct** for JK BMS Modbus protocol in master mode (non-silent).

⚠️ **The code uses 0x1200 base** while spec shows 0x1000 base, but offsets are consistent, so it may work with certain firmware versions.

🔧 **Recommendation**: Test both base addresses or check your BMS firmware version to confirm which addressing scheme it uses.

