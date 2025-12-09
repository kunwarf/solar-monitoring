# Custom Register Reading Enhancement Summary

## ✅ **Enhancement Complete: Specific Register Reading with Custom Parameters**

### **Overview:**
Enhanced both `senergy_register_scanner.py` and `example_register_scan.py` to support reading specific registers with user-defined parameters including address, length, unit, scale, and data type.

## **🔧 New Features Added:**

### **1. CustomRegisterRequest Dataclass:**
```python
@dataclass
class CustomRegisterRequest:
    """Custom register reading request with user-specified parameters."""
    address: int          # Register address (e.g., 0x2000)
    length: int           # Number of registers to read (1, 2, 3, etc.)
    unit: str = ""        # Unit for display (e.g., "W", "V", "A", "%", "kWh")
    scale: float = 1.0    # Scaling factor to apply to raw value
    data_type: str = "auto"  # "auto", "uint16", "int16", "uint32", "int32", "float32", "ascii"
    description: str = "" # Optional description
```

### **2. New Methods in SenergyRegisterScanner:**

#### **`read_custom_register(request: CustomRegisterRequest)`**
- Reads a single register with custom parameters
- Supports auto-detection of data type
- Applies custom scaling and unit formatting
- Returns `RegisterInfo` object with formatted results

#### **`read_multiple_custom_registers(requests: List[CustomRegisterRequest])`**
- Reads multiple registers with different parameters
- Processes each register sequentially with delays
- Returns list of `RegisterInfo` objects

#### **`_auto_detect_data_type(raw_values: List[int], length: int)`**
- Automatically detects data type based on register length and values
- Smart detection for ASCII strings
- Fallback to appropriate data types

### **3. Enhanced Example Script:**

#### **New Mode: `custom`**
```bash
python example_register_scan.py custom
```

#### **5 Comprehensive Examples:**

**Example 1: Single Register with Custom Parameters**
```python
soc_request = CustomRegisterRequest(
    address=0x2000,
    length=1,
    unit="%",
    scale=0.1,
    data_type="U16",
    description="Battery State of Charge"
)
```

**Example 2: Multiple Registers with Different Parameters**
```python
custom_requests = [
    CustomRegisterRequest(address=0x2002, length=1, unit="A", scale=0.01, data_type="U16", description="Battery Current"),
    CustomRegisterRequest(address=0x2003, length=1, unit="W", scale=1.0, data_type="U16", description="Battery Power"),
    CustomRegisterRequest(address=0x2004, length=1, unit="°C", scale=0.1, data_type="U16", description="Battery Temperature"),
    CustomRegisterRequest(address=0x2005, length=2, unit="kWh", scale=0.01, data_type="U32", description="Battery Daily Charge Energy")
]
```

**Example 3: Auto-Detection Mode**
```python
unknown_request = CustomRegisterRequest(
    address=0x3000,
    length=1,
    unit="",
    scale=1.0,
    data_type="auto",  # Auto-detect data type
    description="Unknown Register (Auto-detect)"
)
```

**Example 4: Interactive Mode**
- Prompts user for register address, length, unit, scale, data type, and description
- Real-time register reading with custom parameters
- Supports hex address input (0x2000) or decimal (8192)

## **🎯 Usage Examples:**

### **Command Line Usage:**
```bash
# Run custom register reading examples
python example_register_scan.py custom

# Get help
python example_register_scan.py help
```

### **Programmatic Usage:**
```python
from senergy_register_scanner import SenergyRegisterScanner, CustomRegisterRequest

# Create scanner
scanner = SenergyRegisterScanner(port="/dev/ttyUSB0", baudrate=9600, slave_id=1)
await scanner.connect()

# Read specific register
request = CustomRegisterRequest(
    address=0x2000,      # Battery SOC register
    length=1,            # Single register
    unit="%",            # Percentage unit
    scale=0.1,           # Scale factor
    data_type="U16",     # 16-bit unsigned integer
    description="Battery State of Charge"
)

result = await scanner.read_custom_register(request)
if result:
    print(f"Battery SOC: {result.value} {result.unit}")
```

## **📊 Supported Data Types:**

| Data Type | Description | Use Case |
|-----------|-------------|----------|
| `auto` | Auto-detect based on length and values | Unknown registers |
| `uint16` | 16-bit unsigned integer | Single register values |
| `int16` | 16-bit signed integer | Single register with negative values |
| `uint32` | 32-bit unsigned integer | Two registers combined |
| `int32` | 32-bit signed integer | Two registers with negative values |
| `float32` | 32-bit floating point | Two registers as float |
| `ascii` | ASCII string | Multiple registers as text |

## **🔧 Supported Units:**

| Unit | Description | Example |
|------|-------------|---------|
| `V` | Volts | Battery voltage |
| `A` | Amperes | Battery current |
| `W` | Watts | Power |
| `%` | Percentage | State of charge |
| `°C` | Celsius | Temperature |
| `kWh` | Kilowatt-hours | Energy |
| `Hz` | Hertz | Frequency |
| `ASCII` | Text string | Device model, serial number |

## **⚡ Key Features:**

### **1. Flexible Parameter Specification:**
- **Address**: Hex (0x2000) or decimal (8192) format
- **Length**: 1, 2, 3, or more registers
- **Unit**: Any string for display formatting
- **Scale**: Any float value for unit conversion
- **Data Type**: Auto-detection or manual specification

### **2. Smart Auto-Detection:**
- Automatically detects data type based on register length
- Identifies ASCII strings in multi-register values
- Fallback to appropriate data types

### **3. Interactive Mode:**
- Real-time parameter input
- Immediate register reading and display
- User-friendly prompts and error handling

### **4. Batch Processing:**
- Read multiple registers with different parameters
- Sequential processing with delays
- Comprehensive result reporting

## **✅ Verification:**
- ✅ Both files compile successfully
- ✅ All imports work correctly
- ✅ New functionality integrated seamlessly
- ✅ Backward compatibility maintained

## **📁 Files Enhanced:**
- `senergy_register_scanner.py` - Added `CustomRegisterRequest` dataclass and custom reading methods
- `example_register_scan.py` - Added comprehensive examples and interactive mode

## **🚀 Usage Instructions:**

1. **Configure connection settings** in the script (port, baudrate, slave_id)
2. **Run custom examples**: `python example_register_scan.py custom`
3. **Use interactive mode** to read any register with custom parameters
4. **Integrate into your code** using the `CustomRegisterRequest` class

The enhanced scanner now provides complete flexibility for reading specific registers with any combination of parameters, making it perfect for discovering and testing unknown registers or reading known registers with custom formatting.
