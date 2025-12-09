# IAMMeter Integration Guide

## IAMMeter Specifications

### Device Models

#### Single-Phase Wi-Fi Energy Meter (WEM3080)
- **Purpose**: Monitors bidirectional energy flow in single-phase systems
- **Mounting**: DIN-rail mounting
- **Standards**: CE, FCC, RoHs, RCM compliant
- **Open API**: Yes, for custom server integration

#### Three-Phase Wi-Fi Energy Meter (WEM3080T)
- **Purpose**: Monitors bidirectional energy flow in three-phase or split-phase systems
- **Mounting**: DIN-rail mounting
- **Standards**: CE, FCC, UL, RoHs, RCM compliant
- **Open API**: Yes, for custom server integration

### Electrical Characteristics

- **Input Voltage**: 100–380 V AC
- **Current Transformer (CT) Rating**: 100A (other ratings optional)
- **Measurement Accuracy**:
  - Voltage: ±1.0%
  - Current: ±1.0%
  - Active Power: ±1.0%
  - Active Energy: Class 1 (IEC62053-21)
- **Power Consumption**: ≤2W (220VAC input)

### Environmental Conditions

- **Operating Temperature**: -20 to +60℃

### Communication Interfaces

IAMMeter devices support multiple integration methods:

1. **Modbus/TCP**
   - Data retrieval up to 1 sample per second
   - Suitable for industrial systems (ICS, DCS, SCADA)
   - Network-based (Ethernet/Wi-Fi)

2. **MQTT**
   - Publish data to third-party MQTT brokers
   - Real-time monitoring
   - Integration with Home Assistant and other platforms

3. **HTTP/HTTPS**
   - Upload data to specified servers
   - Flexible integration with custom backends
   - POST requests with JSON payloads

4. **RESTful API**
   - Local APIs for data retrieval
   - Simple HTTP GET requests
   - Access to all available data

5. **TCP/TLS**
   - Secure TCP connections
   - Encrypted data transmission

## Integration Architecture

### Option 1: HTTP/HTTPS Webhook Integration (Recommended)

IAMMeter can be configured to POST data to your backend API endpoint.

**Advantages:**
- Simple setup (configure device IP/URL)
- No polling required
- Real-time data delivery
- Works well with existing FastAPI backend

**Implementation Steps:**

1. **Create API Endpoint** (`solarhub/api_server.py`):
```python
@app.post("/api/iammeter/webhook")
async def iammeter_webhook(request: Request):
    """
    Receive data from IAMMeter device via HTTP POST.
    Expected payload format (based on IAMMeter documentation):
    {
        "Serial": "device_serial",
        "Data": [
            {
                "Voltage": 230.5,
                "Current": 10.2,
                "Power": 2345.1,
                "Energy": 1234.56,
                "Frequency": 50.0,
                "PF": 0.95
            }
        ],
        "Time": "2024-01-15T10:30:00Z"
    }
    """
    try:
        data = await request.json()
        # Process and store IAMMeter data
        # Map to your telemetry format
        # Store in database via DataLogger
        return {"status": "ok"}
    except Exception as e:
        log.error(f"IAMMeter webhook error: {e}")
        return {"status": "error", "message": str(e)}, 400
```

2. **Create IAMMeter Data Processor** (`solarhub/adapters/iammeter.py`):
```python
from typing import Dict, Any, Optional
from datetime import datetime
from solarhub.models import Telemetry
from solarhub.logging.logger import DataLogger
import logging

log = logging.getLogger(__name__)

class IAMMeterProcessor:
    """
    Processes data from IAMMeter devices received via webhook.
    Maps IAMMeter data format to internal Telemetry model.
    """
    
    def __init__(self, device_id: str, logger: DataLogger):
        self.device_id = device_id
        self.logger = logger
    
    def parse_iammeter_data(self, raw_data: Dict[str, Any]) -> Optional[Telemetry]:
        """
        Parse IAMMeter webhook payload into Telemetry object.
        
        IAMMeter typically provides:
        - Voltage (V)
        - Current (A)
        - Power (W) - can be positive (import) or negative (export)
        - Energy (kWh) - cumulative
        - Frequency (Hz)
        - Power Factor (PF)
        """
        try:
            # Extract data array (IAMMeter can have multiple channels)
            data_array = raw_data.get("Data", [])
            if not data_array:
                log.warning(f"No data array in IAMMeter payload for {self.device_id}")
                return None
            
            # Use first channel (or aggregate if multiple)
            channel_data = data_array[0]
            
            # Map IAMMeter fields to Telemetry model
            # Note: IAMMeter measures grid connection, so this maps to grid_power_w
            power_w = float(channel_data.get("Power", 0))
            
            # Determine import vs export based on power sign
            # Positive = import (consuming from grid)
            # Negative = export (feeding to grid)
            grid_power_w = power_w
            grid_import = power_w if power_w > 0 else 0
            grid_export = abs(power_w) if power_w < 0 else 0
            
            # Energy is cumulative in kWh, convert to Wh for consistency
            energy_kwh = float(channel_data.get("Energy", 0))
            energy_wh = energy_kwh * 1000
            
            # Create telemetry object
            telemetry = Telemetry(
                inverter_id=self.device_id,
                timestamp=datetime.now(),
                # Grid measurements
                grid_power_w=grid_power_w,
                grid_voltage_v=float(channel_data.get("Voltage", 0)),
                grid_current_a=float(channel_data.get("Current", 0)),
                grid_frequency_hz=float(channel_data.get("Frequency", 50.0)),
                # Energy totals
                today_import_energy=energy_wh,  # This would need daily reset logic
                today_export_energy=0,  # Would need separate tracking
                # Power factor
                power_factor=float(channel_data.get("PF", 1.0)),
            )
            
            return telemetry
            
        except Exception as e:
            log.error(f"Error parsing IAMMeter data: {e}", exc_info=True)
            return None
    
    async def process_and_store(self, raw_data: Dict[str, Any]):
        """Process IAMMeter data and store in database."""
        telemetry = self.parse_iammeter_data(raw_data)
        if telemetry:
            # Store via DataLogger
            await self.logger.log_telemetry(telemetry)
            log.info(f"Stored IAMMeter data for {self.device_id}: "
                    f"Power={telemetry.grid_power_w}W, "
                    f"Voltage={telemetry.grid_voltage_v}V")
```

3. **Register IAMMeter Devices in Config** (`config.yaml`):
```yaml
# Add IAMMeter devices section
iammeter_devices:
  - id: "grid_meter_1"
    name: "Main Grid Connection Meter"
    serial: "WEM3080_XXXXXX"
    webhook_url: "http://your-server:8000/api/iammeter/webhook"
    location: "main_panel"
    ct_ratio: 100  # Current transformer ratio
    voltage_rating: 230  # Nominal voltage
```

4. **Update API Server** to handle webhooks:
```python
from solarhub.adapters.iammeter import IAMMeterProcessor

# In api_server.py, add webhook handler
@app.post("/api/iammeter/webhook")
async def iammeter_webhook(request: Request, app: SolarApp = Depends(get_app)):
    data = await request.json()
    device_serial = data.get("Serial")
    
    # Find device config
    device_config = None
    for dev in app.cfg.iammeter_devices or []:
        if dev.serial == device_serial:
            device_config = dev
            break
    
    if not device_config:
        log.warning(f"Unknown IAMMeter device: {device_serial}")
        return {"status": "error", "message": "Unknown device"}, 400
    
    # Process data
    processor = IAMMeterProcessor(device_config.id, app.logger)
    await processor.process_and_store(data)
    
    return {"status": "ok"}
```

### Option 2: MQTT Integration

IAMMeter can publish to MQTT broker that your system already uses.

**Advantages:**
- Leverages existing MQTT infrastructure
- Real-time data via MQTT subscriptions
- Works with Home Assistant integration

**Implementation Steps:**

1. **Subscribe to IAMMeter MQTT Topics** in `solarhub/app.py`:
```python
# In SolarApp.__init__ or init()
# IAMMeter typically publishes to: iammeter/{serial}/data
self.mqtt.subscribe(f"iammeter/+/data", self._handle_iammeter_mqtt)

async def _handle_iammeter_mqtt(self, topic: str, payload: bytes):
    """Handle IAMMeter MQTT messages."""
    try:
        # Parse topic: iammeter/{serial}/data
        parts = topic.split("/")
        if len(parts) < 3:
            return
        device_serial = parts[1]
        
        # Find device config
        device_config = None
        for dev in self.cfg.iammeter_devices or []:
            if dev.serial == device_serial:
                device_config = dev
                break
        
        if not device_config:
            return
        
        # Parse JSON payload
        import json
        data = json.loads(payload.decode())
        
        # Process data
        processor = IAMMeterProcessor(device_config.id, self.logger)
        await processor.process_and_store(data)
        
    except Exception as e:
        log.error(f"Error handling IAMMeter MQTT: {e}", exc_info=True)
```

### Option 3: Modbus/TCP Integration

For direct Modbus/TCP communication (polling-based).

**Advantages:**
- Direct control over polling frequency
- Standard Modbus protocol
- Can integrate with existing Modbus infrastructure

**Implementation Steps:**

1. **Create IAMMeter Modbus Adapter** (`solarhub/adapters/iammeter_modbus.py`):
```python
from typing import Optional, Dict, Any
from pymodbus.client import AsyncModbusTcpClient
from solarhub.adapters.base import InverterAdapter
from solarhub.models import Telemetry
import logging

log = logging.getLogger(__name__)

class IAMMeterModbusAdapter(InverterAdapter):
    """
    IAMMeter adapter using Modbus/TCP protocol.
    Polls device over network (Ethernet/Wi-Fi).
    """
    
    def __init__(self, inv):
        super().__init__(inv)
        self.client: Optional[AsyncModbusTcpClient] = None
        self.host = inv.adapter.host  # IP address
        self.port = inv.adapter.port or 502  # Modbus TCP port
        self.unit_id = inv.adapter.unit_id or 1  # Modbus unit ID
        
        # IAMMeter Modbus register map (example - verify with actual device)
        # These addresses may vary by model
        self.registers = {
            "voltage": 0x0000,  # Voltage (V) - 1 register, scale 10
            "current": 0x0001,  # Current (A) - 1 register, scale 100
            "power": 0x0002,   # Active Power (W) - 2 registers (signed)
            "energy": 0x0004,   # Active Energy (kWh) - 2 registers
            "frequency": 0x0006,  # Frequency (Hz) - 1 register, scale 100
            "pf": 0x0007,      # Power Factor - 1 register, scale 1000
        }
    
    async def connect(self):
        """Connect to IAMMeter via Modbus/TCP."""
        try:
            from pymodbus.client import AsyncModbusTcpClient
            self.client = AsyncModbusTcpClient(
                host=self.host,
                port=self.port,
            )
            ok = await self.client.connect()
            if ok and self.client.connected:
                log.info(f"Connected to IAMMeter at {self.host}:{self.port}")
            else:
                raise RuntimeError(f"Failed to connect to IAMMeter at {self.host}:{self.port}")
        except Exception as e:
            log.error(f"Error connecting to IAMMeter: {e}", exc_info=True)
            raise
    
    async def close(self):
        """Close Modbus/TCP connection."""
        if self.client:
            await self.client.close()
            self.client = None
    
    async def poll(self) -> Telemetry:
        """Poll IAMMeter device and return Telemetry."""
        if not self.client or not self.client.connected:
            await self.connect()
        
        try:
            # Read voltage (1 register, scale 10)
            voltage_reg = await self.client.read_holding_registers(
                self.registers["voltage"], 1, unit=self.unit_id
            )
            voltage = voltage_reg.registers[0] / 10.0 if voltage_reg.registers else 0
            
            # Read current (1 register, scale 100)
            current_reg = await self.client.read_holding_registers(
                self.registers["current"], 1, unit=self.unit_id
            )
            current = current_reg.registers[0] / 100.0 if current_reg.registers else 0
            
            # Read power (2 registers, signed 32-bit)
            power_reg = await self.client.read_holding_registers(
                self.registers["power"], 2, unit=self.unit_id
            )
            if power_reg.registers and len(power_reg.registers) >= 2:
                # Combine two 16-bit registers into signed 32-bit
                power = (power_reg.registers[0] << 16) | power_reg.registers[1]
                if power & 0x80000000:  # Check sign bit
                    power = power - 0x100000000  # Convert to signed
            else:
                power = 0
            
            # Read energy (2 registers, unsigned 32-bit, in kWh)
            energy_reg = await self.client.read_holding_registers(
                self.registers["energy"], 2, unit=self.unit_id
            )
            if energy_reg.registers and len(energy_reg.registers) >= 2:
                energy_kwh = ((energy_reg.registers[0] << 16) | energy_reg.registers[1]) / 1000.0
            else:
                energy_kwh = 0
            
            # Read frequency (1 register, scale 100)
            freq_reg = await self.client.read_holding_registers(
                self.registers["frequency"], 1, unit=self.unit_id
            )
            frequency = freq_reg.registers[0] / 100.0 if freq_reg.registers else 50.0
            
            # Read power factor (1 register, scale 1000)
            pf_reg = await self.client.read_holding_registers(
                self.registers["pf"], 1, unit=self.unit_id
            )
            power_factor = pf_reg.registers[0] / 1000.0 if pf_reg.registers else 1.0
            
            # Create Telemetry object
            from datetime import datetime
            telemetry = Telemetry(
                inverter_id=self.inv.id,
                timestamp=datetime.now(),
                grid_power_w=power,
                grid_voltage_v=voltage,
                grid_current_a=current,
                grid_frequency_hz=frequency,
                power_factor=power_factor,
                today_import_energy=energy_kwh * 1000,  # Convert to Wh
            )
            
            return telemetry
            
        except Exception as e:
            log.error(f"Error polling IAMMeter: {e}", exc_info=True)
            raise
    
    async def handle_command(self, cmd: Dict[str, Any]):
        """IAMMeter is read-only, no commands supported."""
        log.warning("IAMMeter does not support commands")
```

2. **Register Adapter** in `solarhub/app.py`:
```python
from solarhub.adapters.iammeter_modbus import IAMMeterModbusAdapter

ADAPTERS = {
    "senergy": SenergyAdapter,
    "powdrive": PowdriveAdapter,
    "iammeter": IAMMeterModbusAdapter,  # Add this
}
```

3. **Configure in config.yaml**:
```yaml
inverters:
  - id: "grid_meter_1"
    name: "Main Grid Meter"
    adapter:
      type: "iammeter"
      host: "192.168.1.100"  # IAMMeter IP address
      port: 502              # Modbus TCP port
      unit_id: 1             # Modbus unit ID
```

## Configuration Schema

Add to `solarhub/config.py`:

```python
from pydantic import BaseModel
from typing import Optional, List

class IAMMeterDeviceConfig(BaseModel):
    id: str
    name: str
    serial: str
    webhook_url: Optional[str] = None
    location: Optional[str] = None
    ct_ratio: int = 100
    voltage_rating: float = 230.0

class HubConfig(BaseModel):
    # ... existing fields ...
    iammeter_devices: Optional[List[IAMMeterDeviceConfig]] = None
```

## Data Flow Integration

### Energy Calculation Integration

IAMMeter data should integrate with your existing `EnergyCalculator`:

1. **Grid Import/Export Tracking**: IAMMeter provides grid power, which feeds into:
   - `grid_power_w` → used for real-time monitoring
   - `today_import_energy` / `today_export_energy` → used for daily energy calculations

2. **Billing Integration**: IAMMeter data can be used for:
   - Net metering calculations
   - Grid import/export tracking for billing cycles
   - TOU (Time-of-Use) tariff calculations

### API Endpoints

Add endpoints to expose IAMMeter data:

```python
@app.get("/api/iammeter/devices")
async def get_iammeter_devices(app: SolarApp = Depends(get_app)):
    """List all configured IAMMeter devices."""
    devices = app.cfg.iammeter_devices or []
    return {"devices": [dev.dict() for dev in devices]}

@app.get("/api/iammeter/{device_id}/latest")
async def get_iammeter_latest(device_id: str, app: SolarApp = Depends(get_app)):
    """Get latest reading from IAMMeter device."""
    # Query latest telemetry for this device
    # Return formatted data
    pass
```

## Testing

1. **Test Webhook** (if using HTTP):
```bash
curl -X POST http://localhost:8000/api/iammeter/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "Serial": "WEM3080_XXXXXX",
    "Data": [{
      "Voltage": 230.5,
      "Current": 10.2,
      "Power": 2345.1,
      "Energy": 1234.56,
      "Frequency": 50.0,
      "PF": 0.95
    }],
    "Time": "2024-01-15T10:30:00Z"
  }'
```

2. **Test Modbus/TCP** (if using Modbus):
   - Use Modbus client tools to verify register addresses
   - Check device documentation for exact register map

## Notes

- **Register Map**: IAMMeter register addresses may vary by model. Verify with device documentation.
- **Energy Reset**: IAMMeter energy is cumulative. You'll need to track daily resets or calculate deltas.
- **Multiple Channels**: Some IAMMeter models support multiple measurement channels (e.g., 3-phase).
- **CT Ratio**: Account for current transformer ratio when calculating actual current/power.

## Recommended Approach

For your solar monitoring system, **HTTP/HTTPS webhook integration (Option 1)** is recommended because:
1. Simplest to implement
2. Real-time data delivery
3. No polling overhead
4. Works well with FastAPI backend
5. Device handles retries and connection management

The device can be configured via its web interface to POST data to your API endpoint at regular intervals (e.g., every 5-10 seconds).

