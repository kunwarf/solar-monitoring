# Frontend Telemetry Data Flow Analysis

## Problem Statement
Summary cards are showing data correctly, but the Device Hierarchy section shows all devices as "Offline" with 0.0 kW values, even though telemetry data is being received from the backend.

## Data Flow Analysis

### 1. Summary Cards (Working ✅)

**Data Path:**
```
Index.tsx
  → useEnergyStatsData()
    → DataProvider.energyStats
      → useMemo([homeTelemetry])
        → homeTelemetry from useHomeTelemetry()
          → telemetryService.getSystemNow()
            → /api/system/now
```

**Why it works:**
- Direct dependency on `homeTelemetry` from React Query
- When API response updates, `homeTelemetry` changes, triggering `useMemo` to re-run
- Data flows directly from API → hook → component

### 2. Device Hierarchy (Not Working ❌)

**Data Path:**
```
HierarchicalDeviceOverview.tsx
  → useHomeHierarchyData()
    → DataProvider.homeHierarchy
      → useMemo([manager, systems])  ← PROBLEM HERE
        → Transforms hierarchy objects
          → inverter.getTelemetry()
          → pack.getTelemetry()
          → meter.getTelemetry()
```

**Why it doesn't work:**
1. **Telemetry Update Flow:**
   - `useHomeTelemetry()` calls `telemetryService.getSystemNow()`
   - `getSystemNow()` extracts individual device telemetry from nested response
   - Updates hierarchy objects via `manager.updateTelemetry()` and `manager.updateBatteryTelemetry()`
   - **These updates mutate the hierarchy objects directly**

2. **React Re-render Issue:**
   - The `homeHierarchy` `useMemo` depends only on `[manager, systems]`
   - When telemetry updates, the objects are mutated but `manager` and `systems` references don't change
   - React doesn't detect the mutation, so `useMemo` doesn't re-run
   - The transformed hierarchy data stays stale with old (or null) telemetry values

3. **Result:**
   - Hierarchy objects have updated telemetry internally
   - But the transformed `homeHierarchy` object still has old values
   - Components show "Offline" and 0.0 kW because they're reading from stale transformed data

## Root Cause

The `homeHierarchy` transformation in `DataProvider.tsx` line 98 has incorrect dependencies:

```typescript
const homeHierarchy: HomeHierarchy | null = useMemo(() => {
  // ... transforms hierarchy objects
  // ... calls inverter.getTelemetry(), pack.getTelemetry(), etc.
}, [manager, systems]);  // ❌ Missing homeTelemetry dependency
```

## Solution

Add `homeTelemetry` to the dependency array to trigger re-transformation when telemetry updates:

```typescript
const homeHierarchy: HomeHierarchy | null = useMemo(() => {
  // ... transforms hierarchy objects
}, [manager, systems, homeTelemetry]);  // ✅ Added homeTelemetry
```

**Why this works:**
- When `homeTelemetry` updates (from API), the `useMemo` re-runs
- The transformation re-reads hierarchy objects (which now have updated telemetry)
- Components receive fresh data and re-render

## Additional Issues to Check

1. **Telemetry Extraction**: Verify that `telemetryService.getSystemNow()` correctly extracts telemetry from the nested response structure (`system.inverter_arrays[].inverters[].telemetry`)

2. **Response Structure**: Confirm backend `/api/system/now` returns data in expected format:
   ```json
   {
     "system": {
       "inverter_arrays": [
         {
           "inverters": [
             {
               "inverter_id": "powdrive1",
               "telemetry": {
                 "pv_power_w": 1000,
                 "load_power_w": 500,
                 ...
               }
             }
           ]
         }
       ],
       "battery_arrays": [
         {
           "battery_packs": [
             {
               "pack_id": "battery1",
               "telemetry": {
                 "soc": 95,
                 "power": 1000,
                 ...
               }
             }
           ]
         }
       ]
     }
   }
   ```

3. **Normalization**: Check that `normalizeTelemetry()` correctly converts backend format to frontend `TelemetryData` format

4. **Status Calculation**: Verify `getStatus()` method correctly determines online/offline based on telemetry freshness

## Files to Modify

1. `webapp-react/src/apps/start/src/data/DataProvider.tsx`
   - Line 203: Add `homeTelemetry` to dependency array

2. Verify telemetry extraction in:
   - `webapp-react/src/api/services/telemetry.ts` (lines 66-126)

## Testing Checklist

- [ ] Summary cards continue to show correct data
- [ ] Device hierarchy shows real-time telemetry values (not 0.0 kW)
- [ ] Device status shows "online" when telemetry is recent
- [ ] Inverter metrics (solar, load, grid, battery power) update correctly
- [ ] Battery pack metrics (SOC, power, voltage) update correctly
- [ ] Array aggregates calculate correctly from individual device telemetry
- [ ] System aggregates calculate correctly from array telemetry

