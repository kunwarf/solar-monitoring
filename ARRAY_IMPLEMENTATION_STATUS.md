# Array System Implementation - Current Status

## ✅ Completed Components

### 1. Configuration & Models
- ✅ **Config Schema** (`solarhub/config.py`): Added `ArrayConfig`, `BatteryPackConfig`, `BatteryPackAttachment`
- ✅ **Domain Models** (`solarhub/array_models.py`): Created `Array`, `BatteryPack`, `ArrayTelemetry`, `BatteryPackTelemetry`
- ✅ **Telemetry Model** (`solarhub/models.py`): Added `array_id` field
- ✅ **Config Migration** (`solarhub/config_migration.py`): Backward compatibility helper

### 2. Database
- ✅ **Schema Migration** (`solarhub/database_migrations.py`): Creates all new tables
- ✅ **Logger Updates** (`solarhub/logging/logger.py`): 
  - Added `array_id` to `insert_sample()`
  - Added `insert_array_sample()` method
  - Auto-runs migration on startup

### 3. Data Aggregation
- ✅ **Array Aggregator** (`solarhub/array_aggregator.py`): 
  - Aggregates inverter telemetry per array
  - Calculates energy-weighted SOC across packs
  - Provides per-inverter and per-pack breakdowns

### 4. Device Adapters
- ✅ **PowdriveAdapter** (`solarhub/adapters/powdrive.py`): Includes `array_id` in telemetry
- ✅ **SenergyAdapter** (`solarhub/adapters/senergy.py`): Includes `array_id` in telemetry

### 5. API Server
- ✅ **GET /api/arrays**: List all arrays with membership
- ✅ **GET /api/arrays/{array_id}/now**: Consolidated telemetry for array
- ✅ **GET /api/now**: Updated to support `array_id` filter parameter

### 6. Application Integration
- ✅ **Main** (`solarhub/main.py`): 
  - Migrates config on load
  - Backfills `array_id` in database
- ✅ **SolarApp** (`solarhub/app.py`):
  - Tracks arrays and packs
  - Aggregates telemetry per array
  - Publishes array telemetry to MQTT
  - Stores array samples in database

## 🚧 Remaining Work

### 1. Additional API Endpoints
- ⏳ `GET /api/arrays/{array_id}/forecast` - Per-array forecast
- ⏳ `GET /api/arrays/{array_id}/scheduler` - Scheduler state
- ⏳ `POST /api/arrays/{array_id}/attach_pack` - Attach/move pack
- ⏳ `POST /api/arrays/{array_id}/scheduler/override` - Temporary override
- ⏳ Update `/api/devices` to include arrays and packs

### 2. Smart Scheduler
- ⏳ Instantiate one scheduler per active array
- ⏳ Handle multi-pack allocation
- ⏳ Respect per-pack limits (max_charge_kw, max_discharge_kw)
- ⏳ Distribute power across packs (headroom, health, cycle aging)
- ⏳ Support per-array TOU windows and policies
- ⏳ Fan out commands to inverters and packs

### 3. MQTT/Home Assistant
- ⏳ Publish array-level entities with HA discovery
- ⏳ Publish pack-level entities with HA discovery
- ⏳ Add device relationships (array as parent)
- ⏳ Update topic structure: `<base>/arrays/<array_id>/state`, `<base>/packs/<pack_id>/state`

## 🎯 What Works Now

1. **Configuration**: Arrays, battery packs, and attachments can be defined in `config.yaml`
2. **Backward Compatibility**: Legacy configs automatically get a default array
3. **Database**: All new tables created, existing data can be backfilled
4. **Telemetry**: All adapters include `array_id` in telemetry
5. **Aggregation**: Array telemetry is aggregated and stored
6. **API**: Basic array endpoints are available
7. **MQTT**: Array telemetry is published to MQTT

## 📝 Example Usage

### Configuration
```yaml
arrays:
  - id: array_north
    name: "North Roof"
    inverter_ids: [senergy_1, powdrive_1]

inverters:
  - id: senergy_1
    array_id: array_north  # Required
    adapter:
      type: senergy
      # ...

battery_packs:
  - id: pytes_pack_A
    name: "Pytes 10kWh Pack A"
    nominal_kwh: 10.24
    max_charge_kw: 5
    max_discharge_kw: 5

attachments:
  - pack_id: pytes_pack_A
    array_id: array_north
    attached_since: "2025-10-01T00:00:00+05:00"
```

### API Calls
```bash
# List all arrays
GET /api/arrays

# Get array telemetry
GET /api/arrays/array_north/now

# Get all inverters (filtered by array)
GET /api/now?array_id=array_north
```

### MQTT Topics
```
solar/fleet/arrays/array_north/state  # Array telemetry
solar/fleet/inverters/senergy_1/regs  # Per-inverter (unchanged)
```

## 🔄 Migration Path

1. **On first startup**: Config is automatically migrated if no arrays defined
2. **Database**: Schema is automatically updated, existing data backfilled
3. **No breaking changes**: All existing functionality continues to work
4. **Gradual adoption**: Can add arrays incrementally

## 📊 Progress Summary

- **Core Infrastructure**: ✅ 100% Complete
- **Data Flow**: ✅ 100% Complete  
- **API Endpoints**: 🟡 50% Complete (basic endpoints done, advanced pending)
- **Scheduler Integration**: ⏳ 0% Complete
- **HA/MQTT Discovery**: ⏳ 0% Complete

**Overall**: ~70% Complete

