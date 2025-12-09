# Intelligent Register Discovery - Enhanced Implementation

## 🧠 **AI-Like Analysis for Meaningful Register Discovery**

I've enhanced the Senergy Register Scanner with intelligent discovery capabilities that use a step-by-step approach to find meaningful register values by learning from known registers and trying different combinations of parameters.

## 🚀 **Key Enhancements**

### **1. Multi-Parameter Analysis**
The intelligent discovery now tries multiple combinations of:
- **Data Types**: U16, S16, U32, S32
- **Scaling Factors**: 0.001, 0.01, 0.1, 1.0, 10.0, 100.0
- **Units**: V, A, W, Hz, °C, %, Wh, kWh, Ah, s, min, h, ms, mA
- **Register Sizes**: 1 or 2 registers (16-bit or 32-bit)

### **2. Learning from Known Registers**
The system learns from nearby known registers:
- **Scaling Factors**: Extracts scaling factors from registers within 10 addresses
- **Units**: Learns units from nearby registers
- **Address Patterns**: Uses address ranges to predict likely units and scaling

### **3. Meaningful Value Detection**
Intelligent filtering based on realistic value ranges:
- **Voltage**: 10-500V (reasonable for solar systems)
- **Current**: 0.1-100A (typical inverter currents)
- **Power**: 1-10,000W (realistic power ranges)
- **Frequency**: 45-65Hz (grid frequency range)
- **Temperature**: -20°C to 80°C (operating range)
- **Percentage**: 0-100% (SOC, efficiency, etc.)

### **4. Scoring and Ranking System**
Each discovered register gets a score based on:
- **Value Range**: Higher scores for realistic values
- **Unit Presence**: Bonus for having appropriate units
- **Scaling Factor**: Bonus for precision scaling
- **ASCII Strings**: High score for readable text
- **Penalty**: Deduction for unrealistic values

## 📊 **How It Works**

### **Step 1: Raw Data Collection**
```python
# Read raw register values
raw_reg_info = await self.read_register(address)
```

### **Step 2: Multi-Interpretation Analysis**
```python
# Try different data types and sizes
interpretations = [
    {"type": "U16", "size": 1},
    {"type": "S16", "size": 1},
    {"type": "U32", "size": 2},
    {"type": "S32", "size": 2},
]
```

### **Step 3: Scaling Factor Learning**
```python
# Learn from nearby known registers
nearby_registers = []
for known_addr, known_info in self.known_registers.items():
    if abs(known_addr - address) <= 10:
        nearby_registers.append(known_info)
```

### **Step 4: Unit Pattern Recognition**
```python
# Address-based unit prediction
if 0x1000 <= address <= 0x1FFF:  # Real-time data
    units.extend(["V", "A", "W", "Hz", "°C", "%"])
elif 0x2000 <= address <= 0x2FFF:  # Battery data
    units.extend(["V", "A", "W", "%", "°C", "Wh", "kWh", "Ah"])
```

### **Step 5: Meaningful Value Filtering**
```python
# Check for realistic value ranges
if reg.unit == "V" and 10 <= abs(reg.value) <= 500:
    return True  # Meaningful voltage
elif reg.unit == "A" and 0.1 <= abs(reg.value) <= 100:
    return True  # Meaningful current
```

### **Step 6: Scoring and Ranking**
```python
# Calculate likelihood score
score = 0.0
if reg.unit == "V" and 10 <= abs(reg.value) <= 500:
    score += 2.0  # High score for realistic voltage
if reg.unit:  # Bonus for having unit
    score += 0.5
if reg.scale != 1.0:  # Bonus for precision
    score += 0.3
```

## 🎯 **Usage Examples**

### **Basic Intelligent Discovery**
```bash
python example_register_scan.py intelligent
```

### **Programmatic Usage**
```python
from senergy_register_scanner import SenergyRegisterScanner

scanner = SenergyRegisterScanner(port="/dev/ttyUSB0")
await scanner.connect()

# Perform intelligent discovery
results = await scanner.intelligent_discovery_analysis(0x3000, 0x3FFF)

# Access ranked results
top_registers = results['ranked'][:10]  # Top 10 most likely meaningful
voltage_registers = results['by_unit']['V']  # All voltage registers
```

## 📈 **Expected Results**

### **Before (Simple Discovery)**
```
0x3000: 2024 (raw value)
0x3001: 2305 (raw value)
0x3002: 5120 (raw value)
```

### **After (Intelligent Discovery)**
```
0x3000: 2024 (Year - U16, scale=1.0, unit="")
0x3001: 23.05 (Date - U16, scale=0.01, unit="")
0x3002: 51.20 (Time - U16, scale=0.01, unit="h")
```

## 🔍 **Analysis Output**

### **Console Output**
```
🧠 Starting Intelligent Register Discovery Analysis...
INTELLIGENT DISCOVERY MODE: Scanning 0x3000 to 0x3FFF
========================================================================================================================
Addr   | Type | Sz | Raw Values           | Value           | Description       
------------------------------------------------------------------------------------------------------------------------
0x3000 | U16  |  1 | [0x07E8]             | 2024            | Unknown U16 (scale=1.0, unit=)
0x3001 | U16  |  1 | [0x0901]             | 9.01            | Unknown U16 (scale=0.01, unit=)
0x3002 | U16  |  1 | [0x1400]             | 20.0 h          | Unknown U16 (scale=0.1, unit=h)

📊 DISCOVERY ANALYSIS RESULTS
==================================================
Total meaningful registers found: 15
Top 10 most likely meaningful registers:
--------------------------------------------------
 1. 0x3000: 2024 (U16, scale=1.0)
 2. 0x3001: 9.01 (U16, scale=0.01)
 3. 0x3002: 20.0 h (U16, scale=0.1)
```

### **File Output** (`intelligent_discovery_analysis.txt`)
```
Senergy Inverter - Intelligent Discovery Analysis
============================================================

Scan range: 0x3000 to 0x3FFF
Total meaningful registers: 15

TOP RANKED REGISTERS (Most Likely Meaningful):
--------------------------------------------------
  1. 0x3000 | U16 | 1 | 2024  | scale=1.0
  2. 0x3001 | U16 | 1 | 9.01  | scale=0.01
  3. 0x3002 | U16 | 1 | 20.0 h | scale=0.1

BREAKDOWN BY DATA TYPE:
------------------------------
U16 (12 registers):
  0x3000: 2024 (scale=1.0)
  0x3001: 9.01 (scale=0.01)

BREAKDOWN BY UNIT:
------------------------------
h (3 registers):
  0x3002: 20.0 (U16, scale=0.1)
  0x3003: 0.0 (U16, scale=0.1)
```

## 🎯 **Benefits**

### **1. Higher Success Rate**
- **Before**: Found raw values, many meaningless
- **After**: Finds meaningful values with proper units and scaling

### **2. Reduced Manual Analysis**
- **Before**: Manual interpretation of raw values
- **After**: Automatic interpretation with confidence scoring

### **3. Better Register Identification**
- **Before**: Unknown registers with raw data
- **After**: Categorized registers with likely meanings

### **4. Time Savings**
- **Before**: Hours of manual analysis
- **After**: Automated analysis with ranked results

## 🔧 **Technical Implementation**

### **Key Methods Added**
- `_analyze_unknown_register()`: Multi-parameter analysis
- `_get_learned_scaling_factors()`: Learning from nearby registers
- `_get_learned_units()`: Unit pattern recognition
- `_is_meaningful_value()`: Value range validation
- `_rank_discovered_registers()`: Scoring and ranking
- `intelligent_discovery_analysis()`: Complete analysis workflow

### **Scoring Algorithm**
```python
def calculate_score(reg: RegisterInfo) -> float:
    score = 0.0
    
    # Base score for having a value
    if reg.value is not None:
        score += 1.0
    
    # Bonus for reasonable value ranges
    if reg.unit == "V" and 10 <= abs(reg.value) <= 500:
        score += 2.0
    elif reg.unit == "A" and 0.1 <= abs(reg.value) <= 100:
        score += 2.0
    # ... more range checks
    
    # Bonus for having a unit
    if reg.unit:
        score += 0.5
    
    # Bonus for scaling factor
    if reg.scale != 1.0:
        score += 0.3
    
    return score
```

## 🚀 **Perfect for Your Use Case**

This intelligent discovery system is ideal for:
1. **Finding missing registers** with meaningful data
2. **Understanding register purposes** through value analysis
3. **Building comprehensive register maps** for your monitoring system
4. **Identifying undocumented features** in your inverter
5. **Reducing manual analysis time** from hours to minutes

The system will help you discover registers that contain useful data like timestamps, configuration values, status flags, and measurement data that aren't documented in the specification.
