# USB Device Auto-Detection and Auto-Recovery System Design

## Overview

This document describes the design for an automatic USB device detection and auto-recovery system that will:
1. Automatically discover USB-connected devices on startup
2. Identify device types by probing with test commands
3. Handle device disconnections gracefully with auto-recovery
4. Maintain device availability status and retry logic

## Goals

- **Zero-Configuration Setup**: Automatically detect and configure USB devices without manual port assignment
- **Robust Recovery**: Handle device disconnections gracefully with automatic retry
- **Device Identification**: Identify device types by probing with test commands
- **Non-Blocking**: Discovery and recovery should not block normal operations

## Architecture

### Components

1. **Device Discovery Service** (`solarhub/device_discovery.py`)
   - Scans USB ports on startup
   - Probes devices to identify type
   - Creates device configurations automatically

2. **Device Registry** (`solarhub/device_registry.py`)
   - Tracks discovered devices and their ports
   - Manages device availability status
   - Handles port reassignment on reconnection

3. **Auto-Recovery Manager** (`solarhub/auto_recovery.py`)
   - Monitors device health during polling
   - Implements retry logic with exponential backoff
   - Temporarily disables failed devices

4. **Enhanced Adapter Base** (modify `solarhub/adapters/base.py`)
   - Add device identification methods
   - Add health check methods
   - Add connection state tracking

## Detailed Design

### 1. Device Discovery Service

#### 1.1 Discovery Process

```
STARTUP DISCOVERY FLOW (Optimized):

PHASE 1: Check Known Devices from Database
1. Load all known devices from database (with saved ports)
2. For each known device:
   a. Try to connect to its saved port
   b. Read serial number through command/register to query device to verify it's the same device
      if there is no command for serial number avaialble then we can use an other register/command.
   c. If found and verified:
      * Mark device as "active" and port as "used"
      * Update last_seen timestamp
      * Continue to next known device
   d. if not found, Scan all available ports (excluding already-used ports)
   b. For each available port:
      - Try to connect with device's known parameters
      -  Read serial number through command/register to query device to verify it's the same device
         if there is no command for serial number avaialble then we can use an other register/command.
      - If found and serial matches:
         * Update device port assignment
         * Mark device as "active" and port as "used"
         * Update port_history
         * Break (device found, stop searching)
      - If not found:
         * Continue to next port
      - IF not found after attempting all available ports then mark this device as missing.
   
3. For each device marked as "missing":
   
   c. If device not found on any port:
      * Mark device as "missing" with 15-minute retry timer
      * Set next_retry_time = now + 15 minutes
      * Status = "recovering"

PHASE 2: Discover New Devices (if ports available)
4. Get list of unused ports (ports not assigned to any device)
5. For each unused port:
   a. For each supported device type :
      - Try to connect with device-specific parameters
      - Execute identification probe (read test register/command)
      - Read serial number
      - If successful:
         * Check if serial number exists in database
         * If exists: Update port assignment (device moved)
         * If new: Create new device entry with device_id = {type}_{serial_last6}
         * Mark port as used
         * Break (device found on this port, move to next port)
      - If failed:
         * Close connection
         * Try next device type
   b. If no device found on port, mark port as "available" (no device)

PHASE 3: Finalize and Cleanup
6. Check if all available ports have been scanned
7. If all ports scanned and all devices found:
   a. For any devices still marked as "missing":
      * These devices were not found on any port
      * Since all ports are exhausted and all devices found:
        → Device is likely decommissioned/permanently removed
      * Permanently disable device (status = "permanently_disabled")
      * Log warning for administrator attention
8. Save all device configurations to database
9. Start normal polling loop

STOP CONDITION:
- Discovery stops when all available USB ports are exhausted
- No need to continue scanning once all ports are checked
```

#### 1.2 Device Identification Probes

Each adapter type will have a unique identification method that includes reading the serial number:

**Senergy Inverter:**
- Step 1: Connect to device via Modbus RTU/TCP
- Step 2: Read device serial number register to verify it's Senergy and get serial number:
  - Register: Address 6672 (decimal), 8 registers (16 bytes)
  - Type: Holding register, ASCII encoded string
  - Register map entry: `{"id": "device_serial_number", "addr": 6672, "size": 8, "type": "U16", "kind": "holding", "unit": "ascii"}`
  - Expected format: "1234-123456789" (example)
- Implementation:
  - `check_connectivity()`: Reads register 6672 to verify device responds
  - `read_serial_number()`: Reads register 6672 and decodes ASCII to get serial number
- Expected response: Valid register values and readable serial number (minimum 3 characters)
- Timeout: 2 seconds per step

**Powdrive Inverter:**
- Step 1: Connect to device via Modbus RTU/TCP
- Step 2: Read device serial number register to verify it's Powdrive and get serial number:
  - Register: Address 3 (decimal), 5 registers (10 bytes)
  - Type: Holding register, ASCII encoded string
  - Register map entry: `{"id": "device_serial_number", "addr": 3, "size": 5, "type": "U16", "kind": "holding", "encoder": "ascii"}`
  - Expected format: ASCII string (up to 10 characters)
- Implementation:
  - `check_connectivity()`: Reads register 3 to verify device responds
  - `read_serial_number()`: Reads register 3 and decodes ASCII to get serial number
- Expected response: Valid register values and readable serial number (minimum 3 characters)
- Timeout: 2 seconds per step

**Pytes Battery:**
- Step 1: use Send identification command - verify it's Pytes
- Step 2: Read battery serial number from device info
- Expected response: Valid battery data and serial number
- Timeout: 2 seconds per step

**IAMMeter:**
- Step 1: Read register `0x0038` (serial number) - verify it's IAMMeter
- Step 2: Read device serial number from Modbus holding registers (address 0x38, 8 registers)
- Expected response: Valid serial number (ASCII encoded, 16 bytes)
- Timeout: 2 seconds per step
- Note: IAMMeter serial number is stored at address 0x38 (56 decimal), 8 registers (16 bytes) containing ASCII-encoded serial number

**Serial Number Format:**
- Serial numbers are normalized to uppercase alphanumeric strings
- Special characters are removed
- Used as primary key for device matching

#### 1.3 Discovery Priority

Device types will be tried in this order (configurable):
1. Battery adapters (Pytes) - highest priority
2. Inverter adapters (Senergy, Powdrive)
3. Energy meters (IAMMeter)

Reason: Battery data is critical, inverters are primary, meters are secondary.

#### 1.4 Device Identification by Serial Number

**Serial Number-Based Identification:**
- Each device type will have a method to read its serial number
- Serial number is the primary identifier (not port)
- Port can change, but serial number is permanent

**Device Matching Logic:**
```
When device discovered on port:
1. Read device serial number
2. Query database for devices with same serial number and type
3. If found:
   - Match found: This is the same device (port may have changed)
   - Reuse existing configuration
   - Update port assignment
   - Mark as "reconnected"
4. If not found:
   - New device: Serial number not in database
   - Create new device entry
   - Generate device ID: {device_type}_{serial_last6} (e.g., `senergy_123456`)
   - Save to database
```

**Serial Number Reading Methods:**
- **Senergy**: Read serial number register (typically 0x0010-0x0015, ASCII)
- **Powdrive**: Read serial number register (device-specific)
- **Pytes**: Read battery serial number from device info
- **IAMMeter**: Read device serial from Modbus register

#### 1.5 Configuration Generation

When a device is discovered:
- **If existing device (serial match)**: Reuse existing config, update port
- **If new device**: Generate device ID from serial number: `{device_type}_{serial_last6}`
  - Example: Serial "SN1234567890" → Device ID "senergy_456789"
  - Format: Take last 6 alphanumeric characters from serial number
  - Normalize: Uppercase, alphanumeric only (remove special characters)
- Create minimal configuration with discovered parameters
- Save to database with serial number as key
- Port assignment is dynamic (updated on each discovery)

#### 1.6 Device ID Usage

The device ID (`{device_type}_{serial_last6}`) is used consistently throughout the system:

**Home Assistant Integration:**
- Entity IDs: `sensor.{device_id}_power`, `sensor.{device_id}_voltage`, etc.
- Device name: `{device_type} {serial_last6}` (e.g., "Senergy 456789")
- Unique ID: `{device_id}` for device tracking

**API Endpoints:**
- Filter by device: `/api/now?inverter_id={device_id}`
- Device status: `/api/devices/{device_id}/status`
- Device commands: `/api/devices/{device_id}/command`

**MQTT Topics:**
- State: `{base_topic}/{device_id}/state`
- Commands: `{base_topic}/{device_id}/cmd`
- Availability: `{base_topic}/{device_id}/availability`

**Database Queries:**
- Filter telemetry by device_id
- Track device history and statistics
- Device-specific configurations

**Examples:**
- Serial "SN1234567890" → Device ID "senergy_456789"
- Serial "PD9876543210" → Device ID "powdrive_43210"
- Serial "PYTES-BAT-001" → Device ID "pytes_bat001"

### 2. Device Registry

#### 2.1 Registry Structure

```python
class DeviceEntry:
    device_id: str  # Generated from serial: {type}_{serial_last6}
    device_type: str  # "senergy", "powdrive", "pytes", "iammeter"
    serial_number: str  # Device serial number (primary identifier)
    port: str  # "/dev/ttyUSB0", "COM3", etc. (dynamic, can change)
    last_known_port: Optional[str]  # Last port where device was found
    adapter_config: InverterAdapterConfig | BatteryAdapterConfig
    adapter_instance: InverterAdapter | BatteryAdapter
    status: DeviceStatus  # "active", "recovering", "permanently_disabled"
    last_seen: datetime
    failure_count: int
    next_retry_time: Optional[datetime]
    discovery_timestamp: datetime
    first_discovered: datetime  # First time this device was discovered
    port_history: List[str]  # Track port changes over time
    is_auto_discovered: bool  # True if discovered automatically, False if manual config
```

#### 2.2 Registry Operations

- `register_device(device_entry)`: Add discovered device
- `find_device_by_serial(serial_number, device_type)`: Find device by serial number
- `update_device_port(device_id, new_port)`: Update port assignment (device moved)
- `unregister_device(device_id)`: Remove device
- `get_device(device_id)`: Get device entry
- `get_device_by_serial(serial_number, device_type)`: Get device by serial number
- `get_devices_by_type(device_type)`: Get all devices of type
- `get_all_devices()`: Get all registered devices
- `update_device_status(device_id, status)`: Update device status
- `mark_device_failed(device_id)`: Mark device as failed
- `mark_device_recovered(device_id)`: Mark device as recovered

### 3. Auto-Recovery Manager

#### 3.1 Failure Detection

During normal polling:
- If `adapter.poll()` raises exception or times out:
  - Mark device as failed
  - Increment failure count
  - Calculate retry delay (exponential backoff)
  - Set next retry time

#### 3.2 Recovery Process

```
RECOVERY FLOW:
1. Check for devices with status="recovering" and next_retry_time <= now
2. For each device:
   a. First, try the last known port (if available)
   b. If not found, scan all available ports to find the device
   c. For each port:
      - Try to connect with device's known parameters
      - Read serial number to verify match
      - If found and serial matches:
         * Update device port assignment
         * Mark device as "active"
         * Reset failure count
         * Update port_history
         * Resume normal polling
         * Break (device found)
   d. If device not found on any port:
      * Check if all ports have been scanned
      * If all ports exhausted:
         → Device not found anywhere
         → Increment failure count
         → Calculate new retry delay (exponential backoff)
         → Set next_retry_time = now + retry_delay
         → Keep status as "recovering"
      * If max failures reached (10):
         → Permanently disable device
         → Status = "permanently_disabled"
         → Log error for administrator
3. Continue monitoring
```

#### 3.3 Permanent Disable Logic

**Conditions for Permanent Disable:**
1. **During Discovery**: If all ports are scanned, all devices found, but a known device is still missing
   - Reason: Device likely decommissioned/permanently removed
   - Action: Mark as "permanently_disabled" immediately
   - Logic: All ports exhausted + all devices found = missing device is gone

2. **During Recovery**: After 10 consecutive recovery failures
   - Reason: Device consistently unavailable despite retries
   - Action: Mark as "permanently_disabled"

**Permanently Disabled Devices:**
- Not included in normal polling
- Not included in discovery scans
- Can be manually re-enabled via API (`POST /api/devices/{device_id}/re-enable`)
- Require administrator intervention to reactivate

#### 3.4 Retry Strategy

**Exponential Backoff:**
- Initial retry: 15 minutes (900 seconds)
- Max retry interval: 2 hours (7200 seconds)
- Backoff multiplier: 1.5x per failure
- Max failures before permanent disable: 10

**Retry Schedule Example:**
- Failure 1: Retry after 15 minutes
- Failure 2: Retry after 22.5 minutes (15 * 1.5)
- Failure 3: Retry after 33.75 minutes (22.5 * 1.5)
- Failure 4: Retry after 50.6 minutes
- ... up to max of 2 hours

**Permanent Disable:**
- After 10 consecutive failures, device is permanently disabled
- Requires manual intervention or restart to re-enable
- Logs warning for administrator attention

### 4. Enhanced Polling Loop

#### 4.1 Modified Polling Flow

```
POLLING LOOP:
1. Get all active devices from registry
2. For each device:
   a. Check if device is disabled and not ready for retry
      - If yes, skip this device
   b. Try to poll device (with timeout)
   c. If successful:
      * Update last_seen timestamp
      * Reset failure count (if was recovering)
      * Process telemetry data
   d. If failed:
      * Call auto-recovery manager to handle failure
      * Log error
      * Continue to next device
3. Run recovery check (in background)
4. Wait for polling interval
5. Repeat
```

#### 4.2 Health Check

Each adapter will implement a lightweight health check:
- Read a single register or execute simple command
- Timeout: 1 second
- Used for quick connection verification

### 5. Configuration Management

#### 5.1 Auto-Discovered Config

Auto-discovered devices can be stored in:
- **Option A**: Separate `auto_discovered_devices.yaml` file
- **Option B**: In-memory registry (lost on restart, re-discovered)
- **Option C**: Database table (persistent across restarts)

**Recommended: Option C (Database)**
- Persistent across restarts
- Can be manually edited
- Can be merged with main config

#### 5.2 Config Merge Strategy

On startup:
1. Load main `config.yaml`
2. Load auto-discovered devices from database
3. Merge configurations:
   - Manual config takes precedence (if port conflicts)
   - Auto-discovered devices fill gaps
   - Resolve conflicts (log warnings)

#### 5.3 User Override

Users can:
- Manually configure devices in `config.yaml` (takes precedence)
- Disable auto-discovery for specific ports
- Manually enable/disable auto-discovered devices

### 6. API Enhancements

#### 6.1 New Endpoints

**GET `/api/devices/discovery/status`**
- Returns discovery status and discovered devices

**POST `/api/devices/discovery/start`**
- Manually trigger device discovery

**POST `/api/devices/{device_id}/enable`**
- Manually enable a disabled device

**POST `/api/devices/{device_id}/disable`**
- Manually disable a device

**POST `/api/devices/{device_id}/re-enable`**
- Re-enable a permanently disabled device
- Triggers new discovery scan for the device

**GET `/api/devices/{device_id}/status`**
- Get device status, failure count, next retry time
- Include: current port, last_known_port, port_history, is_auto_discovered

**POST `/api/devices/{device_id}/retry`**
- Manually trigger retry for failed device

#### 6.2 Enhanced Endpoints

**GET `/api/devices`**
- Include auto-discovered devices
- Include device status (active/disabled/recovering)
- Include failure count and next retry time

### 7. Logging and Monitoring

#### 7.1 Discovery Logging

- Log each port scan attempt
- Log successful device identification
- Log failed identification attempts (debug level)
- Log configuration generation

#### 7.2 Recovery Logging

- Log device failures (warning level)
- Log recovery attempts (info level)
- Log successful recoveries (info level)
- Log permanent disables (error level)

#### 7.3 Metrics

Track:
- Number of discovered devices
- Number of active devices
- Number of disabled devices
- Average recovery time
- Failure rates per device type

### 8. Implementation Phases

#### Phase 1: Core Discovery (Week 1)
- [ ] Implement device discovery service
- [ ] Implement device identification probes for each adapter
- [ ] Implement device registry
- [ ] Test discovery on startup

#### Phase 2: Auto-Recovery (Week 2)
- [ ] Implement auto-recovery manager
- [ ] Integrate failure detection in polling loop
- [ ] Implement retry logic with exponential backoff
- [ ] Test recovery scenarios

#### Phase 3: Configuration Management (Week 3)
- [ ] Implement database storage for discovered devices
- [ ] Implement config merge logic
- [ ] Add API endpoints
- [ ] Add UI for device management

#### Phase 4: Testing and Refinement (Week 4)
- [ ] End-to-end testing
- [ ] Performance testing
- [ ] Edge case handling
- [ ] Documentation

### 9. Configuration Options

Add to `config.yaml`:

```yaml
device_discovery:
  enabled: true  # Enable/disable auto-discovery
  scan_on_startup: true  # Scan on startup
  scan_interval_minutes: 60  # Periodic scan interval (0 = disabled)
  priority_order:  # Device type priority for discovery
    - pytes  # Battery first
    - senergy
    - powdrive
    - iammeter
  auto_recovery:
    enabled: true
    initial_retry_minutes: 15
    max_retry_minutes: 120
    backoff_multiplier: 1.5
    max_failures: 10
  identification:
    timeout_seconds: 2
    test_register: 0x0000  # Default test register
    max_retries: 2  # Retries per identification attempt
    read_serial_number: true  # Read serial number for device matching
```

### 10. Edge Cases and Error Handling

#### 10.1 Port Conflicts
- If manual config uses a port, skip auto-discovery on that port
- Log warning if auto-discovered device conflicts with manual config
- Port exclusion is not supported (user requirement)

#### 10.2 Multiple Devices of Same Type
- Allow multiple devices of same type
- Generate unique IDs from serial number: `senergy_123456`, `senergy_789012`, etc.
- Device ID format: `{device_type}_{serial_last6}`
- Used consistently for:
  - Device identification in system
  - Home Assistant entity names (e.g., `sensor.senergy_123456_power`)
  - API filters and queries
  - MQTT topics
- Each device is uniquely identified by serial number, not port
- Port can change, but device identity persists

#### 10.4 Discovery Completion Logic
- Discovery stops when all available USB ports are exhausted
- Known devices from database are checked first (on their saved ports)
- Missing known devices trigger full port scan
- If all ports scanned and device still not found → 15-minute retry timer
- If all ports exhausted AND all devices found → Missing devices are permanently disabled
  - Reason: All ports checked, device not found anywhere = likely decommissioned
  - Action: Mark as "permanently_disabled" (can be manually re-enabled later)

#### 10.3 Device Removal During Discovery
- Handle port unavailability gracefully
- Skip unavailable ports, continue with others

#### 10.4 Slow Devices
- Use timeouts for all identification probes
- Don't block discovery on slow devices
- Mark as "slow" and retry later

#### 10.5 Partial Configurations
- If device is discovered but config is incomplete, mark as "partial"
- Allow manual completion via API/UI

### 11. Testing Strategy

#### 11.1 Unit Tests
- Device identification probes
- Registry operations
- Recovery logic
- Retry calculations

#### 11.2 Integration Tests
- Full discovery flow
- Recovery scenarios
- Config merge logic

#### 11.3 Manual Testing Scenarios
1. **Startup Discovery**: Connect devices, restart app, verify discovery
2. **Device Removal**: Remove device during operation, verify recovery
3. **Device Reconnection**: Reconnect device, verify auto-recovery
4. **Multiple Devices**: Connect multiple devices, verify all discovered
5. **Port Conflicts**: Configure manual device, verify conflict handling

### 12. Migration Path

#### 12.1 Existing Configurations
- Existing `config.yaml` devices continue to work
- Auto-discovery runs in parallel
- No breaking changes

#### 12.2 Gradual Adoption
- Users can enable/disable auto-discovery
- Can manually configure devices as before
- Can mix manual and auto-discovered devices

### 13. Performance Considerations

#### 13.1 Discovery Time
- Target: Complete discovery in < 30 seconds for 4 ports
- Parallel port scanning (if possible)
- Quick timeouts for identification

#### 13.2 Recovery Overhead
- Recovery checks run in background
- Don't block normal polling
- Minimal CPU/memory overhead

#### 13.3 Registry Size
- In-memory registry (fast access)
- Database sync for persistence (async)

## Design Decisions (Finalized)

1. **Discovery Persistence**: ✅ **YES** - Auto-discovered devices persist in database

2. **Retry Strategy**: ✅ **15 minutes** initial retry, exponential backoff, configurable

3. **Discovery Frequency**: ✅ **YES** - Periodically re-scan for new devices, configurable interval

4. **Device Identification**: ✅ **Serial Number-Based** - Devices identified by serial number, not port
   - Same serial + type = same device (reuse config, update port)
   - New serial + same type = new device (create new entry)
   - Port can change, device identity persists
   - Device ID format: `{device_type}_{serial_last6}` (e.g., `senergy_123456`)
   - Used for: Device ID, Home Assistant entities, API filters, MQTT topics

5. **Port Exclusion**: ✅ **NO** - Users cannot exclude ports from discovery

6. **Config Override**: Manual config always overrides auto-discovered (if port conflicts)

7. **Permanent Disable**: 
   - After 10 consecutive recovery failures, OR
   - During discovery: if all ports exhausted and device still not found
   - Manual re-enable required via API
   - Status: "permanently_disabled"

## Database Schema

### Device Discovery Table

```sql
CREATE TABLE device_discovery (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL UNIQUE,  -- {type}_{serial_last6} (e.g., "senergy_123456")
    device_type TEXT NOT NULL,  -- "senergy", "powdrive", "pytes", "iammeter"
    serial_number TEXT NOT NULL,  -- Device serial number (primary identifier)
    port TEXT,  -- Current port assignment (can change)
    port_history TEXT,  -- JSON array of previous ports
    adapter_config TEXT NOT NULL,  -- JSON serialized adapter config
    status TEXT NOT NULL DEFAULT 'active',  -- "active", "recovering", "permanently_disabled"
    last_known_port TEXT,  -- Last port where device was successfully found
    is_auto_discovered INTEGER DEFAULT 1,  -- 1 = auto-discovered, 0 = manual config
    failure_count INTEGER DEFAULT 0,
    next_retry_time TEXT,  -- ISO datetime string
    first_discovered TEXT NOT NULL,  -- ISO datetime string
    last_seen TEXT,  -- ISO datetime string
    discovery_timestamp TEXT NOT NULL,  -- ISO datetime string
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_device_discovery_serial ON device_discovery(serial_number, device_type);
CREATE INDEX idx_device_discovery_status ON device_discovery(status);
```

## Serial Number Reading Implementation

Each adapter must implement a `read_serial_number()` method:

```python
# In base adapter
@abstractmethod
async def read_serial_number(self) -> Optional[str]:
    """
    Read device serial number for identification.
    Returns None if serial number cannot be read.
    """
    raise NotImplementedError
```

**Implementation Examples:**

**Senergy:**
```python
async def read_serial_number(self) -> Optional[str]:
    # Read serial number from registers 0x0010-0x0015 (6 registers, ASCII)
    regs = await self._read_holding_regs(0x0010, 6)
    if regs:
        # Decode ASCII from registers
        serial = self._regs_to_ascii(regs)
        return serial.strip() if serial else None
    return None
```

**Powdrive:**
```python
async def read_serial_number(self) -> Optional[str]:
    # Read serial number from device-specific register
    # (Implementation depends on Powdrive register map)
    pass
```

## Approval Checklist

- [x] Review discovery flow and priority order
- [x] Review retry strategy and timing (15 min initial, exponential backoff)
- [x] Review configuration management approach (database persistence)
- [x] Review device identification (serial number-based)
- [x] Review API endpoint design
- [x] Review edge cases and error handling
- [x] Approve implementation phases
- [x] Approve testing strategy

---

**Document Version**: 1.1  
**Last Updated**: 2024-01-15  
**Status**: ✅ Approved - Ready for Implementation

