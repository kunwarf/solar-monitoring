# Device Discovery Implementation Locations

## Overview

The device discovery logic is implemented across several files. Here's where each component lives:

## 1. Main Implementation

### `solarhub/device_discovery.py`
**Primary file containing the discovery logic**

- **Class**: `DeviceDiscoveryService`
- **Main Method**: `discover_devices()` - Implements the 4-phase discovery process:
  1. **Phase 1**: Check known devices from database
  2. **Phase 2**: Search for missing known devices on all ports
  3. **Phase 3**: Discover new devices on unused ports
  4. **Phase 4**: Finalize and cleanup

- **Key Methods**:
  - `get_available_ports()` - Scans for USB serial ports (`/dev/ttyUSB*` or `COM*`)
  - `identify_device_on_port()` - Attempts to identify a device on a specific port
    - Connects to device
    - Calls `check_connectivity()` 
    - Calls `read_serial_number()`
    - Returns `(serial_number, adapter_config)` if successful

- **Configuration**:
  - `enabled` - Enable/disable discovery
  - `scan_on_startup` - Run discovery on application startup
  - `scan_interval_minutes` - Periodic scan interval
  - `priority_order` - Device type priority: `["pytes", "senergy", "powdrive", "iammeter"]`
  - `identification_timeout` - Timeout for device identification (default: 3.0 seconds)
  - `max_retries` - Maximum retries per identification attempt

## 2. Integration Points

### `solarhub/app.py`
**Application initialization and periodic discovery**

- **Initialization** (lines ~100-134):
  - Creates `DeviceRegistry` instance
  - Creates `DeviceDiscoveryService` instance
  - Creates `AutoRecoveryManager` instance
  - Configures discovery service from `config.yaml`

- **Startup Discovery** (lines ~186-193):
  - Runs discovery on startup if `scan_on_startup` is enabled
  - Called before initializing devices to update ports

- **Periodic Discovery** (lines ~618-819):
  - Runs periodic discovery scans based on `scan_interval_minutes`
  - Background task that runs continuously

### `solarhub/api_server.py`
**API endpoint for manual discovery trigger**

- **Endpoint**: `POST /api/discovery/trigger` (line ~1670)
- **Function**: `api_trigger_discovery()`
- Allows manual triggering of device discovery via API

## 3. Database Layer

### `solarhub/device_registry.py`
**Device storage and retrieval**

- **Class**: `DeviceRegistry`
- **Methods**:
  - `get_all_devices()` - Get all devices from database
  - `find_device_by_serial()` - Find device by serial number
  - `register_device()` - Register/update device in database
  - `update_device_port()` - Update device port assignment
  - `normalize_serial()` - Normalize serial number for matching
  - `generate_device_id()` - Generate device ID: `{type}_{serial_last6}`

### `solarhub/database_migrations.py`
**Database schema creation**

- **Function**: `migrate_to_device_discovery()` (line ~322)
- Creates `device_discovery` table with columns:
  - `device_id` (PRIMARY KEY)
  - `device_type`
  - `serial_number`
  - `port`
  - `last_known_port`
  - `port_history` (JSON)
  - `adapter_config` (JSON)
  - `status`
  - `failure_count`
  - `next_retry_time`
  - `first_discovered`
  - `last_seen`
  - `discovery_timestamp`
  - `is_auto_discovered`

- **Indexes**:
  - `idx_device_discovery_serial` - On `(serial_number, device_type)`
  - `idx_device_discovery_status` - On `status`
  - `idx_device_discovery_port` - On `port`

## 4. Device Adapters

Each adapter implements device-specific identification methods:

### `solarhub/adapters/senergy.py`
- `check_connectivity()` - Reads register 6672 (serial number)
- `read_serial_number()` - Reads register 6672, decodes ASCII

### `solarhub/adapters/powdrive.py`
- `check_connectivity()` - Reads register 3 (serial number)
- `read_serial_number()` - Reads register 3, decodes ASCII

### `solarhub/adapters/battery_pytes.py`
- `check_connectivity()` - Sends "info" command
- `read_serial_number()` - Reads serial from device info response

### `solarhub/adapters/iammeter.py`
- `check_connectivity()` - Reads register 0x38 (serial number)
- `read_serial_number()` - Reads register 0x38, decodes ASCII

## 5. Auto Recovery

### `solarhub/auto_recovery.py` (if exists)
**Handles device recovery and retry logic**

- Manages retry timers for missing devices
- Implements exponential backoff
- Marks devices as permanently disabled after max failures

## 6. Configuration

### `config.yaml`
**Discovery configuration**

```yaml
discovery:
  enabled: true
  scan_on_startup: true
  scan_interval_minutes: 60
  priority_order:
    - pytes
    - senergy
    - powdrive
    - iammeter
  identification_timeout: 3.0
  max_retries: 2
  auto_recovery:
    enabled: true
    initial_retry_minutes: 15
    max_retry_minutes: 120
    backoff_multiplier: 1.5
    max_failures: 10
```

## Discovery Flow

```
1. Application Startup (app.py)
   └─> Initialize DeviceDiscoveryService
   └─> Run discovery on startup (if enabled)

2. Discovery Process (device_discovery.py)
   ├─> Phase 1: Check known devices
   │   └─> For each known device:
   │       └─> Try to connect on saved port
   │       └─> Verify serial number matches
   │
   ├─> Phase 2: Search for missing devices
   │   └─> For each missing device:
   │       └─> Scan all available ports
   │       └─> Try to identify device
   │
   ├─> Phase 3: Discover new devices
   │   └─> For each unused port:
   │       └─> Try each device type (by priority)
   │       └─> If device found:
   │           └─> Register new device
   │
   └─> Phase 4: Finalize
       └─> Mark permanently missing devices
       └─> Save all devices to database

3. Device Identification (identify_device_on_port)
   ├─> Connect to device
   ├─> Call adapter.check_connectivity()
   ├─> Call adapter.read_serial_number()
   └─> Return (serial_number, adapter_config)

4. Database Storage (device_registry.py)
   └─> Store/update device in device_discovery table
```

## Key Files Summary

| File | Purpose | Key Components |
|------|---------|----------------|
| `solarhub/device_discovery.py` | Main discovery logic | `DeviceDiscoveryService`, `discover_devices()`, `identify_device_on_port()` |
| `solarhub/app.py` | Integration | Initialization, startup discovery, periodic scans |
| `solarhub/api_server.py` | API endpoint | Manual discovery trigger |
| `solarhub/device_registry.py` | Database operations | `DeviceRegistry`, CRUD operations |
| `solarhub/database_migrations.py` | Schema | `device_discovery` table creation |
| `solarhub/adapters/*.py` | Device identification | `check_connectivity()`, `read_serial_number()` |

## Testing Discovery

To manually trigger discovery:
1. Via API: `POST /api/discovery/trigger`
2. Via code: `await app.discovery_service.discover_devices(...)`
3. Automatically: On startup (if enabled) or periodically (based on interval)

