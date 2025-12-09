# Port History Tracking Implementation

## Summary

Port history tracking has been implemented to comply with the design document requirement (line 69: "Update port_history"). The system now tracks all port changes for devices, maintaining a history of ports each device has been connected to.

## Implementation Details

### 1. Database Schema
- **Field**: `port_history` (TEXT, JSON array)
- **Storage**: Stored as JSON array of port strings
- **Example**: `["/dev/ttyUSB0", "/dev/ttyUSB1"]`

### 2. DeviceEntry Model
- **Field**: `port_history: List[str]`
- **Type**: List of port strings
- **Initialization**: Empty list `[]` for new devices

### 3. Port History Update Logic

Port history is updated in two places:

#### A. `device_registry.py` - `update_device_port()` method
- **Location**: Lines 226-257
- **Logic**: 
  - When port changes, adds old port to history if not already present
  - Updates database with new port and updated history
- **Note**: This method updates the database but doesn't update the in-memory device object

#### B. `device_discovery.py` - Port update locations
- **Updated locations**:
  1. **Phase 2 - Missing device found** (lines 483-490)
     - When a missing device is found on a new port
     - Updates port history before saving device
  
  2. **Phase 1 - Manually configured inverter** (lines 314-321)
     - When manually configured inverter port changes
     - Updates port history
  
  3. **Phase 1 - Manually configured battery** (lines 413-420)
     - When manually configured battery port changes
     - Updates port history
  
  4. **Phase 2 - Manually configured missing device** (lines 576-584)
     - When manually configured missing device found on new port
     - Updates port history
  
  5. **Phase 3 - Existing device moved** (lines 698-705)
     - When existing device discovered on new port
     - Updates port history

### 4. Port History Update Pattern

The following pattern is used consistently throughout:

```python
# When device port changes:
old_port = device.port
self.registry.update_device_port(device.device_id, port)  # Updates database
device.port = port
# Update port_history in memory to match database
if old_port and old_port != port:
    if old_port not in device.port_history:
        device.port_history.append(old_port)
# Then save device
self.registry.register_device(device)
```

### 5. Port History Rules

- **Only unique ports**: Ports are only added if not already in history
- **Only on change**: Port history is only updated when port actually changes
- **Preserves order**: Ports are added in chronological order (oldest first)
- **Current port not in history**: Current port is stored in `port` field, not in `port_history`

## Example Scenarios

### Scenario 1: Device Moves Between Ports
```
Initial: device.port = "/dev/ttyUSB0", port_history = []
After move to USB1: device.port = "/dev/ttyUSB1", port_history = ["/dev/ttyUSB0"]
After move to USB2: device.port = "/dev/ttyUSB2", port_history = ["/dev/ttyUSB0", "/dev/ttyUSB1"]
```

### Scenario 2: Device Returns to Previous Port
```
Current: device.port = "/dev/ttyUSB2", port_history = ["/dev/ttyUSB0", "/dev/ttyUSB1"]
Moves back to USB0: device.port = "/dev/ttyUSB0", port_history = ["/dev/ttyUSB0", "/dev/ttyUSB1"]
(USB0 already in history, so no duplicate added)
```

### Scenario 3: New Device
```
New device: device.port = "/dev/ttyUSB3", port_history = []
(No history until device moves)
```

## API Access

Port history is available via the API:

```json
{
  "device_id": "senergy_123456",
  "port": "/dev/ttyUSB2",
  "port_history": ["/dev/ttyUSB0", "/dev/ttyUSB1"],
  ...
}
```

## Testing

To verify port history tracking:

1. **Move device to new port**: Device should have old port in history
2. **Check database**: `port_history` field should contain JSON array
3. **Check API**: Port history should be visible in device details
4. **Multiple moves**: History should accumulate ports in order

## Future Enhancements (Optional)

1. **Add timestamps**: Store port changes with timestamps:
   ```json
   [
     {"port": "/dev/ttyUSB0", "timestamp": "2024-01-01T10:00:00"},
     {"port": "/dev/ttyUSB1", "timestamp": "2024-01-01T11:00:00"}
   ]
   ```

2. **Limit history size**: Keep only last N ports (e.g., last 10)

3. **Port change reason**: Track why port changed (discovery, manual, etc.)

## Compliance

✅ **Design Document Compliance**: 
- Line 69 requirement: "Update port_history" - **IMPLEMENTED**
- Port history is updated whenever device port assignment changes
- History is preserved in database and accessible via API

## Files Modified

1. **`solarhub/device_discovery.py`**
   - Added port history tracking in 5 locations where ports are updated
   - Ensures in-memory device object matches database state

2. **`solarhub/device_registry.py`**
   - `update_device_port()` method already had port history logic
   - No changes needed (already compliant)

## Notes

- Port history is stored as a simple list of port strings
- Current port is NOT included in history (stored separately in `port` field)
- Port history is preserved across device status changes
- Port history is included in device serialization/API responses

