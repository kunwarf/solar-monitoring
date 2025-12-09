# Inverter-Specific Settings Pages - Requirements Document

## Current State

### Existing Implementation
- **Single Settings Page**: `InverterConfigWizard` component handles all inverter settings
- **Dynamic TOU Windows**: `TOUWindowGrid` adapts based on capabilities from API
- **Inverter Selection**: Dropdown selector to choose which inverter to configure
- **API Endpoints**:
  - `/api/inverter/capabilities` - Returns TOU window capabilities
  - `/api/inverter/tou-windows` - Returns/updates TOU windows
  - `/api/inverter/sensors` - Returns inverter control sensors

### Current Inverter Types & Differences

#### Senergy Inverter
- **TOU Windows**: 3 separate charge windows + 3 separate discharge windows
- **Window Structure**: Fixed type (charge or discharge)
- **Settings**: Standard inverter controls + TOU windows

#### Powdrive Inverter
- **TOU Windows**: 6 bidirectional windows
- **Window Structure**: Each window can be charge, discharge, or auto (determined by target SOC)
- **Settings**: Standard inverter controls + TOU windows + voltage mode support

## Requirements

### 1. Modular Settings Components Architecture

Create reusable, card-based components for each settings section. Each section will be displayed as a separate card, and components can be reused across inverter types where appropriate.

#### 1.1 Component Structure
```
webapp-react/src/components/wizard/inverter/
├── InverterConfigWizard.tsx (main router component)
├── pages/
│   ├── SenergySettingsPage.tsx
│   ├── PowdriveSettingsPage.tsx
│   ├── SolArkSettingsPage.tsx (future)
│   └── DeyeSettingsPage.tsx (future)
└── sections/
    ├── SpecificationCard.tsx (common - all inverters)
    ├── GridSettingsCard.tsx (common - all inverters)
    ├── AuxiliarySettingsCard.tsx (common - all inverters)
    ├── BatteryTypeCard.tsx (common - all inverters)
    ├── BatteryChargingCard.tsx (common - all inverters)
    ├── WorkModeCard.tsx (common - all inverters)
    ├── WorkModeDetailCard.tsx (common - all inverters)
    ├── TOUWindowsCard.tsx (type-specific variants)
    │   ├── SenergyTOUCard.tsx (3 charge + 3 discharge)
    │   ├── PowdriveTOUCard.tsx (6 bidirectional - reusable for Sol-Ark/Deye)
    │   └── GenericTOUCard.tsx (fallback)
    └── InverterControlsCard.tsx (common - all inverters)
```

#### 1.2 Component Responsibilities

**InverterConfigWizard (Router)**
- Detects inverter type from selected inverter
- Renders appropriate type-specific settings page
- Handles inverter selection dropdown
- Manages common state (selected inverter, loading, etc.)

**Settings Page Components (SenergySettingsPage, PowdriveSettingsPage, etc.)**
- Composes relevant section cards for that inverter type
- Determines which cards to show based on inverter capabilities
- Manages page-level state and data fetching

**Section Card Components**
- Each card is a self-contained, reusable component
- Displays settings in a card format with edit functionality
- Handles its own data loading and saving
- Can be reused across multiple inverter types where applicable

### 2. Inverter Type Detection

#### 2.1 Detection Methods (Priority Order)
1. **From API Response**: Add `adapter_type` to `/api/inverter/capabilities` endpoint
2. **From Config**: Use `/api/devices` endpoint which returns `adapter.type`
3. **Fallback**: Use capabilities to infer type (bidirectional = Powdrive, separate = Senergy)

#### 2.2 API Enhancement
Add `adapter_type` field to capabilities response:
```json
{
  "inverter_id": "senergy1",
  "capabilities": {
    "adapter_type": "senergy",  // NEW
    "max_windows": 3,
    "bidirectional": false,
    "separate_charge_discharge": true,
    "max_charge_windows": 3,
    "max_discharge_windows": 3
  }
}
```

### 3. Settings Sections (Card Components)

Based on the UI images, the following sections should be implemented as separate card components:

#### 3.1 Specification Card (Common - All Inverters) - **READ ONLY**
**Fields:**
- Driver (adapter type): Deye/SunSynk/Sol-Ark 3 Phase, Senergy, Powdrive, etc.
- Serial number
- Protocol version
- Max AC output power (kW)
- MPPT connections
- Parallel (Enabled/Disabled)
- Modbus number

**Component:** `SpecificationCard.tsx`
**Reusability:** ✅ All inverters
**Edit Mode:** ❌ Read-only (display only)

#### 3.2 Grid Settings Card (Common - All Inverters)
**Fields:**
- Grid voltage high (V)
- Grid voltage low (V)
- Grid frequency (Hz)
- Grid frequency high (Hz)
- Grid frequency low (Hz)
- Grid peak shaving (Enabled/Disabled)
- Grid peak shaving power (kW)

**Component:** `GridSettingsCard.tsx`
**Reusability:** ✅ All inverters

#### 3.3 Auxiliary/Generator Settings Card (Common - All Inverters)
**Fields:**
- Auxiliary port (Generator input, etc.)
- Generator connected to grid input (Enabled/Disabled)
- Generator peak shaving (Enabled/Disabled)
- Generator peak shaving power (kW)
- Generator stop capacity (%)
- Generator start capacity (%)
- Generator max run time (h)
- Generator down time (h)

**Component:** `AuxiliarySettingsCard.tsx`
**Reusability:** ✅ All inverters

#### 3.4 Battery Type Card (Common - All Inverters)
**Fields:**
- Battery type (Lithium, Lead-acid, etc.)
- Lithium protocol (if applicable)
- Battery operation (State of charge, Voltage, etc.)
- Battery capacity (Ah)

**Component:** `BatteryTypeCard.tsx`
**Reusability:** ✅ All inverters

#### 3.5 Battery Charging Card (Common - All Inverters)
**Fields:**
- Max discharge current (A)
- Max charge current (A)
- Max grid charge current (A)
- Max generator charge current (A)
- Battery float charge voltage (V)
- Battery absorption charge voltage (V)
- Battery equalization charge voltage (V)

**Component:** `BatteryChargingCard.tsx`
**Reusability:** ✅ All inverters

#### 3.6 Work Mode Card (Common - All Inverters)
**Fields:**
- Remote switch (On/Off)
- Grid charge (Enabled/Disabled)
- Generator charge (Enabled/Disabled)
- Force generator on (Enabled/Disabled)
- Output shutdown capacity (%)
- Stop battery discharge capacity (%)
- Start battery discharge capacity (%)
- Start grid charge capacity (%)

**Component:** `WorkModeCard.tsx`
**Reusability:** ✅ All inverters

#### 3.7 Work Mode Detail Card (Common - All Inverters)
**Fields:**
- Work mode (Zero export to load, etc.)
- Solar export when battery full (Enabled/Disabled)
- Energy pattern (Load first, etc.)
- Max sell power (kW)
- Max solar power (kW)
- Grid trickle feed (W)

**Component:** `WorkModeDetailCard.tsx`
**Reusability:** ✅ All inverters

#### 3.8 TOU Windows Card (Type-Specific)
**Senergy Variant:**
- 3 Charge Windows (separate section)
- 3 Discharge Windows (separate section)
- Each window: start time, end time, power, target SOC

**Powdrive/Sol-Ark/Deye Variant:**
- 6 Bidirectional Windows (single section)
- Each window: start time, end time, power, target SOC, target voltage (optional)
- Window type selector: Auto/Charge/Discharge

**Components:**
- `SenergyTOUCard.tsx` - Senergy-specific (3+3)
- `PowdriveTOUCard.tsx` - Powdrive/Sol-Ark/Deye (6 bidirectional)
- `GenericTOUCard.tsx` - Fallback for unknown types

**Reusability:** 
- Senergy: Senergy only
- Powdrive: ✅ Powdrive, Sol-Ark, Deye (shared component)

#### 3.9 Inverter Controls Card (Common - All Inverters)
**Fields:**
- Dynamic list of editable sensors/registers from API
- Each sensor: name, current value, type, unit, min/max, description
- Edit functionality for each sensor

**Component:** `InverterControlsCard.tsx`
**Reusability:** ✅ All inverters (sensors may differ, but component is reusable)

### 4. Implementation Approach

#### 4.1 Phase 1: Refactor Current Component
- Extract common logic from `InverterConfigWizard`
- Create type-specific components
- Add type detection logic
- Maintain backward compatibility

#### 4.2 Phase 2: Enhance API
- Add `adapter_type` to capabilities endpoint
- Ensure all necessary data is available

#### 4.3 Phase 3: Type-Specific UI
- Implement SenergySettingsPage with Senergy-specific layout
- Implement PowdriveSettingsPage with Powdrive-specific layout
- Test with both inverter types

### 5. UI/UX Considerations

#### 5.1 Card Layout
- Each settings section displayed as a separate card
- Cards arranged in a responsive grid layout
- Each card has:
  - Title with "edit" link/button
  - Two-column layout: Label | Value
  - Edit mode: Form fields with save/cancel
  - View mode: Read-only display of current values
- Consistent card styling with theme support (dark/light)

#### 5.2 Page Layout
- Settings page shows all relevant cards for the selected inverter type
- Cards can be shown/hidden based on inverter capabilities
- Responsive: 1 column (mobile) → 2 columns (tablet) → 3 columns (desktop)
- Cards are independent - can edit one at a time

#### 5.3 User Experience
- Clear indication of which inverter type is being configured (in Specification card)
- Helpful descriptions for each setting
- Validation appropriate for each setting type
- Error handling for unsupported operations
- Loading states for each card
- Success/error feedback on save

### 6. Component Reusability Matrix

| Component | Senergy | Powdrive | Sol-Ark | Deye | Notes |
|-----------|---------|----------|---------|------|-------|
| SpecificationCard | ✅ | ✅ | ✅ | ✅ | All inverters |
| GridSettingsCard | ✅ | ✅ | ✅ | ✅ | All inverters |
| AuxiliarySettingsCard | ✅ | ✅ | ✅ | ✅ | All inverters |
| BatteryTypeCard | ✅ | ✅ | ✅ | ✅ | All inverters |
| BatteryChargingCard | ✅ | ✅ | ✅ | ✅ | All inverters |
| WorkModeCard | ✅ | ✅ | ✅ | ✅ | All inverters |
| WorkModeDetailCard | ✅ | ✅ | ✅ | ✅ | All inverters |
| SenergyTOUCard | ✅ | ❌ | ❌ | ❌ | Senergy only |
| PowdriveTOUCard | ❌ | ✅ | ✅ | ✅ | Shared by Powdrive/Sol-Ark/Deye |
| InverterControlsCard | ✅ | ✅ | ✅ | ✅ | All inverters (sensors may differ) |

### 7. Future Extensibility

#### 7.1 Adding New Inverter Types
1. Create new page component: `{Brand}SettingsPage.tsx`
2. Compose relevant section cards (reuse common cards, create type-specific if needed)
3. Add type detection in router
4. Define capabilities in adapter
5. Update API to return new type

#### 7.2 Adding New Settings Sections
1. Create new card component: `{Section}Card.tsx`
2. Add to relevant settings pages
3. Implement API endpoints if needed
4. Add to reusability matrix

#### 7.3 Settings Variations
- Some inverters may have more/less settings within a section
- Cards should handle missing/optional fields gracefully
- Some inverters may have completely different settings
- Create new card components for unique sections

## Implementation Details

### Component Props Interface
Each card component should follow this pattern:
```typescript
interface SettingsCardProps {
  inverterId: string
  data?: any  // Current values from API (passed from page)
  onSave?: (values: any) => Promise<void>
  loading?: boolean
  saving?: boolean
  onDataChange?: () => void  // Callback to refresh data after save
}
```

### Data Flow
1. **Page Load/Inverter Selection**: Settings page loads ALL data for selected inverter
2. **Data Distribution**: Settings page passes relevant data to each card component
3. **Card Display**: Cards display data in read-only mode by default
4. **Edit Mode**: User clicks "edit" on a card → card enters edit mode
5. **Save Operation**: 
   - Card calls API to save changes
   - API writes to inverter registers via adapter
   - API re-reads changed registers from inverter to confirm
   - API updates cached telemetry data (adapter.last_tel.extra)
   - API returns updated values
6. **Data Refresh**: After successful save, page refreshes data for that section
7. **Cache Update**: System caches updated register values in memory (adapter.last_tel.extra)

### API Endpoints Required

#### GET Endpoints (Read Data)
All endpoints follow this pattern:
1. Check settings cache for inverter_id and section
2. If cache hit: 
   - Check timestamp → If expired (>= 1 hour old): Read from inverter → Update cache → Return
   - If not expired (< 1 hour old): Return cached values
3. If cache miss: Read registers from inverter → Store in cache with timestamp → Return values

**Cache Expiration Logic**:
```python
import time
CACHE_EXPIRY_SECONDS = 3600  # 1 hour

def is_cache_valid(cache_entry):
    if not cache_entry or 'timestamp' not in cache_entry:
        return False
    age = time.time() - cache_entry['timestamp']
    return age < CACHE_EXPIRY_SECONDS
```

**Note**: Settings registers are NOT read during regular polling. They are read on-demand when these endpoints are called.

- `GET /api/inverter/specification?inverter_id={id}` - Specification data (read-only)
- `GET /api/inverter/grid-settings?inverter_id={id}` - Grid settings
- `GET /api/inverter/auxiliary-settings?inverter_id={id}` - Auxiliary/Generator settings
- `GET /api/inverter/battery-type?inverter_id={id}` - Battery type settings
- `GET /api/inverter/battery-charging?inverter_id={id}` - Battery charging settings
- `GET /api/inverter/work-mode?inverter_id={id}` - Work mode settings
- `GET /api/inverter/work-mode-detail?inverter_id={id}` - Work mode detail settings
- `GET /api/inverter/tou-windows?inverter_id={id}` - TOU windows (existing, may need update)
- `GET /api/inverter/sensors?inverter_id={id}` - Inverter controls (existing, may need update)

#### POST Endpoints (Update Data)
All POST endpoints follow this pattern:
1. Receive updated values in request body
2. Write to inverter registers via adapter.handle_command() or adapter.write_by_ident()
3. **Re-read only changed registers from inverter** to confirm values
4. Update settings cache with read-back values (not adapter.last_tel.extra)
5. Save to database (solar_app.logger.set_config())
6. Republish via MQTT if available (optional for settings)
7. Return updated values in response

**Important**: Only the registers that were actually changed are re-read and updated in cache. Other cached settings remain unchanged.

- `POST /api/inverter/grid-settings` - Update grid settings
- `POST /api/inverter/auxiliary-settings` - Update auxiliary/generator settings
- `POST /api/inverter/battery-type` - Update battery type settings
- `POST /api/inverter/battery-charging` - Update battery charging settings
- `POST /api/inverter/work-mode` - Update work mode settings
- `POST /api/inverter/work-mode-detail` - Update work mode detail settings
- `POST /api/inverter/tou-windows` - Update TOU windows (existing)
- `POST /api/inverter/sensors/{sensor_id}` - Update sensor value (existing)

**Note:** Specification endpoint is read-only (no POST endpoint needed)

## Settings Registers vs Operational Registers

### Register Classification

**Operational Registers** (Read during polling):
- Power values: `pv_power_w`, `load_power_w`, `grid_power_w`, `batt_power_w`
- Voltage/Current: `battery_voltage_v`, `battery_current_a`, `grid_voltage_v`
- Status: `battery_soc_pct`, `inverter_temp_c`, `working_mode_raw`
- Energy totals: `pv_energy_today_kwh`, `load_energy_today_kwh`
- **Stored in**: `adapter.last_tel.extra` (updated every few seconds)

**Settings Registers** (Read on-demand, NOT during polling):
- Grid settings: `grid_voltage_high_v`, `grid_voltage_low_v`, `grid_frequency_hz`, `grid_peak_shaving_power_w`
- Battery settings: `battery_type`, `battery_capacity_ah`, `battery_max_charge_current_a`, `battery_absorption_voltage_v`
- Work mode: `hybrid_work_mode`, `grid_charge`, `generator_charge_enabled`
- TOU windows: `charge_start_time_1`, `charge_power_1`, `discharge_start_time_1`, etc.
- **Stored in**: `solar_app.settings_cache[inverter_id]` (read on-demand)

### Identifying Settings Registers

**Criteria for Settings Registers**:
1. Configuration values that change infrequently
2. User-configurable parameters
3. Not needed for real-time monitoring
4. Typically have `rw: "RW"` in register map (writable)
5. Examples: voltage limits, capacity thresholds, time windows, mode selections

**Implementation Note**:
- Adapter polling should skip settings registers
- Settings registers should be read only when:
  - Settings API endpoint is called
  - Settings are updated (re-read changed registers)

## Data Availability & Register Mapping

### Specification Data
**Source:** Config + Telemetry registers (read-only, can be cached)
- `adapter.type` from config → Driver name
- `device_serial_number` register → Serial number
- `protocol_version_raw` register → Protocol version
- `rated_power_w` register → Max AC output power
- `mppt_count` or similar → MPPT connections
- `parallel_enabled` or similar → Parallel status
- `modbus_address` register → Modbus number

**Status:** ✅ Available in register maps
**Cache Strategy:** Can be cached in settings cache (read once, rarely changes)

### Grid Settings Data
**Source:** Settings registers (from register maps, NOT in polling)
- Grid voltage high/low limits
- Grid frequency settings
- Grid peak shaving settings

**Status:** ⚠️ Need to verify specific register IDs in register maps
**Cache Strategy:** Read on-demand, cache in settings cache

### Auxiliary/Generator Settings
**Source:** Settings registers (from register maps, NOT in polling)
- Generator port usage
- Generator charge settings
- Generator peak shaving
- Generator start/stop capacity

**Status:** ⚠️ Need to verify specific register IDs in register maps
**Cache Strategy:** Read on-demand, cache in settings cache

### Battery Type & Charging Settings
**Source:** Settings registers (from register maps, NOT in polling)
- Battery type, capacity, operation mode
- Charge/discharge currents
- Voltage settings (float, absorption, equalization)

**Status:** ✅ Available in register maps (battery_type, battery_capacity_ah, battery_max_charge_current_a, etc.)
**Cache Strategy:** Read on-demand, cache in settings cache

### Work Mode Settings
**Source:** Settings registers (from register maps, NOT in polling)
- Work mode, grid charge, generator charge
- Capacity thresholds

**Status:** ⚠️ Need to verify specific register IDs in register maps
**Cache Strategy:** Read on-demand, cache in settings cache

## Implementation Details

### Register Reading Strategy

#### Operational Registers (Polled Regularly)
- **Read during polling**: Power, voltage, current, SOC, temperature, etc.
- **Stored in**: `adapter.last_tel.extra` (updated every few seconds)
- **Purpose**: Real-time monitoring and telemetry

#### Settings Registers (Read On-Demand)
- **NOT read during polling**: Settings registers are excluded from regular polling
- **Read on-demand**: Only when settings page is accessed or section is requested
- **Stored in**: Separate settings cache (not in `adapter.last_tel.extra`)
- **Purpose**: Configuration values that change infrequently

### Settings Cache Strategy

#### Separate Settings Cache
- **Cache Location**: Separate in-memory cache (e.g., `solar_app.settings_cache[inverter_id]`)
- **Cache Structure**: Dictionary organized by section (grid, battery, work_mode, etc.)
- **Cache Lifetime**: 
  - **Expiration Time**: 1 hour (3600 seconds)
  - **Timestamp Tracking**: Each cached section includes a timestamp of when it was cached
  - **Cache Invalidation**: Cache expires after 1 hour, requiring re-read from inverter
- **Cache Invalidation Triggers**:
  1. **Time-based**: Cache entry older than 1 hour → Expired → Re-read from inverter
  2. **Update-based**: Settings are updated → Cache invalidated for that section → Re-read changed registers
  3. **Manual**: System restart or manual cache clear

#### Cache Update Flow
1. **First Access**: 
   - GET endpoint called → Check cache → Cache miss → Read registers from inverter → Store in cache with timestamp → Return
2. **Subsequent Access (Cache Valid)**:
   - GET endpoint called → Check cache → Cache hit → Check timestamp → Not expired (< 1 hour) → Return cached values
3. **Subsequent Access (Cache Expired)**:
   - GET endpoint called → Check cache → Cache hit → Check timestamp → Expired (>= 1 hour) → Read registers from inverter → Update cache with new timestamp → Return
4. **After Update**:
   - POST endpoint → Write to inverter → Re-read updated registers → Update cache for changed registers with new timestamp → Return updated values

### Register Refresh After Save
After saving settings via POST endpoint:
1. **Write to Inverter**: Use `adapter.handle_command()` or `adapter.write_by_ident()`
2. **Re-read Only Changed Registers**: Use `adapter.read_by_ident()` for each changed register
   - Read back immediately after write to confirm value was accepted
   - Use read-back value (not the written value) to ensure accuracy
   - Only re-read registers that were actually changed (not all settings)
3. **Update Settings Cache**: Update settings cache with read-back values
   - Update only the changed registers in cache
   - Keep other cached settings unchanged
4. **Save to Database**: Save updated values to database via `solar_app.logger.set_config()`
5. **Republish MQTT**: Republish updated telemetry via MQTT if available (optional, settings may not need MQTT)
6. **Return Updated Data**: Return refreshed values in API response

### Data Caching Strategy

#### Two-Tier Caching System

**Tier 1: Operational Data Cache** (`adapter.last_tel.extra`)
- **Content**: Real-time operational registers (power, voltage, SOC, etc.)
- **Update Frequency**: Every few seconds (during polling)
- **Purpose**: Telemetry and monitoring
- **Excludes**: Settings registers

**Tier 2: Settings Cache** (`solar_app.settings_cache[inverter_id]`)
- **Content**: Configuration/settings registers
- **Update Frequency**: On-demand (when settings page accessed)
- **Update Trigger**: After settings are changed
- **Expiration**: 1 hour (3600 seconds)
- **Purpose**: Settings management
- **Structure**: 
  ```python
  {
    "inverter_id": {
      "specification": {
        "data": {...},
        "timestamp": 1234567890.0  # Unix timestamp
      },
      "grid_settings": {
        "data": {...},
        "timestamp": 1234567890.0
      },
      "battery_type": {
        "data": {...},
        "timestamp": 1234567890.0
      },
      "battery_charging": {
        "data": {...},
        "timestamp": 1234567890.0
      },
      "work_mode": {
        "data": {...},
        "timestamp": 1234567890.0
      },
      "work_mode_detail": {
        "data": {...},
        "timestamp": 1234567890.0
      },
      "auxiliary": {
        "data": {...},
        "timestamp": 1234567890.0
      },
      "tou_windows": {
        "data": {...},
        "timestamp": 1234567890.0
      }
    }
  }
  ```

#### Cache Benefits
- **Efficiency**: Settings not read during every poll (only when needed)
- **Performance**: Fast response times (cache hit = no inverter read)
- **Accuracy**: Read-back after write ensures cache matches inverter state
- **Reduced Load**: Minimal inverter communication (only on-demand and after updates)

### Frontend Data Flow
1. **Page Load/Inverter Selection**: 
   - Frontend calls GET endpoints for all sections
   - API checks settings cache:
     - Cache miss → Read from inverter → Cache with timestamp → Return
     - Cache hit + valid (< 1 hour) → Return cached values
     - Cache hit + expired (>= 1 hour) → Read from inverter → Update cache with new timestamp → Return
2. **User Edits Settings**:
   - Frontend calls POST endpoint with changed values
   - API writes to inverter → Re-reads changed registers → Updates cache with new timestamp → Returns updated values
3. **After Save**:
   - Frontend may call GET endpoint again to refresh UI
   - API returns from updated cache (fresh timestamp, no inverter read needed)
4. **After 1 Hour**:
   - Next GET request will detect expired cache → Re-read from inverter → Update cache → Return fresh data

### Missing Fields Handling
- If a register doesn't exist for an inverter type:
  - Show field as "N/A" or "Not Available"
  - Disable edit for that field
  - Don't hide the entire card (show available fields only)

## Proposed Implementation Plan

### Phase 1: Foundation & API
1. ✅ **Requirements Finalization** (this document)
2. ⏳ **Settings Cache Implementation**: 
   - Create separate settings cache structure in SolarApp
   - Implement cache get/set/clear methods
   - Add timestamp tracking for each cached section
   - Implement cache expiration logic (1 hour expiry)
   - Ensure settings registers are excluded from polling
3. ⏳ **API Enhancement**: 
   - Add `adapter_type` to capabilities endpoint
   - Create GET endpoints for each settings section:
     - Check cache → Validate timestamp → Return cached or re-read from inverter
   - Create POST endpoints for each settings section:
     - Write + re-read changed registers + update cache with new timestamp
   - Implement on-demand register reading (not during polling)
4. ⏳ **Register Mapping Verification**: 
   - Verify all required registers exist in register maps
   - Document register IDs for each settings section
   - Identify which registers are settings (exclude from polling)
   - Handle missing registers gracefully
5. ⏳ **Component Structure**: Create folder structure and base components

### Phase 2: Common Cards
4. ⏳ **SpecificationCard**: Implement specification display (read-only)
5. ⏳ **GridSettingsCard**: Implement grid settings with edit functionality
6. ⏳ **AuxiliarySettingsCard**: Implement auxiliary/generator settings with edit
7. ⏳ **BatteryTypeCard**: Implement battery type settings with edit
8. ⏳ **BatteryChargingCard**: Implement battery charging settings with edit
9. ⏳ **WorkModeCard**: Implement work mode settings with edit
10. ⏳ **WorkModeDetailCard**: Implement work mode detail settings with edit
11. ⏳ **InverterControlsCard**: Refactor existing controls into card format

### Phase 3: Type-Specific Cards
12. ⏳ **SenergyTOUCard**: Implement Senergy TOU (3+3 windows)
13. ⏳ **PowdriveTOUCard**: Implement Powdrive TOU (6 bidirectional) - reusable for Sol-Ark/Deye

### Phase 4: Settings Pages
14. ⏳ **InverterConfigWizard**: Refactor to router component with data loading
15. ⏳ **SenergySettingsPage**: 
   - Load all data on mount/inverter selection
   - Compose Senergy-specific cards
   - Pass data to cards as props
   - Handle data refresh after saves
16. ⏳ **PowdriveSettingsPage**: 
   - Load all data on mount/inverter selection
   - Compose Powdrive-specific cards
   - Pass data to cards as props
   - Handle data refresh after saves

### Phase 5: Testing & Polish
17. ⏳ **Testing**: Test with Senergy and Powdrive inverters
18. ⏳ **Theme Support**: Ensure all cards support dark/light themes
19. ⏳ **Responsive Design**: Test on mobile/tablet/desktop
20. ⏳ **Documentation**: Update user docs if needed

