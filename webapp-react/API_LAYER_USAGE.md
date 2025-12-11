# Common API Layer Usage Guide

## Overview

The frontend now uses a **common API layer with hierarchy objects** that provides a clean, type-safe way to access and manipulate system data across all apps. This replaces complex transformation logic with simple object access and method calls.

## Architecture

```
Frontend Apps (start, default, v0)
    ↓
Common Data Layer (Hierarchy Objects)
    ↓
API Communication Layer (Services)
    ↓
Backend API
```

## Key Components

### 1. Hierarchy Object Classes

Located in `src/api/models/`:

- **`System`** - Top-level container (represents a system/home)
- **`InverterArray`** - Array of inverters
- **`BatteryArray`** - Array of battery packs
- **`Inverter`** - Individual inverter device
- **`BatteryPack`** - Individual battery pack
- **`Meter`** - Energy meter device

Each class provides:
- Properties for device/array metadata
- Methods for computed values (e.g., `getTotalPower()`, `getSOC()`)
- Telemetry management
- Relationship navigation

### 2. HierarchyManager

Singleton manager (`src/api/managers/HierarchyManager.ts`) that:
- Loads hierarchy from backend
- Maintains object relationships
- Updates telemetry for all devices
- Provides access methods

### 3. React Hooks

Located in `src/api/hooks/useHierarchyObjects.ts`:

- `useHierarchyManager()` - Get manager instance
- `useSystem(systemId)` - Get system by ID
- `useInverter(inverterId)` - Get inverter by ID
- `useBatteryPack(packId)` - Get battery pack by ID
- `useMeter(meterId)` - Get meter by ID
- `useAllSystems()` - Get all systems
- `useAllInverters()` - Get all inverters
- `useAllBatteryPacks()` - Get all battery packs
- `useAllMeters()` - Get all meters
- `useSystemTotalPower(systemId)` - Get system total power
- `useSystemTotalBatterySOC(systemId)` - Get system battery SOC

### 4. Data Synchronization Service

Located in `src/api/services/DataSyncService.ts`:

- Polls backend for telemetry updates
- Updates hierarchy objects automatically
- Configurable polling interval (default: 5 seconds)
- Enable/disable polling

## Usage Examples

### Basic Usage

```typescript
import { useSystem, useInverter } from '@/api/hooks/useHierarchyObjects'

function MyComponent() {
  const system = useSystem('system')
  const inverter = useInverter('inverter1')
  
  if (!system || !inverter) {
    return <div>Loading...</div>
  }
  
  return (
    <div>
      <h1>{system.name}</h1>
      <p>Total Power: {system.getTotalPower()} kW</p>
      <p>Battery SOC: {system.getTotalBatterySOC()}%</p>
      
      <h2>{inverter.name}</h2>
      <p>Power: {inverter.getPower()} kW</p>
      <p>Status: {inverter.getStatus()}</p>
    </div>
  )
}
```

### Accessing Arrays

```typescript
import { useSystem } from '@/api/hooks/useHierarchyObjects'

function ArraysList() {
  const system = useSystem('system')
  
  if (!system) return null
  
  return (
    <div>
      <h2>Inverter Arrays</h2>
      {system.inverterArrays.map(array => (
        <div key={array.id}>
          <h3>{array.name}</h3>
          <p>Total Power: {array.getTotalPower()} kW</p>
          <p>Inverters: {array.inverters.map(inv => inv.name).join(', ')}</p>
        </div>
      ))}
      
      <h2>Battery Arrays</h2>
      {system.batteryArrays.map(array => (
        <div key={array.id}>
          <h3>{array.name}</h3>
          <p>SOC: {array.getTotalSOC()}%</p>
          <p>Capacity: {array.getTotalCapacity()} kWh</p>
        </div>
      ))}
    </div>
  )
}
```

### Using Telemetry

```typescript
import { useInverter } from '@/api/hooks/useHierarchyObjects'

function InverterStatus({ inverterId }: { inverterId: string }) {
  const inverter = useInverter(inverterId)
  
  if (!inverter) return null
  
  const telemetry = inverter.getTelemetry()
  const isOnline = inverter.hasRecentTelemetry(10)
  
  return (
    <div>
      <h3>{inverter.name}</h3>
      <p>Status: {inverter.getStatus()}</p>
      {telemetry && (
        <div>
          <p>PV Power: {telemetry.pvPower} kW</p>
          <p>Grid Power: {telemetry.gridPower} kW</p>
          <p>Load Power: {telemetry.loadPower} kW</p>
          <p>Battery Power: {telemetry.batteryPower} kW</p>
        </div>
      )}
    </div>
  )
}
```

### Data Synchronization

The `DataSyncService` is automatically started in the `start` app's `DataProvider`. For other apps, you can manually start it:

```typescript
import { useEffect } from 'react'
import { getDataSyncService } from '@/api/services/DataSyncService'
import { useHierarchyManager } from '@/api/hooks/useHierarchyObjects'

function MyApp() {
  const { manager } = useHierarchyManager()
  
  useEffect(() => {
    if (manager && manager.isLoaded()) {
      const syncService = getDataSyncService({
        pollingInterval: 5000, // 5 seconds
        enabled: true,
        updateHierarchy: false,
      })
      syncService.startPolling()
      
      return () => {
        syncService.stopPolling()
      }
    }
  }, [manager])
  
  return <div>...</div>
}
```

## App-Specific Implementation

### Start App (Modern Dashboard)

**Location**: `src/apps/start/src/data/DataProvider.tsx`

- Uses hierarchy objects via `useAllSystems()` hook
- Transforms hierarchy objects to match `mockData` structure for backward compatibility
- Automatically starts data synchronization
- Maintains exact same interface for frontend components

**Key Features**:
- Simplified from 1000+ lines to ~375 lines
- Uses hierarchy object methods for computed values
- Maintains backward compatibility

### Default App (Legacy Dashboard)

**Location**: `src/apps/default/AppLayout.tsx`

- Uses `useAllSystems()` hook to get systems
- Transforms hierarchy objects to `ArrayInfo[]` format for backward compatibility
- Maintains `ArrayContext` for array selection

**Key Features**:
- Replaced direct API calls with hierarchy objects
- Maintains backward compatibility with existing components

### V0 App (Analytics)

**Status**: Uses mock/static data

- Currently uses hardcoded mock data
- Can be updated to use hierarchy objects in the future if needed
- No changes required at this time

## Migration Guide

### Before (Old Way)

```typescript
// Complex transformation logic
const homeHierarchy = useMemo(() => {
  // 500+ lines of transformation
  // Manual mapping of API responses
  // Complex nested loops
}, [apiHierarchy, homeTelemetry, ...])
```

### After (New Way)

```typescript
// Simple object access
const system = useSystem('system')
const totalPower = system?.getTotalPower() || 0
const batterySOC = system?.getTotalBatterySOC() || 0

// Navigate hierarchy
const inverter = system?.inverterArrays[0]?.inverters[0]
const inverterPower = inverter?.getPower() || 0
```

## Benefits

1. **Code Simplification**: ~70% reduction in transformation logic
2. **Type Safety**: Full TypeScript support with compile-time error checking
3. **Consistency**: All apps use the same data structure
4. **Maintainability**: Single source of truth for hierarchy
5. **Performance**: Efficient object relationships and cached computed values

## API Endpoints

The hierarchy objects work with these backend endpoints:

- `GET /api/config` - Complete hierarchy structure
- `GET /api/home/now` - System-level telemetry
- `GET /api/arrays/{array_id}/now` - Array-level telemetry
- `GET /api/now?inverter_id={id}` - Inverter telemetry
- `GET /api/battery/now?bank_id={id}` - Battery pack telemetry
- `GET /api/meters/{meter_id}/now` - Meter telemetry

## Troubleshooting

### Hierarchy Not Loading

```typescript
const { manager, isLoading } = useHierarchyManager()

if (isLoading) {
  return <div>Loading hierarchy...</div>
}

if (!manager || !manager.isLoaded()) {
  return <div>Failed to load hierarchy</div>
}
```

### Telemetry Not Updating

Ensure data synchronization is started:

```typescript
useEffect(() => {
  const syncService = getDataSyncService()
  syncService.startPolling()
  return () => syncService.stopPolling()
}, [])
```

### Device Not Found

```typescript
const inverter = useInverter('inverter1')

if (!inverter) {
  console.warn('Inverter not found in hierarchy')
  return null
}
```

## Future Enhancements

1. **WebSocket Support**: Real-time updates via WebSocket instead of polling
2. **Caching Strategy**: More sophisticated caching for better performance
3. **Optimistic Updates**: Update UI immediately, sync with backend later
4. **Error Recovery**: Automatic retry and recovery mechanisms

## Related Documentation

- `FRONTEND_REFACTORING_PLAN.md` - Complete refactoring plan
- `COMPLETE_HIERARCHY_STRUCTURE.md` - Backend hierarchy structure
- `IMPLEMENTATION_PLAN.md` - Backend implementation plan

---

**Last Updated**: 2025-01-XX  
**Version**: 1.0

