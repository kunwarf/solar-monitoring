# Complete Hierarchy Implementation Plan

## Overview

This document outlines the implementation plan for migrating to the new database-driven hierarchy structure as defined in `COMPLETE_HIERARCHY_STRUCTURE.md`.

## Implementation Phases

### Phase 1: Database Schema & Migrations (Foundation)
**Priority: CRITICAL**

1. **Create New Tables**
   - `systems` table
   - `adapter_base` table
   - `adapters` table
   - `inverters` table
   - `battery_arrays` table
   - `battery_array_attachments` table
   - `batteries` table
   - `battery_cells` table
   - `battery_pack_adapters` table
   - `meters` table
   - Aggregated tables: `array_hourly_energy`, `system_hourly_energy`, `battery_bank_hourly`, `array_daily_summary`, `system_daily_summary`, `battery_bank_daily`

2. **Add Foreign Keys**
   - Add `system_id` to all existing tables
   - Add `battery_array_id` to `battery_packs`
   - Add `adapter_id` to `inverters` and `meters`
   - Update all sample tables with proper foreign keys

3. **Data Migration (Automatic on Startup)**
   - **Production Data Migration**:
     - Migrate existing `arrays` data to new structure (add `system_id`)
     - Migrate existing `battery_packs` data (add `battery_array_id`, `system_id`)
     - Migrate existing `inverter_config` to `inverters` table
     - Migrate existing `energy_samples` (add `system_id`, `array_id`)
     - Migrate existing `battery_bank_samples` (add `system_id`, `battery_array_id`)
     - Migrate existing `meter_samples` (add `system_id`)
     - Backfill `system_id` in all existing tables
     - Create default system if none exists
   - **config.yaml Migration**:
     - Read `config.yaml` and populate new catalog tables
     - Extract adapter configs and populate `adapters` table
     - Link devices to adapters via foreign keys
   - **Migration Safety**:
     - Create database backup before migration (optional but recommended)
     - Make migration idempotent (safe to run multiple times)
     - Log all migration steps for debugging

**Files to Create/Modify:**
- `solarhub/database_migrations.py` - Add new migration functions:
  - `migrate_to_hierarchy_schema()` - Create all new tables
  - `migrate_config_yaml_to_database()` - Migrate config.yaml to database
  - `migrate_production_data()` - Migrate existing production data
  - `backfill_system_ids()` - Backfill system_id in all tables
  - `create_default_system()` - Create default system if none exists
- `solarhub/logging/logger.py` - Update `_init()` to call migration functions
- `solarhub/config_manager.py` - Add config.yaml to database migration logic

---

### Phase 2: Object-Oriented Hierarchy Classes
**Priority: HIGH**

Create Python classes representing the hierarchy:

1. **Base Classes**
   - `BaseDevice` - Abstract base for all devices
   - `BaseArray` - Abstract base for arrays

2. **System Classes**
   - `System` - Represents a system (top-level)
   - `InverterArray` - Represents an inverter array
   - `BatteryArray` - Represents a battery array
   - `Inverter` - Represents an individual inverter
   - `BatteryPack` - Represents a battery pack
   - `Battery` - Represents an individual battery unit
   - `BatteryCell` - Represents a battery cell
   - `Meter` - Represents an energy meter

3. **Adapter Classes**
   - `AdapterBase` - Represents adapter_base table entry
   - `AdapterInstance` - Represents adapters table entry

4. **Telemetry Management**
   - Each device class maintains its own telemetry cache
   - `TelemetryManager` - Centralized telemetry storage and retrieval

**Files to Create:**
- `solarhub/hierarchy/__init__.py`
- `solarhub/hierarchy/base.py` - Base classes
- `solarhub/hierarchy/system.py` - System class
- `solarhub/hierarchy/arrays.py` - Array classes
- `solarhub/hierarchy/devices.py` - Device classes (Inverter, BatteryPack, Meter)
- `solarhub/hierarchy/batteries.py` - Battery and Cell classes
- `solarhub/hierarchy/adapters.py` - Adapter classes
- `solarhub/hierarchy/telemetry.py` - Telemetry management

---

### Phase 3: Configuration Loading from Database
**Priority: HIGH**

1. **config.yaml to Database Migration (Initial Implementation)**
   - Read `config.yaml` on startup
   - Parse hierarchy structure from `config.yaml`
   - Migrate to database tables:
     - `home` → `systems` table
     - `arrays` → `arrays` table (with `system_id`)
     - `inverters` → `inverters` table (with `system_id`, `array_id`, `adapter_id`)
     - `battery_bank_arrays` → `battery_arrays` table (with `system_id`)
     - `battery_banks` → `battery_packs` table (with `battery_array_id`, `system_id`)
     - `battery_bank_array_attachments` → `battery_array_attachments` table
     - `meters` → `meters` table (with `system_id`, `adapter_id`)
     - Adapter configs → `adapters` and `adapter_base` tables
   - Auto-create default system/arrays if none exist in config

2. **Database Configuration Loader (Future)**
   - Load systems from `systems` table
   - Load arrays from `arrays` and `battery_arrays` tables
   - Load devices from `inverters`, `battery_packs`, `meters` tables
   - Load adapters from `adapters` and `adapter_base` tables
   - Build hierarchy objects from database

3. **Auto-Discovery Integration** ⏸️ DEFERRED
   - Will be implemented in a future phase

**Files to Create/Modify:**
- `solarhub/hierarchy/migrator.py` - Migrate config.yaml to database
- `solarhub/hierarchy/loader.py` - Database configuration loader (future)
- `solarhub/config_manager.py` - Update to use hierarchy migrator/loader

---

### Phase 4: Telemetry Logging Updates
**Priority: HIGH**

1. **Update Logger Methods**
   - Update `insert_energy_sample()` to include `system_id`
   - Update `insert_battery_bank_sample()` to include `system_id`, `battery_array_id`
   - Update `insert_meter_sample()` to include `system_id`
   - Add methods for new aggregated tables

2. **SOC Tracking**
   - **Priority**: Battery pack SOC if available, fallback to inverter SOC
   - Track SOC per battery pack (from battery adapter)
   - Fallback to inverter SOC if battery pack not available
   - Aggregate SOC for battery arrays (average of all packs in array)
   - Store SOC in aggregated tables (`battery_bank_hourly`, `battery_bank_daily`)
   - Update SOC calculation logic in telemetry processing

**Files to Modify:**
- `solarhub/logging/logger.py` - Update all logging methods
- `solarhub/energy_calculator.py` - Update to use new tables

---

### Phase 5: Runtime Object Building
**Priority: HIGH**

1. **Update SolarApp**
   - Replace current runtime object building with hierarchy classes
   - Load hierarchy from database
   - Build runtime objects from hierarchy classes
   - Maintain backward compatibility during transition

2. **Telemetry Polling**
   - Update polling loops to use hierarchy objects
   - Each device maintains its own telemetry
   - Aggregate telemetry at array/system levels

**Files to Modify:**
- `solarhub/app.py` - Update `_build_runtime_objects()`
- `solarhub/app.py` - Update polling methods

---

### Phase 6: API Layer Transformation
**Priority: MEDIUM**

#### 6.1 Update Existing Endpoints to Use New Hierarchy

1. **`/api/config`** - Return hierarchy from database
   - Load systems, arrays, devices from database
   - Return complete hierarchy structure
   - Include adapter information
   - Format: Match existing response structure for compatibility

2. **`/api/home/now`** - System-level telemetry
   - Use `system_id` from database
   - Aggregate data from all arrays in the system
   - Include system-level meters
   - Return structure:
     ```json
     {
       "system_id": "system",
       "system_name": "My Solar System",
       "timestamp": "2025-01-XX...",
       "telemetry": {
         "pv_power_w": 0,
         "load_power_w": 0,
         "battery_power_w": 0,
         "grid_power_w": 0,
         "battery_soc_pct": 0
       },
       "arrays": [...],
       "meters": [...],
       "daily_energy": {...},
       "financial_metrics": {...}
     }
     ```

3. **`/api/arrays/{id}/now`** - Array-level telemetry
   - Use `array_id` from database
   - Aggregate data from all inverters in the array
   - Include attached battery array data
   - Return structure:
     ```json
     {
       "array_id": "array1",
       "array_name": "Ground Floor",
       "system_id": "system",
       "timestamp": "2025-01-XX...",
       "telemetry": {...},
       "inverters": [...],
       "battery_array": {...}
     }
     ```

4. **`/api/battery/now`** - Battery pack telemetry
   - Use `pack_id` from database
   - Include `battery_array_id` and `system_id`
   - Return structure:
     ```json
     {
       "pack_id": "battery1",
       "pack_name": "Pylontech Battery Bank",
       "battery_array_id": "battery_array2",
       "system_id": "system",
       "timestamp": "2025-01-XX...",
       "telemetry": {...},
       "devices": [...],
       "cells": [...]
     }
     ```

5. **`/api/inverter/{id}/now`** - Individual inverter telemetry
   - Use `inverter_id` from database
   - Include `array_id` and `system_id`
   - Return structure:
     ```json
     {
       "inverter_id": "powdrive1",
       "inverter_name": "Powdrive",
       "array_id": "array2",
       "system_id": "system",
       "timestamp": "2025-01-XX...",
       "telemetry": {...}
     }
     ```

6. **`/api/meter/{id}/now`** - Individual meter telemetry
   - Use `meter_id` from database
   - Include `system_id` and `array_id` (if attached to array)
   - Return structure:
     ```json
     {
       "meter_id": "grid_meter_1",
       "meter_name": "IAMMeter",
       "system_id": "system",
       "array_id": null,
       "timestamp": "2025-01-XX...",
       "telemetry": {...}
     }
     ```

#### 6.2 New CRUD Endpoints for Hierarchy Management

1. **Systems Management**
   - `GET /api/systems` - List all systems
   - `GET /api/systems/{id}` - Get system details
   - `POST /api/systems` - Create new system
   - `PUT /api/systems/{id}` - Update system
   - `DELETE /api/systems/{id}` - Delete system

2. **Arrays Management**
   - `GET /api/arrays` - List all arrays (with system_id filter)
   - `GET /api/arrays/{id}` - Get array details
   - `POST /api/arrays` - Create new array
   - `PUT /api/arrays/{id}` - Update array
   - `DELETE /api/arrays/{id}` - Delete array

3. **Inverters Management**
   - `GET /api/inverters` - List all inverters (with system_id/array_id filters)
   - `GET /api/inverters/{id}` - Get inverter details
   - `POST /api/inverters` - Create new inverter
   - `PUT /api/inverters/{id}` - Update inverter
   - `DELETE /api/inverters/{id}` - Delete inverter

4. **Battery Arrays Management**
   - `GET /api/battery-arrays` - List all battery arrays
   - `GET /api/battery-arrays/{id}` - Get battery array details
   - `POST /api/battery-arrays` - Create new battery array
   - `PUT /api/battery-arrays/{id}` - Update battery array
   - `DELETE /api/battery-arrays/{id}` - Delete battery array

5. **Battery Packs Management**
   - `GET /api/battery-packs` - List all battery packs
   - `GET /api/battery-packs/{id}` - Get battery pack details
   - `POST /api/battery-packs` - Create new battery pack
   - `PUT /api/battery-packs/{id}` - Update battery pack
   - `DELETE /api/battery-packs/{id}` - Delete battery pack

6. **Battery Array Attachments Management**
   - `GET /api/battery-array-attachments` - List all attachments
   - `POST /api/battery-array-attachments` - Create attachment
   - `PUT /api/battery-array-attachments/{battery_array_id}/{inverter_array_id}` - Update attachment
   - `DELETE /api/battery-array-attachments/{battery_array_id}/{inverter_array_id}` - Delete attachment

7. **Meters Management**
   - `GET /api/meters` - List all meters
   - `GET /api/meters/{id}` - Get meter details
   - `POST /api/meters` - Create new meter
   - `PUT /api/meters/{id}` - Update meter
   - `DELETE /api/meters/{id}` - Delete meter

8. **Adapters Management**
   - `GET /api/adapters` - List all adapter instances
   - `GET /api/adapters/{id}` - Get adapter details
   - `GET /api/adapter-base` - List all adapter base types
   - `POST /api/adapters` - Create new adapter instance
   - `PUT /api/adapters/{id}` - Update adapter instance
   - `DELETE /api/adapters/{id}` - Delete adapter instance

#### 6.3 Historical Data Endpoints (Updated)

1. **`/api/energy/hourly`** - Hourly energy data
   - Support filtering by `system_id`, `array_id`, `inverter_id`
   - Return data from new aggregated tables

2. **`/api/energy/daily`** - Daily energy summaries
   - Support filtering by `system_id`, `array_id`, `inverter_id`
   - Return data from new aggregated tables

3. **`/api/battery/hourly`** - Battery hourly energy
   - Support filtering by `system_id`, `battery_array_id`, `pack_id`
   - Return data from `battery_bank_hourly` table

4. **`/api/battery/daily`** - Battery daily summaries
   - Support filtering by `system_id`, `battery_array_id`, `pack_id`
   - Return data from `battery_bank_daily` table

#### 6.4 Response Structure Transformation

**All endpoints should return:**
- `system_id` - System identifier
- `array_id` - Array identifier (if applicable)
- `device_id` - Device identifier
- Hierarchy context (parent relationships)
- Timestamp information
- Telemetry data with proper units

**Error Responses:**
- 404 if system/array/device not found
- 400 for invalid requests
- 500 for server errors
- Include error details and hierarchy context

#### 6.5 Endpoint Transformation Mapping

| Current Endpoint | New Structure | Changes Required |
|-----------------|---------------|------------------|
| `/api/home/now` | Use `system_id` from database | Load system from DB, aggregate from arrays |
| `/api/arrays/{id}/now` | Use `array_id` from database | Include `system_id` in response |
| `/api/battery/now` | Use `pack_id` from database | Include `battery_array_id`, `system_id` |
| `/api/meter/now` | Use `meter_id` from database | Include `system_id`, `array_id` (if attached) |
| `/api/inverters` | Load from `inverters` table | Include `array_id`, `system_id` |
| `/api/config` | Load from database tables | Return complete hierarchy from DB |
| `/api/arrays` | Load from `arrays` table | Include `system_id` |
| `/api/energy/hourly` | Query new aggregated tables | Filter by `system_id`, `array_id` |
| `/api/energy/daily` | Query new aggregated tables | Filter by `system_id`, `array_id` |
| `/api/arrays/{id}/energy/hourly` | Query `array_hourly_energy` | Include `system_id` |
| `/api/arrays/{id}/energy/daily` | Query `array_daily_summary` | Include `system_id` |

#### 6.6 Helper Functions to Create

1. **Hierarchy Query Helpers**
   - `get_system_by_id(system_id)` - Load system from database
   - `get_array_by_id(array_id)` - Load array with system context
   - `get_inverter_by_id(inverter_id)` - Load inverter with array/system context
   - `get_battery_pack_by_id(pack_id)` - Load battery pack with array/system context
   - `get_meter_by_id(meter_id)` - Load meter with system context
   - `get_battery_array_by_id(battery_array_id)` - Load battery array with system context

2. **Telemetry Aggregation Helpers**
   - `aggregate_system_telemetry(system_id)` - Aggregate all arrays in system
   - `aggregate_array_telemetry(array_id)` - Aggregate all inverters in array
   - `aggregate_battery_array_telemetry(battery_array_id)` - Aggregate all packs in battery array
   - `get_soc_for_system(system_id)` - Get SOC (battery pack if available, else inverter)

3. **Historical Data Helpers**
   - `get_hourly_energy(system_id, array_id, inverter_id, date_range)` - Query aggregated tables
   - `get_daily_summary(system_id, array_id, inverter_id, date_range)` - Query aggregated tables
   - `get_battery_hourly_energy(battery_array_id, pack_id, date_range)` - Query battery aggregated tables
   - `get_battery_daily_summary(battery_array_id, pack_id, date_range)` - Query battery aggregated tables

**Files to Create/Modify:**
- `solarhub/api_server.py` - Complete rewrite of endpoints
- `solarhub/api_helpers.py` - New file for hierarchy query helpers
- `solarhub/api_aggregation.py` - New file for telemetry aggregation helpers

---

### Phase 7: Aggregation & Energy Calculation
**Priority: MEDIUM**

1. **Update Aggregators**
   - Update `ArrayAggregator` to use new hierarchy
   - Create `SystemAggregator` for system-level aggregation
   - Create `BatteryArrayAggregator` for battery array aggregation

2. **Update Energy Calculator**
   - Use new aggregated tables
   - Calculate hourly/daily summaries per hierarchy level
   - Backfill aggregated data from samples

**Files to Modify:**
- `solarhub/array_aggregator.py` - Update for new structure
- `solarhub/energy_calculator.py` - Update for new tables

---

## Decisions Made (Final)

1. **Implementation Approach**: ✅ One phase at a time (incremental)
2. **Backward Compatibility**: ❌ Not required - can break compatibility
3. **Starting Phase**: ✅ Phase 1 (Database Schema)
4. **Auto-Discovery**: ⏸️ Deferred for now (will be implemented later)
5. **Configuration Source**: ✅ Read from `config.yaml` to build hierarchy for DB (for now)
6. **Data Migration**: ✅ Automatic on startup
7. **Production Data**: ✅ Must be migrated to new structure
8. **Testing**: ✅ Manual testing by user
9. **SOC Tracking**: ✅ Battery pack SOC if available, fallback to inverter SOC
10. **Database Backup**: ✅ User has taken backup
11. **Migration Safety**: ✅ Should be idempotent (safe to run multiple times)

---

## Implementation Order (Confirmed)

1. **Phase 1** - Database Schema & Migrations (Foundation) ✅ START HERE
2. **Phase 2** - Object-Oriented Classes (Structure)
3. **Phase 3** - Configuration Loading from config.yaml (Data Flow)
4. **Phase 4** - Telemetry Logging Updates (Data Collection)
5. **Phase 5** - Runtime Object Building (Integration)
6. **Phase 6** - API Layer Updates (Interface)
7. **Phase 7** - Aggregation & Energy Calculation (Analysis)

**Note**: Auto-discovery integration is deferred and will be implemented in a future phase.

---

## Estimated Complexity

- **Phase 1**: Medium (Database schema is well-defined)
- **Phase 2**: High (New class hierarchy needs careful design)
- **Phase 3**: Medium (Configuration loading logic exists, needs refactoring)
- **Phase 4**: Medium (Logging methods need updates)
- **Phase 5**: High (Core application logic changes)
- **Phase 6**: Medium (API endpoints need updates)
- **Phase 7**: Medium (Aggregation logic needs updates)

**Total Estimated Effort**: Large (2-3 weeks of focused development)

---

## Next Steps

1. ✅ Review and update implementation plan (COMPLETED)
2. ✅ All questions answered (COMPLETED)
3. ✅ API layer transformation plan created (COMPLETED)
4. ✅ SOC tracking decision made (COMPLETED)
5. ⏳ **READY FOR IMPLEMENTATION** - Awaiting approval to start Phase 1
6. Start with Phase 1 (Database Schema & Migrations)
7. Create database migration script
8. Implement config.yaml to database migration
9. Test migration on development database
10. Proceed with subsequent phases incrementally

## Phase 1 Detailed Tasks

### Task 1.1: Create New Database Tables
- [ ] Create `systems` table
- [ ] Create `adapter_base` table
- [ ] Create `adapters` table
- [ ] Create `inverters` table
- [ ] Create `battery_arrays` table
- [ ] Create `battery_array_attachments` table
- [ ] Create `batteries` table
- [ ] Create `battery_cells` table
- [ ] Create `battery_pack_adapters` table
- [ ] Create `meters` table
- [ ] Create aggregated tables (`array_hourly_energy`, `system_hourly_energy`, `battery_bank_hourly`, `array_daily_summary`, `system_daily_summary`, `battery_bank_daily`)

### Task 1.2: Add Foreign Keys to Existing Tables
- [ ] Add `system_id` to `arrays` table
- [ ] Add `system_id` to `battery_packs` table
- [ ] Add `battery_array_id` to `battery_packs` table
- [ ] Add `system_id` to `energy_samples` table
- [ ] Add `array_id` to `energy_samples` table (if missing)
- [ ] Add `system_id` to `array_samples` table
- [ ] Add `system_id` to `battery_bank_samples` table
- [ ] Add `battery_array_id` to `battery_bank_samples` table
- [ ] Add `system_id` to `battery_unit_samples` table
- [ ] Add `pack_id`, `battery_id` to `battery_unit_samples` table
- [ ] Add `system_id` to `battery_cell_samples` table
- [ ] Add `battery_id`, `pack_id` to `battery_cell_samples` table
- [ ] Add `system_id` to `meter_samples` table
- [ ] Add `system_id` to `hourly_energy` table
- [ ] Add `array_id` to `hourly_energy` table (if missing)
- [ ] Add `system_id` to `daily_summary` table
- [ ] Add `array_id` to `daily_summary` table (if missing)
- [ ] Add `system_id` to `meter_hourly_energy` table
- [ ] Add `system_id` to `meter_daily` table

### Task 1.3: Create Migration Functions
- [ ] Create `migrate_to_hierarchy_schema()` function
- [ ] Create `migrate_config_yaml_to_database()` function
- [ ] Create `migrate_production_data()` function
- [ ] Create `backfill_system_ids()` function
- [ ] Create `create_default_system()` function
- [ ] Add migration calls to `DataLogger.__init__()`

### Task 1.4: Create Indexes
- [ ] Create indexes for all new foreign keys
- [ ] Create indexes for aggregated tables
- [ ] Create indexes for query optimization

