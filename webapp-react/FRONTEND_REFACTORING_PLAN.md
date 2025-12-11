# Frontend Refactoring Plan: Common API Layer & Hierarchy Structure

## Executive Summary

This document outlines the plan to refactor the frontend to use a **common API communication layer** with a **hierarchy-aware object structure**. This will simplify code, eliminate redundancy, and ensure all three apps (start, default, v0) share the same data access patterns.

---

## Current State Analysis

### 1. Three Frontend Apps

1. **`start`** (Solar Monitoring - Modern Dashboard)
   - Location: `webapp-react/src/apps/start/`
   - Uses: `DataProvider.tsx` with complex transformation logic
   - Data Source: API hooks (`useHomeHierarchy`, `useHomeTelemetry`, etc.)
   - Status: ✅ Already using API layer, but with complex transformation

2. **`default`** (Legacy Dashboard)
   - Location: `webapp-react/src/apps/default/`
   - Uses: Unknown (needs investigation)
   - Data Source: Unknown
   - Status: ⚠️ Needs analysis

3. **`v0`** (Analytics)
   - Location: `webapp-react/src/apps/v0/`
   - Uses: Unknown (needs investigation)
   - Data Source: Unknown
   - Status: ⚠️ Needs analysis

### 2. Current API Layer Structure

**Location**: `webapp-react/src/api/`

```
api/
├── client.ts              # HTTP client with caching (localStorage)
├── services/              # Direct API service calls
│   ├── hierarchy.ts      # Hierarchy/configuration services
│   ├── telemetry.ts      # Telemetry data services
│   └── energy.ts         # Energy/historical data services
├── hooks/                 # React Query hooks
│   ├── useHierarchy.ts   # Hierarchy hooks
│   ├── useTelemetry.ts   # Telemetry hooks
│   └── useEnergy.ts      # Energy hooks
├── types/                 # TypeScript type definitions
│   ├── hierarchy.ts     # Hierarchy types
│   ├── telemetry.ts      # Telemetry types
│   └── energy.ts         # Energy types
└── normalizers/          # Data transformation/normalization
    ├── telemetry.ts      # Telemetry normalizers
    └── energy.ts         # Energy normalizers
```

### 3. Current Issues

#### Issue 1: Complex Transformation Logic
- **Location**: `webapp-react/src/apps/start/src/data/DataProvider.tsx`
- **Problem**: 1000+ lines of complex transformation logic
- **Impact**: Hard to maintain, error-prone, difficult to debug
- **Example**: Manual mapping of API responses to mockData structure

#### Issue 2: Redundant Code
- **Problem**: Each app may have its own data fetching/transformation logic
- **Impact**: Code duplication, inconsistent behavior
- **Example**: Multiple implementations of hierarchy transformation

#### Issue 3: No Hierarchy Objects
- **Problem**: Data is transformed to flat structures
- **Impact**: Loss of hierarchy relationships, difficult to navigate
- **Example**: Arrays and batteries are separate, not linked

#### Issue 4: Inconsistent Data Access
- **Problem**: Different apps may access data differently
- **Impact**: Inconsistent behavior, harder to maintain
- **Example**: Some apps use hooks, others may use direct API calls

---

## Proposed Solution: Common API Layer with Hierarchy Objects

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend Apps                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                    │
│  │  start   │  │ default │  │   v0    │                    │
│  └────┬─────┘  └────┬────┘  └────┬────┘                    │
│       │             │             │                          │
│       └─────────────┴─────────────┘                          │
│                    │                                          │
│       ┌────────────▼────────────┐                            │
│       │   Common Data Layer     │                            │
│       │  (Hierarchy Objects)    │                            │
│       └────────────┬────────────┘                            │
│                    │                                          │
│       ┌────────────▼────────────┐                            │
│       │   API Communication     │                            │
│       │   Layer (Services)       │                            │
│       └────────────┬────────────┘                            │
│                    │                                          │
│       ┌────────────▼────────────┐                            │
│       │      Backend API        │                            │
│       └─────────────────────────┘                            │
└─────────────────────────────────────────────────────────────┘
```

### Core Components

#### 1. Hierarchy Object Classes

Create TypeScript classes that mirror the backend hierarchy structure:

```typescript
// webapp-react/src/api/models/System.ts
export class System {
  id: string
  name: string
  description?: string
  timezone: string
  inverterArrays: InverterArray[]
  batteryArrays: BatteryArray[]
  meters: Meter[]
  
  // Methods
  getTotalPower(): number
  getTotalBatterySOC(): number
  getInverterById(id: string): Inverter | null
  getBatteryPackById(id: string): BatteryPack | null
}

// webapp-react/src/api/models/InverterArray.ts
export class InverterArray {
  id: string
  name: string
  systemId: string
  inverters: Inverter[]
  attachedBatteryArray: BatteryArray | null
  
  // Methods
  getTotalPower(): number
  getAverageEfficiency(): number
}

// webapp-react/src/api/models/BatteryArray.ts
export class BatteryArray {
  id: string
  name: string
  systemId: string
  batteryPacks: BatteryPack[]
  attachedInverterArray: InverterArray | null
  
  // Methods
  getTotalSOC(): number
  getTotalCapacity(): number
}

// webapp-react/src/api/models/Inverter.ts
export class Inverter {
  id: string
  name: string
  arrayId: string
  systemId: string
  telemetry: InverterTelemetry | null
  
  // Methods
  getPower(): number
  getEfficiency(): number
}

// webapp-react/src/api/models/BatteryPack.ts
export class BatteryPack {
  id: string
  name: string
  batteryArrayId: string
  systemId: string
  telemetry: BatteryTelemetry | null
  
  // Methods
  getSOC(): number
  getPower(): number
}

// webapp-react/src/api/models/Meter.ts
export class Meter {
  id: string
  name: string
  systemId: string
  telemetry: MeterTelemetry | null
  
  // Methods
  getPower(): number
  getImportEnergy(): number
  getExportEnergy(): number
}
```

#### 2. Hierarchy Manager

A singleton manager that:
- Loads hierarchy from backend
- Maintains object relationships
- Provides access to all hierarchy objects
- Updates telemetry for all devices
- Provides computed/aggregated values

```typescript
// webapp-react/src/api/managers/HierarchyManager.ts
export class HierarchyManager {
  private systems: Map<string, System> = new Map()
  private inverters: Map<string, Inverter> = new Map()
  private batteryPacks: Map<string, BatteryPack> = new Map()
  private meters: Map<string, Meter> = new Map()
  
  // Singleton instance
  private static instance: HierarchyManager
  
  static getInstance(): HierarchyManager
  
  // Load hierarchy from backend
  async loadHierarchy(): Promise<void>
  
  // Update telemetry for a device
  updateTelemetry(deviceId: string, telemetry: TelemetryData): void
  
  // Get objects
  getSystem(systemId: string): System | null
  getInverter(inverterId: string): Inverter | null
  getBatteryPack(packId: string): BatteryPack | null
  getMeter(meterId: string): Meter | null
  
  // Get all objects
  getAllSystems(): System[]
  getAllInverters(): Inverter[]
  getAllBatteryPacks(): BatteryPack[]
  getAllMeters(): Meter[]
  
  // Computed values
  getSystemTotalPower(systemId: string): number
  getSystemTotalBatterySOC(systemId: string): number
}
```

#### 3. React Hooks for Hierarchy Objects

Hooks that provide access to hierarchy objects:

```typescript
// webapp-react/src/api/hooks/useHierarchyObjects.ts
export function useSystem(systemId: string): System | null
export function useInverter(inverterId: string): Inverter | null
export function useBatteryPack(packId: string): BatteryPack | null
export function useMeter(meterId: string): Meter | null
export function useAllSystems(): System[]
export function useAllInverters(): Inverter[]
export function useAllBatteryPacks(): BatteryPack[]
export function useAllMeters(): Meter[]
```

#### 4. Data Synchronization Service

A service that:
- Polls backend for telemetry updates
- Updates hierarchy objects with new telemetry
- Maintains React Query cache
- Provides real-time updates

```typescript
// webapp-react/src/api/services/DataSyncService.ts
export class DataSyncService {
  private hierarchyManager: HierarchyManager
  private pollingInterval: number = 5000
  
  startPolling(): void
  stopPolling(): void
  updateTelemetry(): Promise<void>
}
```

---

## Implementation Plan

### Phase 1: Create Hierarchy Object Classes

**Goal**: Create TypeScript classes that represent the hierarchy structure.

**Tasks**:
1. Create `webapp-react/src/api/models/` directory
2. Create base classes:
   - `BaseDevice.ts` - Abstract base for all devices
   - `BaseArray.ts` - Abstract base for arrays
3. Create hierarchy classes:
   - `System.ts`
   - `InverterArray.ts`
   - `BatteryArray.ts`
   - `Inverter.ts`
   - `BatteryPack.ts`
   - `Meter.ts`
4. Add methods for:
   - Getting telemetry
   - Computing aggregated values
   - Navigating relationships

**Files to Create**:
- `webapp-react/src/api/models/BaseDevice.ts`
- `webapp-react/src/api/models/BaseArray.ts`
- `webapp-react/src/api/models/System.ts`
- `webapp-react/src/api/models/InverterArray.ts`
- `webapp-react/src/api/models/BatteryArray.ts`
- `webapp-react/src/api/models/Inverter.ts`
- `webapp-react/src/api/models/BatteryPack.ts`
- `webapp-react/src/api/models/Meter.ts`
- `webapp-react/src/api/models/index.ts`

**Estimated Time**: 2-3 hours

---

### Phase 2: Create Hierarchy Manager

**Goal**: Create a singleton manager that maintains the hierarchy and provides access to all objects.

**Tasks**:
1. Create `HierarchyManager.ts`
2. Implement singleton pattern
3. Implement hierarchy loading from backend
4. Implement object relationship building
5. Implement telemetry update methods
6. Implement computed value methods

**Files to Create**:
- `webapp-react/src/api/managers/HierarchyManager.ts`
- `webapp-react/src/api/managers/index.ts`

**Estimated Time**: 3-4 hours

---

### Phase 3: Update API Services

**Goal**: Update existing API services to work with hierarchy objects.

**Tasks**:
1. Update `hierarchyService.ts` to return hierarchy objects
2. Update `telemetryService.ts` to update hierarchy objects
3. Ensure all services work with the new structure

**Files to Modify**:
- `webapp-react/src/api/services/hierarchy.ts`
- `webapp-react/src/api/services/telemetry.ts`

**Estimated Time**: 2-3 hours

---

### Phase 4: Create React Hooks

**Goal**: Create React hooks that provide access to hierarchy objects.

**Tasks**:
1. Create `useHierarchyObjects.ts` hooks
2. Integrate with React Query
3. Provide real-time updates
4. Handle loading/error states

**Files to Create**:
- `webapp-react/src/api/hooks/useHierarchyObjects.ts`
- Update `webapp-react/src/api/hooks/index.ts`

**Estimated Time**: 2-3 hours

---

### Phase 5: Create Data Synchronization Service

**Goal**: Create a service that keeps hierarchy objects in sync with backend.

**Tasks**:
1. Create `DataSyncService.ts`
2. Implement polling logic
3. Update hierarchy objects with new telemetry
4. Integrate with React Query cache

**Files to Create**:
- `webapp-react/src/api/services/DataSyncService.ts`
- Update `webapp-react/src/api/services/index.ts`

**Estimated Time**: 2-3 hours

---

### Phase 6: Refactor `start` App

**Goal**: Update the `start` app to use the new hierarchy objects.

**Tasks**:
1. Simplify `DataProvider.tsx` to use hierarchy objects
2. Remove complex transformation logic
3. Use hierarchy object methods for computed values
4. Test all components still work

**Files to Modify**:
- `webapp-react/src/apps/start/src/data/DataProvider.tsx`

**Estimated Time**: 3-4 hours

---

### Phase 7: Update `default` and `v0` Apps

**Goal**: Update legacy apps to use the new common layer.

**Tasks**:
1. Analyze current data access patterns in `default` app
2. Analyze current data access patterns in `v0` app
3. Refactor to use hierarchy objects
4. Remove redundant code
5. Test all functionality

**Files to Modify**:
- `webapp-react/src/apps/default/**/*.tsx` (TBD after analysis)
- `webapp-react/src/apps/v0/**/*.tsx` (TBD after analysis)

**Estimated Time**: 4-6 hours

---

### Phase 8: Cleanup and Documentation

**Goal**: Remove old code and document the new structure.

**Tasks**:
1. Remove `mockData.ts` (if no longer needed)
2. Remove old transformation logic
3. Update documentation
4. Add JSDoc comments to all classes
5. Create usage examples

**Files to Remove/Update**:
- `webapp-react/src/apps/start/src/data/mockData.ts` (possibly)
- Various transformation files

**Estimated Time**: 2-3 hours

---

## Benefits

### 1. Code Simplification
- **Before**: 1000+ lines of transformation logic
- **After**: Simple object access and method calls
- **Reduction**: ~70% code reduction

### 2. Consistency
- All apps use the same data structure
- Same methods for computed values
- Same error handling

### 3. Maintainability
- Single source of truth for hierarchy
- Easy to add new features
- Easy to debug

### 4. Type Safety
- Full TypeScript support
- Compile-time error checking
- Better IDE autocomplete

### 5. Performance
- Efficient object relationships
- Cached computed values
- Optimized React re-renders

---

## Migration Strategy

### Step 1: Parallel Implementation
- Keep existing `DataProvider.tsx` working
- Implement new hierarchy objects alongside
- Test new implementation

### Step 2: Gradual Migration
- Migrate one app at a time
- Start with `start` app (most modern)
- Then migrate `default` and `v0`

### Step 3: Cleanup
- Remove old code once all apps migrated
- Update documentation
- Final testing

---

## Backend API Requirements

The backend must provide:

1. **`/api/config`** - Complete hierarchy structure
   - Systems, arrays, inverters, battery packs, meters
   - All relationships and metadata

2. **`/api/systems/{system_id}/now`** - System-level telemetry
   - Aggregated power, SOC, etc.

3. **`/api/arrays/{array_id}/now`** - Array-level telemetry
   - Array power, attached battery data

4. **`/api/inverters/{inverter_id}/now`** - Inverter telemetry
   - Individual inverter data

5. **`/api/battery-packs/{pack_id}/now`** - Battery pack telemetry
   - Individual battery pack data

6. **`/api/meters/{meter_id}/now`** - Meter telemetry
   - Individual meter data

**Note**: Most of these endpoints already exist or can be adapted from existing endpoints.

---

## Example Usage

### Before (Current)

```typescript
// Complex transformation in DataProvider.tsx
const homeHierarchy = useMemo(() => {
  // 500+ lines of transformation logic
  // Manual mapping of API responses
  // Complex nested loops
  // Error-prone
}, [apiHierarchy, homeTelemetry, ...]);
```

### After (Proposed)

```typescript
// Simple object access
const system = useSystem('system');
const totalPower = system?.getTotalPower() || 0;
const batterySOC = system?.getTotalBatterySOC() || 0;

// Navigate hierarchy
const inverter = system?.inverterArrays[0]?.inverters[0];
const inverterPower = inverter?.getPower() || 0;

// Access telemetry
const batteryPack = system?.batteryArrays[0]?.batteryPacks[0];
const batterySOC = batteryPack?.getSOC() || 0;
```

---

## File Structure

```
webapp-react/src/api/
├── models/                    # Hierarchy object classes
│   ├── BaseDevice.ts
│   ├── BaseArray.ts
│   ├── System.ts
│   ├── InverterArray.ts
│   ├── BatteryArray.ts
│   ├── Inverter.ts
│   ├── BatteryPack.ts
│   ├── Meter.ts
│   └── index.ts
├── managers/                  # Singleton managers
│   ├── HierarchyManager.ts
│   └── index.ts
├── services/                  # API services (updated)
│   ├── hierarchy.ts
│   ├── telemetry.ts
│   ├── energy.ts
│   ├── DataSyncService.ts
│   └── index.ts
├── hooks/                      # React hooks (updated)
│   ├── useHierarchy.ts
│   ├── useTelemetry.ts
│   ├── useEnergy.ts
│   ├── useHierarchyObjects.ts  # NEW
│   └── index.ts
├── types/                      # TypeScript types
│   ├── hierarchy.ts
│   ├── telemetry.ts
│   └── energy.ts
├── normalizers/                # Data normalizers (may be simplified)
│   ├── telemetry.ts
│   └── energy.ts
├── client.ts                   # HTTP client
└── index.ts                    # Main exports
```

---

## Testing Strategy

### Unit Tests
- Test hierarchy object classes
- Test HierarchyManager
- Test computed value methods

### Integration Tests
- Test API service integration
- Test React hooks
- Test data synchronization

### E2E Tests
- Test all three apps work correctly
- Test real-time updates
- Test error handling

---

## Timeline Estimate

| Phase | Description | Time Estimate |
|-------|-------------|---------------|
| Phase 1 | Create Hierarchy Object Classes | 2-3 hours |
| Phase 2 | Create Hierarchy Manager | 3-4 hours |
| Phase 3 | Update API Services | 2-3 hours |
| Phase 4 | Create React Hooks | 2-3 hours |
| Phase 5 | Create Data Sync Service | 2-3 hours |
| Phase 6 | Refactor `start` App | 3-4 hours |
| Phase 7 | Update `default` and `v0` Apps | 4-6 hours |
| Phase 8 | Cleanup and Documentation | 2-3 hours |
| **Total** | | **20-29 hours** |

---

## Questions to Resolve

1. **Should we keep `mockData.ts`?**
   - Option A: Remove it completely
   - Option B: Keep as fallback for development
   - **Recommendation**: Remove it, use hierarchy objects instead

2. **How to handle backward compatibility?**
   - Option A: Break compatibility, force all apps to migrate
   - Option B: Keep old `DataProvider` alongside new one
   - **Recommendation**: Option A (clean break)

3. **Should we use a state management library?**
   - Option A: React Query + Context (current)
   - Option B: Zustand/Redux for hierarchy state
   - **Recommendation**: Option A (React Query is sufficient)

4. **How to handle real-time updates?**
   - Option A: Polling (current)
   - Option B: WebSocket
   - **Recommendation**: Option A for now, WebSocket later

---

## Next Steps

1. ✅ **Review this plan** - Get approval from team
2. ⏳ **Analyze `default` and `v0` apps** - Understand their current data access
3. ⏳ **Start Phase 1** - Create hierarchy object classes
4. ⏳ **Implement incrementally** - One phase at a time
5. ⏳ **Test thoroughly** - Ensure all apps work correctly

---

## Appendix: Backend API Endpoints Reference

### Hierarchy Endpoints
- `GET /api/config` - Complete hierarchy structure
- `GET /api/systems` - List all systems
- `GET /api/systems/{system_id}` - Get system details

### Telemetry Endpoints
- `GET /api/home/now` - System-level telemetry (legacy, will be `/api/systems/{system_id}/now`)
- `GET /api/arrays/{array_id}/now` - Array-level telemetry
- `GET /api/now?inverter_id={id}` - Inverter telemetry
- `GET /api/battery/now?bank_id={id}` - Battery pack telemetry
- `GET /api/meters/{meter_id}/now` - Meter telemetry

### Energy Endpoints
- `GET /api/energy/hourly` - Hourly energy data
- `GET /api/energy/daily` - Daily energy summaries
- `GET /api/battery/hourly` - Battery hourly energy
- `GET /api/battery/daily` - Battery daily summaries

---

**Document Version**: 1.0  
**Last Updated**: 2025-01-XX  
**Author**: AI Assistant  
**Status**: Draft - Awaiting Review

