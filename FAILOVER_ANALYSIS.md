# Failover Adapter Analysis & Fix Plan

## Executive Summary

The `jkbms_tcpip` adapter was working perfectly before the hierarchy migration. After moving to database-based configuration, several issues emerged in the initialization and failover logic that prevent the passive listening adapter from functioning correctly.

## Architecture Overview

### Before Hierarchy Migration (Working)
- Configuration came from `config.yaml`
- Battery adapters were initialized directly from config
- `jkbms_tcpip` adapter started its listening loop in `connect()`
- Connection checks were simpler and more reliable

### After Hierarchy Migration (Broken)
- Configuration comes from database hierarchy
- Battery packs load adapters from `battery_pack_adapters` table
- Failover adapter wraps multiple adapters with lazy initialization
- Connection checks are more complex and can cause false positives

## Root Causes Identified

### 1. **Connection Check False Positives** (CRITICAL)
**Location**: `solarhub/app.py:2737-2749`

**Problem**:
- Connection check for `jkbms_tcpip` uses `raw_conn.getpeername()` 
- This can raise `OSError` even when socket is connected (timing, socket state)
- False disconnection detection triggers unnecessary reconnection attempts
- Reconnection interferes with the passive listening loop

**Code**:
```python
elif hasattr(current, 'raw_conn') and current.raw_conn:
    try:
        if hasattr(current.raw_conn, 'getpeername'):
            current.raw_conn.getpeername()  # Can fail even when connected!
            is_connected = True
    except (OSError, AttributeError):
        is_connected = False  # False negative!
```

### 2. **Reconnection Logic Interference** (CRITICAL)
**Location**: `solarhub/app.py:2774-2783`

**Problem**:
- When connection check fails, it calls `adapter.connect()` again
- For `jkbms_tcpip`: Has guard `if self.raw_conn is not None: return` (line 461)
- But the listening loop might be in a bad state or stopped
- No mechanism to restart the listening loop if it failed

**Code**:
```python
if not is_connected:
    log.warning(f"Battery adapter for {bank_id} not connected, attempting reconnection...")
    await adapter.connect()  # Returns early if already connected, but loop might be dead
```

### 3. **Failover Adapter Lazy Initialization Issue** (HIGH)
**Location**: `solarhub/adapters/battery_failover.py:108-146`

**Problem**:
- `connect()` only connects primary adapter (priority 1)
- If primary fails during runtime, failover is triggered
- But if connection check incorrectly detects primary as disconnected, it tries to reconnect primary instead of failing over
- The failover logic in `_try_failover()` is only called from `poll()` on exception, not from connection check

**Code**:
```python
async def connect(self):
    # Only connects primary adapter
    for idx in range(len(self.adapter_configs)):
        adapter = self._create_adapter_instance(idx)  # Lazy creation
        await adapter.connect()  # Only connects first successful
        self.current_adapter = adapter
        return  # Exits after first success
```

### 4. **Passive Listening Loop Lifecycle** (HIGH)
**Location**: `solarhub/adapters/battery_jkbms_tcpip.py:459-515, 547-698`

**Problem**:
- Listening loop is started in `connect()` (line 501)
- If `connect()` is called again, it returns early (line 461-463)
- No mechanism to check if listening loop is still running
- No mechanism to restart listening loop if it stopped
- Connection check doesn't verify listening loop status

**Code**:
```python
async def connect(self):
    if self.raw_conn is not None:
        log.debug("Already connected")
        return  # Exits early, but loop might be dead!
    
    # ... connection code ...
    self._listening_task = asyncio.create_task(self._listen_loop())  # Started once
```

### 5. **Missing Listening Loop Status Check** (MEDIUM)
**Location**: `solarhub/adapters/battery_jkbms_tcpip.py`

**Problem**:
- No `check_connectivity()` method for `jkbms_tcpip`
- Connection check relies on socket state, not listening loop state
- Listening loop could be dead but socket still connected

## Concrete Fix Steps

### Step 1: Fix Connection Check for Passive Adapters
**File**: `solarhub/app.py`
**Location**: `_poll_battery()` method (lines 2720-2783)

**Action**:
1. Add special handling for `jkbms_tcpip` adapter
2. Check listening loop status instead of just socket status
3. For passive adapters, check if listening task is running and has discovered batteries

**Implementation**:
```python
# For jkbms_tcpip, check listening loop status
if hasattr(current, '_listening_task') and current._listening_task:
    # Check if listening loop is still running
    if current._listening_task.done():
        is_connected = False  # Loop died
    elif hasattr(current, 'batteries') and len(current.batteries) > 0:
        # Loop is running and has discovered batteries
        is_connected = True
    elif hasattr(current, '_connect_time'):
        # Loop is running but no batteries yet - check timeout
        time_since_connect = time.time() - current._connect_time
        if time_since_connect < 60:  # Give 60 seconds to discover
            is_connected = True  # Still waiting for discovery
        else:
            is_connected = False  # Timeout - no batteries discovered
    else:
        is_connected = True  # Loop running, assume connected
elif hasattr(current, 'raw_conn') and current.raw_conn:
    # Fallback to socket check
    try:
        if hasattr(current.raw_conn, 'getpeername'):
            current.raw_conn.getpeername()
            is_connected = True
        else:
            is_connected = current.raw_conn.is_open if hasattr(current.raw_conn, 'is_open') else False
    except (OSError, AttributeError):
        is_connected = False
```

### Step 2: Add `check_connectivity()` Method to jkbms_tcpip
**File**: `solarhub/adapters/battery_jkbms_tcpip.py`

**Action**:
1. Add `check_connectivity()` method that checks both socket and listening loop
2. Return `True` only if socket is connected AND listening loop is running

**Implementation**:
```python
async def check_connectivity(self) -> bool:
    """Check if adapter is connected and listening loop is running."""
    if not self.raw_conn:
        return False
    
    # Check socket connection
    try:
        if self.connection_type == "tcpip":
            if hasattr(self.raw_conn, 'getpeername'):
                self.raw_conn.getpeername()
            else:
                return False
        else:  # rtu
            if hasattr(self.raw_conn, 'is_open'):
                if not self.raw_conn.is_open:
                    return False
            else:
                return False
    except (OSError, AttributeError):
        return False
    
    # Check listening loop
    if not self._listening_task:
        return False
    
    if self._listening_task.done():
        return False  # Loop died
    
    # If we have discovered batteries, we're definitely connected
    if len(self.batteries) > 0:
        return True
    
    # If loop is running but no batteries yet, check timeout
    if hasattr(self, '_connect_time'):
        time_since_connect = time.time() - self._connect_time
        if time_since_connect < 60:  # Give 60 seconds
            return True  # Still waiting
    
    # Loop is running, assume connected
    return True
```

### Step 3: Fix Reconnection Logic for Passive Adapters
**File**: `solarhub/app.py`
**Location**: `_poll_battery()` method (lines 2774-2783)

**Action**:
1. For passive adapters, don't just call `connect()` again
2. Check if listening loop needs restart
3. For failover adapters, use `check_connectivity()` first before reconnecting

**Implementation**:
```python
if not is_connected:
    log.warning(f"Battery adapter for {bank_id or 'legacy'} not connected, attempting reconnection...")
    
    # For failover adapters, try check_connectivity first
    if hasattr(adapter, 'check_connectivity'):
        try:
            is_connected = await adapter.check_connectivity()
            if is_connected:
                log.debug(f"Battery adapter for {bank_id} is actually connected (false positive check)")
                # Continue to poll
            else:
                # Really disconnected, try failover or reconnect
                if hasattr(adapter, '_try_failover'):
                    # Failover adapter - try failover first
                    if await adapter._try_failover():
                        log.info(f"Failover successful for {bank_id}")
                        is_connected = True
                    else:
                        # All adapters failed, try reconnecting primary
                        await adapter.connect()
                else:
                    # Single adapter - reconnect
                    await adapter.connect()
        except Exception as e:
            log.warning(f"Connectivity check failed for {bank_id}: {e}")
            # Fall through to reconnect
    else:
        # No check_connectivity method, just reconnect
        try:
            await adapter.connect()
            log.info(f"Successfully reconnected battery adapter for {bank_id or 'legacy'}")
        except Exception as e:
            log.warning(f"Failed to reconnect battery adapter for {bank_id or 'legacy'}: {e}")
            self._devices_connected = False
            return
```

### Step 4: Add Listening Loop Restart Capability
**File**: `solarhub/adapters/battery_jkbms_tcpip.py`

**Action**:
1. Modify `connect()` to restart listening loop if it's dead
2. Add method to check and restart listening loop if needed

**Implementation**:
```python
async def connect(self):
    """Connect to RS485 gateway via TCP/IP or serial port."""
    # Check if we need to restart listening loop
    if self.raw_conn is not None:
        # Connection exists, but check if listening loop is alive
        if self._listening_task and self._listening_task.done():
            log.warning("Listening loop died, restarting...")
            # Clean up dead task
            try:
                await self._listening_task
            except Exception:
                pass
            self._listening_task = None
            # Restart listening loop
            self._stop_listening = False
            self._listening_task = asyncio.create_task(self._listen_loop())
            log.info("Restarted listening loop for JK BMS RS485 adapter")
            return
        elif not self._listening_task:
            # Connection exists but no listening loop - restart it
            log.warning("Connection exists but no listening loop, restarting...")
            self._stop_listening = False
            self._listening_task = asyncio.create_task(self._listen_loop())
            log.info("Started listening loop for existing connection")
            return
        else:
            log.debug("Already connected and listening loop is running")
            return
    
    # ... rest of connection code ...
```

### Step 5: Improve Failover Adapter Connection Check
**File**: `solarhub/adapters/battery_failover.py`

**Action**:
1. Improve `check_connectivity()` to properly check current adapter
2. Use adapter's own `check_connectivity()` if available

**Implementation**:
```python
async def check_connectivity(self) -> bool:
    """Check if current adapter is connected and responding."""
    if not self.current_adapter:
        return False
    
    try:
        # Use adapter's own check_connectivity if available
        if hasattr(self.current_adapter, 'check_connectivity'):
            return await self.current_adapter.check_connectivity()
        else:
            # Fallback: try to poll (but this might be expensive)
            await self.current_adapter.poll()
            return True
    except Exception:
        # Adapter is not responding, try failover
        if await self._try_failover():
            return await self.check_connectivity()  # Recursive check with new adapter
        return False
```

### Step 6: Add Better Logging for Debugging
**Files**: Multiple

**Action**:
1. Add debug logs when connection check fails
2. Log listening loop status
3. Log battery discovery status

**Implementation**:
- Add logs in connection check to show why it failed
- Add logs in listening loop to show discovery progress
- Add logs in failover to show which adapter is being tried

## Testing Plan

1. **Test Connection Check**:
   - Verify it doesn't trigger false positives
   - Verify it correctly detects when listening loop dies
   - Verify it correctly detects when socket disconnects

2. **Test Reconnection**:
   - Verify reconnection restarts listening loop if needed
   - Verify reconnection doesn't interfere with running loop
   - Verify reconnection works after network interruption

3. **Test Failover**:
   - Verify primary adapter connects first
   - Verify failover triggers when primary fails
   - Verify failover doesn't trigger on false positives

4. **Test Listening Loop**:
   - Verify loop starts on connection
   - Verify loop restarts if it dies
   - Verify loop discovers batteries correctly

## Priority Order

1. **Step 1** (Connection Check Fix) - CRITICAL - Fixes false positives
2. **Step 2** (check_connectivity Method) - CRITICAL - Provides proper connectivity check
3. **Step 3** (Reconnection Logic) - HIGH - Prevents interference with listening loop
4. **Step 4** (Listening Loop Restart) - HIGH - Ensures loop can recover
5. **Step 5** (Failover Check) - MEDIUM - Improves failover reliability
6. **Step 6** (Logging) - LOW - Helps with debugging

## Expected Outcome

After implementing these fixes:
- Connection check will correctly identify when adapter is truly disconnected
- Reconnection will properly restart listening loop if needed
- Failover will work correctly when primary adapter fails
- Passive listening adapters will maintain their listening loops reliably
- System will recover gracefully from network interruptions

