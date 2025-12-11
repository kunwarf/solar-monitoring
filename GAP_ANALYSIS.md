# Gap Analysis: Current Implementation vs. Correct API Structure

## Executive Summary

The current implementation has several gaps between how it structures data and how the backend API actually works. The main issues are:

1. **Device ID Mismatch**: Device IDs created in `DataProvider` don't match the actual backend device IDs
2. **Battery Data Lookup Complexity**: Multiple fallback chains and complex ID matching logic
3. **Inconsistent Telemetry Fetching**: Telemetry pages use different strategies to find data
4. **Missing Direct API Mapping**: Not using the correct API endpoints based on device hierarchy
5. **Duplicate Battery Array Creation**: Battery arrays are created twice (once in InverterArray, once in System)

---

## 1. Device ID Structure Gap

### Current Implementation

**In `DataProvider.tsx` (lines 677-742):**
- **Inverters**: Uses `inv.id` directly (e.g., `powdrive1`, `senergy1`) ✅ **CORRECT**
- **Batteries**: Creates synthetic IDs like `${batteryArrayId}-pack-${idx + 1}` or `${batteryArrayId}-${idx + 1}` ❌ **WRONG**
- **Meters**: Uses `meter.id` directly ✅ **CORRECT**

**Example Battery IDs Created:**
```typescript
// Line 264: pack.pack_id || `${array.batteryArrayId}-pack-${idx + 1}`
// Line 279: `${array.batteryArrayId}-${idx + 1}`
// Line 294: `${array.batteryArrayId}-1`
// Line 309: `${array.batteryArrayId}-1`
// Line 324: `${array.batteryArrayId}-1`
```

**Problem**: These synthetic IDs don't match actual backend battery bank IDs (e.g., `jkbms_bank_ble`, `battery1`).

### Correct Structure (from API)

**From `/api/config`:**
- Battery banks have IDs like: `jkbms_bank_ble`, `battery1`
- Battery arrays contain `battery_bank_ids: ['jkbms_bank_ble']`
- Battery array attachments link: `battery_bank_array_id: "battery_array1"` → `inverter_array_id: "array1"`

**From `/api/battery/now`:**
- Returns banks with IDs matching config (e.g., `jkbms_bank_ble`)
- Each bank has `devices[]` array with individual battery units
- Each bank has `cells_data[]` with cell-level information

### Impact

When clicking a battery device:
- Device ID: `battery_array1-pack-1` (synthetic)
- Telemetry page tries to find: `battery_array1-pack-1`
- API expects: `jkbms_bank_ble` (actual bank ID)
- **Result**: Battery telemetry lookup fails or finds wrong data

---

## 2. Battery Data Lookup Complexity

### Current Implementation

**In `DataProvider.tsx` (lines 203-343):**
1. First tries: `batteryDataMap.get(array.batteryArrayId)` (by array ID)
2. Then tries: Loop through `batteryArrayConfig.batteryBankIds` to find by bank ID
3. Then checks: `rawData?.packs` from array telemetry
4. Then checks: `batteryData.devices` from battery telemetry
5. Then checks: Aggregate battery data from array telemetry
6. Finally: Creates placeholder if nothing found

**In `BatteryCellGrid.tsx` (lines 316-360):**
1. Parses device ID with regex: `/^([^-]+(?:-[^-]+)*?)(?:-pack-|-)(\d+)$/`
2. Tries to find battery array by `potentialArrayId`
3. Fetches ALL battery data: `useBatteryTelemetry(undefined)`
4. Tries to match by array ID first
5. Then tries to match by bank IDs
6. Falls back to first available battery

**Problem**: Too many fallback chains, complex ID parsing, and fetching all batteries when only one is needed.

### Correct Approach

Based on hierarchy understanding:
1. **Battery Array** → Contains `batteryBankIds: ['jkbms_bank_ble']`
2. **Battery Bank ID** → Use directly: `/api/battery/now?bank_id=jkbms_bank_ble`
3. **Individual Battery Unit** → From `bank.devices[]` array
4. **Cell Data** → From `bank.cells_data[]` or `bank.cells[]`

**Simplified Flow:**
```
Device Click: battery_array1-pack-1
  ↓
Find Battery Array: battery_array1
  ↓
Get batteryBankIds: ['jkbms_bank_ble']
  ↓
Use pack index (1) to select: jkbms_bank_ble
  ↓
Fetch: /api/battery/now?bank_id=jkbms_bank_ble
  ↓
Display: bank.devices[0] (first battery unit) or cells_data[0]
```

---

## 3. Inconsistent Telemetry Fetching

### Current Implementation

**InverterTelemetry.tsx (line 110):**
```typescript
const { data: telemetry } = useInverterTelemetry(device.id, {...})
// Uses: /api/now?inverter_id=${device.id}
```
✅ **CORRECT** - Device ID matches backend inverter ID

**BatteryCellGrid.tsx (line 338):**
```typescript
const allBatteryData = useBatteryTelemetry(undefined, {...})
// Uses: /api/battery/now (fetches ALL batteries)
```
❌ **INEFFICIENT** - Fetches all batteries, then tries to match by ID

**MeterTelemetry.tsx (line 143):**
```typescript
const { data: homeTelemetry } = useHomeTelemetry({...})
// Uses: /api/home/now
// Then finds: homeTelemetry.meters.find(m => m.id === device.id)
```
✅ **CORRECT** - But relies on home telemetry containing all meters

### Correct Approach

**For Inverters:**
- Device ID = Inverter ID (e.g., `powdrive1`)
- API: `/api/now?inverter_id=powdrive1` ✅

**For Batteries:**
- Device should store: `{ batteryBankId: 'jkbms_bank_ble', packIndex: 0 }`
- API: `/api/battery/now?bank_id=jkbms_bank_ble` ✅
- Then extract: `bank.devices[packIndex]` or `bank.cells_data[packIndex]`

**For Meters:**
- Device ID = Meter ID (e.g., `grid_meter_1`)
- API: `/api/home/now` → `meters.find(m => m.id === device.id)` ✅

---

## 4. Missing Direct API Mapping

### Current Implementation

**Hierarchy Structure:**
```
Home
  └── Systems[]
      └── System
          ├── inverterArrays[] (1 array)
          │   └── inverters[] (multiple inverters)
          └── batteryArrays[] (1 array)
              └── batteries[] (multiple battery units)
```

**Problem**: 
- Battery arrays are created **twice** (lines 203-343 and 401-533 in DataProvider)
- Battery IDs are synthetic, not using actual bank IDs
- No direct mapping from device → API endpoint

### Correct Structure (Based on API Understanding)

```
Home
  └── Systems[]
      └── System (Inverter Array)
          ├── id: "array1"
          ├── name: "Ground Floor"
          ├── inverterIds: ["powdrive1", "powdrive2"]
          ├── batteryArrayId: "battery_array1" (from attachment)
          │
          ├── Inverters[]
          │   └── Inverter
          │       ├── id: "powdrive1" (actual inverter ID)
          │       ├── name: "Powdrive" (from config)
          │       └── API: /api/now?inverter_id=powdrive1
          │
          └── BatteryArray
              ├── id: "battery_array1"
              ├── name: "Ground Floor Battery Array"
              ├── batteryBankIds: ["jkbms_bank_ble"] (from config)
              └── Batteries[]
                  └── Battery
                      ├── id: "jkbms_bank_ble" (actual bank ID)
                      ├── name: "Pylontech Battery Bank" (from config)
                      ├── packIndex: 0 (which battery unit in the bank)
                      └── API: /api/battery/now?bank_id=jkbms_bank_ble
```

---

## 5. Device Creation Logic Issues

### Current Implementation

**In `DataProvider.tsx` (lines 703-718):**
```typescript
batteryArray.batteries.map((bat) => ({
  id: bat.id,  // This is synthetic: "battery_array1-pack-1"
  name: bat.name,
  type: "battery" as const,
  ...
}))
```

**Problem**: 
- `bat.id` is synthetic (created earlier in the same file)
- Doesn't match backend bank ID
- Telemetry page can't use it directly

### Correct Approach

**Device should store:**
```typescript
{
  id: "jkbms_bank_ble",  // Actual bank ID from config
  name: "Pylontech Battery Bank #1",
  type: "battery",
  batteryBankId: "jkbms_bank_ble",  // For API calls
  packIndex: 0,  // Which battery unit (0, 1, 2...)
  batteryArrayId: "battery_array1",  // Parent array
  ...
}
```

---

## 6. Aggregation Logic Gaps

### Current Implementation

**In `DataProvider.tsx` (lines 145-201):**
- Fetches array telemetry for each inverter array
- Extracts individual inverter data from `raw.inverters[]`
- Divides array totals if individual data not available
- Creates battery data from `raw.packs[]` or `batteryData.devices[]`

**Problem**:
- Aggregation happens at wrong level (array level, not system level)
- Battery data mixing (array telemetry packs vs. battery telemetry devices)
- No clear separation between array-level and device-level data

### Correct Approach

**Based on API Understanding:**

1. **Array Telemetry** (`/api/arrays/{arrayId}/now`):
   - Aggregated data for all inverters in array
   - May include `packs[]` if battery is attached
   - Use for: Array-level metrics, aggregated displays

2. **Inverter Telemetry** (`/api/now?inverter_id={id}`):
   - Individual inverter data
   - Use for: Inverter detail pages

3. **Battery Telemetry** (`/api/battery/now?bank_id={id}`):
   - Individual battery bank data
   - Contains `devices[]` (battery units) and `cells_data[]` (cell info)
   - Use for: Battery detail pages

4. **Home Telemetry** (`/api/home/now`):
   - Home-level aggregated data
   - Contains `meters[]` array
   - Use for: Home dashboard, meter data

---

## 7. Navigation and URL Parameters

### Current Implementation

**HierarchicalDeviceOverview.tsx (lines 315, 345, 389):**
```typescript
<Link to={`/start/telemetry?device=${inverter.id}`}>
<Link to={`/start/telemetry?device=${battery.id}`}>
<Link to={`/start/telemetry?device=${meter.id}`}>
```

**Problem**:
- Battery `id` is synthetic (e.g., `battery_array1-pack-1`)
- Telemetry page receives this synthetic ID
- Must parse and match to find actual battery data

### Correct Approach

**Option 1: Use actual bank ID + pack index**
```typescript
<Link to={`/start/telemetry?device=${batteryBankId}&pack=${packIndex}`}>
```

**Option 2: Use composite ID**
```typescript
<Link to={`/start/telemetry?device=battery:${batteryBankId}:${packIndex}`}>
```

**Option 3: Store full device context**
```typescript
device = {
  id: "jkbms_bank_ble",
  type: "battery",
  batteryBankId: "jkbms_bank_ble",
  packIndex: 0,
  ...
}
// URL: /start/telemetry?device=jkbms_bank_ble&type=battery&pack=0
```

---

## Summary of Gaps

| Issue | Current | Correct | Impact |
|-------|---------|---------|--------|
| **Battery Device IDs** | Synthetic (`battery_array1-pack-1`) | Actual bank ID (`jkbms_bank_ble`) | High - Telemetry lookup fails |
| **Battery Data Lookup** | Complex fallback chains | Direct: `/api/battery/now?bank_id={id}` | High - Inefficient, error-prone |
| **Device Structure** | Flat device list | Hierarchical with context | Medium - Missing relationships |
| **Telemetry Fetching** | Inconsistent strategies | Direct API mapping | Medium - Performance issues |
| **Battery Array Creation** | Created twice | Created once with correct IDs | Low - Code duplication |
| **Aggregation Logic** | Mixed array/device data | Clear separation by level | Medium - Incorrect aggregations |

---

## Recommendations

### 1. Simplify Device ID Structure
- Use actual backend IDs for all devices
- Store additional context (packIndex, batteryBankId) in device object
- Remove synthetic ID generation

### 2. Direct API Mapping
- Map device type + ID directly to API endpoint
- Inverter: `/api/now?inverter_id={id}`
- Battery: `/api/battery/now?bank_id={id}`
- Meter: `/api/home/now` → `meters.find(m => m.id === id)`

### 3. Simplify Battery Data Flow
- Remove complex fallback chains
- Use hierarchy to get `batteryBankIds` from battery array
- Fetch battery data directly using bank ID
- Extract pack/unit data from `bank.devices[]` or `bank.cells_data[]`

### 4. Clear Data Separation
- Array-level: Use array telemetry for aggregated displays
- Device-level: Use individual device telemetry for detail pages
- Home-level: Use home telemetry for dashboard metrics

### 5. Consistent Device Structure
```typescript
interface Device {
  id: string;  // Actual backend ID
  name: string;  // From config
  type: 'inverter' | 'battery' | 'meter';
  
  // Context for API calls
  inverterId?: string;  // For inverters
  batteryBankId?: string;  // For batteries
  packIndex?: number;  // For battery units
  batteryArrayId?: string;  // Parent array
  
  // Hierarchy context
  systemId?: string;
  inverterArrayId?: string;
  
  // Display data
  metrics: {...};
  status: 'online' | 'offline' | 'warning';
}
```

---

---

## 8. Energy Meter Attachment and Display Gaps

### Current Implementation

**Backend API (`/api/home/now` - lines 929-938):**
```python
# Get home-attached meters (attachment_target == "home")
meter_telemetry = {}
if solar_app.cfg.meters:
    for meter_cfg in solar_app.cfg.meters:
        if getattr(meter_cfg, 'attachment_target', None) == "home":
            meter_id = meter_cfg.id
            if hasattr(solar_app, 'meter_last') and solar_app.meter_last:
                meter_tel = solar_app.meter_last.get(meter_id)
                if meter_tel:
                    meter_telemetry[meter_id] = meter_tel
```

**Config Structure (`config.yaml` - line 201):**
```yaml
meters:
  - id: grid_meter_1
    name: IAMMeter
    array_id: home  # ← Uses array_id, not attachment_target
    adapter:
      type: iammeter
      # ...
```

**Config Model (`solarhub/config.py` - line 147):**
```python
class MeterConfig(BaseModel):
    id: str
    name: Optional[str] = None
    array_id: Optional[str] = None  # ← Field is array_id
    adapter: MeterAdapterConfig
```

**Frontend DataProvider (lines 543-576):**
```typescript
const meters: Meter[] = (homeTelemetry?.meters || []).map(meter => {
  // Maps meters from homeTelemetry.meters array
  // Expects: { id, name, power, importKwh, exportKwh }
})
```

**Frontend Display (`HierarchicalDeviceOverview.tsx` - lines 514-522):**
```typescript
{homeHierarchy.meters.length > 0 && (
  <div className="space-y-2">
    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide px-1">Energy Meters</p>
    {homeHierarchy.meters.map((meter) => (
      <MeterCard key={meter.id} meter={meter} />
    ))}
  </div>
)}
```

### Problem

**Mismatch between Config Field and Backend Filter:**
1. **Config uses**: `array_id: "home"` (line 201 in config.yaml)
2. **Backend checks**: `attachment_target == "home"` (line 933 in api_server.py)
3. **Config model has**: `array_id` field, but no `attachment_target` field
4. **Result**: Meters with `array_id: "home"` are **NOT** included in `/api/home/now` response because the filter doesn't match

**Additional Issues:**
- Backend only includes meters in `meter_telemetry` if `meter_last.get(meter_id)` returns data
- If meter adapter hasn't polled yet, `meter_last` might be empty
- Frontend expects `homeTelemetry.meters` array, but it might be empty or undefined
- No fallback to show meters from config even if telemetry is missing

### Correct Structure (Based on API Understanding)

**From `HIERARCHY_CONFIGURATION_GUIDE.md` (lines 140-159):**
```yaml
meters:
  - id: grid_meter_1
    name: "Main Grid Connection Meter"
    attachment_target: home  # ← Should use attachment_target
    adapter:
      type: iammeter
      # ...
  
  - id: array1_meter
    name: "Array 1 Grid Meter"
    attachment_target: array1  # ← Can attach to specific array
    adapter:
      type: iammeter
      # ...
```

**Backend API Response Structure:**
```json
{
  "status": "ok",
  "home": {
    "meters": [
      {
        "meter_id": "grid_meter_1",
        "power_w": 1234.5,
        "voltage_v": 230.0,
        "current_a": 5.4,
        "frequency_hz": 50.0
      }
    ]
  }
}
```

**Frontend Normalizer (`telemetry.ts` - lines 80-86):**
```typescript
meters: data.meters?.map((meter) => ({
  id: meter.meter_id,
  name: meter.name,
  power: (meter.power_w || 0) / 1000,
  importKwh: meter.import_kwh || 0,
  exportKwh: meter.export_kwh || 0,
}))
```

**Note**: The normalizer expects `import_kwh` and `export_kwh` fields, but the backend `meter_breakdown` (lines 376-401 in array_aggregator.py) only includes `power_w`, `voltage_v`, `current_a`, `frequency_hz`. **Missing import/export energy fields!**

### Impact

1. **Meters Not Showing**: Meters configured with `array_id: "home"` are filtered out because backend checks `attachment_target`
2. **Missing Energy Data**: Frontend expects `importKwh` and `exportKwh`, but backend doesn't provide them in `meter_breakdown`
3. **No Fallback**: If meter telemetry is missing, meters don't appear even if configured
4. **Array-Level Meters**: Meters attached to arrays (not home) are not included in `/api/home/now` at all

### Correct Approach

**Option 1: Fix Config Field Name (Recommended)**
- Update config to use `attachment_target` instead of `array_id` for meters
- Update `MeterConfig` model to support both `array_id` (legacy) and `attachment_target` (new)
- Backend should check both: `attachment_target == "home"` OR `array_id == "home"`

**Option 2: Fix Backend Filter**
- Update backend to check `array_id == "home"` instead of `attachment_target == "home"`
- Or check both fields: `getattr(meter_cfg, 'attachment_target', None) == "home" or getattr(meter_cfg, 'array_id', None) == "home"`

**Option 3: Add Missing Energy Fields**
- Backend should include `import_kwh` and `export_kwh` in `meter_breakdown`
- These should come from meter telemetry or daily summaries
- Frontend normalizer expects these fields

**Option 4: Show Meters from Config**
- Even if telemetry is missing, show meters from config
- Use placeholder values (0) for power/energy if telemetry unavailable
- This ensures meters appear in hierarchy even before first poll

### Meter Hierarchy Understanding

**From Configuration Guide:**
- Meters can be attached to **"home"** (measures total consumption across all arrays)
- Meters can be attached to **specific arrays** (measures consumption for that array)
- Home-level meters appear in `/api/home/now` response
- Array-level meters should appear in `/api/arrays/{arrayId}/now` response (if implemented)

**Current Implementation:**
- Only home-level meters are included in `/api/home/now`
- Array-level meters are not exposed via API
- Frontend only displays home-level meters
- No way to show array-level meters in hierarchy

### Recommendations

1. **Fix Config/Backend Mismatch**:
   - Support both `array_id` and `attachment_target` in config
   - Backend should check both fields when filtering meters
   - Or standardize on one field name

2. **Add Missing Energy Fields**:
   - Include `import_kwh` and `export_kwh` in backend `meter_breakdown`
   - Fetch from meter daily summaries or telemetry
   - Update `HomeTelemetry` model to include these fields

3. **Show Meters from Config**:
   - Even if telemetry is missing, include meters from config
   - Use placeholder values until telemetry is available
   - This ensures meters appear in UI immediately

4. **Support Array-Level Meters**:
   - Include array-level meters in array telemetry response
   - Display them under their respective systems in hierarchy
   - Or create a separate section for array-level meters

5. **Consistent Field Names**:
   - Use `attachment_target` consistently (matches battery array attachments pattern)
   - Or use `array_id` consistently (matches inverter pattern)
   - Document which field to use in config guide

---

## Summary of Gaps (Updated)

| Issue | Current | Correct | Impact |
|-------|---------|---------|--------|
| **Battery Device IDs** | Synthetic (`battery_array1-pack-1`) | Actual bank ID (`jkbms_bank_ble`) | High - Telemetry lookup fails |
| **Battery Data Lookup** | Complex fallback chains | Direct: `/api/battery/now?bank_id={id}` | High - Inefficient, error-prone |
| **Device Structure** | Flat device list | Hierarchical with context | Medium - Missing relationships |
| **Telemetry Fetching** | Inconsistent strategies | Direct API mapping | Medium - Performance issues |
| **Battery Array Creation** | Created twice | Created once with correct IDs | Low - Code duplication |
| **Aggregation Logic** | Mixed array/device data | Clear separation by level | Medium - Incorrect aggregations |
| **Meter Config Field** | Uses `array_id: "home"` | Should use `attachment_target: "home"` | High - Meters not showing |
| **Meter Energy Data** | Missing `import_kwh`/`export_kwh` | Include in backend response | Medium - Missing data in UI |
| **Meter Fallback** | No meters if telemetry missing | Show from config with placeholders | Medium - Meters don't appear |
| **Array-Level Meters** | Not exposed via API | Include in array telemetry | Low - Feature missing |

---

## Next Steps

1. **Refactor DataProvider**: Simplify battery device creation to use actual bank IDs
2. **Update Device Structure**: Add context fields (batteryBankId, packIndex)
3. **Simplify Telemetry Fetching**: Direct API mapping based on device type and ID
4. **Update Navigation**: Use actual device IDs in URLs, pass context via query params if needed
5. **Remove Duplicate Logic**: Consolidate battery array creation into single location
6. **Fix Meter Configuration**: Support both `array_id` and `attachment_target`, or standardize on one
7. **Add Meter Energy Fields**: Include `import_kwh` and `export_kwh` in backend meter response
8. **Show Meters from Config**: Display meters even if telemetry is missing (with placeholders)
9. **Test with Real Data**: Verify with actual backend responses

